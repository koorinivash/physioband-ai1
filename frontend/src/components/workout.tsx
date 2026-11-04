/** Domain components: stat tiles, session rows, quality badges and model status notice. */
import { Ionicons } from '@expo/vector-icons';
import React from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { colors, fonts, qualityColors, radius, spacing, type } from '../constants/theme';
import type { ModelStatus, QualityLabel, WorkoutSession } from '../types/api';
import { formatDate, formatDuration, formatTime, qualityTone } from '../utils/format';
import { PressableScale } from './animated';
import { Badge, IconCircle } from './ui';

type IconName = React.ComponentProps<typeof Ionicons>['name'];

export function StatTile({ icon, label, value, unit, tint = colors.primary, bg = colors.primaryTint }: {
  icon: IconName;
  label: string;
  value: string | number;
  unit?: string;
  tint?: string;
  bg?: string;
}) {
  return (
    <View style={styles.tile}>
      <IconCircle name={icon} color={tint} bg={bg} size={36} />
      <Text style={styles.tileValue} numberOfLines={1} adjustsFontSizeToFit>
        {value}
        {unit ? <Text style={styles.tileUnit}> {unit}</Text> : null}
      </Text>
      <Text style={styles.tileLabel}>{label}</Text>
    </View>
  );
}

export function QualityBadge({ label, display }: { label: QualityLabel | string; display?: string }) {
  const c = qualityColors[label] ?? qualityColors.unclassified;
  const text = display ?? { correct: 'Correct', incomplete: 'Incomplete', too_fast: 'Too fast', irregular: 'Irregular', unclassified: 'Unclassified' }[label] ?? label;
  return <Badge label={text} color={c.fg} bg={c.bg} icon={c.icon as IconName} />;
}

export function SessionRow({ session, onPress }: { session: WorkoutSession; onPress: () => void }) {
  const tone = qualityTone(session.quality_score);
  return (
    <PressableScale onPress={onPress} style={styles.row} accessibilityRole="button" accessibilityLabel={`${session.exercise_name} on ${formatDate(session.start_time)}`}>
      <IconCircle name="barbell" color={colors.primary} bg={colors.primaryTint} />
      <View style={{ flex: 1, marginLeft: spacing.md }}>
        <Text style={type.bodyStrong}>{session.exercise_name}</Text>
        <Text style={type.caption}>
          {formatDate(session.start_time)} · {formatTime(session.start_time)} · {formatDuration(session.duration_s)}
        </Text>
        {session.status === 'interrupted' ? (
          <Text style={[type.caption, { color: colors.warning, marginTop: 2 }]}>Interrupted session</Text>
        ) : session.status === 'active' ? (
          <Text style={[type.caption, { color: colors.info, marginTop: 2 }]}>In progress</Text>
        ) : null}
      </View>
      <View style={{ alignItems: 'flex-end' }}>
        <Text style={[styles.rowScore, { color: tone.fg }]}>{session.quality_score === null ? '—' : `${Math.round(session.quality_score)}%`}</Text>
        <Text style={type.caption}>{session.total_reps} reps</Text>
      </View>
    </PressableScale>
  );
}

/** Shown wherever AI results appear, so a demo / unvalidated model is never mistaken for a validated one. */
export function ModelNotice({ model, compact }: { model: ModelStatus | null | undefined; compact?: boolean }) {
  if (!model) return null;
  if (!model.available) {
    return (
      <View style={[styles.notice, { backgroundColor: colors.warningSoft }]}>
        <Ionicons name="alert-circle" size={16} color={colors.warning} />
        <Text style={styles.noticeText}>AI quality model unavailable — repetitions are counted but not classified.</Text>
      </View>
    );
  }
  const demo = model.dataset_type === 'synthetic';
  if (!demo && model.validated) return null;
  return (
    <View style={[styles.notice, { backgroundColor: demo ? colors.accentSoft : colors.infoSoft }]}>
      <Ionicons name="flask" size={16} color={demo ? colors.accent : colors.info} />
      <Text style={styles.noticeText}>
        {demo
          ? compact
            ? 'Demo AI model (synthetic data) — not validated'
            : 'Demo AI model trained on synthetic data. Classifications only demonstrate the pipeline and are not a validated assessment.'
          : 'AI model trained on collected data; not clinically validated.'}
      </Text>
    </View>
  );
}

export function MetricLine({ label, value, icon }: { label: string; value: string; icon: IconName }) {
  return (
    <View style={styles.metric}>
      <Ionicons name={icon} size={17} color={colors.textMuted} />
      <Text style={[type.body, { flex: 1, marginLeft: 10 }]}>{label}</Text>
      <Text style={type.bodyStrong}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  tile: {
    flex: 1,
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    padding: spacing.md,
    borderWidth: 1,
    borderColor: colors.border,
    minWidth: 96,
  },
  tileValue: { fontFamily: fonts.bold, fontSize: 22, color: colors.text, marginTop: spacing.sm, letterSpacing: -0.4 },
  tileUnit: { fontFamily: fonts.medium, fontSize: 13, color: colors.textMuted },
  tileLabel: { fontFamily: fonts.medium, fontSize: 12, color: colors.textMuted, marginTop: 2 },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    padding: spacing.md + 2,
    borderWidth: 1,
    borderColor: colors.border,
    marginBottom: spacing.sm + 2,
  },
  rowScore: { fontFamily: fonts.bold, fontSize: 18 },
  notice: { flexDirection: 'row', alignItems: 'center', padding: spacing.md, borderRadius: radius.md, gap: 8 },
  noticeText: { flex: 1, fontFamily: fonts.medium, fontSize: 12, lineHeight: 17, color: colors.textSecondary },
  metric: { flexDirection: 'row', alignItems: 'center', paddingVertical: 11, borderBottomWidth: 1, borderBottomColor: colors.border },
});
