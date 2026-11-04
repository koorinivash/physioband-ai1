import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import React, { useRef, useState } from 'react';
import { Animated, KeyboardAvoidingView, Platform, ScrollView, StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { FadeIn, PressableScale } from '../components/animated';
import { LogoBadge } from '../components/Logo';
import { Banner, Button, TextField } from '../components/ui';
import { API_URL, normalizeApiUrl } from '../constants/config';
import { colors, fonts, gradients, radius, shadow, spacing, type } from '../constants/theme';
import { useAuth } from '../context/AuthContext';
import { errorMessage, getApiBaseUrl, setApiBaseUrl } from '../services/api/client';
import { secureStorage } from '../services/storage/secureStorage';
import { EMAIL_RE } from '../utils/format';

type Mode = 'login' | 'register';

export default function AuthScreen() {
  const { login, register } = useAuth();
  const [mode, setMode] = useState<Mode>('login');
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [serverError, setServerError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const slide = useRef(new Animated.Value(0)).current;

  const switchMode = (m: Mode) => {
    setMode(m);
    setErrors({});
    setServerError(null);
    Animated.spring(slide, { toValue: m === 'login' ? 0 : 1, useNativeDriver: true, friction: 8 }).start();
  };

  const validate = () => {
    const e: Record<string, string> = {};
    if (mode === 'register' && name.trim().length < 2) e.name = 'Enter your name (at least 2 characters)';
    if (!EMAIL_RE.test(email.trim())) e.email = 'Enter a valid email address';
    if (mode === 'register') {
      if (password.length < 8) e.password = 'Use at least 8 characters';
      else if (!/[A-Za-z]/.test(password) || !/\d/.test(password)) e.password = 'Include at least one letter and one number';
      if (confirm !== password) e.confirm = 'Passwords do not match';
    } else if (!password) e.password = 'Enter your password';
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const submit = async () => {
    setServerError(null);
    if (!validate()) return;
    setBusy(true);
    try {
      if (mode === 'login') await login(email, password);
      else await register(name, email, password);
    } catch (err) {
      setServerError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  const indicatorX = slide.interpolate({ inputRange: [0, 1], outputRange: [0, 1] });

  return (
    <View style={{ flex: 1, backgroundColor: colors.background }}>
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined} style={{ flex: 1 }}>
        <ScrollView contentContainerStyle={{ paddingBottom: 40 }} keyboardShouldPersistTaps="handled" showsVerticalScrollIndicator={false}>
          <LinearGradient colors={gradients.hero} start={{ x: 0, y: 0 }} end={{ x: 1, y: 1 }} style={styles.hero}>
            <View style={styles.heroCircle} />
            <SafeAreaView edges={['top']}>
              <FadeIn style={{ paddingHorizontal: spacing.xl, paddingTop: spacing.lg }}>
                <LogoBadge size={84} ring />
                <Text style={styles.heroTitle}>{mode === 'login' ? 'Welcome back' : 'Create your account'}</Text>
                <Text style={styles.heroSubtitle}>
                  {mode === 'login' ? 'Sign in to continue your training.' : 'Track every rep with AI-powered feedback.'}
                </Text>
              </FadeIn>
            </SafeAreaView>
          </LinearGradient>

          <FadeIn delay={120} style={styles.card}>
            <View style={styles.tabs}>
              <TabIndicator progress={indicatorX} />
              {(['login', 'register'] as Mode[]).map((m) => (
                <PressableScale key={m} onPress={() => switchMode(m)} style={styles.tab} accessibilityRole="tab" accessibilityState={{ selected: mode === m }}>
                  <Text style={[styles.tabText, mode === m && { color: colors.primaryDark }]}>{m === 'login' ? 'Sign in' : 'Register'}</Text>
                </PressableScale>
              ))}
            </View>

            {serverError ? <Banner tone="danger" message={serverError} /> : null}

            {mode === 'register' ? (
              <TextField label="Full name" icon="person-outline" value={name} onChangeText={setName} placeholder="Your name" autoCapitalize="words" error={errors.name} />
            ) : null}
            <TextField
              label="Email"
              icon="mail-outline"
              value={email}
              onChangeText={setEmail}
              placeholder="you@example.com"
              keyboardType="email-address"
              autoCapitalize="none"
              autoComplete="email"
              error={errors.email}
            />
            <TextField
              label="Password"
              icon="lock-closed-outline"
              value={password}
              onChangeText={setPassword}
              placeholder={mode === 'register' ? 'At least 8 characters' : 'Your password'}
              secure
              autoCapitalize="none"
              error={errors.password}
              returnKeyType={mode === 'login' ? 'go' : 'next'}
              onSubmitEditing={mode === 'login' ? () => void submit() : undefined}
            />
            {mode === 'register' ? (
              <TextField label="Confirm password" icon="shield-checkmark-outline" value={confirm} onChangeText={setConfirm} placeholder="Repeat password" secure autoCapitalize="none" error={errors.confirm} />
            ) : null}

            <Button title={mode === 'login' ? 'Sign in' : 'Create account'} onPress={submit} loading={busy} style={{ marginTop: spacing.sm }} />

            <Text style={styles.switchText}>
              {mode === 'login' ? "Don't have an account? " : 'Already registered? '}
              <Text style={styles.switchLink} onPress={() => switchMode(mode === 'login' ? 'register' : 'login')}>
                {mode === 'login' ? 'Register' : 'Sign in'}
              </Text>
            </Text>
          </FadeIn>

          <FadeIn delay={240}>
            <ServerSetting />
          </FadeIn>
        </ScrollView>
      </KeyboardAvoidingView>
    </View>
  );
}

/** Lets the user point the installed APK at another backend (e.g. a new Render URL) without rebuilding. */
function ServerSetting() {
  const [editing, setEditing] = useState(false);
  const [current, setCurrent] = useState(getApiBaseUrl());
  const [draft, setDraft] = useState(current);

  const save = async () => {
    const url = normalizeApiUrl(draft);
    setApiBaseUrl(url);
    await secureStorage.setServerUrl(url);
    setCurrent(url);
    setEditing(false);
  };
  const reset = async () => {
    setApiBaseUrl(API_URL);
    await secureStorage.clearServerUrl();
    setCurrent(API_URL);
    setDraft(API_URL);
    setEditing(false);
  };

  if (!editing) {
    return (
      <PressableScale onPress={() => { setDraft(current); setEditing(true); }} style={styles.footer} accessibilityRole="button" accessibilityLabel="Change server address">
        <Ionicons name="server-outline" size={13} color={colors.textMuted} />
        <Text style={[type.caption, { marginLeft: 6, flexShrink: 1 }]} numberOfLines={1}>
          {current}
        </Text>
        <Ionicons name="create-outline" size={13} color={colors.primary} style={{ marginLeft: 6 }} />
      </PressableScale>
    );
  }
  return (
    <View style={[styles.card, { marginTop: spacing.lg }]}>
      <TextField label="Server address" icon="server-outline" value={draft} onChangeText={setDraft} autoCapitalize="none" autoCorrect={false} keyboardType="url" placeholder="https://your-service.onrender.com" />
      <Text style={[type.caption, { marginBottom: spacing.md }]}>"/api/v1" is added automatically. Use https for Render.</Text>
      <View style={{ flexDirection: 'row', gap: spacing.sm }}>
        <Button title="Default" variant="ghost" size="md" onPress={() => void reset()} style={{ flex: 1 }} />
        <Button title="Save" size="md" onPress={() => void save()} disabled={!draft.trim()} style={{ flex: 1 }} />
      </View>
    </View>
  );
}

function TabIndicator({ progress }: { progress: Animated.AnimatedInterpolation<number> }) {
  const [w, setW] = useState(0);
  return (
    <View style={StyleSheet.absoluteFill} onLayout={(e) => setW(e.nativeEvent.layout.width / 2)} pointerEvents="none">
      <Animated.View
        style={[
          styles.indicator,
          { width: w - 6, transform: [{ translateX: progress.interpolate({ inputRange: [0, 1], outputRange: [3, w + 3] }) }] },
        ]}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  hero: { paddingBottom: 70, overflow: 'hidden' },
  heroCircle: { position: 'absolute', width: 260, height: 260, borderRadius: 130, backgroundColor: 'rgba(255,255,255,0.08)', right: -60, top: -40 },
  heroTitle: { fontFamily: fonts.extrabold, fontSize: 30, color: '#FFFFFF', marginTop: spacing.xl, letterSpacing: -0.6 },
  heroSubtitle: { fontFamily: fonts.medium, fontSize: 15, color: 'rgba(255,255,255,0.85)', marginTop: 6 },
  card: { backgroundColor: colors.surface, borderRadius: radius.xxl, padding: spacing.xl, marginTop: -48, marginHorizontal: spacing.xl, borderWidth: 1, borderColor: colors.border, ...shadow.card },
  tabs: { flexDirection: 'row', backgroundColor: colors.surfaceMuted, borderRadius: radius.lg, padding: 3, marginBottom: spacing.xl, borderWidth: 1, borderColor: colors.border },
  tab: { flex: 1, height: 42, alignItems: 'center', justifyContent: 'center' },
  tabText: { fontFamily: fonts.semibold, fontSize: 14, color: colors.textMuted },
  indicator: { position: 'absolute', top: 3, bottom: 3, borderRadius: radius.md, backgroundColor: colors.surface, ...shadow.card },
  switchText: { fontFamily: fonts.regular, fontSize: 14, color: colors.textSecondary, textAlign: 'center', marginTop: spacing.lg },
  switchLink: { fontFamily: fonts.semibold, color: colors.primary },
  footer: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', marginTop: spacing.xl },
});
