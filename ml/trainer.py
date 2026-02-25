import os
import json
import pickle
import logging
import numpy as np
from datetime import datetime
from typing import Callable, Optional

from sklearn.datasets import load_iris, load_wine, load_breast_cancer, load_digits
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score

from config import config

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════
# 1. pure data, no behaviour mixed in
#    DATASETS and MODELS are just lookup tables
#    Accessing a value is O(1) dict lookup, nothing more
# ══════════════════════════════════════════════════════════════

DATASETS: dict[str, dict] = {
    "iris":          {"loader": load_iris,          "description": "Iris flower classification (3 classes, 4 features)",         "task": "classification"},
    "wine":          {"loader": load_wine,           "description": "Wine quality classification (3 classes, 13 features)",       "task": "classification"},
    "breast_cancer": {"loader": load_breast_cancer,  "description": "Breast cancer diagnosis (binary, 30 features)",             "task": "classification"},
    "digits":        {"loader": load_digits,         "description": "Handwritten digit recognition (10 classes, 64 features)",   "task": "classification"},
}

MODELS: dict[str, dict] = {
    "random_forest":      {"class": RandomForestClassifier,    "default_params": {"n_estimators": 100, "max_depth": None, "random_state": 42, "n_jobs": -1}},
    "gradient_boosting":  {"class": GradientBoostingClassifier,"default_params": {"n_estimators": 100, "learning_rate": 0.1, "max_depth": 3, "random_state": 42}},
    "logistic_regression":{"class": LogisticRegression,        "default_params": {"max_iter": 1000, "random_state": 42, "C": 1.0}},
    "svm":                {"class": SVC,                       "default_params": {"kernel": "rbf", "probability": True, "random_state": 42, "C": 1.0}},
}

# Models that support warm-start incremental fitting
INCREMENTAL_MODELS = frozenset({"random_forest", "gradient_boosting"})


# ══════════════════════════════════════════════════════════════
# 2. training strategies as separate functions
#    Each strategy is independently testable.
# ══════════════════════════════════════════════════════════════

def _train_incremental(
    pipeline: Pipeline,
    X_train: np.ndarray,
    y_train: np.ndarray,
    params: dict,
    callback: Optional[Callable],
) -> list[dict]:
    """
    Warm-start training for tree-based models.
    Fits in 10 steps, reporting progress after each step.
    """
    n_estimators = params.get("n_estimators", 100)
    batch_size   = max(1, n_estimators // 10)
    history      = []
    range_end    = 10

    for step in range(1, range_end + 1):
        trees_so_far = min(step * batch_size, n_estimators)

        pipeline.set_params(**{"model__n_estimators": trees_so_far})
        pipeline.set_params(**{"model__warm_start": step > 1})
        pipeline.fit(X_train, y_train)

        train_acc     = pipeline.score(X_train, y_train)
        epoch_metrics = {"step": step, "trees": trees_so_far, "train_accuracy": round(float(train_acc), 4)}
        history.append(epoch_metrics)

        logger.info(f"  Step {step}/{range_end} | trees={trees_so_far} | train_acc={train_acc:.4f}")

        if callback:
            callback(step, 10, epoch_metrics)

    return history


def _train_single_fit(
    pipeline: Pipeline,
    X_train: np.ndarray,
    y_train: np.ndarray,
    params: dict,
    callback: Optional[Callable],
) -> list[dict]:
    """
    Single-shot training for models that don't support warm-start.
    (LogisticRegression, SVM)
    """
    if callback:
        callback(1, 3, {"stage": "fitting"})

    pipeline.fit(X_train, y_train)

    if callback:
        callback(2, 3, {"stage": "evaluating"})

    return []   # no epoch history for single-fit models


# dispatch table — model_type → training strategy
TRAINING_STRATEGIES: dict[str, Callable] = {
    model: _train_incremental for model in INCREMENTAL_MODELS
}
# all other models fall back to single fit — set as default in .get()


# ══════════════════════════════════════════════════════════════
# 3. EXTRACTED HELPERS — each does exactly one thing
# ══════════════════════════════════════════════════════════════

def _build_pipeline(model_type: str, params: dict, scale: bool) -> Pipeline:
    estimator = MODELS[model_type]["class"](**params)
    steps     = ([("scaler", StandardScaler())] if scale else []) + [("model", estimator)]
    return Pipeline(steps)


def _merge_params(model_type: str, overrides: dict) -> dict:
    return {**MODELS[model_type]["default_params"], **overrides}

# Type converters as pure data ──────────────────
# Each numpy type maps to a converter lambda.
# checks use a dispatch table.


_NUMPY_CONVERTERS: list[tuple] = [
    (dict,        lambda obj: {_sanitize(k): _sanitize(v) for k, v in obj.items()}),
    (list,        lambda obj: [_sanitize(v) for v in obj]),
    (np.ndarray,  lambda obj: obj.tolist()),
    (np.integer,  lambda obj: int(obj)),
    (np.floating, lambda obj: float(obj)),
]

def _sanitize(obj):
    """
    Recursively convert numpy types to native Python types.
    Celery serializes results to JSON — numpy int64/float32 etc.
    are not JSON serializable, so we convert them here.
    """
    converter = next(
        (fn for type_, fn in _NUMPY_CONVERTERS if isinstance(obj, type_)),
        None,
    )
    return converter(obj) if converter else obj


def _evaluate(
    pipeline:     Pipeline,
    X_test:       np.ndarray,
    y_test:       np.ndarray,
    X_train:      np.ndarray,
    y_train:      np.ndarray,
    cv_folds:     int,
    class_names:  list[str],
    dataset_meta: dict,
    history:      list[dict],
) -> dict:
    """Compute all evaluation metrics after training is complete."""
    y_pred     = pipeline.predict(X_test)
    cv_scores  = cross_val_score(pipeline, X_train, y_train, cv=cv_folds, scoring="accuracy", n_jobs=-1)

    metrics = {
        "test_accuracy":         round(float(accuracy_score(y_test, y_pred)), 4),
        "f1_score_weighted":     round(float(f1_score(y_test, y_pred, average="weighted")), 4),
        "cv_mean":               round(float(cv_scores.mean()), 4),
        "cv_std":                round(float(cv_scores.std()), 4),
        "cv_scores":             [round(float(s), 4) for s in cv_scores],
        "confusion_matrix":      confusion_matrix(y_test, y_pred).tolist(),
        "classification_report": classification_report(y_test, y_pred, target_names=class_names, output_dict=True),
        "training_history":      history,
        "dataset":               dataset_meta,
    }
    # sanitize all numpy types before Celery serializes to JSON
    return _sanitize(metrics)


def _build_dataset_meta(data, dataset_name: str, X: np.ndarray, y: np.ndarray) -> dict:
    return {
        "name":          dataset_name,
        "n_samples":     int(X.shape[0]),
        "n_features":    int(X.shape[1]),
        "n_classes":     int(len(np.unique(y))),
        "class_names":   list(data.target_names),
        "feature_names": list(data.feature_names),
    }


# ══════════════════════════════════════════════════════════════
# 4. MODEL TRAINER — just orchestrates the above helpers
#    Each method does one thing
# ══════════════════════════════════════════════════════════════

class ModelTrainer:
    """
    Trains sklearn models on built-in datasets.

    Config keys:
      dataset      : one of DATASETS keys  (default: "iris")
      model_type   : one of MODELS keys    (default: "random_forest")
      model_params : dict, overrides default hyperparameters
      test_size    : float, train/test split (default: 0.2)
      cv_folds     : int, cross-validation folds (default: 5)
      scale        : bool, apply StandardScaler (default: True)
    """

    def __init__(self, cfg: dict):
        self.cfg          = cfg
        self.dataset_name = cfg.get("dataset",    "iris")
        self.model_type   = cfg.get("model_type", "random_forest")
        self.test_size    = cfg.get("test_size",  0.2)
        self.cv_folds     = cfg.get("cv_folds",   5)
        self.scale        = cfg.get("scale",      True)

        self.X_train = self.X_test = self.y_train = self.y_test = None
        self.pipeline:     Optional[Pipeline] = None
        self.dataset_meta: dict               = {}

        self._validate_config()

    def _validate_config(self):
        errors = [
            f"Unknown dataset '{self.dataset_name}'. Choose from: {list(DATASETS.keys())}"
            for _ in [None] if self.dataset_name not in DATASETS
        ] + [
            f"Unknown model_type '{self.model_type}'. Choose from: {list(MODELS.keys())}"
            for _ in [None] if self.model_type not in MODELS
        ]
        if errors:
            raise ValueError(" | ".join(errors))

    # ── Stage 1: Load ──────────────────────────────────────────

    def load_data(self):
        logger.info(f"Loading dataset: {self.dataset_name}")

        data              = DATASETS[self.dataset_name]["loader"]()
        X, y              = data.data, data.target
        self.dataset_meta = _build_dataset_meta(data, self.dataset_name, X, y)

        self.X_train, self.X_test, self.y_train, self.y_test = train_test_split(
            X, y, test_size=self.test_size, random_state=42, stratify=y,
        )

        logger.info(f"Loaded — train: {len(self.X_train)}, test: {len(self.X_test)}, classes: {self.dataset_meta['n_classes']}")

    # ── Stage 2: Train ─────────────────────────────────────────

    def train(self, epoch_callback: Optional[Callable] = None) -> dict:
        logger.info(f"Training model: {self.model_type}")

        params        = _merge_params(self.model_type, self.cfg.get("model_params", {}))
        self.pipeline = _build_pipeline(self.model_type, params, self.scale)

        # dispatch to the right training strategy — no if/else needed
        strategy = TRAINING_STRATEGIES.get(self.model_type, _train_single_fit)
        history  = strategy(self.pipeline, self.X_train, self.y_train, params, epoch_callback)

        if epoch_callback:
            epoch_callback(10, 10, {"stage": "done"})

        metrics = _evaluate(
            self.pipeline, self.X_test, self.y_test,
            self.X_train, self.y_train,
            self.cv_folds, self.dataset_meta["class_names"],
            self.dataset_meta, history,
        )

        logger.info(f"Done — test_acc={metrics['test_accuracy']}, cv={metrics['cv_mean']}±{metrics['cv_std']}")
        return {"metrics": metrics}

    # ── Stage 3: Save ──────────────────────────────────────────

    def save(self, job_id: str) -> str:
        #model_dir = os.environ.get("MODEL_DIR", "models")
        model_dir = config.MODEL_DIR
        os.makedirs(model_dir, exist_ok=True)

        artifact = {
            "job_id":       job_id,
            "created_at":   datetime.utcnow().isoformat(),
            "dataset":      self.dataset_name,
            "model_type":   self.model_type,
            "config":       self.cfg,
            "dataset_meta": self.dataset_meta,
            "pipeline":     self.pipeline,
        }

        pkl_path  = os.path.join(model_dir, f"{job_id}.pkl")
        meta_path = os.path.join(model_dir, f"{job_id}.meta.json")

        with open(pkl_path, "wb") as f:
            pickle.dump(artifact, f)

        with open(meta_path, "w") as f:
            meta = {k: v for k, v in artifact.items() if k != "pipeline"}
            json.dump(_sanitize(meta), f, indent=2)

        logger.info(f"Model saved → {pkl_path}")
        return pkl_path

    def cleanup(self):
        self.pipeline = None
        self.X_train  = self.X_test = self.y_train = self.y_test = None