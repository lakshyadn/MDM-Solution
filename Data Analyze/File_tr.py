from __future__ import annotations
import profile
#from pyexpat import model

from pandas.core import series
from sklearn.ensemble import IsolationForest
import joblib

import argparse
import os
import sys
import re
from typing import Dict, Any

import pandas as pd
import numpy as np
ML_FEATURES = ["type_code", "severity"]
MEMORY_FILE = "anomaly_memory.csv"
STRICT_DATE_REGEX = re.compile(
    r"^\d{4}[-/]\d{2}[-/]\d{2}$"
)

 # -----------------------
# Load data
# -----------------------
SEMANTIC_TO_PANDAS_DTYPE = {
    "integer": "Int64",
    "web_address": "string",
    "float": "Float64",
    "numeric_as_text": "Float64",
    "datetime": "datetime64[ns]",
    "boolean": "boolean",
    "email": "string",
    "id": "string",
    "categorical": "string",
    "free_text": "string",
    "mixed_object": "string",
    "url": "string",
    "ip_address": "string",
}



def load_data(path: str, sheet=None) -> pd.DataFrame:
    if not os.path.exists(path):
        raise FileNotFoundError(path)

    ext = os.path.splitext(path)[1].lower()

    NA_VALUES = ["", " ", "-", "NA", "N/A", "null", "None"]

    if ext in (".csv", ".txt"):
        df = pd.read_csv(
            path,
            dtype=str,
            na_values=NA_VALUES,
            keep_default_na=False
        )

    elif ext in (".xls", ".xlsx", ".xlsm"):
        if sheet is None:
            df = pd.read_excel(path, sheet_name=0, dtype=str)
        else:
            df = pd.read_excel(path, sheet_name=sheet, dtype=str)

        # Normalize Excel junk
        df = df.replace("-", np.nan)

    else:
        raise ValueError("Unsupported file type")

    # ---- Final normalization (important) ----
    # pandas 3.x removed DataFrame.applymap, so normalize column-wise.
    for col in df.columns:
        df[col] = df[col].map(lambda x: x.strip() if isinstance(x, str) else x)

    return df






def analyze_and_fix_structure(df: pd.DataFrame):
    """
    Analyzes CSV structure, detects known bad patterns,
    fixes only deterministic cases, otherwise returns warning.
    """

    issues = []

    # ---------- Case 1: Single-column CSV ----------
    if df.shape[1] == 1:
        first_val = str(df.iloc[0, 0])

        # Header-like first row
        if "," in first_val:
            headers = [h.strip() for h in first_val.split(",")]
            data = df.iloc[1:, 0].tolist()

            # Deterministic row-wise column data
            if len(data) % len(headers) == 0:
                rows = [
                    data[i:i + len(headers)]
                    for i in range(0, len(data), len(headers))
                ]
                fixed_df = pd.DataFrame(rows, columns=headers)
                return fixed_df, "row_wise_column_data_fixed"

            issues.append("single_column_with_header_but_misaligned_data")

    # ---------- Case 2: Transposed table ----------
    if df.shape[0] < df.shape[1]:
        issues.append("possible_transposed_table")

    # ---------- Case 3: Repeated header rows ----------
    header_count = sum(
        df.iloc[i].astype(str).str.contains(df.columns[0], regex=False).any()
        for i in range(min(5, len(df)))
    )
    if header_count > 1:
        issues.append("multiple_header_rows")

    # ---------- Case 4: Empty or junk CSV ----------
    if df.dropna(how="all").empty:
        issues.append("empty_or_all_null_file")

    # ---------- Final decision ----------
    if issues:
        return df, f"unfixable_structure: {', '.join(issues)}"

    return df, None
 


# -----------------------
# Type inference helpers
# -----------------------

BOOL_SET = {"true", "false", "yes", "no", "y", "n", "1", "0"}
EMAIL_REGEX = re.compile(
    r"^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$", re.IGNORECASE
)

WEB_REGEX = re.compile(
    r"^(https?:\/\/|www\.)|(\.(com|org|in|net|io|gov|edu)$)",
    re.IGNORECASE
)


URL_REGEX = re.compile(
    r"^(https?:\/\/)?(www\.)?[a-z0-9\-]+\.[a-z]{2,}([\/\?#].*)?$",
    re.IGNORECASE
)

STRICT_DATE_REGEX = re.compile(
    r"""
    ^(
        (\d{4}[-/\\]\d{2}[-/\\]\d{2}) |   # yyyy-mm-dd
        (\d{2}[-/\\]\d{2}[-/\\]\d{4})     # dd-mm-yyyy
    )$
    """,
    re.VERBOSE
)


IP_REGEX = re.compile(
    r"^(?:\d{1,3}\.){3}\d{1,3}$"
)


def regex_match_series(series: pd.Series, pattern: re.Pattern) -> pd.Series:
    """Safe regex matching for pandas series using compiled pattern."""
    return series.astype(str).map(lambda value: bool(pattern.match(value)))

def suggest_value_fix(column_profile: dict, bad_value: str) -> str:
    """
    Suggests a realistic replacement value
    based on column behavior.
    """

    dominant_type = column_profile["dominant_type"]

    # Numeric column
    if dominant_type in {"integer", "float", "numeric_as_text"}:
        return f"Replace with median value ({column_profile['numeric_stats']['median']})"

    # ID-like column
    if dominant_type == "id":
        return "Remove non-ID characters or mark as invalid ID"

    # Categorical column
    if dominant_type == "categorical":
        top_vals = column_profile["most_common_values"]
        return f"Replace with one of dominant categories: {top_vals}"

    # Web / URL
    if dominant_type == "web_address":
        return "Fix URL format (add https:// or correct domain)"

    # Free text
    if dominant_type == "free_text":
        return "Leave as-is or manually review"

    return "Manual review recommended"

def suggest_replacement(series: pd.Series, bad_indices: list[int]) -> str:
    """
    Suggests concrete replacement values using column statistics.
    """

    clean = series.dropna()

    # Numeric
    numeric = pd.to_numeric(clean, errors="coerce").dropna()
    if len(numeric) > 0 and len(numeric) / len(clean) > 0.8:
        return f"Replace with median value ({int(numeric.median())})"

    # Year-like
    if numeric.between(1900, 2100).mean() > 0.8:
        return f"Replace with most common year ({int(numeric.mode()[0])})"

    # Categorical
    top = clean.astype(str).value_counts().head(3).index.tolist()
    if len(top) > 0:
        return f"Replace with dominant value(s): {top}"

    return "Manual review required"




def infer_column_type(series: pd.Series) -> str:
    #s = series.dropna()
    
    s = series.dropna()

# 🚀 Sampling for performance
    if len(s) > 3000:
        s = s.sample(3000, random_state=42)

    
    if s.empty:
        return "empty"

    # Native pandas types
    if pd.api.types.is_bool_dtype(series):
        return "boolean"
    if pd.api.types.is_integer_dtype(series):
        return "integer"
    if pd.api.types.is_float_dtype(series):
        return "float"
    if pd.api.types.is_datetime64_any_dtype(series):
        return "datetime"

    # Object inference
        # --------------------
    # Object inference
    # --------------------
    s_str = s.astype(str).str.strip().str.lower()

    # Email
    if regex_match_series(s_str, EMAIL_REGEX).mean() > 0.9:
        return "email"
    
    # Web / URL address
    if regex_match_series(s_str, WEB_REGEX).mean() > 0.7:
        return "web_address"


    # URL / Website
    if regex_match_series(s_str, URL_REGEX).mean() > 0.9:
        return "url"

    # IP Address
    if regex_match_series(s_str, IP_REGEX).mean() > 0.9:
        return "ip_address"

    # Boolean as text
    if s_str.isin(BOOL_SET).mean() > 0.9:
        return "boolean"

    # Numeric as text
    if pd.to_numeric(s_str, errors="coerce").notna().mean() > 0.9:
        return "numeric_as_text"

    # Datetime as text
    if pd.to_datetime(s_str, errors="coerce").notna().mean() > 0.9:
        return "datetime"

    uniq = s_str.nunique()
    uniq_ratio = uniq / len(series)

    # ID-like
    if uniq_ratio > 0.9 and s_str.str.len().mean() < 30:
        return "id"

    # Categorical
    # Categorical (non-numeric enums only)
    if (
        uniq <= max(20, 0.05 * len(series))
        and pd.to_numeric(s_str, errors="coerce").isna().mean() > 0.9
        and s_str.str.len().mean() < 20
    ):
        return "categorical"
 

    # Free text
    if s_str.str.len().mean() > 30:
        return "free_text"

    return "mixed_object"
 
def compress_row_ranges(rows: list[int]) -> str:
    if not rows:
        return ""

    rows = sorted(rows)
    ranges = []
    start = prev = rows[0]

    for r in rows[1:]:
        if r == prev + 1:
            prev = r 
        else:
            ranges.append(f"{start}-{prev}" if start != prev else f"{start}")
            start = prev = r

    ranges.append(f"{start}-{prev}" if start != prev else f"{start}")
    return ", ".join(ranges)




def suggest_replacement_value(series: pd.Series, inferred_type: str):
    """
    Suggests a statistically safe replacement value.
    Explainable & deterministic.
    """
    s = series.dropna()

    if s.empty:
        return None

    try:
        if inferred_type in {"integer", "float", "numeric_as_text"}:
            return float(pd.to_numeric(s, errors="coerce").median())

        if inferred_type == "datetime":
            return s.mode().iloc[0]

        if inferred_type in {"categorical", "id", "web_address", "url"}:
            return s.mode().iloc[0]

        if inferred_type == "boolean":
            return s.mode().iloc[0]

    except Exception:
        return None

    return None


def learn_column_pattern(series: pd.Series, inferred_type: str) -> dict:
    """
    Learns dominant patterns from a column to suggest fixes later.
    """
    s = series.dropna()

    if s.empty:
        return {}

    pattern = {
        "inferred_type": inferred_type,
        "top_values": s.value_counts().head(3).to_dict()
    }

    # Numeric columns
    if inferred_type in {"integer", "float", "numeric_as_text"}:
        nums = pd.to_numeric(s, errors="coerce")
        pattern["mean"] = float(nums.mean())
        pattern["median"] = float(nums.median())

    # Datetime columns
    if inferred_type == "datetime":
        dates = pd.to_datetime(s, errors="coerce")
        pattern["most_common_date"] = str(dates.mode().iloc[0])

    return pattern



# -----------------------
# Auto-cast dataframe
# -----------------------
def auto_cast_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    for col in df.columns:
        semantic_type = infer_column_type(df[col])
        target_dtype = SEMANTIC_TO_PANDAS_DTYPE.get(semantic_type)

        try:
            if semantic_type == "datetime":
                df[col] = pd.to_datetime(df[col], errors="coerce")

            elif semantic_type in {"integer", "float", "numeric_as_text"}:
                df[col] = pd.to_numeric(df[col], errors="coerce")

            elif semantic_type == "boolean":
                df[col] = (
                    df[col]
                    .astype(str)
                    .str.lower()
                    .map({"true": True, "false": False, "1": True, "0": False})
                    .astype("boolean")
                )

            elif target_dtype:
                df[col] = df[col].astype(target_dtype)

        except Exception:
            # never break the pipeline
            pass

    return df

# -----------------------
# Datatype mismatch check
# -----------------------



def detect_mixed_datatypes(series: pd.Series, sample_size=5000) -> dict:
    """
    High-confidence mixed datatype detection.
    - Random sampling
    - Sentinel scanning (head, tail, middle)
    - Full scan only if needed
    """

    null_count = int(series.isna().sum())
    non_null = series.dropna()
    n = len(non_null)

    if n == 0:
        return {
            "mode": "empty",
            "counts": {"null": null_count},
            "percentages": {"null": 100.0},
        }

    # ---------- RANDOM SAMPLE ----------
    sample = non_null.sample(
        min(sample_size, n),
        random_state=42
    )

    # ---------- SENTINEL SCAN ----------
    sentinels = pd.concat([
        non_null.head(1000),
        non_null.tail(1000),
        non_null.iloc[n//2 : n//2 + 1000]
    ], ignore_index=True)

    probe = pd.concat([sample, sentinels]).astype(str).str.strip().str.lower()

    numeric = pd.to_numeric(probe, errors="coerce").notna().sum()
    #datetime = pd.to_datetime(probe, errors="coerce").notna().sum()
    datetime = regex_match_series(probe, STRICT_DATE_REGEX).sum()
    boolean = probe.isin({"true", "false", "1", "0", "yes", "no"}).sum()
    web_mask = regex_match_series(probe, WEB_REGEX)


    used = numeric + datetime + boolean
    string = max(0, len(probe) - used)

    contamination_ratio = (string + datetime) / max(1, len(probe))

    # ---------- ESCALATE ----------
    if contamination_ratio > 0.01:
        full = non_null.astype(str).str.strip().str.lower()

        numeric = pd.to_numeric(full, errors="coerce").notna().sum()
        #datetime = pd.to_datetime(full, errors="coerce").notna().sum()
        datetime = regex_match_series(full, STRICT_DATE_REGEX).sum()

        boolean = full.isin({"true", "false", "1", "0", "yes", "no"}).sum()

        used = numeric + datetime + boolean
        string = max(0, len(full) - used)

        mode = "full_scan_triggered"
        total = len(full)

    else:
        mode = "sentinel_sampled"
        total = len(probe)

    counts = {
        "numeric": int(numeric),
        "datetime": int(datetime),
        "boolean": int(boolean),
        "string": int(string),
        "null": int(null_count),
    }

    percentages = {
        k: round(100 * v / max(1, total), 2)
        for k, v in counts.items()
    }

    return {
        "mode": mode,
        "counts": counts
        #"percentages": percentages,
    }





def detect_semantic_mismatch(inferred_type: str, mixed_info: dict) -> dict | None:
    """
    Detects semantic mismatch between inferred column type
    and actual value-level data types.
    """
    counts = mixed_info["counts"]

    # numeric column containing strings
    if inferred_type in {"integer", "float", "numeric_as_text"}:
        if counts.get("string", 0) > 0:
            return {
                "issue": "numeric_column_contains_strings",
                "string_count": counts["string"]
            }

    # datetime column containing strings
    if inferred_type == "datetime":
        if counts.get("string", 0) > 0:
            return {
                "issue": "datetime_column_contains_strings",
                "string_count": counts["string"]
            }

    # boolean column containing strings
    if inferred_type == "boolean":
        if counts.get("string", 0) > 0:
            return {
                "issue": "boolean_column_contains_strings",
                "string_count": counts["string"]
            }

    return None
 
# -----------------------
# Main analysis
# -----------------------

def select_duplicate_key(df: pd.DataFrame, user_key: str | None = None) -> str | None:
    """
    Determines which column should be used for duplicate detection.
    Priority:
    1. User-provided column
    2. Auto-detected ID-like column
    3. First column fallback 
    """


    if user_key and user_key in df.columns:
        return user_key

    # Auto-detect ID-like column
    for col in df.columns:
        inferred = infer_column_type(df[col])
        uniq_ratio = df[col].nunique(dropna=True) / max(1, len(df))

        if inferred in {"id", "numeric_as_text", "integer"} and uniq_ratio > 0.9:
            return col

    # Fallback to first column
    return df.columns[0] if len(df.columns) > 0 else None



def analyze_dataframe(df: pd.DataFrame, duplicate_key: str | None = None) -> Dict[str, Any]:

    if duplicate_key:
        if duplicate_key not in df.columns:
            raise ValueError(
                f"Duplicate key column '{duplicate_key}' not found in data"
            )

        duplicate_count = df.duplicated(subset=[duplicate_key]).sum()
        duplicate_pct = round(100 * duplicate_count / max(1, len(df)), 2)
    else:
        duplicate_count = None
        duplicate_pct = None

    report = {
        "rows": int(len(df)),
        "columns": int(df.shape[1]),
        "duplicate_check_column": duplicate_key,
        "duplicate_rows_pct": duplicate_pct,
        "columns_analysis": {}
    }

    for col in df.columns:
        s = df[col]
        inferred = infer_column_type(s)
        
        profile = {
            "pandas_dtype": str(s.dtype),
            "inferred_type": inferred,
            "null_count": int(s.isna().sum()),
            "null_pct": round(100 * s.isna().sum() / max(1, len(df)), 2),
            "unique_values": int(s.nunique(dropna=True)),
            "_series": s
        }

        # 🔹 Full scan numeric count (for reporting only)
        profile["full_numeric_count"] = int(
            pd.to_numeric(s, errors="coerce").notna().sum()
)


        # 🔹 Attach dominant column pattern (internal use only)
        profile["_column_profile"] = {
            "dominant_type": inferred,
            "most_common_values": (
                s.dropna()
                 .astype(str)
                 .value_counts()
                 .head(5)
                 .index
                 .tolist()
            ),
            "numeric_stats": {
                "median": pd.to_numeric(s, errors="coerce").median()
            } if inferred in {"integer", "float", "numeric_as_text"} else None
        }
        profile["_series"] = s

        if inferred in {"integer", "float", "numeric_as_text", "datetime", "mixed_object"}:
            profile["mixed_datatype_analysis"] = detect_mixed_datatypes(s)
        else:
            profile["mixed_datatype_analysis"] = None
        profile["semantic_mismatch"] = detect_semantic_mismatch(
            inferred,
            profile.get("mixed_datatype_analysis") or {"counts": {}}
)



        flags = []
        if profile["null_pct"] > 40:
            flags.append("high_nulls")
        if profile["unique_values"] <= 1:
            flags.append("constant_column")
        if profile["unique_values"] / max(1, len(df)) > 0.9:
            flags.append("high_cardinality")

        profile["quality_flags"] = flags
        report["columns_analysis"][col] = profile

    report["_dataframe"] = df

    return report

def compress_row_ranges(rows: list[int], max_groups=5) -> str:
    """
    Converts [1,2,3,4,7,9,10,11] → '1–4, 7, 9–11'
    """
    if not rows:
        return ""

    rows = sorted(set(rows))
    ranges = []
    start = prev = rows[0]

    for r in rows[1:]:
        if r == prev + 1:
            prev = r
        else:
            ranges.append((start, prev))
            start = prev = r
    ranges.append((start, prev))

    formatted = []
    for s, e in ranges:
        formatted.append(str(s) if s == e else f"{s}–{e}")

    # Keep output concise
    if len(formatted) > max_groups:
        return ", ".join(formatted[:max_groups]) + " ..."

    return ", ".join(formatted)



def extract_anomalies(report: dict) -> list[dict]:
    anomalies = []

    for col, info in report["columns_analysis"].items():

        # ---- NULLS ----
        if info["null_pct"] > 5:
            series = report["_dataframe"][col]
            null_rows = series[series.isna()].index + 1

            anomalies.append({
                "column": col,
                "type": "nulls",
                "severity": info["null_pct"],
                "affected_rows": compress_row_ranges(null_rows.tolist()),
                "recommendation": "Impute missing values or remove affected rows"
    })


        # ---- MIXED DATATYPE ----
        #md = info.get("mixed_datatype_analysis") or {}
        #string_count = md.get("counts", {}).get("string", 0)
#
        #if string_count > 0 and info["inferred_type"] not in {"string", "free_text"}:
        #    anomalies.append({
        #        "column": col,
        #        "type": "mixed_datatype",
        #        "severity": string_count,
        #        "recommendation": "Standardize column values to a single datatype"
        #    })

        
        series = info.get("_series")
        if series is None:
            continue
        
        md = info.get("mixed_datatype_analysis") or {}
        string_count = md.get("counts", {}).get("string", 0)

        if string_count > 0 and info["inferred_type"] not in {"string", "free_text"}:
        
            bad_mask = (
                series.notna() &
                pd.to_numeric(series, errors="coerce").isna() &
                ~regex_match_series(series, STRICT_DATE_REGEX)
            )

            bad_rows = series[bad_mask].index + 1
            bad_values = series[bad_mask].astype(str).unique()[:3].tolist()

            suggestion = suggest_replacement(series, bad_rows.tolist())

            anomalies.append({
                "column": col,
                "type": "mixed_datatype",
                "severity": len(bad_rows),
                "affected_rows": compress_row_ranges(bad_rows.tolist()),
                "example_bad_values": bad_values,
                "recommendation": suggestion
            })


        # ---- HIGH CARDINALITY ----
        if "high_cardinality" in info.get("quality_flags", []):
            anomalies.append({
                "column": col,
                "type": "high_cardinality",
                "severity": info["unique_values"],
                "recommendation": "Verify if this column should be treated as an ID"
            })

    return anomalies



def encode_anomalies(anomalies: list[dict]) -> pd.DataFrame:
    """
    Converts anomalies into ML-friendly numeric features
    using a FIXED schema.
    """
    df = pd.DataFrame(anomalies)

    if df.empty:
        return pd.DataFrame(columns=ML_FEATURES)

    # Encode anomaly type
    df["type_code"] = df["type"].astype("category").cat.codes

    # Severity is already numeric
    df["severity"] = df["severity"].astype(float)

    # 🔒 RETURN ONLY FIXED FEATURES
    return df[ML_FEATURES]


def save_to_memory(encoded_df: pd.DataFrame):
    """
    Safely appends anomaly patterns to long-term memory
    with strict schema enforcement.
    """
    if encoded_df.empty:
        return

    # Enforce schema
    encoded_df = encoded_df[["type_code", "severity"]]

    if not os.path.exists(MEMORY_FILE):
        encoded_df.to_csv(
            MEMORY_FILE,
            index=False
        )
    else:
        encoded_df.to_csv(
            MEMORY_FILE,
            mode="a",
            header=False,
            index=False
        )

MODEL_PATH = "anomaly_model.pkl"

def get_or_train_model(current_encoded: pd.DataFrame):
    """
    Loads past anomaly memory and trains model on cumulative data.
    Always returns a model or None.
    """

    # Nothing to train on
    if current_encoded.empty and not os.path.exists(MEMORY_FILE):
        return None

    # Load training data
    if os.path.exists(MEMORY_FILE):
        try:
            memory_df = pd.read_csv(
            MEMORY_FILE,
            names=ML_FEATURES,
            header=0,
            on_bad_lines="skip"
            )

            #memory_df = pd.read_csv(MEMORY_FILE)
            train_df = pd.concat(
                [memory_df, current_encoded],
                ignore_index=True
            )
        except Exception:
            train_df = current_encoded
    else:
        train_df = current_encoded

    # Load existing model if available
    if os.path.exists(MODEL_PATH):
        try:
            return joblib.load(MODEL_PATH)
        except Exception:
            pass  # fallback to retrain

    # Train new model
    model = IsolationForest(
        n_estimators=150,
        contamination=0.05,
        random_state=42
    )

    model.fit(train_df)
    joblib.dump(model, MODEL_PATH)

    return model

def attach_confidence(anomalies, predictions):
    for i, (score, label) in enumerate(predictions):
        confidence = round(abs(score), 3)

        anomalies[i]["ml_score"] = confidence
        anomalies[i]["ml_flag"] = "anomaly" if label == -1 else "normal"

        if label == -1 and confidence > 0.25:
            anomalies[i]["recommendation_confidence"] = "high"
        elif label == -1:
            anomalies[i]["recommendation_confidence"] = "medium"


def predict_anomaly_scores(model, X: pd.DataFrame):
    if model is None or X.empty:
        return []

    # 🔒 FORCE SAME FEATURE ORDER
    X = X[ML_FEATURES]

    scores = model.decision_function(X)
    labels = model.predict(X)  # -1 = anomaly

    return list(zip(scores, labels))


# -----------------------
# Pretty print
# -----------------------
def pretty_print(report: Dict[str, Any]) -> None:
    print("\n" + "═" * 44)
    print("📊 DATA QUALITY SUMMARY")
    print("═" * 44)
    print(f"Rows: {report['rows']:,} | Columns: {report['columns']}")
    print(f"Duplicate Rows: {report['duplicate_rows_pct']}%")
    print(f"Duplicate Check Column: {report['duplicate_check_column']}")
    print(f"Duplicate Rows: {report['duplicate_rows_pct']}%")


    for col, info in report["columns_analysis"].items():
        print("\n" + "─" * 44)
        print(f"🔹 Column: {col}")
        print("─" * 44)

        print(f"Type (Inferred) : {info['inferred_type'].replace('_', ' ').title()}")
        print(f"Nulls           : {info['null_count']} ({info['null_pct']}%)")
        print(f"Unique Values   : {info['unique_values']:,}")

        if "full_numeric_count" in info:
            print(f"Numeric Values  : {info['full_numeric_count']:,} (full scan)")


        # Semantic mismatch
        if info.get("semantic_mismatch"):
            sm = info["semantic_mismatch"]
            print("\n❌ Data Issue Detected")
            print(f"• {sm['issue'].replace('_', ' ').capitalize()} "
                  f"({sm['string_count']} rows)")


        md = info.get("mixed_datatype_analysis")
        if md:
            counts = md["counts"]
            real_types = {k: v for k, v in counts.items() if v > 0 and k != "null"}

            if len(real_types) > 1:
                print("\n⚠ Mixed Data Types Detected")
                print(f"   Analysis Mode : {md['mode'].replace('_', ' ').title()}")
                for t, c in real_types.items():
                    print(f"   • {t.capitalize():9}: {c:,}")




        # Flags
        if info["quality_flags"]:
            print(f"\n⚠ Flags: {', '.join(info['quality_flags']).replace('_', ' ').title()}")


# -----------------------
# Entry point
# -----------------------
def main(argv=None):
    parser = argparse.ArgumentParser(description="Universal Data Inspector")
    parser.add_argument("file", help="Path to CSV / Excel file")
    parser.add_argument("--sheet", help="Excel sheet name or index", default=None)
    args = parser.parse_args(argv)

    # ---- Resolve sheet first ----
    sheet = args.sheet
    if sheet is not None:
        try:
            sheet = int(sheet)
        except ValueError:
            pass

    # ---- Load data ONCE ----
    try:
        raw_df = load_data(args.file, sheet)
    except Exception as e:
        print("Error loading file:", e, file=sys.stderr)
        sys.exit(1)

    # ---- Structural intelligence layer ----
    fixed_df, structure_status = analyze_and_fix_structure(raw_df)

    if structure_status:
        if structure_status.startswith("row_wise"):
            print("\n⚠ STRUCTURE ISSUE DETECTED")
            print(f"✔ Auto-fix applied: {structure_status}")
            raw_df = fixed_df
        else:
            print("\n❌ STRUCTURE ISSUE DETECTED")
            print(f"Reason: {structure_status}")
            print("Analysis stopped to prevent incorrect inference.")
            sys.exit(1)

    # ---- Existing pipeline (unchanged) ----
    clean_df = auto_cast_dataframe(raw_df.copy())
    report = analyze_dataframe(raw_df)
    pretty_print(report)

def recommend_fix(anomaly: dict) -> str | None:
    """
    Rule-first, ML-assisted recommendation engine.
    ML can rank confidence, but rules decide validity.
    """

    col = anomaly["column"]
    t = anomaly["type"]
    pattern = anomaly.get("pattern", {})
    inferred = pattern.get("inferred_type")

    # ---------------- NULL VALUES ----------------
    if t == "nulls":
        top_vals = pattern.get("top_values", {})
        if top_vals:
            v = list(top_vals.keys())[0]
            return f"Replace nulls with most frequent value '{v}'"
        return "Impute missing values based on column context"

    # ---------------- MIXED DATATYPE ----------------
    if t == "mixed_datatype":
        if inferred in {"integer", "float", "numeric_as_text"}:
            return "Convert all values to numeric and remove invalid entries"
        if inferred == "datetime":
            return "Standardize values to a single date format"
        return "Standardize all values to the dominant datatype"

    # ---------------- HIGH CARDINALITY ----------------
    if t == "high_cardinality":
        # ❌ NEVER suggest ID for Name / Text
        if inferred in {"free_text", "string"}:
            return "High uniqueness detected — verify if this column should be normalized"
        return "Verify if this column represents a unique identifier (ID)"

    return None

def analyze_file_for_ui(file_path: str, sheet=None, duplicate_key=None):
    """
    Entry point for UI usage (Streamlit / Web).
    Reuses the existing analysis logic safely.
    """
    raw_df = load_data(file_path, sheet)

    fixed_df, structure_status = analyze_and_fix_structure(raw_df)
    if structure_status and structure_status.startswith("row_wise"):
        raw_df = fixed_df

    clean_df = auto_cast_dataframe(raw_df.copy())

    #  PASS duplicate_key HERE
    report = analyze_dataframe(raw_df, duplicate_key=duplicate_key)
    anomalies = extract_anomalies(report)
    encoded = encode_anomalies(anomalies)
    save_to_memory(encoded)
    
    model = get_or_train_model(encoded)

    if model is not None and not encoded.empty:
        predictions = predict_anomaly_scores(model, encoded)
        attach_confidence(anomalies, predictions)
        for a in anomalies:
            a["recommendation"] = recommend_fix(a)


    else:
        predictions = []


    for a in anomalies:
        a["recommendation"] = recommend_fix(a)

    ml_status = {
    "enabled": True,
    "memory_records": int(len(encoded)),
    "model_ready": os.path.exists(MODEL_PATH),
}

    # 🚫 Remove non-serializable internal objects
    for col_info in report["columns_analysis"].values():
        col_info.pop("_series", None)


    report.pop("_dataframe", None)

    return {
    "structure_status": structure_status,
    "report": report,
    "anomalies": anomalies,
    "ml_status": ml_status
}

    

def make_json_safe(obj):
    """
    Recursively converts numpy / pandas objects
    into JSON-serializable Python types.
    """
    import numpy as np
    import pandas as pd

    if isinstance(obj, dict):
        return {k: make_json_safe(v) for k, v in obj.items()}
   
    if isinstance(obj, list):
        return [make_json_safe(v) for v in obj]

    if isinstance(obj, (np.integer,)):
        return int(obj)

    if isinstance(obj, (np.floating,)):
        return float(obj)

    if isinstance(obj, (np.bool_,)):
        return bool(obj)

    if isinstance(obj, (pd.Timestamp,)):
        return obj.isoformat()

    return obj




if __name__ == "__main__":
    main()
