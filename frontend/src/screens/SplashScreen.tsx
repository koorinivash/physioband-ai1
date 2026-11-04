import { LinearGradient } from 'expo-linear-gradient';
import React, { useEffect, useRef } from 'react';
import { Animated, Easing, StyleSheet, Text, View } from 'react-native';

import { LogoMark } from '../components/Logo';
import { colors, fonts, gradients } from '../constants/theme';

/** Animated brand splash shown while the stored session is restored. */
export default function SplashScreen() {
  const intro = useRef(new Animated.Value(0)).current;
  const spin = useRef(new Animated.Value(0)).current;
  const dots = useRef([0, 1, 2].map(() => new Animated.Value(0.3))).current;

  useEffect(() => {
    Animated.spring(intro, { toValue: 1, useNativeDriver: true, friction: 6, tension: 60 }).start();
    Animated.loop(Animated.timing(spin, { toValue: 1, duration: 2400, easing: Easing.linear, useNativeDriver: true })).start();
    dots.forEach((d, i) =>
      Animated.loop(
        Animated.sequence([
          Animated.delay(i * 180),
          Animated.timing(d, { toValue: 1, duration: 420, useNativeDriver: true }),
          Animated.timing(d, { toValue: 0.3, duration: 420, useNativeDriver: true }),
          Animated.delay((2 - i) * 180),
        ]),
      ).start(),
    );
  }, [intro, spin, dots]);

  const rotate = spin.interpolate({ inputRange: [0, 1], outputRange: ['0deg', '360deg'] });

  return (
    <LinearGradient colors={gradients.soft} style={styles.container}>
      <View style={styles.blobA} />
      <View style={styles.blobB} />
      <Animated.View style={{ alignItems: 'center', opacity: intro, transform: [{ scale: intro.interpolate({ inputRange: [0, 1], outputRange: [0.7, 1] }) }] }}>
        <View style={styles.logoWrap}>
          <Animated.View style={[styles.orbit, { transform: [{ rotate }] }]}>
            <View style={styles.orbitDot} />
          </Animated.View>
          <LogoMark size={168} />
        </View>
        <Text style={styles.subtitle}>Intelligent resistance exercise monitoring</Text>
      </Animated.View>
      <View style={styles.loader}>
        {dots.map((d, i) => (
          <Animated.View key={i} style={[styles.dot, { opacity: d, transform: [{ scale: d }] }]} />
        ))}
      </View>
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, alignItems: 'center', justifyContent: 'center', overflow: 'hidden' },
  blobA: { position: 'absolute', width: 320, height: 320, borderRadius: 160, backgroundColor: '#9FF3E6', opacity: 0.35, top: -80, right: -120 },
  blobB: { position: 'absolute', width: 260, height: 260, borderRadius: 130, backgroundColor: '#BFD3EC', opacity: 0.45, bottom: -60, left: -100 },
  logoWrap: { width: 240, height: 240, alignItems: 'center', justifyContent: 'center', marginBottom: 18 },
  orbit: { position: 'absolute', width: 240, height: 240, borderRadius: 120, borderWidth: 2, borderColor: 'rgba(2,28,64,0.12)' },
  orbitDot: { position: 'absolute', top: -7, left: 113, width: 14, height: 14, borderRadius: 7, backgroundColor: colors.primary },
  subtitle: { fontFamily: fonts.semibold, fontSize: 15, color: colors.navy, marginTop: 6, letterSpacing: 0.2 },
  loader: { position: 'absolute', bottom: 80, flexDirection: 'row', gap: 8 },
  dot: { width: 9, height: 9, borderRadius: 5, backgroundColor: colors.primary },
});
