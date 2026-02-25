import "../styles/panels.css";
import { Card } from "../components/Card";
import { Button } from "../components/Button";
import { Select } from "../components/Select";
import { Badge } from "../components/Badge";
import { useExplain } from "../hooks/useExplain";
import type { TrainedModel, ExplainResponse } from "../types";

const PLACEHOLDERS: Record<string, string> = {
  iris: "5.1, 3.5, 1.4, 0.2",
  wine: "13.2, 1.78, 2.14, 11.2, 100, 2.65, 2.76, 0.26, 1.28, 4.38, 1.05, 3.4, 1050",
  breast_cancer: "17.99, 10.38, 122.8, 1001, 0.1184, 0.2776, 0.3001, 0.1471...",
  digits: "0, 0, 5, 13, 9, 1, 0, 0, ... (64 values)",
};

interface Props {
  models: TrainedModel[];
}

export const ExplainPanel = ({ models }: Props) => {
  const {
    selectedId,
    setSelectedId,
    selectedModel,
    explainableModels,
    input,
    setInput,
    result,
    loading,
    error,
    explain,
  } = useExplain(models);

  if (models.length === 0)
    return (
      <Card title="// explain" accent="var(--amber)">
        <p className="panel-muted">Train a model first.</p>
      </Card>
    );

  if (explainableModels.length === 0)
    return (
      <Card title="// explain prediction" accent="var(--amber)">
        <p className="panel-muted">
          Feature importances require random_forest or gradient_boosting. Train
          one first.
        </p>
      </Card>
    );

  return (
    <Card title="// explain prediction" accent="var(--amber)">
      <div className="panel-section">
        <Select
          label="Model (tree-based only)"
          value={selectedId}
          onChange={setSelectedId}
          options={explainableModels.map((m) => m.jobId)}
        />
        {selectedModel && (
          <div className="panel-badges">
            <Badge label={selectedModel.dataset} color="var(--amber)" />
            <Badge label={selectedModel.model} color="var(--blue)" />
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

      <Button onClick={explain} disabled={loading || !input} fullWidth>
        {loading ? "⠸ explaining..." : "▶ explain prediction"}
      </Button>

      {error && <div className="panel-error">✗ {error}</div>}
      {result && <ExplainResult result={result} />}
    </Card>
  );
};

const ExplainResult = ({ result }: { result: ExplainResponse }) => {
  const importances = result.feature_importances;
  const prediction = result.prediction ?? result;
  return (
    <div style={{ marginTop: 16 }}>
      <div className="explain-summary">
        <span className="explain-summary__label">prediction:</span>
        <Badge label={String(prediction.label)} color="var(--green)" />
        <Badge
          label={`${((prediction.confidence ?? 0) * 100).toFixed(1)}%`}
          color="var(--amber)"
        />
      </div>
      {importances && Object.keys(importances).length > 0 ? (
        <FeatureImportances importances={importances} />
      ) : (
        <p className="panel-muted">Feature importances not available.</p>
      )}
    </div>
  );
};

const FeatureImportances = ({
  importances,
}: {
  importances: Record<string, number>;
}) => {
  const sorted = Object.entries(importances).sort(([, a], [, b]) => b - a);
  const maxVal = sorted[0]?.[1] ?? 1;
  return (
    <div>
      <div className="importances__title">Feature Importances</div>
      <div className="importances">
        {sorted.map(([feature, importance], i) => (
          <div
            key={feature}
            className="importance-row"
            style={{ animationDelay: `${i * 0.04}s` }}
          >
            <div className="importance-row__labels">
              <span
                className="importance-row__name"
                style={{ color: i === 0 ? "var(--amber)" : "var(--text)" }}
              >
                {i === 0 ? "▶ " : "  "}
                {feature}
              </span>
              <span className="importance-row__pct">
                {(importance * 100).toFixed(2)}%
              </span>
            </div>
            <div className="importance-row__track">
              <div
                className="importance-row__fill"
                style={{
                  width: `${(importance / maxVal) * 100}%`,
                  background:
                    i === 0
                      ? "linear-gradient(90deg, #92400e, var(--amber))"
                      : "var(--blue)",
                  boxShadow: i === 0 ? "0 0 6px rgba(245,158,11,0.3)" : "none",
                }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
