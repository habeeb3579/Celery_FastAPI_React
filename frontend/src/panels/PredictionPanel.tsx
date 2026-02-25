import "../styles/panels.css";
import { Card } from "../components/Card";
import { Button } from "../components/Button";
import { Select } from "../components/Select";
import { Badge } from "../components/Badge";
import { usePredict } from "../hooks/usePredict";
import type { TrainedModel, PredictResponse } from "../types";

const PLACEHOLDERS: Record<string, string> = {
  iris: "5.1, 3.5, 1.4, 0.2",
  wine: "13.2, 1.78, 2.14, 11.2, 100, 2.65, 2.76, 0.26, 1.28, 4.38, 1.05, 3.4, 1050",
  breast_cancer: "17.99, 10.38, 122.8, 1001, 0.1184, 0.2776, 0.3001, 0.1471...",
  digits: "0, 0, 5, 13, 9, 1, 0, 0, ... (64 values)",
};

interface Props {
  models: TrainedModel[];
}

export const PredictionPanel = ({ models }: Props) => {
  const {
    selectedId,
    setSelectedId,
    selectedModel,
    input,
    setInput,
    result,
    loading,
    error,
    predict,
  } = usePredict(models);

  if (models.length === 0)
    return (
      <Card title="// predict" accent="var(--blue)">
        <p className="panel-muted">No models trained yet.</p>
      </Card>
    );

  return (
    <Card title="// predict" accent="var(--blue)">
      <div className="panel-section">
        <Select
          label="Model"
          value={selectedId}
          onChange={setSelectedId}
          options={models.map((m) => m.jobId)}
        />
        {selectedModel && (
          <div className="panel-badges">
            <Badge label={selectedModel.dataset} color="var(--amber)" />
            <Badge label={selectedModel.model} color="var(--blue)" />
            <Badge
              label={`${(selectedModel.metrics.test_accuracy * 100).toFixed(1)}% acc`}
              color="var(--green)"
            />
          </div>
        )}
      </div>

      <div className="panel-section">
        <label className="panel-label">Feature Values</label>
        <textarea
          className="panel-textarea"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={selectedModel ? PLACEHOLDERS[selectedModel.dataset] : ""}
          rows={3}
        />
      </div>

      <Button
        onClick={predict}
        disabled={loading || !input}
        fullWidth
        variant="ghost"
      >
        {loading ? "⠸ predicting..." : "▶ predict"}
      </Button>

      {error && <div className="panel-error">✗ {error}</div>}
      {result && <PredictionResult result={result} />}
    </Card>
  );
};

const PredictionResult = ({ result }: { result: PredictResponse }) => (
  <div className="predict-result">
    <div className="predict-result__summary">
      <span className="predict-result__label">result:</span>
      <Badge label={result.label} color="var(--green)" />
      <Badge
        label={`${(result.confidence * 100).toFixed(1)}%`}
        color="var(--amber)"
      />
    </div>
    {result.probabilities && (
      <div className="predict-proba">
        {Object.entries(result.probabilities)
          .sort(([, a], [, b]) => b - a)
          .map(([cls, prob]) => (
            <div key={cls} className="predict-proba__row">
              <div className="predict-proba__labels">
                <span
                  className="predict-proba__cls"
                  style={{
                    color:
                      cls === result.label ? "var(--green)" : "var(--text-lo)",
                  }}
                >
                  {cls === result.label ? "▶ " : "  "}
                  {cls}
                </span>
                <span className="predict-proba__pct">
                  {(prob * 100).toFixed(1)}%
                </span>
              </div>
              <div className="predict-proba__track">
                <div
                  className="predict-proba__fill"
                  style={{
                    width: `${prob * 100}%`,
                    background:
                      cls === result.label ? "var(--green)" : "var(--blue)",
                  }}
                />
              </div>
            </div>
          ))}
      </div>
    )}
  </div>
);
