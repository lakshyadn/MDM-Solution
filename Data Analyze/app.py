import streamlit as st
import tempfile
import os
import json

from File_tr import analyze_file_for_ui, load_data, make_json_safe

@st.cache_data(show_spinner=False)
def run_cached_analysis(file_path, sheet, duplicate_key):
    return analyze_file_for_ui(
        file_path,
        sheet=sheet,
        duplicate_key=duplicate_key
    )


st.set_page_config(
    page_title="Universal Data Inspector",
    layout="wide"
)

st.title("📊 Universal Data Inspector")
st.caption("Upload a CSV or Excel file to analyze structure, quality & data issues")

uploaded_file = st.file_uploader(
    "Drop CSV / Excel file here",
    type=["csv", "xlsx", "xls"]
)

sheet_name = st.text_input(
    "Excel Sheet (optional)",
    help="Leave empty for first sheet"
)

sheet_value = None
if sheet_name:
    sheet_value = int(sheet_name) if sheet_name.isdigit() else sheet_name


sheet_input = st.text_input(
    "Excel Sheet (name or index, optional)",
    help="Leave empty for first sheet"
)

sheet_value = None
if sheet_input:
    if sheet_input.isdigit():
        sheet_value = int(sheet_input)
    else:
        sheet_value = sheet_input



dup_column = None
df_columns = []

# ---------- If file uploaded, read columns ----------
if uploaded_file:
    suffix = os.path.splitext(uploaded_file.name)[1]

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded_file.getbuffer())
        temp_file_path = tmp.name

    try:
        preview_df = load_data(
            temp_file_path,
            int(sheet_name) if sheet_name.isdigit() else sheet_name or None
        )
        df_columns = list(preview_df.columns)
    except Exception:
        df_columns = []

    dup_column = st.selectbox(
        "Select column for duplicate detection",
        options=["Auto"] + df_columns
    )

# ---------- Analyze ----------
if uploaded_file and st.button("🔍 Analyze File"):
    with st.spinner("Analyzing data..."):

        #result = analyze_file_for_ui(
        #    temp_file_path
        #    sheet=int(sheet_name) if sheet_name.isdigit() else sheet_name or None,
        #    duplicate_key=None if dup_column == "Auto" else dup_column
        #)

       # result = run_cached_analysis(
       #     temp_file_path,
       #     sheet_value,
       #     None if dup_column == "Auto" else dup_column
       # )
        result = analyze_file_for_ui(
        temp_file_path,
        sheet=sheet_value,
        duplicate_key=None if dup_column == "Auto" else dup_column
)


    report = result["report"]
    structure_status = result["structure_status"]
    ml = result.get("ml_status", {})


    if structure_status:
        if structure_status.startswith("row_wise"):
            st.warning(f"⚠ Structure issue detected & fixed: {structure_status}")
        else:
            st.error(f"❌ Structure issue detected: {structure_status}")
            st.stop()

    st.success("Analysis completed successfully!")

    # ================= ML STATUS =================
    st.subheader("🧠 Machine Learning Status")

    if ml.get("enabled"):
        st.success("ML Engine is ACTIVE")
    else:
        st.warning("ML Engine not initialized")

    st.write(f"📚 Learned anomaly patterns: **{ml.get('memory_records', 0)}**")

    if ml.get("model_ready"):
        st.success("✅ ML is ready to recommend improvements")
    else:
        st.info("⏳ ML is learning from uploaded files")

# ================= ML RECOMMENDATIONS =================
    st.subheader("🛠 ML Recommendations")
    
    has_reco = False
    
    for a in result.get("anomalies", []):
        if a.get("recommendation"):
            has_reco = True
            st.warning(
                f"Column **{a['column']}** → {a['recommendation']} "
                f"(confidence: {a.get('ml_score', 'n/a')})"
            )
    
    if not has_reco:
        st.info("No actionable ML recommendations yet.")
    


    # ---------- SUMMARY ----------
    st.subheader("📈 File Summary")
    c1, c2, c3 = st.columns(3)
    c1.metric("Rows", report["rows"])
    c2.metric("Columns", report["columns"])
    c3.metric("Duplicate %", report["duplicate_rows_pct"])

    st.caption(f"Duplicate check column: {report['duplicate_check_column']}")

    # ---------- COLUMN DETAILS ----------
    st.subheader("🔍 Column Analysis")


    st.subheader("🧠 Machine Learning Status")

    if ml.get("enabled"):
        st.success("ML Engine is ACTIVE")
    else:
        st.warning("ML Engine not initialized")

    st.write(f"📚 Learned anomaly patterns: **{ml.get('memory_records', 0)}**")

    if ml.get("model_ready"):
        st.success("✅ ML is ready to recommend improvements")
    else:
        st.info("⏳ ML is learning. Upload more files to improve accuracy.")


    

    for col, info in report["columns_analysis"].items():
        with st.expander(f"📌 {col}"):
            st.write("**Inferred Type:**", info["inferred_type"])
            st.write("**Null %:**", info["null_pct"])
            st.write("**Unique Values:**", info["unique_values"])

            if info.get("semantic_mismatch"):
                st.error(
                    f"❌ {info['semantic_mismatch']['issue']} "
                    f"(rows: {info['semantic_mismatch']['string_count']})"
                )

            if info.get("quality_flags"):
                st.warning("⚠ " + ", ".join(info["quality_flags"]))

            if info.get("mixed_datatype_analysis"):
                st.write("**Mixed Data Types:**")
                st.json(info["mixed_datatype_analysis"])

                

           


    # ---------- DOWNLOAD ----------
    st.subheader("📥 Download Report")
    safe_report = make_json_safe(report)

    st.download_button(
        "Download JSON Report",
        json.dumps(safe_report, indent=2),
        "data_quality_report.json",
        "application/json"
)


    os.unlink(temp_file_path)

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

