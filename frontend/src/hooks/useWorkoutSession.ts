/**
 * Live workout pipeline on the phone:
 *   BLE samples -> validation -> buffer -> batch (~1 s) -> POST /sensor-data -> live analysis
 *
 * Uploads are strictly sequential with an increasing batch_seq, so the backend can
 * de-duplicate retries. If the network fails, batches stay queued and are retried;
 * the UI shows that cloud analysis is unavailable instead of inventing results.
 */
import * as Haptics from 'expo-haptics';
import { useCallback, useEffect, useRef, useState } from 'react';

import { PROTOCOL } from '../constants/ble';
import { UPLOAD } from '../constants/config';
import { useDevice } from '../context/DeviceContext';
import { ApiError, errorMessage } from '../services/api/client';
import { workoutApi } from '../services/api/endpoints';
import { isUsableSample } from '../services/ble/protocol';
import type { AnalysisResult, EndReason, Repetition, SensorBatch, SensorSample, WorkoutDetail } from '../types/api';

export type WorkoutPhase = 'idle' | 'starting' | 'active' | 'finishing' | 'finished' | 'error';
export type CloudStatus = 'idle' | 'ok' | 'uploading' | 'offline' | 'error';

export function useWorkoutSession(exerciseId: string) {
  const { subscribeSamples, registeredDeviceId, state: bleState } = useDevice();
  const [phase, setPhase] = useState<WorkoutPhase>('idle');
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [latestRep, setLatestRep] = useState<Repetition | null>(null);
  const [cloud, setCloud] = useState<CloudStatus>('idle');
  const [cloudMessage, setCloudMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [queued, setQueued] = useState(0);
  const [samplesSent, setSamplesSent] = useState(0);
  const [startedAt, setStartedAt] = useState<number | null>(null);

  const buffer = useRef<SensorSample[]>([]);
  const queue = useRef<SensorBatch[]>([]);
  const seq = useRef(0);
  const uploading = useRef(false);
  const sessionRef = useRef<string | null>(null);
  const lastTs = useRef(-1);

  // Collect samples from BLE while the session is active.
  useEffect(() => {
    if (phase !== 'active') return;
    return subscribeSamples((samples) => {
      for (const s of samples) {
        // Validation: drop duplicates / out-of-order timestamps and samples with no usable sensor.
        if (s.timestamp_ms <= lastTs.current || !isUsableSample(s)) continue;
        lastTs.current = s.timestamp_ms;
        buffer.current.push(s);
      }
    });
  }, [phase, subscribeSamples]);

  const pump = useCallback(async () => {
    const id = sessionRef.current;
    if (!id || uploading.current) return;
    if (buffer.current.length) {
      while (buffer.current.length) {
        const samples = buffer.current.splice(0, UPLOAD.MAX_BATCH_SAMPLES);
        queue.current.push({ batch_seq: seq.current++, device_id: registeredDeviceId, protocol_version: PROTOCOL.VERSION, samples, analyze: true });
      }
      if (queue.current.length > UPLOAD.MAX_QUEUED_BATCHES) queue.current.splice(0, queue.current.length - UPLOAD.MAX_QUEUED_BATCHES);
    }
    if (!queue.current.length) return;

    uploading.current = true;
    setCloud((c) => (c === 'offline' ? c : 'uploading'));
    try {
      while (queue.current.length) {
        const batch = queue.current[0];
        // Only ask for analysis on the newest batch to avoid redundant work after an outage.
        const res = await workoutApi.uploadSensorData(id, { ...batch, analyze: queue.current.length === 1 });
        queue.current.shift();
        setSamplesSent(res.total_samples);
        if (res.analysis) {
          setAnalysis(res.analysis);
          if (res.analysis.new_reps.length) {
            const rep = res.analysis.new_reps[res.analysis.new_reps.length - 1];
            setLatestRep(rep);
            void Haptics.notificationAsync(
              rep.label === 'correct' ? Haptics.NotificationFeedbackType.Success : Haptics.NotificationFeedbackType.Warning,
            );
          }
        }
        setCloudMessage(res.analysis_error);
        setCloud('ok');
      }
    } catch (e) {
      if (e instanceof ApiError && e.isNetworkError) {
        setCloud('offline');
        setCloudMessage('Cloud AI analysis unavailable — no connection to the server. Sensor data is queued.');
      } else if (e instanceof ApiError && e.code === 'SESSION_NOT_ACTIVE') {
        queue.current = [];
        setCloud('error');
        setCloudMessage('This workout was closed on the server.');
      } else {
        // A rejected batch would block the queue forever; drop it and report.
        queue.current.shift();
        setCloud('error');
        setCloudMessage(errorMessage(e));
      }
    } finally {
      uploading.current = false;
      setQueued(queue.current.length + (buffer.current.length ? 1 : 0));
    }
  }, [registeredDeviceId]);

  useEffect(() => {
    if (phase !== 'active') return;
    const timer = setInterval(() => void pump(), UPLOAD.INTERVAL_MS);
    return () => clearInterval(timer);
  }, [phase, pump]);

  const start = useCallback(async () => {
    setPhase('starting');
    setError(null);
    try {
      const session = await workoutApi.start(exerciseId, registeredDeviceId);
      sessionRef.current = session.id;
      setSessionId(session.id);
      buffer.current = [];
      queue.current = [];
      seq.current = 0;
      lastTs.current = -1;
      setAnalysis(null);
      setLatestRep(null);
      setStartedAt(Date.now());
      setCloud('ok');
      setPhase('active');
      void Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
    } catch (e) {
      setError(errorMessage(e));
      setPhase('error');
    }
  }, [exerciseId, registeredDeviceId]);

  /** Flush remaining data (best effort) and close the session on the server. */
  const finish = useCallback(
    async (reason?: EndReason): Promise<WorkoutDetail | null> => {
      const id = sessionRef.current;
      if (!id) return null;
      setPhase('finishing');
      const endReason: EndReason = reason ?? (bleState === 'connected' ? 'user_completed' : 'device_disconnected');
      for (let i = 0; i < 3 && (buffer.current.length || queue.current.length); i++) {
        while (uploading.current) await new Promise((r) => setTimeout(r, 100));
        await pump();
      }
      try {
        const detail = await workoutApi.complete(id, endReason);
        setPhase('finished');
        void Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
        return detail;
      } catch (e) {
        setError(errorMessage(e));
        setPhase('active');
        return null;
      }
    },
    [bleState, pump],
  );

  return {
    phase,
    sessionId,
    analysis,
    latestRep,
    cloud,
    cloudMessage,
    error,
    queued,
    samplesSent,
    startedAt,
    start,
    finish,
  };
}
