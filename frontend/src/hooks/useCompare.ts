import { useState, useCallback } from "react";
import { forkJoin } from "rxjs";
import { mergeMap, tap, catchError, last, map } from "rxjs/operators";
import { api, pollTrainingStatus$ } from "../api/client";
import type {
  Dataset,
  ModelType,
  TrainedModel,
  TrainMetrics,
  CompareResult,
  CompareState,
} from "../types";

export type { CompareResult, CompareState };

const MODELS: ModelType[] = [
  "random_forest",
  "gradient_boosting",
  "logistic_regression",
  "svm",
];

const initialState: CompareState = {
  running: false,
  dataset: null,
  results: [],
};

// ── Pure helper ────────────────────────────────────────────────

const buildInitialResults = (dataset: Dataset): CompareState => ({
  running: true,
  dataset,
  results: MODELS.map((model) => ({
    model,
    jobId: "",
    metrics: {} as TrainMetrics,
    status: "pending",
  })),
});

// ── Hook ───────────────────────────────────────────────────────

export const useCompare = (onModelTrained: (model: TrainedModel) => void) => {
  const [state, setState] = useState<CompareState>(initialState);

  // ── State updaters ─────────────────────────────────────────

  const patchResult = (model: ModelType, patch: Partial<CompareResult>) =>
    setState((prev) => ({
      ...prev,
      results: prev.results.map((r) =>
        r.model === model ? { ...r, ...patch } : r,
      ),
    }));

  const setDone = () => setState((prev) => ({ ...prev, running: false }));

  // ── Stream builders ────────────────────────────────────────

  const submitAllJobs = (dataset: Dataset) =>
    forkJoin(
      MODELS.map((model) =>
        api.submitTraining({ dataset, model_type: model }).pipe(
          tap((job) =>
            patchResult(model, { jobId: job.job_id, status: "running" }),
          ),
          map((job) => ({ model, jobId: job.job_id })),
        ),
      ),
    );

  const pollAllJobs =
    (dataset: Dataset) => (jobs: { model: ModelType; jobId: string }[]) =>
      forkJoin(
        jobs.map(({ model, jobId }) =>
          pollTrainingStatus$(jobId).pipe(
            last(),
            tap((s) => {
              if (s.state === "success" && s.metrics) {
                patchResult(model, {
                  status: "success",
                  metrics: s.metrics as TrainMetrics,
                });
                onModelTrained({
                  jobId,
                  dataset,
                  model,
                  metrics: s.metrics as TrainMetrics,
                  trainedAt: new Date().toISOString(),
                });
              } else {
                patchResult(model, { status: "failed", error: s.error });
              }
            }),
            catchError((err) => {
              patchResult(model, { status: "failed", error: err.message });
              return [];
            }),
          ),
        ),
      );

  // ── Compare ────────────────────────────────────────────────

  const compareFn = (dataset: Dataset) => {
    setState(buildInitialResults(dataset));
    submitAllJobs(dataset)
      .pipe(mergeMap(pollAllJobs(dataset)))
      .subscribe({ complete: setDone });
  };

  const compare = useCallback(compareFn, [onModelTrained]);

  // ── Reset ──────────────────────────────────────────────────

  const reset = () => setState(initialState);

  return { state, compare, reset };
};
