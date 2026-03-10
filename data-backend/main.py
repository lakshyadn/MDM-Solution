from fastapi import FastAPI, UploadFile, File, HTTPException, Query, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import pandas as pd
import os
import tempfile
from datetime import datetime
import json
import google.generativeai as genai
from dotenv import load_dotenv
from typing import List, Dict, Any

# Import new services for 4-step pipeline
from services.matcher import MatcherService
from services.data_analyze_service import run_data_analyze

load_dotenv()

app = FastAPI(title="Data Discrepancy Detection System")


# def _parse_allowed_origins() -> List[str]:
#     """Load CORS origins from env while preserving localhost defaults for dev."""
#     default_origins = [
#         "http://localhost:5173",
#         "http://localhost:8080",
#         "http://localhost:3000",
#         "http://127.0.0.1:5173",
#     ]
#     raw = os.getenv("FRONTEND_ORIGINS", "")
#     if not raw.strip():
#         return default_origins

#     parsed = [origin.strip() for origin in raw.split(",") if origin.strip()]
#     return parsed or default_origins

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Google Gemini client 
api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    raise ValueError("Missing GOOGLE_API_KEY in .env")

genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-3-flash-preview")

# Initialize 4-step pipeline matcher
matcher_service = MatcherService(api_key)

# Store uploaded datasets in memory
datasets = {}
OUTPUT_DIR = os.getenv(
    "OUTPUT_DIR",
    os.path.join(os.path.dirname(__file__), "outputs"),
)

@app.get("/")
def root():
    return {"message": "Backend is running"}

# Upload Given / Master1 / Master2
@app.post("/upload/{dataset_type}")
async def upload_file(dataset_type: str, file: UploadFile = File(...)):
    filename = file.filename or ""
    is_csv = filename.endswith(".csv")
    is_xlsx = filename.endswith(".xlsx")

    if not (is_csv or is_xlsx):
        return {"error": "Only CSV or XLSX files are supported"}

    if is_csv:
        df = pd.read_csv(file.file)
    else:
        df = pd.read_excel(file.file)
    datasets[dataset_type] = df

    return {
        "message": f"{dataset_type} uploaded successfully",
        "rows": len(df),
        "columns": list(df.columns)
    }


@app.post("/data-analyze/analyze")
async def analyze_data_project(
    file: UploadFile = File(...),
    sheet: str = Form(None),
    duplicate_key: str = Form(None),
):
    """Run integrated Data Analyze pipeline (formerly Streamlit-only) and return JSON result."""
    filename = file.filename or ""
    ext = os.path.splitext(filename)[1].lower()

    if ext not in [".csv", ".txt", ".xls", ".xlsx", ".xlsm"]:
        raise HTTPException(status_code=400, detail="Unsupported file type")

    sheet_value = None
    if sheet is not None and sheet.strip() != "":
        sheet_value = int(sheet) if sheet.strip().isdigit() else sheet.strip()

    duplicate_key_value = None
    if duplicate_key is not None and duplicate_key.strip() != "" and duplicate_key.strip().lower() != "auto":
        duplicate_key_value = duplicate_key.strip()

    temp_path = None
    try:
        file_bytes = await file.read()
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as temp_file:
            temp_file.write(file_bytes)
            temp_path = temp_file.name

        return run_data_analyze(
            file_path=temp_path,
            sheet=sheet_value,
            duplicate_key=duplicate_key_value,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Data analyze failed: {str(e)}")
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except Exception:
                pass


@app.post("/analyze")
def analyze(
    preferred_master: str = Query(..., description="master1 or master2"),
    identifier_field: str = Query(None, description="Field to use for matching records. Auto-detected if not provided.")
):
    """
    Analyze given dataset using scalable 4-step pipeline:
    1. Exact match (normalized)
    2. Fuzzy match (RapidFuzz)
    3. Embedding similarity (Gemini embeddings)
    4. LLM reasoning (for uncertain cases only)
    
    This endpoint scales to 40k+ rows efficiently.
    Works with any dataset - identifier field auto-detected or specified.
    """
    given = datasets.get("given")
    master1 = datasets.get("master1")
    master2 = datasets.get("master2")

    if given is None or master1 is None or master2 is None:
        raise HTTPException(
            status_code=400,
            detail="Upload given, master1, and master2 first"
        )

    if preferred_master not in ["master1", "master2"]:
        raise HTTPException(
            status_code=400,
            detail="preferred_master must be 'master1' or 'master2'"
        )

    # Auto-detect identifier field if not provided
    if not identifier_field:
        columns = list(given.columns)
        # Skip system columns
        skip_cols = ['id', 'record_id', 'updated_at', 'updated_by']
        
        # Try to find column with 'name' in it (company_name, product_name, etc.)
        for col in columns:
            if 'name' in col.lower() and col.lower() not in skip_cols:
                identifier_field = col
                break
        
        # If not found, use first non-system column
        if not identifier_field:
            for col in columns:
                if col.lower() not in skip_cols:
                    identifier_field = col
                    break
        
        # If still not found, default to first column
        if not identifier_field:
            identifier_field = columns[0] if columns else "id"
        
        print(f"Auto-detected identifier field: '{identifier_field}'")

    # Convert dataframes to list of dicts
    given_data = given.to_dict(orient="records")
    master1_data = master1.to_dict(orient="records")
    master2_data = master2.to_dict(orient="records")

    # Honor preferred master selection for the 4-step pipeline.
    # matcher_service expects first master arg = primary/preferred,
    # second master arg = secondary/reference for alternatives.
    if preferred_master == "master1":
        primary_master_data = master1_data
        secondary_master_data = master2_data
    else:
        primary_master_data = master2_data
        secondary_master_data = master1_data
    
    try:
        # Run 4-step pipeline analysis
        anomalies, stats = matcher_service.analyze_datasets(
            given_data=given_data,
            master1_data=primary_master_data,
            master2_data=secondary_master_data,
            identifier_field=identifier_field
        )
        
        return {
            "anomalies": anomalies,
            "statistics": {
                "identifier_field": identifier_field,
                "total_records": stats['total'],
                "exact_matches": stats.get('exact_match', 0),
                "fuzzy_matches": stats.get('fuzzy_anomalies', 0),
                "embedding_matches": stats.get('embedding_anomalies', 0),
                "llm_analyzed": stats.get('llm_analyzed', 0),
                "anomalies_found": stats.get('anomalies_found', 0),
                "efficiency": f"{((stats.get('exact_match', 0) + stats.get('fuzzy_anomalies', 0) + stats.get('embedding_anomalies', 0)) / stats['total'] * 100):.1f}% filtered as exact or high-confidence" if stats['total'] > 0 else "N/A"
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(e)}"
        )


@app.post("/apply-fixes")
def apply_fixes(fixes: List[Dict[str, Any]]):
    """Apply selected fixes to the given dataset"""
    given = datasets.get("given")
    
    if given is None:
        raise HTTPException(status_code=400, detail="No given dataset found")
    
    if not fixes:
        raise HTTPException(status_code=400, detail="No fixes provided")

    # Initialize updated_at and updated_by columns if they don't exist
    if "updated_at" not in given.columns:
        given["updated_at"] = None
    if "updated_by" not in given.columns:
        given["updated_by"] = None

    # Track which records were updated
    updated_records = set()
    timestamp = datetime.utcnow().isoformat()

    def coerce_value_for_column(column: pd.Series, value: Any, field_name: str) -> Any:
        """Convert incoming fix values to match the destination column dtype."""
        if value is None:
            return None

        if isinstance(value, str):
            stripped = value.strip()
            if stripped == "":
                return None
            value = stripped

        dtype = column.dtype

        if pd.api.types.is_integer_dtype(dtype):
            try:
                # Accept numeric strings like "1920" for int columns.
                return int(value)
            except (TypeError, ValueError):
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid integer value '{value}' for field '{field_name}'"
                )

        if pd.api.types.is_float_dtype(dtype):
            try:
                return float(value)
            except (TypeError, ValueError):
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid numeric value '{value}' for field '{field_name}'"
                )

        if pd.api.types.is_bool_dtype(dtype):
            if isinstance(value, bool):
                return value
            if isinstance(value, (int, float)):
                return bool(value)
            if isinstance(value, str):
                lowered = value.lower()
                if lowered in {"true", "1", "yes", "y"}:
                    return True
                if lowered in {"false", "0", "no", "n"}:
                    return False
            raise HTTPException(
                status_code=400,
                detail=f"Invalid boolean value '{value}' for field '{field_name}'"
            )

        if pd.api.types.is_datetime64_any_dtype(dtype):
            try:
                return pd.to_datetime(value, errors="raise")
            except (TypeError, ValueError):
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid datetime value '{value}' for field '{field_name}'"
                )

        return value

    # Apply fixes to the dataframe
    for fix in fixes:
        record_id = fix.get("record_id")
        field = fix.get("field")
        correct_value = fix.get("correct_value")

        if field not in given.columns:
            raise HTTPException(status_code=400, detail=f"Field '{field}' not found in given dataset")

        # Normalize record_id to int when possible
        try:
            record_id_int = int(record_id)
        except (TypeError, ValueError):
            record_id_int = record_id

        coerced_value = coerce_value_for_column(given[field], correct_value, field)
        
        # Prefer matching by an explicit id column to avoid off-by-one errors
        if "id" in given.columns:
            mask = given["id"] == record_id_int
            if mask.any():
                given.loc[mask, field] = coerced_value
                updated_records.add(record_id_int)
            continue
        if "record_id" in given.columns:
            mask = given["record_id"] == record_id_int
            if mask.any():
                given.loc[mask, field] = coerced_value
                updated_records.add(record_id_int)
            continue

        # Fall back to index-based updates
        if record_id_int in given.index:
            given.loc[record_id_int, field] = coerced_value
            updated_records.add(record_id_int)
        elif isinstance(given.index, pd.RangeIndex) and isinstance(record_id_int, int):
            if 0 <= record_id_int < len(given):
                given.loc[record_id_int, field] = coerced_value
                updated_records.add(record_id_int)

    # Update the updated_at and updated_by columns for modified records
    for record_id in updated_records:
        if "id" in given.columns:
            given.loc[given["id"] == record_id, "updated_at"] = timestamp
            given.loc[given["id"] == record_id, "updated_by"] = "System"
        elif "record_id" in given.columns:
            given.loc[given["record_id"] == record_id, "updated_at"] = timestamp
            given.loc[given["record_id"] == record_id, "updated_by"] = "System"
        else:
            if record_id in given.index:
                given.loc[record_id, "updated_at"] = timestamp
                given.loc[record_id, "updated_by"] = "System"

    # Update the dataset
    datasets["given"] = given

    # Write the fixed given dataset to disk
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    file_timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    output_filename = f"given_fixed_{file_timestamp}.csv"
    output_path = os.path.join(OUTPUT_DIR, output_filename)
    given.to_csv(output_path, index=False)
    
    return {
        "message": f"Successfully applied {len(fixes)} fixes",
        "updated_rows": len(fixes),
        "file_name": output_filename,
    }


@app.get("/download/given-fixed/{file_name}")
def download_given_fixed(file_name: str):
    """Download the latest fixed Given CSV by filename."""
    safe_name = os.path.basename(file_name)
    file_path = os.path.join(OUTPUT_DIR, safe_name)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        path=file_path,
        media_type="text/csv",
        filename=safe_name,
    )


@app.get("/status")
def status():
    """Check which datasets are uploaded"""
    return {
        "given": "given" in datasets,
        "master1": "master1" in datasets,
        "master2": "master2" in datasets,
        "given_rows": len(datasets.get("given", pd.DataFrame())),
        "master1_rows": len(datasets.get("master1", pd.DataFrame())),
        "master2_rows": len(datasets.get("master2", pd.DataFrame())),
    }


@app.get("/data/{dataset_type}")
def get_data(dataset_type: str):
    """Retrieve a dataset"""
    if dataset_type not in datasets:
        raise HTTPException(status_code=404, detail=f"Dataset '{dataset_type}' not found")
    
    return datasets[dataset_type].to_dict(orient="records")


@app.get("/pipeline/statistics")
def get_pipeline_statistics():
    """Get statistics from the last pipeline run"""
    stats = matcher_service.get_statistics()
    return {
        "statistics": stats,
        "cache_size": matcher_service.embedding_service.get_cache_size()
    }


@app.post("/pipeline/clear-cache")
def clear_pipeline_cache():
    """Clear the embedding cache to free memory"""
    cache_size_before = matcher_service.embedding_service.get_cache_size()
    matcher_service.clear_cache()
    return {
        "message": "Cache cleared successfully",
        "embeddings_cleared": cache_size_before
    }
