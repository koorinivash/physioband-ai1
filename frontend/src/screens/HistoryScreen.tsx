import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { ActivityIndicator, StyleSheet, Text, View } from 'react-native';

import { FadeIn, PressableScale, Skeleton } from '../components/animated';
import { BarChart, LineChart } from '../components/charts';
import { Banner, Card, EmptyState, Row, Screen, SectionHeader } from '../components/ui';
import { SessionRow } from '../components/workout';
import { colors, fonts, radius, spacing, type } from '../constants/theme';
import { useFocusData } from '../hooks/useAsync';
import { errorMessage } from '../services/api/client';
import { dashboardApi, workoutApi } from '../services/api/endpoints';
import type { WorkoutSession } from '../types/api';
import type { RootStackParamList } from '../types/navigation';
import { formatDate, shortDay } from '../utils/format';

type Nav = NativeStackNavigationProp<RootStackParamList>;
const RANGES = [7, 14, 30] as const;
const PAGE_SIZE = 15;

export default function HistoryScreen() {
  const navigation = useNavigation<Nav>();
  const [days, setDays] = useState<(typeof RANGES)[number]>(14);
  const [more, setMore] = useState<{ items: WorkoutSession[]; page: number; pages: number } | null>(null);
  const [loadingMore, setLoadingMore] = useState(false);
  const [moreError, setMoreError] = useState<string | null>(null);

  const loader = useCallback(async () => {
    const [performance, page] = await Promise.all([dashboardApi.performance(days), workoutApi.list(1, PAGE_SIZE)]);
    setMore({ items: page.items, page: 1, pages: page.pages });
    return { performance, total: page.total };
  }, [days]);
  const { data, error, loading, refreshing, refresh } = useFocusData(loader);

  const firstRender = useRef(true);
  useEffect(() => {
    if (firstRender.current) {
      firstRender.current = false;
      return;
    }
    void refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [days]);
  const changeRange = (d: (typeof RANGES)[number]) => setDays(d);

  const loadMore = async () => {
    if (!more || more.page >= more.pages || loadingMore) return;
    setLoadingMore(true);
    try {
      const next = await workoutApi.list(more.page + 1, PAGE_SIZE);
      setMore({ items: [...more.items, ...next.items], page: next.page, pages: next.pages });
      setMoreError(null);
    } catch (e) {
      setMoreError(errorMessage(e));
    } finally {
      setLoadingMore(false);
    }
  };

  const points = data?.performance.points ?? [];
  const labelFor = (date: string) => (days <= 7 ? shortDay(date) : date.slice(8, 10));

  return (
    <Screen onRefresh={refresh} refreshing={refreshing}>
      <Text style={type.h1}>History</Text>
      <Text style={type.body}>Your sessions and performance trends.</Text>

      <Row style={styles.segment}>
        {RANGES.map((r) => (
          <PressableScale key={r} onPress={() => changeRange(r)} style={[styles.segmentItem, days === r && styles.segmentActive]} accessibilityRole="button" accessibilityState={{ selected: days === r }}>
            <Text style={[styles.segmentText, days === r && { color: colors.primaryDark }]}>{r} days</Text>
          </PressableScale>
        ))}
      </Row>

      {error ? <Banner tone="danger" message={error} action="Retry" onAction={refresh} /> : null}

      <Card>
        <Row style={{ justifyContent: 'space-between' }}>
          <View>
            <Text style={type.label}>Quality score</Text>
            <Text style={[type.h2, { marginTop: 2 }]}>{data?.performance.best_quality == null ? '—' : `Best ${Math.round(data.performance.best_quality)}%`}</Text>
          </View>
          {data?.performance.quality_trend != null ? (
            <Text style={[styles.trend, { color: data.performance.quality_trend >= 0 ? colors.success : colors.danger }]}>
              {data.performance.quality_trend >= 0 ? '▲' : '▼'} {Math.abs(data.performance.quality_trend)}%
            </Text>
          ) : null}
        </Row>
        <View style={{ marginTop: spacing.md }}>
          {loading ? <Skeleton height={150} /> : <LineChart values={points.map((p) => p.quality_score)} labels={points.map((p) => labelFor(p.date))} />}
        </View>
      </Card>

      <Card style={{ marginTop: spacing.md }}>
        <Text style={type.label}>Repetitions per day</Text>
        <Text style={[type.h2, { marginTop: 2, marginBottom: spacing.md }]}>{data?.performance.total_reps ?? 0} total</Text>
        {loading ? <Skeleton height={130} /> : <BarChart data={points.map((p) => ({ label: labelFor(p.date), value: p.total_reps }))} height={130} />}
      </Card>

      <SectionHeader title={`Sessions${data ? ` (${data.total})` : ''}`} />
      {loading ? (
        [0, 1, 2].map((i) => <Skeleton key={i} height={72} style={{ marginBottom: 10 }} />)
      ) : more && more.items.length ? (
        <>
          {more.items.map((s, i) => {
            const showDate = i === 0 || formatDate(s.start_time) !== formatDate(more.items[i - 1].start_time);
            return (
              <FadeIn key={s.id} index={Math.min(i, 8)}>
                {showDate ? <Text style={[type.label, { marginTop: i === 0 ? 0 : spacing.md, marginBottom: spacing.sm }]}>{formatDate(s.start_time)}</Text> : null}
                <SessionRow session={s} onPress={() => navigation.navigate('WorkoutResult', { sessionId: s.id })} />
              </FadeIn>
            );
          })}
          {moreError ? <Banner tone="danger" message={moreError} /> : null}
          {more.page < more.pages ? (
            <PressableScale onPress={() => void loadMore()} style={styles.loadMore} accessibilityRole="button">
              {loadingMore ? <ActivityIndicator color={colors.primary} /> : <Text style={styles.loadMoreText}>Load more</Text>}
            </PressableScale>
          ) : null}
        </>
      ) : (
        <Card>
          <EmptyState icon="calendar-outline" title="No sessions yet" message="Complete a workout to build your history and trends." action="Start workout" onAction={() => navigation.navigate('ExerciseSelection')} />
        </Card>
      )}
    </Screen>
  );
}

const styles = StyleSheet.create({
  segment: { backgroundColor: colors.surface, borderRadius: radius.lg, padding: 4, borderWidth: 1, borderColor: colors.border, marginVertical: spacing.lg },
  segmentItem: { flex: 1, height: 38, borderRadius: radius.md, alignItems: 'center', justifyContent: 'center' },
  segmentActive: { backgroundColor: colors.primaryTint },
  segmentText: { fontFamily: fonts.semibold, fontSize: 13, color: colors.textMuted },
  trend: { fontFamily: fonts.bold, fontSize: 14 },
  loadMore: { height: 48, borderRadius: radius.lg, borderWidth: 1, borderColor: colors.border, backgroundColor: colors.surface, alignItems: 'center', justifyContent: 'center', marginTop: spacing.sm },
  loadMoreText: { fontFamily: fonts.semibold, color: colors.primary, fontSize: 14 },
});
