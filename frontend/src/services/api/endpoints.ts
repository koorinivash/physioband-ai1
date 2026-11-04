/** Typed wrappers for every backend endpoint used by the app (see docs/API_DOCUMENTATION.md). */
import type {
  AnalysisResult,
  DashboardSummary,
  Device,
  EndReason,
  Exercise,
  ModelInfo,
  Page,
  PerformanceResponse,
  SensorBatch,
  SensorBatchResponse,
  TokenResponse,
  User,
  UserProfile,
  WorkoutDetail,
  WorkoutSession,
} from '../../types/api';
import { http } from './client';

const tzOffset = () => -new Date().getTimezoneOffset();

export const authApi = {
  register: (name: string, email: string, password: string) =>
    http.post<TokenResponse>('/auth/register', { name, email, password }).then((r) => r.data),
  login: (email: string, password: string) =>
    http.post<TokenResponse>('/auth/login', { email, password }).then((r) => r.data),
  me: () => http.get<User>('/auth/me').then((r) => r.data),
};

export const userApi = {
  update: (data: { name?: string; profile?: UserProfile }) => http.patch<User>('/users/me', data).then((r) => r.data),
  changePassword: (current_password: string, new_password: string) =>
    http.post<{ message: string }>('/users/me/password', { current_password, new_password }).then((r) => r.data),
};

export const deviceApi = {
  register: (data: {
    device_id: string;
    device_name: string;
    firmware_version: string;
    protocol_version: number;
    ble_address?: string;
    sample_rate_hz?: number;
  }) => http.post<Device>('/devices/register', data).then((r) => r.data),
  list: () => http.get<Device[]>('/devices').then((r) => r.data),
  get: (deviceId: string) => http.get<Device>(`/devices/${encodeURIComponent(deviceId)}`).then((r) => r.data),
  remove: (deviceId: string) => http.delete(`/devices/${encodeURIComponent(deviceId)}`).then((r) => r.data),
};

export const exerciseApi = {
  list: () => http.get<Exercise[]>('/exercises').then((r) => r.data),
  get: (id: string) => http.get<Exercise>(`/exercises/${id}`).then((r) => r.data),
};

export const workoutApi = {
  start: (exercise_id: string, device_id?: string | null) =>
    http.post<WorkoutSession>('/workouts/start', { exercise_id, device_id: device_id ?? null }).then((r) => r.data),
  uploadSensorData: (sessionId: string, batch: SensorBatch) =>
    http.post<SensorBatchResponse>(`/workouts/${sessionId}/sensor-data`, batch).then((r) => r.data),
  analyze: (sessionId: string) => http.post<AnalysisResult>(`/workouts/${sessionId}/analyze`).then((r) => r.data),
  complete: (sessionId: string, end_reason: EndReason = 'user_completed') =>
    http.post<WorkoutDetail>(`/workouts/${sessionId}/complete`, { end_reason }, { timeout: 60000 }).then((r) => r.data),
  list: (page = 1, pageSize = 20) =>
    http.get<Page<WorkoutSession>>('/workouts', { params: { page, page_size: pageSize } }).then((r) => r.data),
  get: (sessionId: string) => http.get<WorkoutDetail>(`/workouts/${sessionId}`).then((r) => r.data),
};

export const mlApi = {
  modelInfo: () => http.get<ModelInfo>('/ml/model-info').then((r) => r.data),
};

export const dashboardApi = {
  summary: () =>
    http.get<DashboardSummary>('/dashboard/summary', { params: { tz_offset_minutes: tzOffset() } }).then((r) => r.data),
  performance: (days = 14) =>
    http
      .get<PerformanceResponse>('/dashboard/performance', { params: { days, tz_offset_minutes: tzOffset() } })
      .then((r) => r.data),
};
