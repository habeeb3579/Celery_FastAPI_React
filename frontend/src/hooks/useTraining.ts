import { useState, useCallback } from "react";
import { firstValueFrom } from "rxjs";
import { api, pollTrainingStatus$ } from "../api/client";
import type {
  Dataset,
  ModelType,
  TrainedModel,
  TrainMetrics,
  TaskState,
  TrainingState,
} from "../types";

export type { TrainingState };

// ── Constants ──────────────────────────────────────────────────

const initialState: TrainingState = {
  status: "idle",
  progress: 0,
  stage: "",
  epoch: null,
  error: null,
  log: [],
};

const MAX_LOG_LINES = 60;

// ── Pure helpers ───────────────────────────────────────────────

const timestamp = () => new Date().toLocaleTimeString();

const toTrainedModel = (
  jobId: string,
  dataset: Dataset,
  modelType: ModelType,
  metrics: TrainMetrics,
): TrainedModel => ({
  jobId,
  dataset,
  model: modelType,
  metrics,
  trainedAt: new Date().toISOString(),
});

// ── Hook ───────────────────────────────────────────────────────

export const useTraining = (onComplete: (model: TrainedModel) => void) => {
  const [state, setState] = useState<TrainingState>(initialState);

  // ── State updaters ─────────────────────────────────────────

  const patch = (partial: Partial<TrainingState>) =>
    setState((prev) => ({ ...prev, ...partial }));

  const addLog = (msg: string) =>
    setState((prev) => ({
      ...prev,
      log: [`[${timestamp()}] ${msg}`, ...prev.log].slice(0, MAX_LOG_LINES),
    }));

  // ── Poll handlers ──────────────────────────────────────────

  const onRunning = (s: {
    progress?: number;
    stage?: string;
    epoch?: number;
  }) => {
    patch({
      progress: s.progress ?? 0,
      stage: s.stage ?? "",
      epoch: s.epoch ?? null,
    });
    if (s.epoch) addLog(`Epoch ${s.epoch} — ${s.stage}`);
  };

  const onSuccess = (
    jobId: string,
    dataset: Dataset,
    modelType: ModelType,
    metrics: TrainMetrics,
  ) => {
    patch({ status: "success", progress: 100 });
    addLog(`Done — accuracy: ${metrics.test_accuracy}`);
    onComplete(toTrainedModel(jobId, dataset, modelType, metrics));
  };

  const onFailed = (error?: string) => {
    patch({ status: "failed", error: error ?? "Unknown error" });
    addLog(`Failed: ${error}`);
  };

  const onError = (err: Error) => {
    patch({ status: "failed", error: err.message });
    addLog(`Error: ${err.message}`);
  };

  // ── Train fn ───────────────────────────────────────────────

  const trainFn = async (dataset: Dataset, modelType: ModelType) => {
    setState({ ...initialState, status: "running" });
    addLog(`Submitting → ${dataset} × ${modelType}`);

    const job = await firstValueFrom(
      api.submitTraining({ dataset, model_type: modelType }),
    );
    addLog(`Queued: ${job.job_id}`);

    const sub = pollTrainingStatus$(job.job_id).subscribe({
      next: (s) => {
        if (s.state === "running") onRunning(s);
        if (s.state === "success" && s.metrics)
          onSuccess(job.job_id, dataset, modelType, s.metrics as TrainMetrics);
        if (s.state === "failed") onFailed(s.error);
      },
      error: onError,
    });

    return () => sub.unsubscribe();
  };

  const train = useCallback(trainFn, [onComplete]);

  // ── Reset ──────────────────────────────────────────────────

  const reset = () => setState(initialState);

  return { state, train, reset };
};
