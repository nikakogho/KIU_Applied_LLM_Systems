# tools/cleaner_tools.py
from __future__ import annotations

from typing import Any, Dict, Tuple
import pandas as pd


def inspect_metadata(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Returns lightweight dataset metadata:
      - shape
      - dtypes (as strings)
      - null counts + null %
      - nunique (non-null)
    """
    null_counts = df.isna().sum()
    null_pct = (df.isna().mean() * 100).round(2)

    return {
        "shape": tuple(df.shape),
        "columns": list(df.columns),
        "dtypes": {c: str(t) for c, t in df.dtypes.items()},
        "null_counts": null_counts.to_dict(),
        "null_pct": null_pct.to_dict(),
        "nunique": df.nunique(dropna=True).to_dict(),
    }


def get_column_stats(df: pd.DataFrame, col: str, max_unique: int = 30) -> Dict[str, Any]:
    """
    Returns per-column stats used by Agent A to decide cleaning.

    For numeric columns:
      - count, mean, std, min, percentiles, max
      - number of nulls
    For non-numeric columns:
      - top value counts
      - a small sample of values
    """
    if col not in df.columns:
        return {"col": col, "ok": False, "error": "column_not_found"}

    s = df[col]
    out: Dict[str, Any] = {
        "col": col,
        "ok": True,
        "dtype": str(s.dtype),
        "n_rows": int(len(s)),
        "n_null": int(s.isna().sum()),
        "null_pct": float((s.isna().mean() * 100.0)),
    }

    if pd.api.types.is_numeric_dtype(s):
        desc = s.describe(percentiles=[0.01, 0.05, 0.5, 0.95, 0.99]).to_dict()

        # Convert numpy types / NaN to JSON-friendly python types
        def _to_py(v: Any) -> Any:
            if pd.isna(v):
                return None
            # floats/ints from numpy -> python scalar
            if hasattr(v, "item"):
                return v.item()
            return v

        out["describe"] = {k: _to_py(v) for k, v in desc.items()}

        # basic outlier hints (optional but useful)
        q1 = s.quantile(0.25)
        q3 = s.quantile(0.75)
        iqr = q3 - q1
        if pd.notna(iqr) and iqr != 0:
            low = q1 - 1.5 * iqr
            high = q3 + 1.5 * iqr
            out["iqr_outlier_bounds"] = {"low": float(low), "high": float(high)}
            out["n_iqr_outliers"] = int(((s < low) | (s > high)).sum())
        else:
            out["iqr_outlier_bounds"] = None
            out["n_iqr_outliers"] = 0

    else:
        # Cast to string safely (preserve missing)
        s_str = s.astype("string")

        vc = s_str.value_counts(dropna=True).head(max_unique)
        out["top_values"] = {str(k): int(v) for k, v in vc.items()}

        sample = s_str.dropna().head(max_unique).tolist()
        out["sample_values"] = [str(x) for x in sample]

        out["n_unique_non_null"] = int(s.nunique(dropna=True))

    return out


def impute_missing(df: pd.DataFrame, col: str, strategy: str) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Imputes missing values in column `col` using strategy in {"mean","median","mode"}.
    Returns: (new_df, info)

    Notes:
      - mean/median require numeric column (otherwise error)
      - mode works for any dtype (but if mode is empty -> error)
    """
    if col not in df.columns:
        raise KeyError(f"Column not found: {col}")

    strategy = strategy.strip().lower()
    if strategy not in {"mean", "median", "mode"}:
        raise ValueError("strategy must be one of: mean, median, mode")

    s = df[col]
    na_before = int(s.isna().sum())

    if na_before == 0:
        return df.copy(), {
            "action": "impute_missing",
            "col": col,
            "strategy": strategy,
            "fill_value": None,
            "na_before": 0,
            "na_after": 0,
            "note": "no_missing_values",
        }

    fill_value: Any

    if strategy in {"mean", "median"}:
        if not pd.api.types.is_numeric_dtype(s):
            raise TypeError(f"Column '{col}' is not numeric; cannot use {strategy}")
        fill_value = float(s.mean()) if strategy == "mean" else float(s.median())

        if pd.isna(fill_value):
            raise ValueError(f"Computed {strategy} is NaN for column '{col}'")

    else:  # mode
        m = s.mode(dropna=True)
        if m.empty:
            raise ValueError(f"Mode is empty for column '{col}' (all values may be NaN)")
        fill_value = m.iloc[0]
        # If it's pandas NA scalar, reject
        if pd.isna(fill_value):
            raise ValueError(f"Computed mode is NaN for column '{col}'")

    new_df = df.copy()
    new_df[col] = new_df[col].fillna(fill_value)
    na_after = int(new_df[col].isna().sum())

    return new_df, {
        "action": "impute_missing",
        "col": col,
        "strategy": strategy,
        "fill_value": (fill_value.item() if hasattr(fill_value, "item") else fill_value),
        "na_before": na_before,
        "na_after": na_after,
    }


def drop_column(df: pd.DataFrame, col: str) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Drops a column from the dataframe.
    Returns: (new_df, info)
    """
    if col not in df.columns:
        return df.copy(), {"action": "drop_column", "col": col, "dropped": False, "reason": "not_found"}

    new_df = df.drop(columns=[col]).copy()
    return new_df, {"action": "drop_column", "col": col, "dropped": True}

CLEANER_TOOLS_SPEC = """
Cleaner Tools (Agent A)

These are the ONLY tools you may request. You must call them by tool name exactly as written.
All tool calls are executed by Python. You will receive the tool output back in the next message.

Tool: inspect_metadata
- Call signature (Python internal): inspect_metadata(df)
- You CANNOT request this tool directly (Python runs it automatically at start and after changes).
- Output (dict):
  {
    "shape": (n_rows, n_cols),
    "columns": [col1, col2, ...],
    "dtypes": { "col": "dtype_string", ... },
    "null_counts": { "col": int, ... },
    "null_pct": { "col": float_percent, ... },
    "nunique": { "col": int, ... }
  }
- Notes:
  - null_pct is percentage in [0, 100]
  - nunique ignores NaN

Tool: get_column_stats
- Request format:
  {"tool": "get_column_stats", "args": {"col": "<COLUMN_NAME>"}}
- Input args:
  - col (string): must exist in the dataframe
- Output (dict) on success:
  Numeric column:
    {
      "col": str,
      "ok": true,
      "dtype": str,
      "n_rows": int,
      "n_null": int,
      "null_pct": float,
      "describe": {
        "count": number,
        "mean": number|null,
        "std": number|null,
        "min": number|null,
        "1%": number|null,
        "5%": number|null,
        "50%": number|null,
        "95%": number|null,
        "99%": number|null,
        "max": number|null
      },
      "iqr_outlier_bounds": {"low": float, "high": float}|null,
      "n_iqr_outliers": int
    }
  Non-numeric column:
    {
      "col": str,
      "ok": true,
      "dtype": str,
      "n_rows": int,
      "n_null": int,
      "null_pct": float,
      "top_values": {"value": count, ...},
      "sample_values": [str, str, ...],
      "n_unique_non_null": int
    }
- Output on failure:
  {"col": "<COLUMN_NAME>", "ok": false, "error": "column_not_found"}

Tool: impute_missing
- Request format:
  {"tool": "impute_missing", "args": {"col": "<COLUMN_NAME>", "strategy": "<STRATEGY>"}}
- Input args:
  - col (string): must exist
  - strategy (string): one of {"mean", "median", "mode"} (case-insensitive)
- Behavior:
  - Fills ONLY missing (NaN) values in that column.
  - mean/median require numeric dtype; otherwise the tool raises an error.
  - mode works on any dtype but fails if mode is empty (e.g., all values NaN).
- Output (dict) on success:
  {
    "action": "impute_missing",
    "col": str,
    "strategy": "mean"|"median"|"mode",
    "fill_value": any,
    "na_before": int,
    "na_after": int,
    "note": "no_missing_values"   # only present when na_before == 0
  }
- Errors you may see:
  - KeyError: column not found
  - TypeError: non-numeric with mean/median
  - ValueError: invalid strategy or computed statistic is NaN / mode empty

Tool: drop_column
- Request format:
  {"tool": "drop_column", "args": {"col": "<COLUMN_NAME>"}}
- Input args:
  - col (string)
- Behavior:
  - Drops the entire column if present.
- Output (dict):
  Success:
    {"action": "drop_column", "col": str, "dropped": true}
  Not found:
    {"action": "drop_column", "col": str, "dropped": false, "reason": "not_found"}

General guidance for tool usage:
- If unsure about a column, call get_column_stats before deciding.
- Prefer minimal cleaning; do not drop columns unless clearly unusable (e.g., IDs with near-unique values).
- Use impute_missing for moderate missingness when it makes sense.
""".strip()
