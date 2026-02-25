// ── Enums ──────────────────────────────────────────────────────

export type Dataset = "iris" | "wine" | "breast_cancer" | "digits";
export type ModelType =
  | "random_forest"
  | "gradient_boosting"
  | "logistic_regression"
  | "svm";
export type TaskState = "pending" | "running" | "success" | "failed";

// ── API request/response types ─────────────────────────────────

export interface TrainRequest {
  dataset: Dataset;
  model_type: ModelType;
  test_size?: number;
  cv_folds?: number;
  scale?: boolean;
}

export interface TrainJobResponse {
  job_id: string;
  task_id: string;
  status: string;
  dataset: Dataset;
  model_type: ModelType;
  poll_url: string;
}

export interface TrainMetrics {
  test_accuracy: number;
  f1_score_weighted: number;
  cv_mean: number;
  cv_std: number;
  cv_scores: number[];
  confusion_matrix: number[][];
  classification_report: Record<string, unknown>;
  training_history: EpochMetrics[];
}

export interface EpochMetrics {
  step: number;
  trees?: number;
  train_accuracy: number;
  stage?: string;
}

export interface TrainStatusResponse {
  state: TaskState;
  job_id: string;
  stage?: string;
  progress?: number;
  epoch?: number;
  metrics?: TrainMetrics;
  predict_url?: string;
  error?: string;
}

export interface PredictRequest {
  input_data: { features: number[] };
}

export interface PredictResponse {
  label_index: number;
  label: string;
  confidence: number;
  probabilities: Record<string, number>;
}

export interface ExplainResponse extends PredictResponse {
  prediction: PredictResponse;
  feature_values: Record<string, number>;
  feature_importances: Record<string, number> | null;
}

// ── App-level types ────────────────────────────────────────────

export interface TrainedModel {
  jobId: string;
  dataset: Dataset;
  model: ModelType;
  metrics: TrainMetrics;
  trainedAt: string;
}

// ── Hook state types ───────────────────────────────────────────

export type ApiStatus = "checking" | "online" | "offline";

export interface TrainingState {
  status: TaskState | "idle";
  progress: number;
  stage: string;
  epoch: number | null;
  error: string | null;
  log: string[];
}

export interface CompareResult {
  model: ModelType;
  jobId: string;
  metrics: TrainMetrics;
  status: "pending" | "running" | "success" | "failed";
  error?: string;
}

export interface CompareState {
  running: boolean;
  dataset: Dataset | null;
  results: CompareResult[];
}
