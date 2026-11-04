import { Ionicons } from '@expo/vector-icons';
import type { NativeStackScreenProps } from '@react-navigation/native-stack';
import { LinearGradient } from 'expo-linear-gradient';
import React, { useCallback } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { FadeIn } from '../components/animated';
import { BarChart, ProgressRing } from '../components/charts';
import { Banner, Button, Card, EmptyState, LoadingState, Row, Screen, SectionHeader } from '../components/ui';
import { MetricLine, QualityBadge, StatTile } from '../components/workout';
import { colors, fonts, gradients, qualityColors, radius, shadow, spacing, type } from '../constants/theme';
import { useFocusData } from '../hooks/useAsync';
import { mlApi, workoutApi } from '../services/api/endpoints';
import type { RootStackParamList } from '../types/navigation';
import { formatDate, formatDuration, formatNumber, formatTime, qualityTone } from '../utils/format';

type Props = NativeStackScreenProps<RootStackParamList, 'WorkoutResult'>;

export default function WorkoutResultScreen({ route, navigation }: Props) {
  const { sessionId, justFinished } = route.params;
  const loader = useCallback(async () => {
    const [detail, model] = await Promise.all([workoutApi.get(sessionId), mlApi.modelInfo().catch(() => null)]);
    return { detail, model };
  }, [sessionId]);
  const { data, error, loading, refreshing, refresh } = useFocusData(loader);

  if (loading) {
    return (
      <Screen edges={['bottom']}>
        <LoadingState label="Loading results" />
      </Screen>
    );
  }
  if (error || !data) {
    return (
      <Screen edges={['bottom']}>
        <Banner tone="danger" title="Could not load workout" message={error ?? 'Unknown error'} action="Retry" onAction={refresh} />
      </Screen>
    );
  }

  const s = data.detail;
  const tone = qualityTone(s.quality_score);
  const demo = s.model_dataset_type === 'synthetic';

  return (
    <Screen edges={['bottom']} onRefresh={refresh} refreshing={refreshing}>
      <FadeIn>
        <LinearGradient colors={gradients.hero} start={{ x: 0, y: 0 }} end={{ x: 1, y: 1 }} style={styles.hero}>
          <View style={styles.heroDeco} />
          {justFinished ? (
            <Row style={{ marginBottom: spacing.md }}>
              <Ionicons name="trophy" size={18} color="#FDE68A" />
              <Text style={styles.done}>Workout complete</Text>
            </Row>
          ) : null}
          <Row>
            <ProgressRing value={s.quality_score ?? 0} size={128} stroke={12} color={colors.teal} track="rgba(255,255,255,0.14)">
              <Text style={styles.ringValue}>{s.quality_score == null ? '—' : `${Math.round(s.quality_score)}%`}</Text>
              <Text style={styles.ringLabel}>quality</Text>
            </ProgressRing>
            <View style={{ flex: 1, marginLeft: spacing.xl }}>
              <Text style={styles.heroTitle}>{s.exercise_name}</Text>
              <Text style={styles.heroLine}>
                {formatDate(s.start_time)} · {formatTime(s.start_time)}
              </Text>
              <Text style={styles.heroLine}>Duration {formatDuration(s.duration_s)}</Text>
              <View style={styles.toneChip}>
                <Text style={styles.toneText}>{s.status === 'active' ? 'In progress' : s.status === 'interrupted' ? 'Interrupted' : tone.label}</Text>
              </View>
            </View>
          </Row>
        </LinearGradient>
      </FadeIn>

      {s.status === 'interrupted' ? (
        <Banner
          tone="warning"
          message={
            s.end_reason === 'device_disconnected'
              ? 'The device disconnected during this workout. Results include the data received before the connection was lost.'
              : 'This workout ended before it was completed normally. Results include the data that was received.'
          }
          style={{ marginTop: spacing.lg }}
        />
      ) : null}
      {demo ? (
        <Banner tone="info" icon="flask" message="Classifications come from a DEMO model trained on synthetic data. They demonstrate the software pipeline and are not a validated exercise assessment." style={{ marginTop: spacing.lg }} />
      ) : null}
      {!s.classification_available && s.total_reps > 0 ? (
        <Banner tone="warning" message="The AI quality model was unavailable, so repetitions were counted but not classified." style={{ marginTop: spacing.lg }} />
      ) : null}

      <FadeIn delay={100}>
        <Row style={{ gap: spacing.sm + 2, marginTop: spacing.lg }}>
          <StatTile icon="layers-outline" label="Total reps" value={s.total_reps} />
          <StatTile icon="checkmark-done" label="Correct" value={s.correct_reps} tint={colors.success} bg={colors.successSoft} />
          <StatTile icon="close-circle-outline" label="Incorrect" value={s.incorrect_reps} tint={colors.coral} bg={colors.coralSoft} />
        </Row>
      </FadeIn>

      <SectionHeader title="Breakdown" />
      <Card>
        <MetricLine icon="remove-circle-outline" label="Incomplete repetitions" value={String(s.incomplete_reps)} />
        <MetricLine icon="speedometer-outline" label="Excessively fast repetitions" value={String(s.too_fast_reps)} />
        <MetricLine icon="pulse-outline" label="Irregular repetitions" value={String(s.irregular_reps)} />
        <MetricLine icon="git-commit-outline" label="Average band tension" value={formatNumber(s.avg_tension_n, 1, ' N')} />
        <MetricLine icon="trending-up-outline" label="Peak band tension" value={formatNumber(s.peak_tension_n, 1, ' N')} />
        <MetricLine icon="time-outline" label="Workout duration" value={formatDuration(s.duration_s)} />
        <MetricLine icon="analytics-outline" label="Sensor samples analysed" value={s.sample_count.toLocaleString()} />
      </Card>

      {s.feedback.length ? (
        <>
          <SectionHeader title="Range of motion per rep" />
          <Card>
            <BarChart data={s.feedback.map((f) => ({ label: String(f.repetition_number), value: f.rom_deg, color: (qualityColors[f.classification] ?? qualityColors.unclassified).fg }))} height={140} unit="°" />
            <Row style={{ flexWrap: 'wrap', gap: 10, marginTop: spacing.md }}>
              {(['correct', 'incomplete', 'too_fast', 'irregular'] as const).map((k) => (
                <Row key={k} style={{ gap: 5 }}>
                  <View style={{ width: 10, height: 10, borderRadius: 3, backgroundColor: qualityColors[k].fg }} />
                  <Text style={type.caption}>{{ correct: 'Correct', incomplete: 'Incomplete', too_fast: 'Too fast', irregular: 'Irregular' }[k]}</Text>
                </Row>
              ))}
            </Row>
          </Card>
        </>
      ) : null}

      <SectionHeader title="Feedback & suggestions" />
      <Card>
        {s.suggestions.length ? (
          s.suggestions.map((tip, i) => (
            <FadeIn key={i} index={i}>
              <Row style={{ alignItems: 'flex-start', marginBottom: i === s.suggestions.length - 1 ? 0 : spacing.md }}>
                <View style={styles.tipIcon}>
                  <Ionicons name="bulb-outline" size={16} color={colors.primary} />
                </View>
                <Text style={[type.body, { flex: 1 }]}>{tip}</Text>
              </Row>
            </FadeIn>
          ))
        ) : (
          <Text style={type.body}>No suggestions yet.</Text>
        )}
      </Card>

      <SectionHeader title="Repetitions" />
      {s.feedback.length === 0 ? (
        <Card>
          <EmptyState icon="hourglass-outline" title="No repetitions recorded" message="No complete repetition was detected in the received sensor data." />
        </Card>
      ) : (
        s.feedback.map((f, i) => (
          <FadeIn key={f.repetition_number} index={i}>
            <View style={styles.rep}>
              <View style={[styles.repNum, { backgroundColor: (qualityColors[f.classification] ?? qualityColors.unclassified).bg }]}>
                <Text style={[styles.repNumText, { color: (qualityColors[f.classification] ?? qualityColors.unclassified).fg }]}>{f.repetition_number}</Text>
              </View>
              <View style={{ flex: 1, marginLeft: spacing.md }}>
                <Row style={{ justifyContent: 'space-between' }}>
                  <QualityBadge label={f.classification} display={f.label_display} />
                  {f.confidence !== null ? <Text style={type.caption}>{Math.round(f.confidence * 100)}% conf.</Text> : null}
                </Row>
                <Text style={[type.body, { marginTop: 6 }]}>{f.message}</Text>
                <Text style={[type.caption, { marginTop: 4 }]}>
                  {f.duration_s.toFixed(1)} s · {Math.round(f.rom_deg)}° range · {f.avg_force_n.toFixed(1)} N
                </Text>
              </View>
            </View>
          </FadeIn>
        ))
      )}

      {data.model ? (
        <Text style={[type.caption, { marginTop: spacing.lg, textAlign: 'center' }]}>
          Model: {data.model.algorithm ?? 'n/a'} {data.model.model_version ? `v${data.model.model_version}` : ''} · {data.model.dataset_type ?? 'unknown'} data ·{' '}
          {data.model.validated ? 'validated' : 'not validated'}
        </Text>
      ) : null}

      <Button title="Back to dashboard" icon="home-outline" onPress={() => navigation.navigate('Main', { screen: 'Home' })} style={{ marginTop: spacing.xl }} />
      {justFinished ? (
        <Button title="New workout" icon="refresh" variant="secondary" onPress={() => navigation.replace('ExerciseSelection')} style={{ marginTop: spacing.md }} />
      ) : null}
    </Screen>
  );
}

const styles = StyleSheet.create({
  hero: { borderRadius: radius.xxl, padding: spacing.xl, overflow: 'hidden', ...shadow.raised },
  heroDeco: { position: 'absolute', width: 220, height: 220, borderRadius: 110, backgroundColor: 'rgba(255,255,255,0.07)', right: -70, top: -90 },
  done: { fontFamily: fonts.bold, fontSize: 14, color: '#FFFFFF', marginLeft: 6 },
  ringValue: { fontFamily: fonts.extrabold, fontSize: 28, color: '#FFFFFF' },
  ringLabel: { fontFamily: fonts.medium, fontSize: 11, color: 'rgba(255,255,255,0.8)' },
  heroTitle: { fontFamily: fonts.extrabold, fontSize: 22, color: '#FFFFFF', letterSpacing: -0.4 },
  heroLine: { fontFamily: fonts.medium, fontSize: 13, color: 'rgba(255,255,255,0.85)', marginTop: 3 },
  toneChip: { alignSelf: 'flex-start', backgroundColor: 'rgba(255,255,255,0.2)', borderRadius: radius.pill, paddingHorizontal: 10, paddingVertical: 4, marginTop: 10 },
  toneText: { fontFamily: fonts.semibold, fontSize: 12, color: '#FFFFFF' },
  tipIcon: { width: 28, height: 28, borderRadius: 9, backgroundColor: colors.primaryTint, alignItems: 'center', justifyContent: 'center', marginRight: 10 },
  rep: { flexDirection: 'row', backgroundColor: colors.surface, borderRadius: radius.lg, padding: spacing.md + 2, borderWidth: 1, borderColor: colors.border, marginBottom: spacing.sm + 2 },
  repNum: { width: 38, height: 38, borderRadius: 12, alignItems: 'center', justifyContent: 'center' },
  repNumText: { fontFamily: fonts.bold, fontSize: 15 },
});
