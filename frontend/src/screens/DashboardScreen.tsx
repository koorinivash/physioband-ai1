import { Ionicons } from '@expo/vector-icons';
import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { LinearGradient } from 'expo-linear-gradient';
import React, { useCallback } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { FadeIn, PressableScale, PulseDot, Skeleton } from '../components/animated';
import { BarChart, ProgressRing } from '../components/charts';
import { LogoBadge } from '../components/Logo';
import { Banner, Button, Card, EmptyState, Row, Screen, SectionHeader } from '../components/ui';
import { ModelNotice, SessionRow, StatTile } from '../components/workout';
import { colors, fonts, gradients, radius, shadow, spacing, type } from '../constants/theme';
import { useAuth } from '../context/AuthContext';
import { useDevice } from '../context/DeviceContext';
import { useFocusData } from '../hooks/useAsync';
import { dashboardApi } from '../services/api/endpoints';
import type { RootStackParamList } from '../types/navigation';
import { firstName, greeting, qualityTone, shortDay } from '../utils/format';

type Nav = NativeStackNavigationProp<RootStackParamList>;

export default function DashboardScreen() {
  const navigation = useNavigation<Nav>();
  const { user } = useAuth();
  const { state: bleState, connected, health } = useDevice();
  const loader = useCallback(async () => {
    const [summary, performance] = await Promise.all([dashboardApi.summary(), dashboardApi.performance(7)]);
    return { summary, performance };
  }, []);
  const { data, error, loading, refreshing, refresh } = useFocusData(loader);

  const today = data?.summary.today;
  const tone = qualityTone(today?.quality_score);
  const isConnected = bleState === 'connected';

  return (
    <Screen onRefresh={refresh} refreshing={refreshing}>
      <FadeIn>
        <Row style={{ justifyContent: 'space-between' }}>
          <LogoBadge size={46} />
          <View style={{ flex: 1, marginLeft: spacing.md }}>
            <Text style={type.caption}>{greeting()}</Text>
            <Text style={type.h1}>{firstName(user?.name)} 👋</Text>
          </View>
          <PressableScale onPress={() => navigation.navigate('DeviceConnect')} style={styles.devicePill} accessibilityLabel="Device connection">
            <PulseDot color={isConnected ? colors.success : bleState === 'reconnecting' ? colors.warning : colors.textMuted} size={8} active={isConnected || bleState === 'reconnecting'} />
            <Text style={styles.devicePillText}>{isConnected ? connected?.name ?? 'Connected' : bleState === 'reconnecting' ? 'Reconnecting' : 'No device'}</Text>
          </PressableScale>
        </Row>
      </FadeIn>

      {error ? <Banner tone="danger" title="Could not load dashboard" message={error} action="Retry" onAction={refresh} style={{ marginTop: spacing.lg }} /> : null}

      <FadeIn delay={80}>
        <LinearGradient colors={gradients.hero} start={{ x: 0, y: 0 }} end={{ x: 1, y: 1 }} style={styles.hero}>
          <View style={styles.heroDeco} />
          <Row style={{ alignItems: 'center' }}>
            <ProgressRing value={today?.quality_score ?? 0} size={124} stroke={12} color={colors.teal} track="rgba(255,255,255,0.14)">
              <Text style={styles.ringValue}>{today?.quality_score == null ? '—' : `${Math.round(today.quality_score)}%`}</Text>
              <Text style={styles.ringLabel}>quality</Text>
            </ProgressRing>
            <View style={{ flex: 1, marginLeft: spacing.xl }}>
              <Text style={styles.heroKicker}>TODAY</Text>
              {loading ? (
                <Skeleton height={28} width={80} style={{ marginTop: 6, opacity: 0.3 }} />
              ) : (
                <Text style={styles.heroBig}>
                  {today?.total_reps ?? 0}
                  <Text style={styles.heroUnit}> reps</Text>
                </Text>
              )}
              <Text style={styles.heroLine}>
                {today?.sessions ?? 0} session{today?.sessions === 1 ? '' : 's'} · {Math.round(today?.active_minutes ?? 0)} min
              </Text>
              <View style={[styles.toneChip]}>
                <Text style={styles.toneText}>{today?.total_reps ? tone.label : 'Ready to train'}</Text>
              </View>
            </View>
          </Row>
        </LinearGradient>
      </FadeIn>

      <FadeIn delay={140}>
        <Row style={{ gap: spacing.sm + 2, marginTop: spacing.lg }}>
          <StatTile icon="layers-outline" label="Total reps" value={today?.total_reps ?? 0} />
          <StatTile icon="checkmark-done" label="Correct" value={today?.correct_reps ?? 0} tint={colors.success} bg={colors.successSoft} />
          <StatTile icon="close-circle-outline" label="Incorrect" value={today?.incorrect_reps ?? 0} tint={colors.coral} bg={colors.coralSoft} />
        </Row>
      </FadeIn>

      <FadeIn delay={200}>
        <PressableScale onPress={() => navigation.navigate('ExerciseSelection')} style={[styles.startCard, shadow.raised]} accessibilityRole="button" accessibilityLabel="Start workout">
          <LinearGradient colors={gradients.primary} start={{ x: 0, y: 0 }} end={{ x: 1, y: 0 }} style={styles.startInner}>
            <View style={styles.startIcon}>
              <Ionicons name="play" size={22} color={colors.primary} />
            </View>
            <View style={{ flex: 1, marginLeft: spacing.md }}>
              <Text style={styles.startTitle}>Start Workout</Text>
              <Text style={styles.startSub}>{isConnected ? `${health.receiving ? 'Sensors live' : 'Waiting for sensor data'}` : 'Connect your PhysioBand first'}</Text>
            </View>
            <Ionicons name="chevron-forward" size={22} color="#FFFFFF" />
          </LinearGradient>
        </PressableScale>
      </FadeIn>

      {data?.summary.active_session_id ? (
        <Banner
          tone="warning"
          title="Unfinished workout"
          message="A previous session was not completed (for example after a lost connection). It will be closed automatically when you start a new workout."
          action="View session"
          onAction={() => navigation.navigate('WorkoutResult', { sessionId: data.summary.active_session_id! })}
          style={{ marginTop: spacing.lg }}
        />
      ) : null}

      <SectionHeader title="This week" />
      <Card>
        {loading ? (
          <Skeleton height={130} />
        ) : (
          <>
            <Row style={{ justifyContent: 'space-between', marginBottom: spacing.md }}>
              <View>
                <Text style={type.label}>Repetitions</Text>
                <Text style={[type.h2, { marginTop: 2 }]}>{data?.performance.total_reps ?? 0}</Text>
              </View>
              {data?.performance.quality_trend != null ? (
                <View style={[styles.trend, { backgroundColor: data.performance.quality_trend >= 0 ? colors.successSoft : colors.dangerSoft }]}>
                  <Ionicons name={data.performance.quality_trend >= 0 ? 'trending-up' : 'trending-down'} size={14} color={data.performance.quality_trend >= 0 ? colors.success : colors.danger} />
                  <Text style={[styles.trendText, { color: data.performance.quality_trend >= 0 ? colors.success : colors.danger }]}>
                    {data.performance.quality_trend > 0 ? '+' : ''}
                    {data.performance.quality_trend}% quality
                  </Text>
                </View>
              ) : null}
            </Row>
            <BarChart data={(data?.performance.points ?? []).map((p) => ({ label: shortDay(p.date), value: p.total_reps }))} height={130} />
          </>
        )}
      </Card>

      <SectionHeader title="Recent workouts" action="See all" onAction={() => navigation.navigate('Main', { screen: 'History' })} />
      {loading ? (
        <>
          <Skeleton height={70} style={{ marginBottom: 10 }} />
          <Skeleton height={70} />
        </>
      ) : data?.summary.recent_sessions.length ? (
        data.summary.recent_sessions.map((s, i) => (
          <FadeIn key={s.id} index={i}>
            <SessionRow session={s} onPress={() => navigation.navigate('WorkoutResult', { sessionId: s.id })} />
          </FadeIn>
        ))
      ) : (
        <Card>
          <EmptyState icon="barbell-outline" title="No workouts yet" message="Your completed sessions and AI feedback will appear here." action="Start your first workout" onAction={() => navigation.navigate('ExerciseSelection')} />
        </Card>
      )}

      {data?.summary.model ? (
        <View style={{ marginTop: spacing.lg }}>
          <ModelNotice model={data.summary.model} />
        </View>
      ) : null}
      {!isConnected ? <Button title="Connect device" icon="bluetooth" variant="ghost" onPress={() => navigation.navigate('DeviceConnect')} style={{ marginTop: spacing.lg }} /> : null}
    </Screen>
  );
}

const styles = StyleSheet.create({
  devicePill: { flexDirection: 'row', alignItems: 'center', backgroundColor: colors.surface, borderRadius: radius.pill, paddingRight: 14, paddingLeft: 4, height: 38, borderWidth: 1, borderColor: colors.border },
  devicePillText: { fontFamily: fonts.semibold, fontSize: 12, color: colors.textSecondary, marginLeft: 2 },
  hero: { borderRadius: radius.xxl, padding: spacing.xl, marginTop: spacing.xl, overflow: 'hidden', ...shadow.raised },
  heroDeco: { position: 'absolute', width: 200, height: 200, borderRadius: 100, backgroundColor: 'rgba(255,255,255,0.07)', right: -50, bottom: -80 },
  ringValue: { fontFamily: fonts.extrabold, fontSize: 26, color: '#FFFFFF' },
  ringLabel: { fontFamily: fonts.medium, fontSize: 11, color: 'rgba(255,255,255,0.8)' },
  heroKicker: { fontFamily: fonts.semibold, fontSize: 11, color: 'rgba(255,255,255,0.75)', letterSpacing: 1.2 },
  heroBig: { fontFamily: fonts.extrabold, fontSize: 36, color: '#FFFFFF', letterSpacing: -1 },
  heroUnit: { fontFamily: fonts.semibold, fontSize: 15, color: 'rgba(255,255,255,0.8)' },
  heroLine: { fontFamily: fonts.medium, fontSize: 13, color: 'rgba(255,255,255,0.85)' },
  toneChip: { alignSelf: 'flex-start', backgroundColor: 'rgba(255,255,255,0.2)', borderRadius: radius.pill, paddingHorizontal: 10, paddingVertical: 4, marginTop: 10 },
  toneText: { fontFamily: fonts.semibold, fontSize: 12, color: '#FFFFFF' },
  startCard: { marginTop: spacing.lg, borderRadius: radius.xl },
  startInner: { flexDirection: 'row', alignItems: 'center', padding: spacing.lg, borderRadius: radius.xl },
  startIcon: { width: 46, height: 46, borderRadius: 16, backgroundColor: '#FFFFFF', alignItems: 'center', justifyContent: 'center' },
  startTitle: { fontFamily: fonts.bold, fontSize: 17, color: '#FFFFFF' },
  startSub: { fontFamily: fonts.medium, fontSize: 13, color: 'rgba(255,255,255,0.85)', marginTop: 2 },
  trend: { flexDirection: 'row', alignItems: 'center', borderRadius: radius.pill, paddingHorizontal: 10, paddingVertical: 5, gap: 4 },
  trendText: { fontFamily: fonts.semibold, fontSize: 12 },
});
