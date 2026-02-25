import { useState, useEffect } from "react";
import { firstValueFrom } from "rxjs";
import { api } from "../api/client";
import type { TrainedModel, PredictResponse } from "../types";

interface UsePredictReturn {
  selectedId: string;
  setSelectedId: (id: string) => void;
  selectedModel: TrainedModel | undefined;
  input: string;
  setInput: (v: string) => void;
  result: PredictResponse | null;
  loading: boolean;
  error: string;
  predict: () => void;
}

export const usePredict = (models: TrainedModel[]): UsePredictReturn => {
  const [selectedId, setSelectedId] = useState("");
  const [input, setInput] = useState("");
  const [result, setResult] = useState<PredictResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (models.length > 0 && !selectedId) setSelectedId(models[0].jobId);
  }, [models]);

  const selectedModel = models.find((m) => m.jobId === selectedId);

  // ── Handlers ───────────────────────────────────────────────

  const parseFeatures = (raw: string): number[] => {
    const features = raw.split(",").map((v) => parseFloat(v.trim()));
    if (features.some(isNaN))
      throw new Error("Enter comma-separated numbers only");
    return features;
  };

  const predictFn = () => {
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

    firstValueFrom(api.predict(selectedId, { input_data: { features } }))
      .then((res) => setResult(res))
      .catch((e) =>
        setError(e instanceof Error ? e.message : "Prediction failed"),
      )
      .finally(() => setLoading(false));
  };

  return {
    selectedId,
    setSelectedId,
    selectedModel,
    input,
    setInput,
    result,
    loading,
    error,
    predict: predictFn,
  };
};
