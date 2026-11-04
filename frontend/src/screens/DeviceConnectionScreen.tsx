import { Ionicons } from '@expo/vector-icons';
import React, { useEffect, useRef, useState } from 'react';
import { Alert, Animated, Easing, StyleSheet, Text, View } from 'react-native';

import { FadeIn, PressableScale, PulseDot } from '../components/animated';
import { Sparkline } from '../components/charts';
import { Badge, Banner, Button, Card, IconCircle, Row, Screen, SectionHeader } from '../components/ui';
import { COMMANDS } from '../constants/ble';
import { colors, fonts, radius, spacing, type } from '../constants/theme';
import { useDevice } from '../context/DeviceContext';
import { errorMessage } from '../services/api/client';
import type { DiscoveredDevice } from '../types/ble';

const STATE_TEXT: Record<string, { label: string; color: string; bg: string }> = {
  unavailable: { label: 'BLE unavailable', color: colors.danger, bg: colors.dangerSoft },
  bluetooth_off: { label: 'Bluetooth off', color: colors.warning, bg: colors.warningSoft },
  unauthorized: { label: 'Permission needed', color: colors.warning, bg: colors.warningSoft },
  idle: { label: 'Not connected', color: colors.textSecondary, bg: colors.surfaceMuted },
  scanning: { label: 'Scanning...', color: colors.info, bg: colors.infoSoft },
  connecting: { label: 'Connecting...', color: colors.info, bg: colors.infoSoft },
  connected: { label: 'Connected', color: colors.success, bg: colors.successSoft },
  reconnecting: { label: 'Reconnecting...', color: colors.warning, bg: colors.warningSoft },
  disconnected: { label: 'Disconnected', color: colors.danger, bg: colors.dangerSoft },
};

export default function DeviceConnectionScreen() {
  const device = useDevice();
  const { state, discovered, connected, info, health, error } = device;
  const [connectingId, setConnectingId] = useState<string | null>(null);
  const [tension, setTension] = useState<number[]>([]);
  const badge = STATE_TEXT[state];

  // Rolling tension trace (sampled from the 4 Hz health snapshot).
  useEffect(() => {
    const f = health.lastSample?.force_n;
    if (state !== 'connected' || f === null || f === undefined) return;
    setTension((t) => [...t.slice(-59), f]);
  }, [health, state]);

  const connect = async (d: DiscoveredDevice) => {
    setConnectingId(d.id);
    try {
      await device.connect(d);
    } catch {
      // error shown from context
    } finally {
      setConnectingId(null);
    }
  };

  const command = async (cmd: number, title: string, message: string) => {
    Alert.alert(title, message, [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Start',
        onPress: async () => {
          try {
            await device.sendCommand(cmd);
          } catch (e) {
            Alert.alert('Command failed', errorMessage(e));
          }
        },
      },
    ]);
  };

  return (
    <Screen edges={[]}>
      <FadeIn>
        <Card style={{ alignItems: 'center', paddingVertical: spacing.xxl }}>
          <Radar active={state === 'scanning' || state === 'connecting' || state === 'reconnecting'} connected={state === 'connected'} />
          <Text style={[type.h2, { marginTop: spacing.lg }]}>{connected ? connected.name : 'PhysioBand Device'}</Text>
          <Badge label={badge.label} color={badge.color} bg={badge.bg} style={{ alignSelf: 'center', marginTop: spacing.sm }} />
          {info ? (
            <Text style={[type.caption, { marginTop: spacing.sm }]}>
              {info.device_id} · firmware {info.firmware} · protocol v{info.protocol}
            </Text>
          ) : null}
        </Card>
      </FadeIn>

      {state === 'unavailable' ? <Banner tone="danger" title="Bluetooth not available" message={device.unavailableReason ?? 'This build has no BLE support.'} style={{ marginTop: spacing.lg }} /> : null}
      {state === 'bluetooth_off' ? <Banner tone="warning" message="Turn on Bluetooth in your phone settings to find the PhysioBand device." style={{ marginTop: spacing.lg }} /> : null}
      {error && state !== 'unavailable' ? <Banner tone="danger" message={error} style={{ marginTop: spacing.lg }} /> : null}

      {state === 'connected' ? (
        <>
          <SectionHeader title="Sensor data" />
          <Card>
            <Row style={{ justifyContent: 'space-between', marginBottom: spacing.md }}>
              <Row>
                <PulseDot color={health.receiving ? colors.success : colors.danger} size={8} active={health.receiving} />
                <Text style={type.bodyStrong}>{health.receiving ? 'Receiving data' : 'No data received'}</Text>
              </Row>
              <Text style={type.caption}>
                {health.samplesPerSecond} Hz · {health.packetsPerSecond} pkt/s
              </Text>
            </Row>
            <SensorRow icon="body-outline" label="Upper-arm MPU6050 (0x68)" ok={health.upperArmOk} />
            <SensorRow icon="hand-left-outline" label="Forearm MPU6050 (0x69)" ok={health.forearmOk} />
            <SensorRow icon="git-commit-outline" label="Load cell (HX711)" ok={health.loadCellOk} note={health.loadCellOk && !health.loadCellCalibrated ? 'not calibrated' : undefined} />
            <SensorRow icon="compass-outline" label="Gyroscope bias" ok={health.gyroCalibrated} okText="Calibrated" badText="Not calibrated" warnOnly />
            {health.lostPackets || health.invalidPackets ? (
              <Text style={[type.caption, { marginTop: spacing.sm }]}>
                Lost packets: {health.lostPackets} · Invalid packets: {health.invalidPackets}
              </Text>
            ) : null}
          </Card>

          <Card style={{ marginTop: spacing.md }}>
            <Row style={{ justifyContent: 'space-between' }}>
              <Text style={type.label}>Band tension</Text>
              <Text style={styles.tensionValue}>{health.lastSample?.force_n == null ? '—' : `${health.lastSample.force_n.toFixed(1)} N`}</Text>
            </Row>
            <View style={{ marginTop: spacing.sm }}>
              <Sparkline values={tension} />
            </View>
            <Text style={type.caption}>Battery level is not reported by this hardware.</Text>
          </Card>

          <SectionHeader title="Calibration" />
          <Row style={{ gap: spacing.sm }}>
            <Button
              title="Tare load cell"
              icon="scale-outline"
              variant="secondary"
              size="md"
              style={{ flex: 1 }}
              onPress={() => command(COMMANDS.TARE_LOAD_CELL, 'Tare load cell', 'Leave the band attached but slack, then press Start.')}
            />
            <Button
              title="Calibrate gyro"
              icon="compass-outline"
              variant="secondary"
              size="md"
              style={{ flex: 1 }}
              onPress={() => command(COMMANDS.CALIBRATE_GYRO, 'Calibrate gyroscopes', 'Place both sensors on a table and keep them completely still for 3 seconds.')}
            />
          </Row>
          <Button title="Disconnect" icon="close-circle-outline" variant="ghost" onPress={() => void device.disconnect()} style={{ marginTop: spacing.lg }} />
        </>
      ) : state !== 'unavailable' ? (
        <>
          <Button
            title={state === 'scanning' ? 'Scanning...' : 'Scan for devices'}
            icon="search"
            onPress={() => void device.startScan()}
            loading={state === 'scanning'}
            disabled={state === 'connecting' || state === 'reconnecting'}
            style={{ marginTop: spacing.xl }}
          />
          <SectionHeader title="Nearby devices" />
          {discovered.length === 0 ? (
            <Card>
              <Text style={[type.body, { textAlign: 'center' }]}>
                {state === 'scanning' ? 'Looking for PhysioBand devices...' : 'Power on the ESP32 and press "Scan for devices". Keep the phone within a few metres.'}
              </Text>
            </Card>
          ) : (
            discovered.map((d, i) => (
              <FadeIn key={d.id} index={i}>
                <PressableScale onPress={() => void connect(d)} style={styles.deviceRow} accessibilityRole="button" accessibilityLabel={`Connect to ${d.name}`}>
                  <IconCircle name="hardware-chip-outline" />
                  <View style={{ flex: 1, marginLeft: spacing.md }}>
                    <Text style={type.bodyStrong}>{d.name}</Text>
                    <Text style={type.caption}>
                      {d.id}
                      {d.rssi !== null ? ` · ${d.rssi} dBm` : ''}
                    </Text>
                  </View>
                  {connectingId === d.id ? <Text style={styles.connectText}>Connecting...</Text> : <Text style={styles.connectText}>Connect</Text>}
                </PressableScale>
              </FadeIn>
            ))
          )}
        </>
      ) : null}
    </Screen>
  );
}

function SensorRow({ icon, label, ok, note, okText = 'OK', badText = 'Not detected', warnOnly }: {
  icon: React.ComponentProps<typeof Ionicons>['name'];
  label: string;
  ok: boolean;
  note?: string;
  okText?: string;
  badText?: string;
  warnOnly?: boolean;
}) {
  const color = ok ? colors.success : warnOnly ? colors.warning : colors.danger;
  return (
    <Row style={styles.sensorRow}>
      <Ionicons name={icon} size={18} color={colors.textMuted} />
      <Text style={[type.body, { flex: 1, marginLeft: 10 }]}>{label}</Text>
      <Badge label={note ?? (ok ? okText : badText)} color={note ? colors.warning : color} bg={note ? colors.warningSoft : ok ? colors.successSoft : warnOnly ? colors.warningSoft : colors.dangerSoft} />
    </Row>
  );
}

/** Animated radar rings used while scanning / connecting. */
function Radar({ active, connected }: { active: boolean; connected: boolean }) {
  const rings = useRef([0, 1, 2].map(() => new Animated.Value(0))).current;
  useEffect(() => {
    if (!active) {
      rings.forEach((r) => r.setValue(0));
      return;
    }
    const anims = rings.map((r, i) =>
      Animated.loop(Animated.sequence([Animated.delay(i * 600), Animated.timing(r, { toValue: 1, duration: 1800, easing: Easing.out(Easing.ease), useNativeDriver: true })])),
    );
    anims.forEach((a) => a.start());
    return () => anims.forEach((a) => a.stop());
  }, [active, rings]);
  const tint = connected ? colors.success : colors.primary;
  return (
    <View style={{ width: 130, height: 130, alignItems: 'center', justifyContent: 'center' }}>
      {rings.map((r, i) => (
        <Animated.View
          key={i}
          style={[
            styles.ring,
            { borderColor: tint, opacity: r.interpolate({ inputRange: [0, 1], outputRange: [0.5, 0] }), transform: [{ scale: r.interpolate({ inputRange: [0, 1], outputRange: [0.5, 1.4] }) }] },
          ]}
        />
      ))}
      <View style={[styles.radarCore, { backgroundColor: connected ? colors.successSoft : colors.primaryTint }]}>
        <Ionicons name={connected ? 'bluetooth' : 'bluetooth-outline'} size={36} color={tint} />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  ring: { position: 'absolute', width: 120, height: 120, borderRadius: 60, borderWidth: 2 },
  radarCore: { width: 78, height: 78, borderRadius: 39, alignItems: 'center', justifyContent: 'center' },
  sensorRow: { paddingVertical: 10, borderTopWidth: 1, borderTopColor: colors.border },
  tensionValue: { fontFamily: fonts.bold, fontSize: 18, color: colors.primary },
  deviceRow: { flexDirection: 'row', alignItems: 'center', backgroundColor: colors.surface, borderRadius: radius.lg, padding: spacing.md + 2, borderWidth: 1, borderColor: colors.border, marginBottom: spacing.sm },
  connectText: { fontFamily: fonts.semibold, fontSize: 13, color: colors.primary },
});
