import axios, { type AxiosInstance } from "axios";
import { from, interval, throwError, type Observable } from "rxjs";
import { catchError, retry, switchMap, takeWhile, tap } from "rxjs/operators";
import type {
  TrainRequest,
  TrainJobResponse,
  TrainStatusResponse,
  PredictRequest,
  PredictResponse,
  ExplainResponse,
} from "../types";

// ── Axios instance ─────────────────────────────────────────────

const http: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? "http://localhost:8090",
  headers: { "Content-Type": "application/json" },
  timeout: 30_000,
});

// ── Interceptors ───────────────────────────────────────────────

// request: log outgoing calls in dev
http.interceptors.request.use((req) => {
  if (import.meta.env.DEV) {
    console.debug(`→ ${req.method?.toUpperCase()} ${req.url}`);
  }
  return req;
});

// response: unwrap errors into readable messages
http.interceptors.response.use(
  (res) => res,
  (err) => {
    const message =
      err.response?.data?.detail ?? err.message ?? "Request failed";
    console.error(`API error: ${message}`);
    return Promise.reject(new Error(message));
  },
);

// ── Helpers ────────────────────────────────────────────────────

/** Wrap axios promise as Observable */
const get = <T>(url: string) => from(http.get<T>(url).then((r) => r.data));
const post = <T>(url: string, body: unknown) =>
  from(http.post<T>(url, body).then((r) => r.data));

// ── REST endpoints ─────────────────────────────────────────────

export const api = {
  health: () => get<{ status: string }>("/health"),

  submitTraining: (body: TrainRequest) =>
    post<TrainJobResponse>("/train", body),

  getTrainingStatus: (jobId: string) =>
    get<TrainStatusResponse>(`/train/${jobId}/status`),

  predict: (modelId: string, body: PredictRequest) =>
    post<PredictResponse>(`/predict/${modelId}`, body),

  explain: (modelId: string, body: PredictRequest) =>
    post<ExplainResponse>(`/predict/${modelId}/explain`, body),
};

// ── Observable streams ─────────────────────────────────────────

const POLL_MS = 1500;

/**
 * pollTrainingStatus$
 *
 * Polls /train/{jobId}/status every 1.5s using RxJS.
 * Completes automatically when state leaves "pending" / "running".
 * Retries up to 3x on network errors with a 2s delay.
 * Cancellable — call sub.unsubscribe() or return from useEffect cleanup.
 *
 */
export const pollTrainingStatus$ = (
  jobId: string,
): Observable<TrainStatusResponse> =>
  interval(POLL_MS).pipe(
    switchMap(() => api.getTrainingStatus(jobId)),
    tap((s) => {
      if (import.meta.env.DEV) {
        console.debug(
          `poll [${jobId.slice(0, 8)}] state=${s.state} progress=${s.progress ?? 0}%`,
        );
      }
    }),
    // emit the terminal state once (includeComplete=true) then complete
    takeWhile((s) => s.state === "pending" || s.state === "running", true),
    retry({ count: 3, delay: 2000 }),
    catchError((err) =>
      throwError(() => new Error(`Polling failed: ${err.message}`)),
    ),
  );
