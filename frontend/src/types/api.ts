/** TypeScript mirrors of the FastAPI schemas in backend/app/schemas. Keep in sync. */

export type QualityLabel = 'correct' | 'incomplete' | 'too_fast' | 'irregular' | 'unclassified';

export interface UserProfile {
  age?: number | null;
  gender?: 'male' | 'female' | 'other' | 'prefer_not_to_say' | null;
  height_cm?: number | null;
  weight_kg?: number | null;
  dominant_arm?: 'left' | 'right' | null;
  training_arm?: 'left' | 'right' | null;
}

export interface User {
  id: string;
  name: string;
  email: string;
  created_at: string;
  profile: UserProfile;
}

export interface TokenResponse {
  access_token: string;
  token_type: 'bearer';
  expires_in: number;
  user: User;
}

export interface Device {
  id: string;
  device_id: string;
  device_name: string;
  firmware_version: string;
  protocol_version: number;
  ble_address?: string | null;
  sample_rate_hz?: number | null;
  registered_at: string;
  last_connected_at?: string | null;
}

export interface Exercise {
  id: string;
  name: string;
  description: string;
  target_muscles: string[];
  supported_movement_types: string[];
  is_active: boolean;
  order: number;
}

/** One decoded sensor sample, as sent to POST /workouts/{id}/sensor-data. */
export interface SensorSample {
  timestamp_ms: number;
  ua: (number | null)[]; // [ax, ay, az (g), gx, gy, gz (deg/s)] upper arm
  fa: (number | null)[]; // forearm, same layout
  force_n: number | null;
  status: number;
}

export interface SensorBatch {
  batch_seq: number;
  device_id?: string | null;
  protocol_version: number;
  samples: SensorSample[];
  analyze: boolean;
}

export interface ModelStatus {
  available: boolean;
  algorithm?: string | null;
  model_version?: string | null;
  dataset_type?: string | null;
  validated: boolean;
  status_note: string;
}

export interface ModelInfo extends ModelStatus {
  trained_at?: string | null;
  classes: string[];
  feature_count?: number | null;
  training_samples?: number | null;
  test_samples?: number | null;
  metrics?: Record<string, unknown> | null;
  load_error?: string | null;
}

export interface Repetition {
  number: number;
  start_timestamp_ms: number;
  end_timestamp_ms: number;
  duration_s: number;
  rom_deg: number;
  avg_force_n: number;
  peak_force_n: number;
  label: QualityLabel;
  label_display: string;
  confidence: number | null;
  probabilities?: Record<string, number> | null;
  feedback: string;
}

export interface LiveStatus {
  movement_phase: 'lifting' | 'lowering' | 'holding' | 'resting';
  upper_arm_status: 'stable' | 'moving' | 'excessive_swing';
  forearm_status: 'active' | 'still';
  current_angle_deg: number;
  current_force_n: number;
  upper_arm_swing_deg: number;
}

export interface AnalysisResult {
  exercise_id: string;
  mode: 'live' | 'final' | 'standalone';
  analyzed_at: string;
  sample_count: number;
  duration_s: number;
  total_reps: number;
  correct_reps: number;
  incorrect_reps: number;
  incomplete_reps: number;
  too_fast_reps: number;
  irregular_reps: number;
  unclassified_reps: number;
  quality_score: number | null;
  avg_tension_n: number | null;
  peak_tension_n: number | null;
  classification_available: boolean;
  reps: Repetition[];
  new_reps: Repetition[];
  live: LiveStatus | null;
  suggestions: string[];
  processing_notes: string[];
  model: ModelStatus;
}

export type SessionStatus = 'active' | 'completed' | 'interrupted';
export type EndReason = 'user_completed' | 'device_disconnected' | 'app_interrupted' | 'superseded';

export interface WorkoutSession {
  id: string;
  user_id: string;
  device_id: string | null;
  exercise_id: string;
  exercise_name: string;
  status: SessionStatus;
  start_time: string;
  end_time?: string | null;
  duration_s?: number | null;
  total_reps: number;
  correct_reps: number;
  incorrect_reps: number;
  incomplete_reps: number;
  too_fast_reps: number;
  irregular_reps: number;
  quality_score: number | null;
  avg_tension_n: number | null;
  peak_tension_n: number | null;
  sample_count: number;
  batch_count: number;
  end_reason?: EndReason | null;
  suggestions: string[];
  classification_available: boolean;
  model_dataset_type?: string | null;
}

export interface Feedback {
  repetition_number: number;
  classification: QualityLabel;
  label_display: string;
  confidence: number | null;
  message: string;
  duration_s: number;
  rom_deg: number;
  avg_force_n: number;
  timestamp: string;
}

export interface WorkoutDetail extends WorkoutSession {
  feedback: Feedback[];
}

export interface SensorBatchResponse {
  session_id: string;
  batch_seq: number;
  accepted: boolean;
  duplicate: boolean;
  stored_samples: number;
  total_samples: number;
  analysis: AnalysisResult | null;
  analysis_error: string | null;
}

export interface Page<T> {
  items: T[];
  page: number;
  page_size: number;
  total: number;
  pages: number;
}

export interface PeriodStats {
  sessions: number;
  total_reps: number;
  correct_reps: number;
  incorrect_reps: number;
  quality_score: number | null;
  active_minutes: number;
  avg_tension_n: number | null;
}

export interface DashboardSummary {
  today: PeriodStats;
  all_time: PeriodStats;
  recent_sessions: WorkoutSession[];
  active_session_id: string | null;
  model: ModelStatus;
}

export interface PerformancePoint {
  date: string;
  sessions: number;
  total_reps: number;
  correct_reps: number;
  quality_score: number | null;
  avg_tension_n: number | null;
}

export interface PerformanceResponse {
  days: number;
  points: PerformancePoint[];
  quality_trend: number | null;
  best_quality: number | null;
  total_reps: number;
}

export interface ApiErrorBody {
  error: { code: string; message: string; details?: unknown };
}
