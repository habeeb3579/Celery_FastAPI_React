import os
import pickle
import logging
import numpy as np
from typing import Union

from config import config

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════
# 1. INPUT PARSING — extract raw values first, reshape once
#
#    All three input formats reduce to the same thing:
#    a flat list of numbers → np.array reshaped to (1, -1)
#
#    So instead of one parser per format, we have one
#    extractor per format and one shared reshape at the end.
# ══════════════════════════════════════════════════════════════

def _extract_values(input_data: Union[dict, list], feature_names: list[str]) -> list:
    """
    Extract raw feature values from any supported input format.
    Returns a plain list — caller handles the numpy conversion.

    Supports:
      - plain list            → used as-is
      - {"features": [...]}   → uses the "features" key
      - {"sepal length": 5.1} → extracted in feature_names order
    """
    try:
        return input_data if isinstance(input_data, list) else input_data.get("features") or [input_data[f] for f in feature_names]
    except KeyError as e:
        raise ValueError(f"Missing feature {e}. Expected: {feature_names}")


def _to_array(values: list) -> np.ndarray:
    return np.array(values).reshape(1, -1)


# ══════════════════════════════════════════════════════════════
# 2. probability building as pure data helper
#    Both predict() and predict_batch() needed the same
#    probability dict — extracted once, used everywhere
# ══════════════════════════════════════════════════════════════

def _build_probabilities(proba: np.ndarray, class_names: list[str]) -> dict:
    return {name: round(float(p), 4) for name, p in zip(class_names, proba)}


def _build_prediction(
    label_idx:   int,
    class_names: list[str],
    proba:       np.ndarray | None,
) -> dict:
    """
    Single unified prediction builder.
    Used by both predict() and predict_batch() — no duplication.
    """
    result = {
        "label_index":   label_idx,
        "label":         class_names[label_idx],
        "probabilities": None,
        "confidence":    None,
    }

    if proba is not None:
        result["probabilities"] = _build_probabilities(proba, class_names)
        result["confidence"]    = round(float(proba.max()), 4)

    return result


# ══════════════════════════════════════════════════════════════
# 3. EXTRACTED HELPERS — each does exactly one thing
# ══════════════════════════════════════════════════════════════

def _load_artifact(model_id: str) -> dict:
    """Load a pickled model artifact from disk."""
    #model_dir = os.environ.get("MODEL_DIR", "models")
    model_dir = config.MODEL_DIR
    pkl_path  = os.path.join(model_dir, f"{model_id}.pkl")

    if not os.path.exists(pkl_path):
        raise FileNotFoundError(
            f"Model not found at '{pkl_path}'. "
            f"Train a model first with job_id='{model_id}'."
        )

    logger.info(f"Loading model from {pkl_path}")
    with open(pkl_path, "rb") as f:
        return pickle.load(f)


def _get_feature_importances(pipeline, feature_names: list[str]) -> dict | None:
    """Extract ranked feature importances for tree models, None for others."""
    model_step = pipeline.named_steps.get("model")

    if not (model_step and hasattr(model_step, "feature_importances_")):
        return None

    ranked = sorted(
        zip(feature_names, model_step.feature_importances_),
        key=lambda x: x[1],
        reverse=True,
    )
    return {name: round(float(imp), 4) for name, imp in ranked}


# ══════════════════════════════════════════════════════════════
# 4. MODEL PREDICTOR — thin, delegates to helpers above
# ══════════════════════════════════════════════════════════════

class ModelPredictor:
    """
    Loads a saved pipeline and runs predictions.

    Supports:
      - predict(input_data)    → label + probabilities
      - predict_batch(batch)   → list of predictions
      - explain(input_data)    → prediction + feature importances
      - model_info()           → metadata about the loaded model
    """

    def __init__(self, artifact: dict):
        self.pipeline      = artifact["pipeline"]
        self.model_type    = artifact["model_type"]
        self.dataset_name  = artifact["dataset"]
        self.dataset_meta  = artifact["dataset_meta"]
        self.job_id        = artifact["job_id"]
        self.created_at    = artifact["created_at"]
        self.class_names   = self.dataset_meta["class_names"]
        self.feature_names = self.dataset_meta["feature_names"]

    @classmethod
    def load(cls, model_id: str) -> "ModelPredictor":
        return cls(_load_artifact(model_id))

    # ── Input parsing ──────────────────────────────────────────

    def _parse_input(self, input_data: Union[dict, list]) -> np.ndarray:
        return _to_array(_extract_values(input_data, self.feature_names))




    # ── Predict ────────────────────────────────────────────────

    def predict(self, input_data: Union[dict, list]) -> dict:
        X         = self._parse_input(input_data)
        label_idx = int(self.pipeline.predict(X)[0])
        proba     = self.pipeline.predict_proba(X)[0] if hasattr(self.pipeline, "predict_proba") else None

        return _build_prediction(label_idx, self.class_names, proba)

    def predict_batch(self, batch: list) -> list:
        if not batch:
            return []

        X          = np.array([self._parse_input(item).flatten() for item in batch])
        label_idxs = self.pipeline.predict(X)
        probas     = self.pipeline.predict_proba(X) if hasattr(self.pipeline, "predict_proba") else None

        return [
            _build_prediction(int(idx), self.class_names, probas[i] if probas is not None else None)
            for i, idx in enumerate(label_idxs)
        ]

    # ── Explain ────────────────────────────────────────────────

    def explain(self, input_data: Union[dict, list]) -> dict:
        X = self._parse_input(input_data)

        return {
            "prediction":          self.predict(input_data),
            "feature_values":      {name: round(float(val), 4) for name, val in zip(self.feature_names, X.flatten())},
            "feature_importances": _get_feature_importances(self.pipeline, self.feature_names),
        }

    # ── Metadata ───────────────────────────────────────────────

    def model_info(self) -> dict:
        return {
            "job_id":        self.job_id,
            "model_type":    self.model_type,
            "dataset":       self.dataset_name,
            "created_at":    self.created_at,
            "n_features":    self.dataset_meta["n_features"],
            "n_classes":     self.dataset_meta["n_classes"],
            "class_names":   self.class_names,
            "feature_names": self.feature_names,
        }