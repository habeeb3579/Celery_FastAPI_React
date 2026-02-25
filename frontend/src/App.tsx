import { useState, useCallback } from "react";
import { Header } from "./panels/Header";
import { TrainingPanel } from "./panels/TrainingPanel";
import { PredictionPanel } from "./panels/PredictionPanel";
import { ComparePanel } from "./panels/ComparePanel";
import { ExplainPanel } from "./panels/ExplainPanel";
import { ModelsPanel } from "./panels/ModelsPanel";
import "./styles/global.css";
import type { TrainedModel } from "./types";

const TAB_IDS = ["train", "compare", "predict", "explain"] as const;
type Tab = (typeof TAB_IDS)[number];

const TABS = TAB_IDS.map((id) => ({ id, label: `// ${id}` }));

export default function App() {
  const [models, setModels] = useState<TrainedModel[]>([]);
  const [activeTab, setActiveTab] = useState<Tab>("train");

  const onModelTrained = useCallback((model: TrainedModel) => {
    setModels((prev) => [...prev, model]);
  }, []);

  return (
    <div className="app">
      <Header />

      <main className="app-main">
        <div className="tabs">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`tab ${activeTab === tab.id ? "tab--active" : ""}`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {activeTab === "train" && (
          <div className="app-grid-2">
            <TrainingPanel onModelTrained={onModelTrained} />
            <ModelsPanel models={models} />
          </div>
        )}
        {activeTab === "compare" && (
          <ComparePanel onModelTrained={onModelTrained} />
        )}
        {activeTab === "predict" && <PredictionPanel models={models} />}
        {activeTab === "explain" && <ExplainPanel models={models} />}
      </main>
    </div>
  );
}
