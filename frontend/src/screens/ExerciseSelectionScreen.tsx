import { Ionicons } from '@expo/vector-icons';
import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { LinearGradient } from 'expo-linear-gradient';
import React, { useCallback } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { FadeIn, PressableScale } from '../components/animated';
import { Badge, Banner, LoadingState, Row, Screen } from '../components/ui';
import { colors, fonts, gradients, radius, shadow, spacing, type } from '../constants/theme';
import { useDevice } from '../context/DeviceContext';
import { useFocusData } from '../hooks/useAsync';
import { exerciseApi } from '../services/api/endpoints';
import type { Exercise } from '../types/api';
import type { RootStackParamList } from '../types/navigation';

type Nav = NativeStackNavigationProp<RootStackParamList>;

const ICONS: Record<string, React.ComponentProps<typeof Ionicons>['name']> = {
  biceps_curl: 'barbell',
  shoulder_press: 'arrow-up-circle',
  chest_press: 'expand',
  seated_row: 'git-pull-request',
  triceps_extension: 'trending-up',
};

export default function ExerciseSelectionScreen() {
  const navigation = useNavigation<Nav>();
  const { state } = useDevice();
  const loader = useCallback(() => exerciseApi.list(), []);
  const { data, error, loading, refresh } = useFocusData(loader);

  const choose = (ex: Exercise) => {
    if (!ex.is_active) return;
    navigation.navigate('LiveWorkout', { exerciseId: ex.id, exerciseName: ex.name });
  };

  return (
    <Screen edges={[]}>
      <Text style={type.body}>Choose an exercise. Only exercises with implemented movement analysis can be started.</Text>
      {state !== 'connected' ? (
        <Banner
          tone="warning"
          title="Device not connected"
          message="Connect your PhysioBand before starting so sensor data can be recorded."
          action="Connect device"
          onAction={() => navigation.navigate('DeviceConnect')}
          style={{ marginTop: spacing.lg }}
        />
      ) : null}
      {error ? <Banner tone="danger" message={error} action="Retry" onAction={refresh} style={{ marginTop: spacing.lg }} /> : null}
      {loading ? <LoadingState label="Loading exercises" /> : null}

      <View style={{ marginTop: spacing.lg }}>
        {(data ?? []).map((ex, i) => (
          <FadeIn key={ex.id} index={i}>
            {ex.is_active ? (
              <PressableScale onPress={() => choose(ex)} style={[styles.featured, shadow.raised]} accessibilityRole="button" accessibilityLabel={`Start ${ex.name}`}>
                <LinearGradient colors={gradients.hero} start={{ x: 0, y: 0 }} end={{ x: 1, y: 1 }} style={styles.featuredInner}>
                  <View style={styles.featuredDeco} />
                  <Row style={{ justifyContent: 'space-between' }}>
                    <View style={styles.featuredIcon}>
                      <Ionicons name={ICONS[ex.id] ?? 'fitness'} size={28} color={colors.primary} />
                    </View>
                    <View style={styles.liveChip}>
                      <View style={styles.liveDot} />
                      <Text style={styles.liveText}>AI analysis available</Text>
                    </View>
                  </Row>
                  <Text style={styles.featuredTitle}>{ex.name}</Text>
                  <Text style={styles.featuredDesc}>{ex.description}</Text>
                  <Row style={{ flexWrap: 'wrap', gap: 6, marginTop: spacing.md }}>
                    {ex.target_muscles.map((m) => (
                      <View key={m} style={styles.muscleChip}>
                        <Text style={styles.muscleText}>{m}</Text>
                      </View>
                    ))}
                  </Row>
                  <Row style={styles.featuredCta}>
                    <Text style={styles.ctaText}>Start exercise</Text>
                    <Ionicons name="arrow-forward" size={18} color={colors.primaryDark} />
                  </Row>
                </LinearGradient>
              </PressableScale>
            ) : (
              <View style={styles.locked} accessibilityState={{ disabled: true }}>
                <View style={styles.lockedIcon}>
                  <Ionicons name={ICONS[ex.id] ?? 'fitness'} size={22} color={colors.textMuted} />
                </View>
                <View style={{ flex: 1, marginLeft: spacing.md }}>
                  <Text style={[type.bodyStrong, { color: colors.textSecondary }]}>{ex.name}</Text>
                  <Text style={type.caption} numberOfLines={1}>
                    {ex.target_muscles.join(' · ')}
                  </Text>
                </View>
                <Badge label="Coming soon" color={colors.textMuted} bg={colors.backgroundAlt} icon="lock-closed" />
              </View>
            )}
          </FadeIn>
        ))}
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  featured: { borderRadius: radius.xxl, marginBottom: spacing.xl },
  featuredInner: { borderRadius: radius.xxl, padding: spacing.xl, overflow: 'hidden' },
  featuredDeco: { position: 'absolute', width: 220, height: 220, borderRadius: 110, backgroundColor: 'rgba(255,255,255,0.08)', right: -70, top: -70 },
  featuredIcon: { width: 56, height: 56, borderRadius: 18, backgroundColor: '#FFFFFF', alignItems: 'center', justifyContent: 'center' },
  liveChip: { flexDirection: 'row', alignItems: 'center', backgroundColor: 'rgba(255,255,255,0.18)', borderRadius: radius.pill, paddingHorizontal: 10, paddingVertical: 5 },
  liveDot: { width: 7, height: 7, borderRadius: 4, backgroundColor: '#00FAD8', marginRight: 6 },
  liveText: { fontFamily: fonts.semibold, fontSize: 11, color: '#FFFFFF' },
  featuredTitle: { fontFamily: fonts.extrabold, fontSize: 26, color: '#FFFFFF', marginTop: spacing.lg, letterSpacing: -0.5 },
  featuredDesc: { fontFamily: fonts.regular, fontSize: 14, lineHeight: 20, color: 'rgba(255,255,255,0.88)', marginTop: 6 },
  muscleChip: { backgroundColor: 'rgba(255,255,255,0.16)', borderRadius: radius.pill, paddingHorizontal: 10, paddingVertical: 4 },
  muscleText: { fontFamily: fonts.medium, fontSize: 12, color: '#FFFFFF' },
  featuredCta: { alignSelf: 'flex-start', backgroundColor: '#FFFFFF', borderRadius: radius.pill, paddingHorizontal: 16, paddingVertical: 10, marginTop: spacing.lg, gap: 8 },
  ctaText: { fontFamily: fonts.bold, fontSize: 14, color: colors.primaryDark },
  locked: { flexDirection: 'row', alignItems: 'center', backgroundColor: colors.surface, borderRadius: radius.lg, padding: spacing.md + 2, borderWidth: 1, borderColor: colors.border, marginBottom: spacing.sm + 2, opacity: 0.85 },
  lockedIcon: { width: 42, height: 42, borderRadius: 14, backgroundColor: colors.backgroundAlt, alignItems: 'center', justifyContent: 'center' },
});
