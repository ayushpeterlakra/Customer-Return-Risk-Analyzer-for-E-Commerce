"""Train and evaluate the ML extension on the SYNTHETIC demo data.

Usage (from backend/, after `python -m scripts.seed`):
    python -m scripts.train

Labels come from data/synthetic_labels.csv (hidden behaviour profiles written by
the seed script), never from the rule-based score, so the models do not just
copy the rules. Results on synthetic data say nothing about real-world fraud.
"""

import json
from datetime import UTC, datetime

import joblib
import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier, export_text
from sqlalchemy import select

from app.db import session_factory
from app.ml.features import FEATURE_COLUMNS, to_row
from app.ml.predictor import model_dir
from app.models import Customer
from app.services.scoring_service import features_for_customers
from scripts.seed import LABELS_PATH

SEED = 42


def build_dataset() -> pd.DataFrame:
    labels = pd.read_csv(LABELS_PATH)
    with session_factory()() as db:
        customers = list(db.scalars(select(Customer)))
        feats = features_for_customers(db, customers)
        ids = {c.id: c.customer_id for c in customers}
    rows = [{"customer_id": ids[pk], **to_row(f)} for pk, f in feats.items()]
    df = pd.DataFrame(rows).merge(labels, on="customer_id", how="inner")
    return df


def pick_threshold(y_true, proba) -> float:
    """Threshold maximising F1 on the training data (never the test set)."""
    precision, recall, thresholds = precision_recall_curve(y_true, proba)
    f1 = 2 * precision * recall / np.clip(precision + recall, 1e-9, None)
    best = int(np.nanargmax(f1[:-1])) if len(thresholds) else 0
    return float(thresholds[best]) if len(thresholds) else 0.5


def evaluate(name, pipeline, X_train, y_train, X_test, y_test) -> dict:
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)
    cv_f1 = cross_val_score(pipeline, X_train, y_train, cv=cv, scoring="f1")
    pipeline.fit(X_train, y_train)
    threshold = pick_threshold(y_train, pipeline.predict_proba(X_train)[:, 1])
    proba = pipeline.predict_proba(X_test)[:, 1]
    pred = (proba >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_test, pred, labels=[0, 1]).ravel()
    return {
        "model": name,
        "threshold": round(threshold, 4),
        "accuracy": round(accuracy_score(y_test, pred), 4),
        "precision": round(precision_score(y_test, pred, zero_division=0), 4),
        "recall": round(recall_score(y_test, pred, zero_division=0), 4),
        "f1": round(f1_score(y_test, pred, zero_division=0), 4),
        "roc_auc": round(roc_auc_score(y_test, proba), 4),
        "cv_f1_mean": round(float(cv_f1.mean()), 4),
        "cv_f1_std": round(float(cv_f1.std()), 4),
        "confusion_matrix": {
            "true_negative": int(tn),
            "false_positive": int(fp),
            "false_negative": int(fn),
            "true_positive": int(tp),
        },
    }


def rule_baseline(df_test: pd.DataFrame, scores: dict) -> dict:
    y = df_test["synthetic_suspicious_label"].to_numpy()
    pred = np.array([1 if scores.get(cid, 0) >= 41 else 0 for cid in df_test["customer_id"]])
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    return {
        "model": "rule_based (score >= 41)",
        "accuracy": round(accuracy_score(y, pred), 4),
        "precision": round(precision_score(y, pred, zero_division=0), 4),
        "recall": round(recall_score(y, pred, zero_division=0), 4),
        "f1": round(f1_score(y, pred, zero_division=0), 4),
        "confusion_matrix": {
            "true_negative": int(tn),
            "false_positive": int(fp),
            "false_negative": int(fn),
            "true_positive": int(tp),
        },
    }


def main() -> None:
    df = build_dataset()
    X = df[FEATURE_COLUMNS].astype(float)
    y = df["synthetic_suspicious_label"].astype(int)
    # Split by customer (one row per customer), stratified so both sets keep the class balance.
    X_train, X_test, y_train, y_test, df_train, df_test = train_test_split(
        X, y, df, test_size=0.2, stratify=y, random_state=SEED
    )

    # Imputation and scaling are fitted inside the pipeline on training folds only (no leakage).
    models = {
        "logistic_regression": Pipeline(
            [
                ("impute", SimpleImputer(strategy="median", add_indicator=True)),
                ("scale", StandardScaler()),
                ("clf", LogisticRegression(class_weight="balanced", max_iter=1000, random_state=SEED)),
            ]
        ),
        "decision_tree": Pipeline(
            [
                ("impute", SimpleImputer(strategy="median", add_indicator=True)),
                (
                    "clf",
                    DecisionTreeClassifier(
                        class_weight="balanced", max_depth=4, min_samples_leaf=5, random_state=SEED
                    ),
                ),
            ]
        ),
    }
    results = {name: evaluate(name, p, X_train, y_train, X_test, y_test) for name, p in models.items()}
    selected = max(results, key=lambda n: (results[n]["f1"], results[n]["recall"]))

    from app.services.scoring_service import scoring_date  # noqa: F401  (documented reference date)

    with session_factory()() as db:
        from app.models import RiskAssessment

        rows = db.execute(
            select(Customer.customer_id, RiskAssessment.risk_score).join(
                RiskAssessment, RiskAssessment.id == Customer.latest_assessment_id
            )
        ).all()
    baseline = rule_baseline(df_test, dict(rows))

    lr = models["logistic_regression"]
    coef_names = list(lr.named_steps["impute"].get_feature_names_out(FEATURE_COLUMNS))
    coefficients = sorted(
        zip(coef_names, lr.named_steps["clf"].coef_[0].round(4).tolist(), strict=True),
        key=lambda kv: -abs(kv[1]),
    )
    tree = models["decision_tree"]
    tree_names = list(tree.named_steps["impute"].get_feature_names_out(FEATURE_COLUMNS))
    importances = sorted(
        zip(tree_names, tree.named_steps["clf"].feature_importances_.round(4).tolist(), strict=True),
        key=lambda kv: -kv[1],
    )

    metrics = {
        "trained_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "data_source": "SYNTHETIC demonstration data generated by scripts/seed.py; labels are the "
        "generator's "
        "hidden behaviour profiles, not confirmed fraud.",
        "dataset": {
            "customers": int(len(df)),
            "train": int(len(X_train)),
            "test": int(len(X_test)),
            "positive_rate": round(float(y.mean()), 4),
            "test_positives": int(y_test.sum()),
        },
        "features": FEATURE_COLUMNS,
        "selected_model": selected,
        "selection_rule": "highest F1 on the held-out test set, ties broken by recall",
        "models": results,
        "rule_based_baseline": baseline,
        "logistic_regression_coefficients": coefficients,
        "decision_tree_importances": [kv for kv in importances if kv[1] > 0],
        "decision_tree_rules": export_text(tree.named_steps["clf"], feature_names=tree_names, max_depth=4),
    }
    out = model_dir()
    out.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "selected_model": selected,
            "features": FEATURE_COLUMNS,
            "models": {n: {"pipeline": models[n], "threshold": results[n]["threshold"]} for n in models},
        },
        out / "model.joblib",
    )
    (out / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    print("Trained on SYNTHETIC data. Test-set results:")
    for name, r in [*results.items(), ("rule_based", baseline)]:
        print(
            f"  {name:<20} acc={r['accuracy']:.3f} precision={r['precision']:.3f} "
            f"recall={r['recall']:.3f} f1={r['f1']:.3f} cm={r['confusion_matrix']}"
        )
    print(f"Selected: {selected}. Saved to {out}")


if __name__ == "__main__":
    main()
