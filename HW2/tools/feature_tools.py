# tools/feature_tools.py
from __future__ import annotations
import re
from typing import Any, Dict, List, Tuple, Optional
import numpy as np
import pandas as pd

FEATURE_TOOLS_SPEC = """
Feature Tools (Agent B)

These are the ONLY tools Agent B may request. Tool calls are executed in Python and outputs are returned.

Tool: create_interaction
- Request format:
  {"tool": "create_interaction", "args": {"expression": "<EXPR>"}}
- Input:
  expression (string) supports either:
   (A) "new_col = colA / colB"
   (B) "new_col = colA + colB"
   (C) "new_col = colA - colB"
   (D) "new_col = colA * colB"
  Where colA/colB must exist in df columns.
- Behavior:
  Creates df[new_col] from the operation. Division by zero becomes NaN.
- Output:
  {"action":"create_interaction","created":true,"new_col":str,"expression":str}

Tool: encode_categorical
- Request format:
  {"tool":"encode_categorical","args":{"col":"<COLUMN_NAME>","method":"onehot|label"}}
- Behavior:
  - onehot: replaces col with one-hot columns using pandas.get_dummies (drop_first=False)
  - label: replaces col with integer codes
- Output:
  {"action":"encode_categorical","col":str,"method":str,"created_cols":[...],"dropped_original":true}

Tool: correlation_analysis
- Request format:
  {"tool":"correlation_analysis","args":{"target":"<TARGET_COLUMN_NAME>","top_n":20}}
- Behavior:
  - Computes association of features to target.
  - Numeric→numeric: abs Pearson correlation.
  - Non-numeric features are label-coded for a rough signal (not perfect, but useful).
- Output:
  {
    "action":"correlation_analysis",
    "target":str,
    "scores":[{"feature":str,"score":float,"note":str},...],
    "warnings":[...]
  }

Tool: select_top_features
- Request format:
  {"tool":"select_top_features","args":{"target":"<TARGET_COLUMN_NAME>","k":10,"keep_cols":["optional","list"]}}
- Behavior:
  - Keeps: target + top-k scored features by correlation_analysis (or keep_cols if provided).
  - Drops the rest.
- Output:
  {"action":"select_top_features","target":str,"k":int,"kept_cols":[...],"dropped_cols":[...]}
""".strip()


def _parse_interaction(expr: str) -> Tuple[str, str, str, str]:
    """
    Parse "new = a / b" etc. Returns (new_col, left, op, right)
    """
    expr = expr.strip()
    m = re.match(r"^\s*([A-Za-z_]\w*)\s*=\s*([A-Za-z_]\w*)\s*([\+\-\*/])\s*([A-Za-z_]\w*)\s*$", expr)
    if not m:
        raise ValueError("Expression must match: new_col = colA <op> colB  where <op> in + - * /")
    return m.group(1), m.group(2), m.group(3), m.group(4)


def create_interaction(df: pd.DataFrame, expression: str) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    new_col, left, op, right = _parse_interaction(expression)
    if left not in df.columns or right not in df.columns:
        raise KeyError(f"Columns not found: {left}, {right}")

    new_df = df.copy()

    a = pd.to_numeric(new_df[left], errors="coerce")
    b = pd.to_numeric(new_df[right], errors="coerce")

    if op == "+":
        new_df[new_col] = a + b
    elif op == "-":
        new_df[new_col] = a - b
    elif op == "*":
        new_df[new_col] = a * b
    elif op == "/":
        with np.errstate(divide="ignore", invalid="ignore"):
            new_df[new_col] = a / b
    else:
        raise ValueError("Unsupported operator")

    return new_df, {"action": "create_interaction", "created": True, "new_col": new_col, "expression": expression}


def encode_categorical(df: pd.DataFrame, col: str, method: str = "onehot") -> Tuple[pd.DataFrame, Dict[str, Any]]:
    if col not in df.columns:
        raise KeyError(f"Column not found: {col}")

    method = method.strip().lower()
    if method not in {"onehot", "label"}:
        raise ValueError("method must be one of: onehot, label")

    new_df = df.copy()

    if method == "onehot":
        dummies = pd.get_dummies(new_df[col].astype("string"), prefix=col, dummy_na=True)
        new_df = new_df.drop(columns=[col])
        new_df = pd.concat([new_df, dummies], axis=1)
        created_cols = list(dummies.columns)

    else:  # label
        codes = new_df[col].astype("string").fillna("__NA__").astype("category").cat.codes
        new_df[col] = codes
        created_cols = [col]

    return new_df, {
        "action": "encode_categorical",
        "col": col,
        "method": method,
        "created_cols": created_cols,
        "dropped_original": method == "onehot",
    }


def correlation_analysis(df: pd.DataFrame, target: str, top_n: int = 20) -> Dict[str, Any]:
    if target not in df.columns:
        raise KeyError(f"Target column not found: {target}")

    y = df[target]
    warnings: List[str] = []
    scores: List[Dict[str, Any]] = []

    # Make numeric target if possible
    y_num = pd.to_numeric(y, errors="coerce")
    if y_num.isna().all():
        warnings.append("Target could not be coerced to numeric; using label codes as proxy.")
        y_num = y.astype("string").fillna("__NA__").astype("category").cat.codes

    for col in df.columns:
        if col == target:
            continue

        s = df[col]
        note = ""

        if pd.api.types.is_numeric_dtype(s):
            x = pd.to_numeric(s, errors="coerce")
        else:
            # Rough proxy signal for categorical
            note = "categorical_encoded_proxy"
            x = s.astype("string").fillna("__NA__").astype("category").cat.codes

        # Correlation requires finite
        x = pd.to_numeric(x, errors="coerce")
        mask = (~x.isna()) & (~y_num.isna())
        if mask.sum() < 3:
            continue

        x_std = float(x[mask].std())
        y_std = float(y_num[mask].std())
        if x_std == 0.0 or y_std == 0.0:
            continue

        corr = float(np.corrcoef(x[mask], y_num[mask])[0, 1])
        if np.isnan(corr):
            continue

        scores.append({"feature": col, "score": abs(corr), "note": note})

    scores.sort(key=lambda d: d["score"], reverse=True)
    return {
        "action": "correlation_analysis",
        "target": target,
        "scores": scores[: int(top_n)],
        "warnings": warnings,
    }


def select_top_features(
    df: pd.DataFrame,
    target: str,
    k: int,
    keep_cols: Optional[List[str]] = None,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    if target not in df.columns:
        raise KeyError(f"Target column not found: {target}")

    if keep_cols:
        keep_set = set(keep_cols) | {target}
    else:
        # fallback: use correlation_analysis internally
        scores = correlation_analysis(df, target=target, top_n=max(k, 50))["scores"]
        top = [s["feature"] for s in scores[:k]]
        keep_set = set(top) | {target}

    dropped = [c for c in df.columns if c not in keep_set]
    kept = [c for c in df.columns if c in keep_set]

    new_df = df[kept].copy()
    return new_df, {
        "action": "select_top_features",
        "target": target,
        "k": int(k),
        "kept_cols": kept,
        "dropped_cols": dropped,
    }
