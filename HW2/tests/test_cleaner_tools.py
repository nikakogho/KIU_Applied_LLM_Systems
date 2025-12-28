# tests/test_cleaner_tools.py
import pandas as pd
import pytest

from tools.cleaner_tools import (
    inspect_metadata,
    get_column_stats,
    impute_missing,
    drop_column,
)


def make_df():
    return pd.DataFrame(
        {
            "num": [1.0, None, 3.0, None],
            "cat": ["a", "b", None, "b"],
            "all_null": [None, None, None, None],
        }
    )


def test_inspect_metadata_basic():
    df = make_df()
    meta = inspect_metadata(df)

    assert meta["shape"] == (4, 3)
    assert set(meta["columns"]) == {"num", "cat", "all_null"}

    # null counts
    assert meta["null_counts"]["num"] == 2
    assert meta["null_counts"]["cat"] == 1
    assert meta["null_counts"]["all_null"] == 4

    # nunique (non-null)
    assert meta["nunique"]["cat"] == 2


def test_get_column_stats_numeric():
    df = make_df()
    stats = get_column_stats(df, "num")

    assert stats["ok"] is True
    assert stats["n_null"] == 2
    assert "describe" in stats
    assert stats["describe"]["count"] == 2  # only non-null values counted


def test_get_column_stats_categorical():
    df = make_df()
    stats = get_column_stats(df, "cat")

    assert stats["ok"] is True
    assert stats["n_null"] == 1
    assert "top_values" in stats
    # 'b' appears twice
    assert stats["top_values"]["b"] == 2


def test_get_column_stats_missing_column_returns_error_object():
    df = make_df()
    stats = get_column_stats(df, "does_not_exist")
    assert stats["ok"] is False
    assert stats["error"] == "column_not_found"


def test_impute_missing_numeric_median():
    df = make_df()
    new_df, info = impute_missing(df, "num", "median")

    assert info["action"] == "impute_missing"
    assert info["col"] == "num"
    assert info["strategy"] == "median"
    assert info["na_before"] == 2
    assert info["na_after"] == 0

    # median of [1, 3] is 2
    assert new_df["num"].isna().sum() == 0
    assert (new_df["num"] == 2.0).sum() == 2


def test_impute_missing_mode_categorical():
    df = make_df()
    new_df, info = impute_missing(df, "cat", "mode")

    assert info["na_before"] == 1
    assert info["na_after"] == 0

    # mode should be 'b' (appears 2x)
    assert new_df["cat"].isna().sum() == 0
    assert new_df.loc[2, "cat"] == "b"


def test_impute_missing_mean_on_non_numeric_raises():
    df = make_df()
    with pytest.raises(TypeError):
        impute_missing(df, "cat", "mean")


def test_impute_missing_mode_on_all_null_raises():
    df = make_df()
    with pytest.raises(ValueError):
        impute_missing(df, "all_null", "mode")


def test_impute_missing_no_missing_is_noop():
    df = pd.DataFrame({"x": [1, 2, 3]})
    new_df, info = impute_missing(df, "x", "mean")
    assert info["note"] == "no_missing_values"
    assert new_df.equals(df)


def test_drop_column_existing():
    df = make_df()
    new_df, info = drop_column(df, "cat")
    assert info["dropped"] is True
    assert "cat" not in new_df.columns
    assert new_df.shape == (4, 2)


def test_drop_column_not_found():
    df = make_df()
    new_df, info = drop_column(df, "nope")
    assert info["dropped"] is False
    assert info["reason"] == "not_found"
    assert new_df.equals(df)
