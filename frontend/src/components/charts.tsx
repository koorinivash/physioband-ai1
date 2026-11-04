/** Lightweight SVG charts (react-native-svg) with entrance animations. */
import React, { useEffect, useRef, useState } from 'react';
import { Animated, Easing, LayoutChangeEvent, Text, View } from 'react-native';
import Svg, { Circle, Defs, G, Line, LinearGradient, Path, Rect, Stop, Text as SvgText } from 'react-native-svg';

import { colors, fonts } from '../constants/theme';

const AnimatedCircle = Animated.createAnimatedComponent(Circle);

/** Circular progress ring; animates to `value` (0-100). */
export function ProgressRing({
  value,
  size = 150,
  stroke = 14,
  color = colors.primary,
  track = colors.primarySoft,
  children,
}: {
  value: number | null;
  size?: number;
  stroke?: number;
  color?: string;
  track?: string;
  children?: React.ReactNode;
}) {
  const r = (size - stroke) / 2;
  const circumference = 2 * Math.PI * r;
  const progress = useRef(new Animated.Value(0)).current;
  useEffect(() => {
    Animated.timing(progress, {
      toValue: Math.max(0, Math.min(100, value ?? 0)),
      duration: 900,
      easing: Easing.out(Easing.cubic),
      useNativeDriver: false,
    }).start();
  }, [value, progress]);
  const offset = progress.interpolate({ inputRange: [0, 100], outputRange: [circumference, 0] });
  return (
    <View style={{ width: size, height: size, alignItems: 'center', justifyContent: 'center' }}>
      <Svg width={size} height={size} style={{ position: 'absolute' }}>
        <Defs>
          <LinearGradient id="ring" x1="0" y1="0" x2="1" y2="1">
            <Stop offset="0" stopColor={color} stopOpacity="0.75" />
            <Stop offset="1" stopColor={color} />
          </LinearGradient>
        </Defs>
        <Circle cx={size / 2} cy={size / 2} r={r} stroke={track} strokeWidth={stroke} fill="none" />
        <G rotation={-90} origin={`${size / 2}, ${size / 2}`}>
          <AnimatedCircle
            cx={size / 2}
            cy={size / 2}
            r={r}
            stroke="url(#ring)"
            strokeWidth={stroke}
            strokeLinecap="round"
            fill="none"
            strokeDasharray={`${circumference} ${circumference}`}
            strokeDashoffset={offset}
          />
        </G>
      </Svg>
      {children}
    </View>
  );
}

function useWidth(initial = 300) {
  const [width, setWidth] = useState(initial);
  const onLayout = (e: LayoutChangeEvent) => setWidth(e.nativeEvent.layout.width);
  return { width, onLayout };
}

function useGrow(deps: unknown) {
  const v = useRef(new Animated.Value(0)).current;
  const [t, setT] = useState(0);
  useEffect(() => {
    v.setValue(0);
    const id = v.addListener(({ value }) => setT(value));
    Animated.timing(v, { toValue: 1, duration: 750, easing: Easing.out(Easing.cubic), useNativeDriver: false }).start();
    return () => v.removeListener(id);
  }, [deps, v]);
  return t;
}

export interface BarDatum {
  label: string;
  value: number;
  color?: string;
}

export function BarChart({ data, height = 150, maxValue, unit = '' }: { data: BarDatum[]; height?: number; maxValue?: number; unit?: string }) {
  const { width, onLayout } = useWidth();
  const t = useGrow(JSON.stringify(data));
  const max = Math.max(maxValue ?? 0, ...data.map((d) => d.value), 1);
  const chartH = height - 22;
  const gap = data.length > 10 ? 4 : 8;
  const barW = Math.max(4, (width - gap * (data.length - 1)) / Math.max(1, data.length));
  return (
    <View onLayout={onLayout}>
      <Svg width={width} height={height}>
        <Defs>
          <LinearGradient id="bar" x1="0" y1="0" x2="0" y2="1">
            <Stop offset="0" stopColor="#00C2AE" />
            <Stop offset="1" stopColor="#063862" />
          </LinearGradient>
        </Defs>
        {[0.5, 1].map((f) => (
          <Line key={f} x1={0} x2={width} y1={chartH - chartH * f} y2={chartH - chartH * f} stroke={colors.border} strokeDasharray="4 6" />
        ))}
        {data.map((d, i) => {
          const h = Math.max(d.value > 0 ? 3 : 0, (d.value / max) * (chartH - 6) * t);
          const x = i * (barW + gap);
          return (
            <G key={`${d.label}-${i}`}>
              <Rect x={x} y={chartH - h} width={barW} height={h} rx={Math.min(6, barW / 2)} fill={d.color ?? 'url(#bar)'} />
              {i % Math.ceil(data.length / 8) === 0 || i === data.length - 1 ? (
                <SvgText x={x + barW / 2} y={height - 4} fontSize={10} fill={colors.textMuted} textAnchor="middle" fontFamily={fonts.medium}>
                  {d.label}
                </SvgText>
              ) : null}
            </G>
          );
        })}
      </Svg>
      {unit ? <Text style={{ position: 'absolute', right: 0, top: 0, fontFamily: fonts.medium, fontSize: 10, color: colors.textMuted }}>max {Math.round(max)}{unit}</Text> : null}
    </View>
  );
}

/** Line chart for 0-100 scores; null values create gaps. */
export function LineChart({ values, labels, height = 160, color = colors.accent }: { values: (number | null)[]; labels: string[]; height?: number; color?: string }) {
  const { width, onLayout } = useWidth();
  const t = useGrow(JSON.stringify(values));
  const chartH = height - 24;
  const n = values.length;
  const x = (i: number) => (n <= 1 ? width / 2 : 8 + (i * (width - 16)) / (n - 1));
  const y = (v: number) => 8 + (chartH - 16) * (1 - v / 100);

  let path = '';
  let area = '';
  let started = false;
  let firstX = 0;
  let lastX = 0;
  values.forEach((v, i) => {
    if (v === null) {
      if (started) area += `L${lastX},${chartH} L${firstX},${chartH} Z `;
      started = false;
      return;
    }
    const px = x(i);
    const py = y(v * t);
    if (!started) {
      path += `M${px},${py} `;
      area += `M${px},${chartH} L${px},${py} `;
      firstX = px;
      started = true;
    } else {
      path += `L${px},${py} `;
      area += `L${px},${py} `;
    }
    lastX = px;
  });
  if (started) area += `L${lastX},${chartH} L${firstX},${chartH} Z`;
  const step = Math.ceil(n / 7);

  return (
    <View onLayout={onLayout}>
      <Svg width={width} height={height}>
        <Defs>
          <LinearGradient id="area" x1="0" y1="0" x2="0" y2="1">
            <Stop offset="0" stopColor={color} stopOpacity="0.22" />
            <Stop offset="1" stopColor={color} stopOpacity="0" />
          </LinearGradient>
        </Defs>
        {[0, 50, 100].map((g) => (
          <G key={g}>
            <Line x1={0} x2={width} y1={8 + (chartH - 16) * (1 - g / 100)} y2={8 + (chartH - 16) * (1 - g / 100)} stroke={colors.border} strokeDasharray="4 6" />
          </G>
        ))}
        <Path d={area} fill="url(#area)" />
        <Path d={path} stroke={color} strokeWidth={3} fill="none" strokeLinejoin="round" strokeLinecap="round" />
        {values.map((v, i) =>
          v === null ? null : <Circle key={i} cx={x(i)} cy={y(v * t)} r={4} fill={colors.surface} stroke={color} strokeWidth={2.5} />,
        )}
        {labels.map((l, i) =>
          i % step === 0 || i === n - 1 ? (
            <SvgText key={i} x={x(i)} y={height - 4} fontSize={10} fill={colors.textMuted} textAnchor="middle" fontFamily={fonts.medium}>
              {l}
            </SvgText>
          ) : null,
        )}
      </Svg>
    </View>
  );
}

/** Rolling real-time signal trace (e.g. band tension). */
export function Sparkline({ values, height = 54, color = colors.primary, min, max }: { values: number[]; height?: number; color?: string; min?: number; max?: number }) {
  const { width, onLayout } = useWidth(200);
  const lo = min ?? Math.min(...values, 0);
  const hi = max ?? Math.max(...values, lo + 1);
  const d = values
    .map((v, i) => `${i === 0 ? 'M' : 'L'}${(i / Math.max(1, values.length - 1)) * width},${height - 3 - ((v - lo) / (hi - lo || 1)) * (height - 6)}`)
    .join(' ');
  return (
    <View onLayout={onLayout}>
      <Svg width={width} height={height}>
        {values.length > 1 ? <Path d={d} stroke={color} strokeWidth={2.2} fill="none" strokeLinejoin="round" /> : null}
      </Svg>
    </View>
  );
}
