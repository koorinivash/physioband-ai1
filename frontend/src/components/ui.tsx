/** Core UI building blocks: Screen, Card, Button, TextField, Badge, banners and states. */
import { Ionicons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import React, { useState } from 'react';
import {
  ActivityIndicator,
  RefreshControl,
  ScrollView,
  StyleProp,
  StyleSheet,
  Text,
  TextInput,
  TextInputProps,
  TextStyle,
  View,
  ViewStyle,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { colors, fonts, gradients, radius, shadow, spacing, type } from '../constants/theme';
import { FadeIn, PressableScale } from './animated';

type IconName = React.ComponentProps<typeof Ionicons>['name'];

export function Screen({
  children,
  scroll = true,
  refreshing,
  onRefresh,
  contentStyle,
  edges = ['top'],
}: {
  children: React.ReactNode;
  scroll?: boolean;
  refreshing?: boolean;
  onRefresh?: () => void;
  contentStyle?: StyleProp<ViewStyle>;
  edges?: ('top' | 'bottom')[];
}) {
  return (
    <SafeAreaView style={styles.screen} edges={edges}>
      {scroll ? (
        <ScrollView
          contentContainerStyle={[styles.content, contentStyle]}
          showsVerticalScrollIndicator={false}
          keyboardShouldPersistTaps="handled"
          refreshControl={
            onRefresh ? (
              <RefreshControl refreshing={!!refreshing} onRefresh={onRefresh} tintColor={colors.primary} colors={[colors.primary]} />
            ) : undefined
          }
        >
          {children}
        </ScrollView>
      ) : (
        <View style={[styles.content, { flex: 1 }, contentStyle]}>{children}</View>
      )}
    </SafeAreaView>
  );
}

export function Card({ children, style, padded = true }: { children: React.ReactNode; style?: StyleProp<ViewStyle>; padded?: boolean }) {
  return <View style={[styles.card, padded && { padding: spacing.lg }, style]}>{children}</View>;
}

export function SectionHeader({ title, action, onAction }: { title: string; action?: string; onAction?: () => void }) {
  return (
    <View style={styles.sectionHeader}>
      <Text style={type.h2}>{title}</Text>
      {action && onAction ? (
        <Text style={styles.sectionAction} onPress={onAction} accessibilityRole="button">
          {action}
        </Text>
      ) : null}
    </View>
  );
}

type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger';

export function Button({
  title,
  onPress,
  variant = 'primary',
  icon,
  loading,
  disabled,
  style,
  size = 'lg',
}: {
  title: string;
  onPress?: () => void;
  variant?: ButtonVariant;
  icon?: IconName;
  loading?: boolean;
  disabled?: boolean;
  style?: StyleProp<ViewStyle>;
  size?: 'md' | 'lg';
}) {
  const isDisabled = disabled || loading;
  const height = size === 'lg' ? 54 : 44;
  const fg = variant === 'primary' || variant === 'danger' ? colors.textOnPrimary : variant === 'secondary' ? colors.primaryDark : colors.textSecondary;
  const content = (
    <View style={[styles.buttonInner, { height }]}>
      {loading ? (
        <ActivityIndicator color={fg} />
      ) : (
        <>
          {icon ? <Ionicons name={icon} size={19} color={fg} style={{ marginRight: 8 }} /> : null}
          <Text style={[styles.buttonText, { color: fg, fontSize: size === 'lg' ? 16 : 14 }]}>{title}</Text>
        </>
      )}
    </View>
  );
  return (
    <PressableScale
      onPress={onPress}
      disabled={isDisabled}
      accessibilityRole="button"
      accessibilityState={{ disabled: !!isDisabled }}
      style={[{ opacity: isDisabled ? 0.55 : 1, borderRadius: radius.lg }, variant === 'primary' && !isDisabled ? shadow.raised : null, style]}
    >
      {variant === 'primary' ? (
        <LinearGradient colors={gradients.primary} start={{ x: 0, y: 0 }} end={{ x: 1, y: 1 }} style={styles.buttonShape}>
          {content}
        </LinearGradient>
      ) : (
        <View
          style={[
            styles.buttonShape,
            variant === 'secondary' && { backgroundColor: colors.primaryTint, borderWidth: 1, borderColor: colors.primarySoft },
            variant === 'ghost' && { backgroundColor: colors.surface, borderWidth: 1, borderColor: colors.border },
            variant === 'danger' && { backgroundColor: colors.danger },
          ]}
        >
          {content}
        </View>
      )}
    </PressableScale>
  );
}

export function TextField({
  label,
  icon,
  error,
  secure,
  style,
  ...props
}: TextInputProps & { label: string; icon?: IconName; error?: string | null; secure?: boolean; style?: StyleProp<ViewStyle> }) {
  const [focused, setFocused] = useState(false);
  const [hidden, setHidden] = useState(!!secure);
  return (
    <View style={[{ marginBottom: spacing.md }, style]}>
      <Text style={styles.fieldLabel}>{label}</Text>
      <View
        style={[
          styles.field,
          focused && { borderColor: colors.primary, backgroundColor: colors.surface },
          !!error && { borderColor: colors.danger },
        ]}
      >
        {icon ? <Ionicons name={icon} size={18} color={focused ? colors.primary : colors.textMuted} style={{ marginRight: 10 }} /> : null}
        <TextInput
          {...props}
          secureTextEntry={hidden}
          placeholderTextColor={colors.textMuted}
          style={styles.fieldInput}
          onFocus={(e) => {
            setFocused(true);
            props.onFocus?.(e);
          }}
          onBlur={(e) => {
            setFocused(false);
            props.onBlur?.(e);
          }}
          accessibilityLabel={label}
        />
        {secure ? (
          <Ionicons
            name={hidden ? 'eye-outline' : 'eye-off-outline'}
            size={19}
            color={colors.textMuted}
            onPress={() => setHidden((h) => !h)}
            accessibilityLabel={hidden ? 'Show password' : 'Hide password'}
          />
        ) : null}
      </View>
      {error ? <Text style={styles.fieldError}>{error}</Text> : null}
    </View>
  );
}

export function Badge({ label, color, bg, icon, style }: { label: string; color: string; bg: string; icon?: IconName; style?: StyleProp<ViewStyle> }) {
  return (
    <View style={[styles.badge, { backgroundColor: bg }, style]}>
      {icon ? <Ionicons name={icon} size={13} color={color} style={{ marginRight: 5 }} /> : null}
      <Text style={[styles.badgeText, { color }]}>{label}</Text>
    </View>
  );
}

export function IconCircle({ name, color = colors.primary, bg = colors.primaryTint, size = 42 }: { name: IconName; color?: string; bg?: string; size?: number }) {
  return (
    <View style={{ width: size, height: size, borderRadius: size / 2.6, backgroundColor: bg, alignItems: 'center', justifyContent: 'center' }}>
      <Ionicons name={name} size={size * 0.48} color={color} />
    </View>
  );
}

export function Banner({
  tone = 'info',
  title,
  message,
  icon,
  action,
  onAction,
  style,
}: {
  tone?: 'info' | 'warning' | 'danger' | 'success';
  title?: string;
  message: string;
  icon?: IconName;
  action?: string;
  onAction?: () => void;
  style?: StyleProp<ViewStyle>;
}) {
  const palette = {
    info: [colors.info, colors.infoSoft, 'information-circle'],
    warning: [colors.warning, colors.warningSoft, 'warning'],
    danger: [colors.danger, colors.dangerSoft, 'alert-circle'],
    success: [colors.success, colors.successSoft, 'checkmark-circle'],
  }[tone] as [string, string, IconName];
  return (
    <FadeIn style={[styles.banner, { backgroundColor: palette[1] }, style]}>
      <Ionicons name={icon ?? palette[2]} size={20} color={palette[0]} style={{ marginTop: 1 }} />
      <View style={{ flex: 1, marginLeft: 10 }}>
        {title ? <Text style={[styles.bannerTitle, { color: colors.text }]}>{title}</Text> : null}
        <Text style={styles.bannerText}>{message}</Text>
        {action && onAction ? (
          <Text style={[styles.bannerAction, { color: palette[0] }]} onPress={onAction} accessibilityRole="button">
            {action}
          </Text>
        ) : null}
      </View>
    </FadeIn>
  );
}

export function EmptyState({ icon, title, message, action, onAction }: { icon: IconName; title: string; message: string; action?: string; onAction?: () => void }) {
  return (
    <FadeIn style={styles.empty}>
      <View style={styles.emptyIcon}>
        <Ionicons name={icon} size={30} color={colors.primary} />
      </View>
      <Text style={[type.h3, { marginTop: spacing.md, textAlign: 'center' }]}>{title}</Text>
      <Text style={[type.body, { textAlign: 'center', marginTop: 4 }]}>{message}</Text>
      {action && onAction ? <Button title={action} onPress={onAction} variant="secondary" size="md" style={{ marginTop: spacing.lg, alignSelf: 'stretch' }} /> : null}
    </FadeIn>
  );
}

export function LoadingState({ label = 'Loading...' }: { label?: string }) {
  return (
    <View style={{ paddingVertical: 48, alignItems: 'center' }}>
      <ActivityIndicator color={colors.primary} size="large" />
      <Text style={[type.caption, { marginTop: 12 }]}>{label}</Text>
    </View>
  );
}

export function Row({ children, style }: { children: React.ReactNode; style?: StyleProp<ViewStyle> }) {
  return <View style={[{ flexDirection: 'row', alignItems: 'center' }, style]}>{children}</View>;
}

export function Label({ children, style }: { children: React.ReactNode; style?: StyleProp<TextStyle> }) {
  return <Text style={[type.label, style]}>{children}</Text>;
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: colors.background },
  content: { padding: spacing.xl, paddingBottom: 120 },
  card: { backgroundColor: colors.surface, borderRadius: radius.xl, borderWidth: 1, borderColor: colors.border, ...shadow.card },
  sectionHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginTop: spacing.xxl, marginBottom: spacing.md },
  sectionAction: { fontFamily: fonts.semibold, color: colors.primary, fontSize: 14 },
  buttonShape: { borderRadius: radius.lg, overflow: 'hidden' },
  buttonInner: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', paddingHorizontal: spacing.xl },
  buttonText: { fontFamily: fonts.semibold, letterSpacing: 0.2 },
  fieldLabel: { fontFamily: fonts.semibold, fontSize: 13, color: colors.textSecondary, marginBottom: 6 },
  field: {
    flexDirection: 'row',
    alignItems: 'center',
    height: 54,
    paddingHorizontal: spacing.lg,
    borderRadius: radius.lg,
    borderWidth: 1.5,
    borderColor: colors.border,
    backgroundColor: colors.surfaceMuted,
  },
  fieldInput: { flex: 1, fontFamily: fonts.medium, fontSize: 15, color: colors.text, paddingVertical: 0 },
  fieldError: { fontFamily: fonts.medium, fontSize: 12, color: colors.danger, marginTop: 5 },
  badge: { flexDirection: 'row', alignItems: 'center', alignSelf: 'flex-start', paddingHorizontal: 10, paddingVertical: 5, borderRadius: radius.pill },
  badgeText: { fontFamily: fonts.semibold, fontSize: 12 },
  banner: { flexDirection: 'row', padding: spacing.md + 2, borderRadius: radius.lg, marginBottom: spacing.md },
  bannerTitle: { fontFamily: fonts.semibold, fontSize: 14, marginBottom: 2 },
  bannerText: { fontFamily: fonts.regular, fontSize: 13, lineHeight: 19, color: colors.textSecondary },
  bannerAction: { fontFamily: fonts.semibold, fontSize: 13, marginTop: 6 },
  empty: { alignItems: 'center', paddingVertical: spacing.xxl, paddingHorizontal: spacing.lg },
  emptyIcon: { width: 68, height: 68, borderRadius: 24, backgroundColor: colors.primaryTint, alignItems: 'center', justifyContent: 'center' },
});
