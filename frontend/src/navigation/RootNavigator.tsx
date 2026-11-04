import { Ionicons } from '@expo/vector-icons';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { DefaultTheme, NavigationContainer, type Theme } from '@react-navigation/native';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import React, { useEffect, useState } from 'react';

import { colors, fonts } from '../constants/theme';
import { useAuth } from '../context/AuthContext';
import AuthScreen from '../screens/AuthScreen';
import DashboardScreen from '../screens/DashboardScreen';
import DeviceConnectionScreen from '../screens/DeviceConnectionScreen';
import ExerciseSelectionScreen from '../screens/ExerciseSelectionScreen';
import HistoryScreen from '../screens/HistoryScreen';
import LiveWorkoutScreen from '../screens/LiveWorkoutScreen';
import ProfileScreen from '../screens/ProfileScreen';
import SplashScreen from '../screens/SplashScreen';
import WorkoutResultScreen from '../screens/WorkoutResultScreen';
import type { RootStackParamList, TabParamList } from '../types/navigation';

const Stack = createNativeStackNavigator<RootStackParamList>();
const Tab = createBottomTabNavigator<TabParamList>();

const navTheme: Theme = {
  ...DefaultTheme,
  dark: false,
  colors: {
    ...DefaultTheme.colors,
    primary: colors.primary,
    background: colors.background,
    card: colors.surface,
    text: colors.text,
    border: colors.border,
    notification: colors.coral,
  },
};

const TAB_ICONS: Record<keyof TabParamList, [React.ComponentProps<typeof Ionicons>['name'], React.ComponentProps<typeof Ionicons>['name']]> = {
  Home: ['home', 'home-outline'],
  History: ['stats-chart', 'stats-chart-outline'],
  Device: ['bluetooth', 'bluetooth-outline'],
  Profile: ['person-circle', 'person-circle-outline'],
};

const headerOptions = {
  headerShadowVisible: false,
  headerStyle: { backgroundColor: colors.background },
  headerTitleStyle: { fontFamily: fonts.bold, fontSize: 17, color: colors.text },
  headerTintColor: colors.primary,
};

function MainTabs() {
  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        headerShown: false,
        tabBarActiveTintColor: colors.primary,
        tabBarInactiveTintColor: colors.textMuted,
        tabBarLabelStyle: { fontFamily: fonts.semibold, fontSize: 11 },
        tabBarStyle: { backgroundColor: colors.surface, borderTopColor: colors.border, height: 64, paddingTop: 6 },
        tabBarIcon: ({ focused, color, size }) => <Ionicons name={TAB_ICONS[route.name][focused ? 0 : 1]} size={size} color={color} />,
      })}
    >
      <Tab.Screen name="Home" component={DashboardScreen} />
      <Tab.Screen name="History" component={HistoryScreen} />
      <Tab.Screen name="Device" component={DeviceConnectionScreen} options={{ headerShown: true, title: 'Device connection', tabBarLabel: 'Device', ...headerOptions }} />
      <Tab.Screen name="Profile" component={ProfileScreen} />
    </Tab.Navigator>
  );
}

const MIN_SPLASH_MS = 1400;

export default function RootNavigator() {
  const { user, ready } = useAuth();
  const [splashDone, setSplashDone] = useState(false);

  useEffect(() => {
    const t = setTimeout(() => setSplashDone(true), MIN_SPLASH_MS);
    return () => clearTimeout(t);
  }, []);

  const showSplash = !ready || !splashDone;

  return (
    <NavigationContainer theme={navTheme}>
      <Stack.Navigator screenOptions={{ ...headerOptions, animation: 'slide_from_right', contentStyle: { backgroundColor: colors.background } }}>
        {showSplash ? (
          <Stack.Screen name="Splash" component={SplashScreen} options={{ headerShown: false, animation: 'fade' }} />
        ) : !user ? (
          <Stack.Screen name="Auth" component={AuthScreen} options={{ headerShown: false, animation: 'fade' }} />
        ) : (
          <>
            <Stack.Screen name="Main" component={MainTabs} options={{ headerShown: false, animation: 'fade' }} />
            <Stack.Screen name="ExerciseSelection" component={ExerciseSelectionScreen} options={{ title: 'Select exercise' }} />
            <Stack.Screen name="DeviceConnect" component={DeviceConnectionScreen} options={{ title: 'Device connection' }} />
            <Stack.Screen name="LiveWorkout" component={LiveWorkoutScreen} options={{ title: 'Live workout', gestureEnabled: false }} />
            <Stack.Screen name="WorkoutResult" component={WorkoutResultScreen} options={{ title: 'Workout result', animation: 'slide_from_bottom' }} />
          </>
        )}
      </Stack.Navigator>
    </NavigationContainer>
  );
}
