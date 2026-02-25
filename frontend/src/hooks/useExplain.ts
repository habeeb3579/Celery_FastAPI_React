import { useState, useEffect } from "react";
import { firstValueFrom } from "rxjs";
import { api } from "../api/client";
import type { TrainedModel, ExplainResponse } from "../types";

const EXPLAINABLE: string[] = ["random_forest", "gradient_boosting"];

interface UseExplainReturn {
  selectedId: string;
  setSelectedId: (id: string) => void;
  selectedModel: TrainedModel | undefined;
  explainableModels: TrainedModel[];
  input: string;
  setInput: (v: string) => void;
  result: ExplainResponse | null;
  loading: boolean;
  error: string;
  explain: () => void;
}

export const useExplain = (models: TrainedModel[]): UseExplainReturn => {
  const [selectedId, setSelectedId] = useState("");
  const [input, setInput] = useState("");
  const [result, setResult] = useState<ExplainResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const explainableModels = models.filter((m) => EXPLAINABLE.includes(m.model));

  useEffect(() => {
    if (explainableModels.length > 0 && !selectedId)
      setSelectedId(explainableModels[0].jobId);
  }, [models]);

  const selectedModel = explainableModels.find((m) => m.jobId === selectedId);

  // ── Handlers ───────────────────────────────────────────────

  const parseFeatures = (raw: string): number[] => {
    const features = raw.split(",").map((v) => parseFloat(v.trim()));
    if (features.some(isNaN))
      throw new Error("Enter comma-separated numbers only");
    return features;
  };

  const explainFn = () => {
    if (!selectedModel) return;
    setLoading(true);
    setError("");
    setResult(null);

    const features = (() => {
      try {
        return parseFeatures(input);
      } catch (e) {
        setError(e instanceof Error ? e.message : "Invalid input");
        setLoading(false);
        return null;
      }
    })();

    if (!features) return;

    firstValueFrom(api.explain(selectedId, { input_data: { features } }))
      .then((res) => setResult(res))
      .catch((e) => setError(e instanceof Error ? e.message : "Explain failed"))
      .finally(() => setLoading(false));
  };

  return {
    selectedId,
    setSelectedId,
    selectedModel,
    explainableModels,
    input,
    setInput,
    result,
    loading,
    error,
    explain: explainFn,
  };
};
