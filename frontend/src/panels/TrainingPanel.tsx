import { useState } from "react";
import "../styles/panels.css";
import { Card } from "../components/Card";
import { Button } from "../components/Button";
import { Select } from "../components/Select";
import { ProgressBar } from "../components/ProgressBar";
import { TerminalLog } from "../components/TerminalLog";
import { useTraining } from "../hooks/useTraining";
import type { Dataset, ModelType, TrainedModel } from "../types";

const DATASETS: Dataset[] = ["iris", "wine", "breast_cancer", "digits"];
const MODELS: ModelType[] = [
  "random_forest",
  "gradient_boosting",
  "logistic_regression",
  "svm",
];

interface Props {
  onModelTrained: (model: TrainedModel) => void;
}

export const TrainingPanel = ({ onModelTrained }: Props) => {
  const [dataset, setDataset] = useState<Dataset>("iris");
  const [modelType, setModelType] = useState<ModelType>("random_forest");
  const { state, train } = useTraining(onModelTrained);

  const isRunning = state.status === "running";

  return (
    <Card title="// train model">
      <div className="panel-grid-2 panel-section">
        <Select
          label="Dataset"
          value={dataset}
          onChange={(v) => setDataset(v as Dataset)}
          options={DATASETS}
        />
        <Select
          label="Model Type"
          value={modelType}
          onChange={(v) => setModelType(v as ModelType)}
          options={MODELS}
        />
      </div>

      <Button
        onClick={() => train(dataset, modelType)}
        disabled={isRunning}
        fullWidth
      >
        {isRunning ? "⠸ training in progress..." : "▶ start training"}
      </Button>

      {isRunning && (
        <div className="training-progress">
          <ProgressBar value={state.progress} label={state.stage} />
          {state.epoch && (
            <div className="training-epoch">epoch {state.epoch}</div>
          )}
        </div>
      )}

      {state.error && <div className="training-error">✗ {state.error}</div>}

      <div className="panel-section" style={{ marginTop: 16 }}>
        <TerminalLog lines={state.log} />
      </div>
    </Card>
  );
};
