import type { NavigatorScreenParams } from '@react-navigation/native';

export type TabParamList = {
  Home: undefined;
  History: undefined;
  Device: undefined;
  Profile: undefined;
};

export type RootStackParamList = {
  Splash: undefined;
  Auth: undefined;
  Main: NavigatorScreenParams<TabParamList> | undefined;
  ExerciseSelection: undefined;
  DeviceConnect: undefined;
  LiveWorkout: { exerciseId: string; exerciseName: string };
  WorkoutResult: { sessionId: string; justFinished?: boolean };
};

declare global {
  // eslint-disable-next-line @typescript-eslint/no-namespace
  namespace ReactNavigation {
    interface RootParamList extends RootStackParamList {}
  }
}
