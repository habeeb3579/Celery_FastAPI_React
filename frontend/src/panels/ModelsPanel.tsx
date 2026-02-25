import "../styles/panels.css";
import { Card } from "../components/Card";
import { Badge } from "../components/Badge";
import { theme } from "../styles/theme";
import type { TrainedModel } from "../types";

interface Props {
  models: TrainedModel[];
}

export const ModelsPanel = ({ models }: Props) => (
  <Card title="// trained models" accent="var(--green)">
    {models.length === 0 ? (
      <p className="panel-muted">No models trained yet.</p>
    ) : (
      <div className="models-list">
        {[...models].reverse().map((m) => (
          <ModelRow key={m.jobId} model={m} />
        ))}
      </div>
    )}
  </Card>
);

const ModelRow = ({ model }: { model: TrainedModel }) => {
  const acc = model.metrics.test_accuracy;
  const accColor =
    acc >= 0.95 ? "var(--green)" : acc >= 0.85 ? "var(--amber)" : "var(--red)";

  return (
    <div className="model-row">
      <Badge label={model.dataset} color="var(--amber)" />
      <Badge label={model.model} color="var(--blue)" />
      <span className="model-row__id">{model.jobId.slice(0, 8)}...</span>
      <span className="model-row__cv">
        cv {(model.metrics.cv_mean * 100).toFixed(1)}% ±
        {(model.metrics.cv_std * 100).toFixed(1)}
      </span>
      <span className="model-row__acc" style={{ color: accColor }}>
        {(acc * 100).toFixed(1)}%
      </span>
    </div>
  );
};
