import { Ionicons } from '@expo/vector-icons';
import { usePreventRemove } from '@react-navigation/native';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import React, { useEffect, useRef, useState } from 'react';
import { Alert, Animated, StyleSheet, Text, View } from 'react-native';

import { Bump, FadeIn, PulseDot } from '../components/animated';
import { ProgressRing, Sparkline } from '../components/charts';
import { Banner, Button, Card, Row, Screen } from '../components/ui';
import { ModelNotice } from '../components/workout';
import { colors, fonts, qualityColors, radius, spacing, type } from '../constants/theme';
import { useDevice } from '../context/DeviceContext';
import { useWorkoutSession } from '../hooks/useWorkoutSession';
import type { LiveStatus } from '../types/api';
import type { RootStackParamList } from '../types/navigation';
import { formatClock } from '../utils/format';

type Props = NativeStackScreenProps<RootStackParamList, 'LiveWorkout'>;

const PHASE_TEXT: Record<LiveStatus['movement_phase'], string> = {
  lifting: 'Lifting',
  lowering: 'Lowering',
  holding: 'Holding',
  resting: 'Resting',
};
const UA_TEXT: Record<LiveStatus['upper_arm_status'], { text: string; color: string }> = {
  stable: { text: 'Stable', color: colors.success },
  moving: { text: 'Moving', color: colors.warning },
  excessive_swing: { text: 'Swinging', color: colors.danger },
};

export default function LiveWorkoutScreen({ route, navigation }: Props) {
  const { exerciseId, exerciseName } = route.params;
  const { state: bleState, health, connected } = useDevice();
  const w = useWorkoutSession(exerciseId);
  const [elapsed, setElapsed] = useState(0);
  const [tension, setTension] = useState<number[]>([]);
  const finishing = useRef(false);

  const a = w.analysis;
  const live = a?.live ?? null;
  const active = w.phase === 'active' || w.phase === 'finishing';

  useEffect(() => {
    if (!w.startedAt || w.phase !== 'active') return;
    const t = setInterval(() => setElapsed((Date.now() - w.startedAt!) / 1000), 500);
    return () => clearInterval(t);
  }, [w.startedAt, w.phase]);

  useEffect(() => {
    const f = health.lastSample?.force_n;
    if (f === null || f === undefined) return;
    setTension((arr) => [...arr.slice(-79), f]);
  }, [health]);

  const finish = async (reason?: 'user_completed' | 'device_disconnected' | 'app_interrupted') => {
    if (finishing.current) return;
    finishing.current = true;
    const detail = await w.finish(reason);
    finishing.current = false;
    if (detail) navigation.replace('WorkoutResult', { sessionId: detail.id, justFinished: true });
  };

  // Leaving mid-workout asks for confirmation and closes the session on the server.
  usePreventRemove(w.phase === 'active', ({ data }) => {
    Alert.alert('End workout?', 'Your repetitions so far will be saved and analysed.', [
      { text: 'Keep training', style: 'cancel' },
      {
        text: 'End workout',
        style: 'destructive',
        onPress: async () => {
          const detail = await w.finish('app_interrupted');
          if (detail) navigation.dispatch(data.action);
        },
      },
    ]);
  });

  const latest = w.latestRep;
  const latestColors = latest ? qualityColors[latest.label] ?? qualityColors.unclassified : null;

  return (
    <Screen edges={['bottom']}>
      <Row style={{ justifyContent: 'space-between' }}>
        <View>
          <Text style={type.label}>Exercise</Text>
          <Text style={type.h2}>{exerciseName}</Text>
        </View>
        <View style={styles.timer}>
          <Ionicons name="time-outline" size={16} color={colors.primary} />
          <Text style={styles.timerText}>{formatClock(elapsed)}</Text>
        </View>
      </Row>

      {/* Connection & cloud status */}
      <Row style={{ gap: spacing.sm, marginTop: spacing.lg }}>
        <StatusChip
          ok={bleState === 'connected' && health.receiving}
          warn={bleState === 'reconnecting'}
          label={bleState === 'connected' ? (health.receiving ? `Sensors ${health.samplesPerSecond} Hz` : 'No sensor data') : bleState === 'reconnecting' ? 'Reconnecting' : 'Device offline'}
          icon="bluetooth"
        />
        <StatusChip
          ok={w.cloud === 'ok' || w.cloud === 'uploading'}
          warn={w.cloud === 'idle'}
          label={w.cloud === 'offline' ? `Offline · ${w.queued} queued` : w.cloud === 'error' ? 'Cloud error' : w.cloud === 'idle' ? 'Cloud AI ready' : 'Cloud AI live'}
          icon="cloud-outline"
        />
      </Row>

      {bleState !== 'connected' && w.phase === 'idle' ? (
        <Banner tone="warning" title="Device not connected" message="Connect your PhysioBand to record this workout." action="Connect" onAction={() => navigation.navigate('DeviceConnect')} style={{ marginTop: spacing.lg }} />
      ) : null}
      {bleState === 'reconnecting' && active ? (
        <Banner tone="warning" message={`Bluetooth connection to ${connected?.name ?? 'the device'} was lost. Reconnecting automatically...`} style={{ marginTop: spacing.lg }} />
      ) : null}
      {(bleState === 'disconnected' || bleState === 'idle') && active ? (
        <Banner tone="danger" title="Device disconnected" message="Reconnect from the Device tab, or end the workout to save what was recorded." action="End workout" onAction={() => void finish('device_disconnected')} style={{ marginTop: spacing.lg }} />
      ) : null}
      {w.cloudMessage ? <Banner tone={w.cloud === 'offline' ? 'warning' : 'info'} message={w.cloudMessage} style={{ marginTop: spacing.lg }} /> : null}
      {w.error ? <Banner tone="danger" message={w.error} style={{ marginTop: spacing.lg }} /> : null}

      {/* Rep counter */}
      <FadeIn style={{ alignItems: 'center', marginTop: spacing.xl }}>
        <ProgressRing value={a?.quality_score ?? 0} size={210} stroke={16} color={latestColors?.fg ?? colors.primary} track={colors.primarySoft}>
          <Bump trigger={a?.total_reps}>
            <Text style={styles.repCount}>{a?.total_reps ?? 0}</Text>
          </Bump>
          <Text style={styles.repLabel}>repetitions</Text>
          <Text style={styles.qualityText}>{a?.quality_score == null ? 'quality —' : `${Math.round(a.quality_score)}% quality`}</Text>
        </ProgressRing>
      </FadeIn>

      {/* Latest rep feedback */}
      <View style={{ marginTop: spacing.lg, minHeight: 86 }}>
        {latest && latestColors ? (
          <FeedbackCard key={latest.number} title={`Rep ${latest.number} · ${latest.label_display}`} message={latest.feedback} color={latestColors.fg} bg={latestColors.bg} icon={latestColors.icon} confidence={latest.confidence} />
        ) : (
          <Card style={{ alignItems: 'center' }}>
            <Text style={type.body}>{active ? 'Waiting for your first complete repetition...' : 'Press Start, then perform slow, controlled curls.'}</Text>
          </Card>
        )}
      </View>

      {/* Counts */}
      <Row style={{ gap: spacing.sm, marginTop: spacing.md }}>
        <CountTile label="Correct" value={a?.correct_reps ?? 0} color={colors.success} />
        <CountTile label="Incomplete" value={a?.incomplete_reps ?? 0} color={colors.warning} />
        <CountTile label="Too fast" value={a?.too_fast_reps ?? 0} color={colors.coral} />
        <CountTile label="Irregular" value={a?.irregular_reps ?? 0} color={colors.accent} />
      </Row>

      {/* Movement status */}
      <Card style={{ marginTop: spacing.md }}>
        <StatusLine icon="body-outline" label="Upper-arm movement" value={live ? UA_TEXT[live.upper_arm_status].text : health.upperArmOk ? 'Sensor OK' : 'No signal'} color={live ? UA_TEXT[live.upper_arm_status].color : health.upperArmOk ? colors.textSecondary : colors.danger} />
        <StatusLine icon="hand-left-outline" label="Forearm movement" value={live ? (live.forearm_status === 'active' ? `Active · ${Math.round(live.current_angle_deg)}°` : 'Still') : health.forearmOk ? 'Sensor OK' : 'No signal'} color={live?.forearm_status === 'active' ? colors.primary : colors.textSecondary} />
        <StatusLine icon="pulse-outline" label="Current movement" value={live ? PHASE_TEXT[live.movement_phase] : '—'} color={colors.text} />
        <StatusLine icon="speedometer-outline" label="Elbow range (last rep)" value={latest ? `${Math.round(latest.rom_deg)}°` : '—'} color={colors.text} last />
      </Card>

      {/* Band tension (measured directly from the load cell) */}
      <Card style={{ marginTop: spacing.md }}>
        <Row style={{ justifyContent: 'space-between' }}>
          <Text style={type.label}>Resistance-band tension</Text>
          <Text style={styles.tension}>{health.lastSample?.force_n == null ? '—' : `${health.lastSample.force_n.toFixed(1)} N`}</Text>
        </Row>
        <View style={{ marginTop: spacing.sm }}>
          <Sparkline values={tension} color={colors.accent} />
        </View>
        <Text style={type.caption}>Average during reps: {a?.avg_tension_n == null ? '—' : `${a.avg_tension_n.toFixed(1)} N`}</Text>
      </Card>

      {a ? (
        <View style={{ marginTop: spacing.md }}>
          <ModelNotice model={a.model} compact />
        </View>
      ) : null}

      <View style={{ marginTop: spacing.xl }}>
        {w.phase === 'idle' || w.phase === 'error' || w.phase === 'starting' ? (
          <Button title="Start" icon="play" onPress={() => void w.start()} loading={w.phase === 'starting'} disabled={bleState !== 'connected'} />
        ) : (
          <Button title="Finish workout" icon="stop-circle-outline" variant="danger" onPress={() => void finish()} loading={w.phase === 'finishing'} />
        )}
      </View>
    </Screen>
  );
}

function FeedbackCard({ title, message, color, bg, icon, confidence }: { title: string; message: string; color: string; bg: string; icon: string; confidence: number | null }) {
  const v = useRef(new Animated.Value(0)).current;
  useEffect(() => {
    Animated.spring(v, { toValue: 1, useNativeDriver: true, friction: 7 }).start();
  }, [v]);
  return (
    <Animated.View style={[styles.feedback, { backgroundColor: bg, opacity: v, transform: [{ translateY: v.interpolate({ inputRange: [0, 1], outputRange: [20, 0] }) }, { scale: v.interpolate({ inputRange: [0, 1], outputRange: [0.96, 1] }) }] }]}>
      <Ionicons name={icon as React.ComponentProps<typeof Ionicons>['name']} size={28} color={color} />
      <View style={{ flex: 1, marginLeft: spacing.md }}>
        <Text style={[styles.feedbackTitle, { color }]}>{title}</Text>
        <Text style={styles.feedbackText}>{message}</Text>
        {confidence !== null ? <Text style={type.caption}>Model confidence {Math.round(confidence * 100)}%</Text> : null}
      </View>
    </Animated.View>
  );
}

function StatusChip({ ok, warn, label, icon }: { ok: boolean; warn?: boolean; label: string; icon: React.ComponentProps<typeof Ionicons>['name'] }) {
  const color = ok ? colors.success : warn ? colors.warning : colors.danger;
  return (
    <View style={styles.chip}>
      <PulseDot color={color} size={7} active={ok} />
      <Ionicons name={icon} size={14} color={colors.textSecondary} />
      <Text style={styles.chipText} numberOfLines={1}>
        {label}
      </Text>
    </View>
  );
}

function CountTile({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <View style={[styles.count, { borderTopColor: color }]}>
      <Bump trigger={value}>
        <Text style={[styles.countValue, { color }]}>{value}</Text>
      </Bump>
      <Text style={styles.countLabel}>{label}</Text>
    </View>
  );
}

function StatusLine({ icon, label, value, color, last }: { icon: React.ComponentProps<typeof Ionicons>['name']; label: string; value: string; color: string; last?: boolean }) {
  return (
    <Row style={[styles.statusLine, last && { borderBottomWidth: 0 }]}>
      <Ionicons name={icon} size={18} color={colors.textMuted} />
      <Text style={[type.body, { flex: 1, marginLeft: 10 }]}>{label}</Text>
      <Text style={[styles.statusValue, { color }]}>{value}</Text>
    </Row>
  );
}

const styles = StyleSheet.create({
  timer: { flexDirection: 'row', alignItems: 'center', gap: 6, backgroundColor: colors.primaryTint, paddingHorizontal: 12, paddingVertical: 8, borderRadius: radius.pill },
  timerText: { fontFamily: fonts.bold, fontSize: 16, color: colors.primaryDark, fontVariant: ['tabular-nums'] },
  chip: { flex: 1, flexDirection: 'row', alignItems: 'center', gap: 4, backgroundColor: colors.surface, borderRadius: radius.pill, borderWidth: 1, borderColor: colors.border, paddingRight: 10, height: 36 },
  chipText: { flex: 1, fontFamily: fonts.semibold, fontSize: 12, color: colors.textSecondary },
  repCount: { fontFamily: fonts.extrabold, fontSize: 64, color: colors.text, letterSpacing: -2 },
  repLabel: { fontFamily: fonts.medium, fontSize: 13, color: colors.textMuted, marginTop: -6 },
  qualityText: { fontFamily: fonts.semibold, fontSize: 13, color: colors.primary, marginTop: 6 },
  feedback: { flexDirection: 'row', alignItems: 'center', padding: spacing.lg, borderRadius: radius.xl },
  feedbackTitle: { fontFamily: fonts.bold, fontSize: 15 },
  feedbackText: { fontFamily: fonts.regular, fontSize: 13, lineHeight: 19, color: colors.textSecondary, marginTop: 2 },
  count: { flex: 1, backgroundColor: colors.surface, borderRadius: radius.md, borderWidth: 1, borderColor: colors.border, borderTopWidth: 3, paddingVertical: spacing.md, alignItems: 'center' },
  countValue: { fontFamily: fonts.extrabold, fontSize: 22 },
  countLabel: { fontFamily: fonts.medium, fontSize: 11, color: colors.textMuted, marginTop: 2 },
  statusLine: { paddingVertical: 10, borderBottomWidth: 1, borderBottomColor: colors.border },
  statusValue: { fontFamily: fonts.semibold, fontSize: 14 },
  tension: { fontFamily: fonts.bold, fontSize: 18, color: colors.accent },
});

