import { useState } from "react";
import "../styles/panels.css";
import { Card } from "../components/Card";
import { Button } from "../components/Button";
import { Select } from "../components/Select";
import { Badge } from "../components/Badge";
import { ProgressBar } from "../components/ProgressBar";
import { useCompare } from "../hooks/useCompare";
import type { Dataset, TrainedModel } from "../types";

const DATASETS: Dataset[] = ["iris", "wine", "breast_cancer", "digits"];

const STATUS_COLOR: Record<string, string> = {
  pending: "var(--text-lo)",
  running: "var(--amber)",
  success: "var(--green)",
  failed: "var(--red)",
};

const STATUS_ICON: Record<string, string> = {
  pending: "○",
  running: "⠸",
  success: "●",
  failed: "✗",
};

interface Props {
  onModelTrained: (model: TrainedModel) => void;
}

export const ComparePanel = ({ onModelTrained }: Props) => {
  const [dataset, setDataset] = useState<Dataset>("iris");
  const { state, compare, reset } = useCompare(onModelTrained);

  const successResults = state.results
    .filter((r) => r.status === "success")
    .sort((a, b) => b.metrics.test_accuracy - a.metrics.test_accuracy);

  const completedCount = state.results.filter(
    (r) => r.status === "success" || r.status === "failed",
  ).length;

  const overallProgress =
    state.results.length > 0
      ? Math.round((completedCount / state.results.length) * 100)
      : 0;

  return (
    <Card title="// compare models" accent="var(--blue)">
      <div className="compare-controls">
        <Select
          label="Dataset"
          value={dataset}
          onChange={(v) => setDataset(v as Dataset)}
          options={DATASETS}
        />
        <div className="compare-controls__btns">
          <Button
            onClick={() => compare(dataset)}
            disabled={state.running}
            variant="ghost"
          >
            {state.running ? "⠸ running..." : "▶ run all models"}
          </Button>
          {!state.running && state.results.length > 0 && (
            <Button onClick={reset} variant="danger">
              reset
            </Button>
          )}
        </div>
      </div>

      {state.results.length > 0 && (
        <div className="compare-rows">
          {state.results.map((r) => (
            <div key={r.model} className="compare-row">
              <span
                className="compare-row__icon"
                style={{ color: STATUS_COLOR[r.status] }}
              >
                {STATUS_ICON[r.status]}
              </span>
              <span className="compare-row__model">{r.model}</span>
              <span
                className="compare-row__acc"
                style={{
                  color:
                    r.status === "success"
                      ? r.metrics.test_accuracy >= 0.95
                        ? "var(--green)"
                        : r.metrics.test_accuracy >= 0.85
                          ? "var(--amber)"
                          : "var(--red)"
                      : "var(--text-lo)",
                }}
              >
                {r.status === "success"
                  ? `${(r.metrics.test_accuracy * 100).toFixed(1)}%`
                  : r.status === "failed"
                    ? "failed"
                    : "—"}
              </span>
            </div>
          ))}
          {state.running && (
            <ProgressBar
              value={overallProgress}
              label="overall progress"
              color="var(--blue)"
            />
          )}
        </div>
      )}

      {successResults.length > 0 && (
        <div className="compare-ranking">
          <div className="compare-ranking__title">
            Ranking — {state.dataset}
          </div>
          {successResults.map((r, i) => {
            const isTop = i === 0 && !state.running;
            return (
              <div
                key={r.model}
                className={`compare-result ${isTop ? "compare-result--top" : ""}`}
                style={{ animationDelay: `${i * 0.05}s` }}
              >
                <div className="compare-result__header">
                  <div className="compare-result__left">
                    <span className="compare-result__rank">#{i + 1}</span>
                    <Badge
                      label={r.model}
                      color={isTop ? "var(--green)" : "var(--blue)"}
                    />
                  </div>
                  <div className="compare-result__right">
                    <span className="compare-result__cv">
                      cv {(r.metrics.cv_mean * 100).toFixed(1)}% ±
                      {(r.metrics.cv_std * 100).toFixed(1)}
                    </span>
                    <span
                      className="compare-result__acc"
                      style={{ color: isTop ? "var(--green)" : "var(--amber)" }}
                    >
                      {(r.metrics.test_accuracy * 100).toFixed(1)}%
                    </span>
                  </div>
                </div>
                <div className="compare-bar-track">
                  <div
                    className="compare-bar-fill"
                    style={{
                      width: `${r.metrics.test_accuracy * 100}%`,
                      background: isTop ? "var(--green)" : "var(--blue)",
                      boxShadow: isTop
                        ? "0 0 6px rgba(16,185,129,0.4)"
                        : "none",
                    }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      )}
    </Card>
  );
};
