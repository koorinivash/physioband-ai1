/** Small, purposeful animation primitives built on React Native's Animated API. */
import React, { useEffect, useRef } from 'react';
import { Animated, Easing, Pressable, PressableProps, StyleProp, ViewStyle } from 'react-native';

/** Fades and slides content in on mount; `index` staggers lists. */
export function FadeIn({
  children,
  delay = 0,
  index = 0,
  offset = 14,
  style,
}: {
  children: React.ReactNode;
  delay?: number;
  index?: number;
  offset?: number;
  style?: StyleProp<ViewStyle>;
}) {
  const v = useRef(new Animated.Value(0)).current;
  useEffect(() => {
    Animated.timing(v, {
      toValue: 1,
      duration: 420,
      delay: delay + index * 60,
      easing: Easing.out(Easing.cubic),
      useNativeDriver: true,
    }).start();
  }, [v, delay, index]);
  return (
    <Animated.View
      style={[
        style,
        { opacity: v, transform: [{ translateY: v.interpolate({ inputRange: [0, 1], outputRange: [offset, 0] }) }] },
      ]}
    >
      {children}
    </Animated.View>
  );
}

const AnimatedPressable = Animated.createAnimatedComponent(Pressable);

/** Pressable that gently scales down while pressed. */
export function PressableScale({
  children,
  style,
  scaleTo = 0.97,
  ...props
}: Omit<PressableProps, 'style'> & { style?: StyleProp<ViewStyle>; scaleTo?: number; children: React.ReactNode }) {
  const scale = useRef(new Animated.Value(1)).current;
  const animate = (to: number) =>
    Animated.spring(scale, { toValue: to, useNativeDriver: true, speed: 40, bounciness: 6 }).start();
  return (
    <AnimatedPressable
      onPressIn={() => animate(scaleTo)}
      onPressOut={() => animate(1)}
      {...props}
      style={[style, { transform: [{ scale }] }]}
    >
      {children}
    </AnimatedPressable>
  );
}

/** Pulsing status dot (used for live / connected indicators). */
export function PulseDot({ color, size = 10, active = true }: { color: string; size?: number; active?: boolean }) {
  const v = useRef(new Animated.Value(0)).current;
  useEffect(() => {
    if (!active) {
      v.setValue(0);
      return;
    }
    const loop = Animated.loop(
      Animated.timing(v, { toValue: 1, duration: 1400, easing: Easing.out(Easing.ease), useNativeDriver: true }),
    );
    loop.start();
    return () => loop.stop();
  }, [v, active]);
  return (
    <Animated.View style={{ width: size * 2.4, height: size * 2.4, alignItems: 'center', justifyContent: 'center' }}>
      {active && (
        <Animated.View
          style={{
            position: 'absolute',
            width: size * 2.4,
            height: size * 2.4,
            borderRadius: size * 1.2,
            backgroundColor: color,
            opacity: v.interpolate({ inputRange: [0, 1], outputRange: [0.35, 0] }),
            transform: [{ scale: v.interpolate({ inputRange: [0, 1], outputRange: [0.4, 1] }) }],
          }}
        />
      )}
      <Animated.View style={{ width: size, height: size, borderRadius: size / 2, backgroundColor: color }} />
    </Animated.View>
  );
}

/** Shimmering placeholder block for loading states. */
export function Skeleton({ height = 16, width = '100%', radius = 10, style }: {
  height?: number;
  width?: number | `${number}%`;
  radius?: number;
  style?: StyleProp<ViewStyle>;
}) {
  const v = useRef(new Animated.Value(0.4)).current;
  useEffect(() => {
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(v, { toValue: 1, duration: 700, useNativeDriver: true }),
        Animated.timing(v, { toValue: 0.4, duration: 700, useNativeDriver: true }),
      ]),
    );
    loop.start();
    return () => loop.stop();
  }, [v]);
  return <Animated.View style={[{ height, width, borderRadius: radius, backgroundColor: '#E2E8F0', opacity: v }, style]} />;
}

/** Briefly scales its child up whenever `trigger` changes (e.g. rep counter). */
export function Bump({ trigger, children }: { trigger: unknown; children: React.ReactNode }) {
  const scale = useRef(new Animated.Value(1)).current;
  const first = useRef(true);
  useEffect(() => {
    if (first.current) {
      first.current = false;
      return;
    }
    Animated.sequence([
      Animated.timing(scale, { toValue: 1.18, duration: 120, useNativeDriver: true }),
      Animated.spring(scale, { toValue: 1, useNativeDriver: true, bounciness: 12 }),
    ]).start();
  }, [trigger, scale]);
  return <Animated.View style={{ transform: [{ scale }] }}>{children}</Animated.View>;
}
