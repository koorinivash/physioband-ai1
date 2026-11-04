import { Ionicons } from '@expo/vector-icons';
import { useNavigation } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';
import { LinearGradient } from 'expo-linear-gradient';
import React, { useCallback, useState } from 'react';
import { Alert, StyleSheet, Text, View } from 'react-native';

import { FadeIn, PressableScale } from '../components/animated';
import { Banner, Button, Card, Row, Screen, SectionHeader, TextField } from '../components/ui';
import { MetricLine, ModelNotice } from '../components/workout';
import { colors, fonts, gradients, radius, spacing, type } from '../constants/theme';
import { useAuth } from '../context/AuthContext';
import { useDevice } from '../context/DeviceContext';
import { useFocusData } from '../hooks/useAsync';
import { errorMessage, getApiBaseUrl } from '../services/api/client';
import { deviceApi, mlApi, userApi } from '../services/api/endpoints';
import { secureStorage } from '../services/storage/secureStorage';
import type { UserProfile } from '../types/api';
import type { RootStackParamList } from '../types/navigation';
import { formatDate } from '../utils/format';

type Nav = NativeStackNavigationProp<RootStackParamList>;

export default function ProfileScreen() {
  const navigation = useNavigation<Nav>();
  const { user, setUser, logout } = useAuth();
  const ble = useDevice();
  const loader = useCallback(async () => {
    const [devices, model] = await Promise.all([deviceApi.list(), mlApi.modelInfo().catch(() => null)]);
    return { devices, model };
  }, []);
  const { data, refresh } = useFocusData(loader);

  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(user?.name ?? '');
  const [age, setAge] = useState(user?.profile.age ? String(user.profile.age) : '');
  const [height, setHeight] = useState(user?.profile.height_cm ? String(user.profile.height_cm) : '');
  const [weight, setWeight] = useState(user?.profile.weight_kg ? String(user.profile.weight_kg) : '');
  const [arm, setArm] = useState<UserProfile['training_arm']>(user?.profile.training_arm ?? 'right');
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<{ tone: 'success' | 'danger'; text: string } | null>(null);

  const [pwOpen, setPwOpen] = useState(false);
  const [currentPw, setCurrentPw] = useState('');
  const [newPw, setNewPw] = useState('');

  const save = async () => {
    const num = (v: string) => (v.trim() ? Number(v) : null);
    const profile: UserProfile = { age: num(age), height_cm: num(height), weight_kg: num(weight), training_arm: arm };
    if ([profile.age, profile.height_cm, profile.weight_kg].some((v) => v !== null && Number.isNaN(v))) {
      setMessage({ tone: 'danger', text: 'Age, height and weight must be numbers.' });
      return;
    }
    setSaving(true);
    try {
      setUser(await userApi.update({ name: name.trim(), profile }));
      setEditing(false);
      setMessage({ tone: 'success', text: 'Profile updated.' });
    } catch (e) {
      setMessage({ tone: 'danger', text: errorMessage(e) });
    } finally {
      setSaving(false);
    }
  };

  const changePassword = async () => {
    setSaving(true);
    try {
      await userApi.changePassword(currentPw, newPw);
      setPwOpen(false);
      setCurrentPw('');
      setNewPw('');
      setMessage({ tone: 'success', text: 'Password changed.' });
    } catch (e) {
      setMessage({ tone: 'danger', text: errorMessage(e) });
    } finally {
      setSaving(false);
    }
  };

  const forget = (deviceId: string) =>
    Alert.alert('Remove device?', 'The device will be unlinked from your account. Past workouts are kept.', [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Remove',
        style: 'destructive',
        onPress: async () => {
          try {
            await deviceApi.remove(deviceId);
            await secureStorage.clearLastDevice();
            void refresh();
          } catch (e) {
            Alert.alert('Could not remove device', errorMessage(e));
          }
        },
      },
    ]);

  const confirmLogout = () =>
    Alert.alert('Log out?', 'You will need to sign in again.', [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Log out', style: 'destructive', onPress: () => void logout() },
    ]);

  const initials = (user?.name ?? '?').split(/\s+/).map((p) => p[0]).slice(0, 2).join('').toUpperCase();

  return (
    <Screen>
      <FadeIn>
        <LinearGradient colors={gradients.soft} style={styles.header}>
          <LinearGradient colors={gradients.hero} style={styles.avatar}>
            <Text style={styles.avatarText}>{initials}</Text>
          </LinearGradient>
          <Text style={[type.h2, { marginTop: spacing.md }]}>{user?.name}</Text>
          <Text style={type.body}>{user?.email}</Text>
          {user ? <Text style={type.caption}>Member since {formatDate(user.created_at)}</Text> : null}
        </LinearGradient>
      </FadeIn>

      {message ? <Banner tone={message.tone} message={message.text} style={{ marginTop: spacing.lg }} /> : null}

      <SectionHeader title="Account" action={editing ? 'Cancel' : 'Edit'} onAction={() => setEditing((e) => !e)} />
      <Card>
        {editing ? (
          <>
            <TextField label="Name" value={name} onChangeText={setName} icon="person-outline" />
            <Row style={{ gap: spacing.sm }}>
              <TextField label="Age" value={age} onChangeText={setAge} keyboardType="number-pad" style={{ flex: 1 }} />
              <TextField label="Height (cm)" value={height} onChangeText={setHeight} keyboardType="decimal-pad" style={{ flex: 1 }} />
              <TextField label="Weight (kg)" value={weight} onChangeText={setWeight} keyboardType="decimal-pad" style={{ flex: 1 }} />
            </Row>
            <Text style={styles.fieldLabel}>Training arm</Text>
            <Row style={{ gap: spacing.sm, marginBottom: spacing.lg }}>
              {(['left', 'right'] as const).map((a) => (
                <PressableScale key={a} onPress={() => setArm(a)} style={[styles.choice, arm === a && styles.choiceActive]}>
                  <Text style={[styles.choiceText, arm === a && { color: colors.primaryDark }]}>{a === 'left' ? 'Left arm' : 'Right arm'}</Text>
                </PressableScale>
              ))}
            </Row>
            <Button title="Save changes" onPress={save} loading={saving} />
          </>
        ) : (
          <>
            <MetricLine icon="person-outline" label="Name" value={user?.name ?? '—'} />
            <MetricLine icon="calendar-outline" label="Age" value={user?.profile.age ? String(user.profile.age) : '—'} />
            <MetricLine icon="resize-outline" label="Height" value={user?.profile.height_cm ? `${user.profile.height_cm} cm` : '—'} />
            <MetricLine icon="barbell-outline" label="Weight" value={user?.profile.weight_kg ? `${user.profile.weight_kg} kg` : '—'} />
            <MetricLine icon="hand-right-outline" label="Training arm" value={user?.profile.training_arm ? `${user.profile.training_arm[0].toUpperCase()}${user.profile.training_arm.slice(1)}` : '—'} />
          </>
        )}
        {!editing ? (
          pwOpen ? (
            <View style={{ marginTop: spacing.lg }}>
              <TextField label="Current password" value={currentPw} onChangeText={setCurrentPw} secure autoCapitalize="none" />
              <TextField label="New password" value={newPw} onChangeText={setNewPw} secure autoCapitalize="none" placeholder="8+ characters, letters and numbers" />
              <Row style={{ gap: spacing.sm }}>
                <Button title="Cancel" variant="ghost" size="md" onPress={() => setPwOpen(false)} style={{ flex: 1 }} />
                <Button title="Update" size="md" onPress={changePassword} loading={saving} disabled={!currentPw || newPw.length < 8} style={{ flex: 1 }} />
              </Row>
            </View>
          ) : (
            <Button title="Change password" icon="key-outline" variant="ghost" size="md" onPress={() => setPwOpen(true)} style={{ marginTop: spacing.lg }} />
          )
        ) : null}
      </Card>

      <SectionHeader title="Device settings" action="Manage" onAction={() => navigation.navigate('DeviceConnect')} />
      <Card>
        <Row style={{ marginBottom: spacing.sm }}>
          <Ionicons name="bluetooth" size={18} color={ble.state === 'connected' ? colors.success : colors.textMuted} />
          <Text style={[type.bodyStrong, { marginLeft: 8 }]}>{ble.state === 'connected' ? `Connected to ${ble.connected?.name}` : 'No device connected'}</Text>
        </Row>
        {(data?.devices ?? []).length === 0 ? (
          <Text style={type.body}>No registered devices yet. Devices are registered automatically on first connection.</Text>
        ) : (
          data!.devices.map((d) => (
            <Row key={d.id} style={styles.deviceRow}>
              <View style={{ flex: 1 }}>
                <Text style={type.bodyStrong}>{d.device_name}</Text>
                <Text style={type.caption}>
                  {d.device_id} · fw {d.firmware_version} · last used {d.last_connected_at ? formatDate(d.last_connected_at) : '—'}
                </Text>
              </View>
              <Ionicons name="trash-outline" size={20} color={colors.danger} onPress={() => forget(d.device_id)} accessibilityLabel={`Remove ${d.device_name}`} />
            </Row>
          ))
        )}
      </Card>

      <SectionHeader title="AI model" />
      <Card>
        {data?.model ? (
          <>
            <MetricLine icon="hardware-chip-outline" label="Algorithm" value={data.model.algorithm ?? 'Not loaded'} />
            <MetricLine icon="git-branch-outline" label="Version" value={data.model.model_version ?? '—'} />
            <MetricLine icon="server-outline" label="Training data" value={data.model.dataset_type ?? '—'} />
            <MetricLine icon="shield-checkmark-outline" label="Validated" value={data.model.validated ? 'Yes' : 'No'} />
            <View style={{ marginTop: spacing.md }}>
              <ModelNotice model={data.model} />
            </View>
          </>
        ) : (
          <Text style={type.body}>Model information unavailable.</Text>
        )}
      </Card>

      <SectionHeader title="About" />
      <Card>
        <MetricLine icon="cloud-outline" label="Server" value={getApiBaseUrl().replace(/^https?:\/\//, '')} />
        <MetricLine icon="information-circle-outline" label="App version" value="1.0.0" />
        <Text style={[type.caption, { marginTop: spacing.md, lineHeight: 17 }]}>
          PhysioBand AI provides exercise feedback for training purposes only. It is not a medical device and does not provide clinical diagnosis or guarantee injury prevention.
        </Text>
      </Card>

      <Button title="Log out" icon="log-out-outline" variant="ghost" onPress={confirmLogout} style={{ marginTop: spacing.xl }} />
    </Screen>
  );
}

const styles = StyleSheet.create({
  header: { alignItems: 'center', borderRadius: radius.xxl, paddingVertical: spacing.xxl, borderWidth: 1, borderColor: colors.border },
  avatar: { width: 84, height: 84, borderRadius: 30, alignItems: 'center', justifyContent: 'center' },
  avatarText: { fontFamily: fonts.extrabold, fontSize: 30, color: '#FFFFFF' },
  fieldLabel: { fontFamily: fonts.semibold, fontSize: 13, color: colors.textSecondary, marginBottom: 6 },
  choice: { flex: 1, height: 46, borderRadius: radius.lg, borderWidth: 1.5, borderColor: colors.border, alignItems: 'center', justifyContent: 'center', backgroundColor: colors.surfaceMuted },
  choiceActive: { borderColor: colors.primary, backgroundColor: colors.primaryTint },
  choiceText: { fontFamily: fonts.semibold, fontSize: 14, color: colors.textSecondary },
  deviceRow: { paddingVertical: spacing.md, borderTopWidth: 1, borderTopColor: colors.border },
});
