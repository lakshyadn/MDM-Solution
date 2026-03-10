# Data Discrepancy Detection & Correction System

A full-stack AI-powered system to detect and fix data inconsistencies across multiple database sources.

## Overview

This system allows you to:
- Upload three CSV files: a Given database and two Master databases
- Use Google Gemini AI to detect discrepancies (typos, mismatches, semantic differences)
- View a detailed table of anomalies with color-coded values
- Select and apply corrections to the Given database
- Track changes and export corrected data

## Architecture

### Backend (FastAPI)

**Location:** `/data-backend`

**Key Features:**
- RESTful API with CORS support
- In-memory dataset storage
- Google Gemini integration for anomaly detection
- CSV file upload handling

**Endpoints:**

```
POST /upload/{dataset_type}
  - dataset_type: given | master1 | master2
  - Upload CSV files
  
POST /compare?preferred_master=master1|master2
  - Compare given data with preferred master
  - Returns structured JSON anomalies
  
POST /apply-fixes
  - Apply selected fixes to given dataset
  - Body: Array of {record_id, field, correct_value}
  
GET /status
  - Check upload status and record counts
  
GET /data/{dataset_type}
  - Retrieve full dataset as JSON
```

### Frontend (React + TypeScript)

**Location:** `/data-frontend`

**Key Features:**
- Modern React components with TypeScript
- Axios-based API service layer
- Tab-based workflow (Upload → Compare & Fix)
- Real-time anomaly table with filtering
- Loading states and error handling

**Components:**

- `FileUploader.tsx` - Drag-and-drop file upload UI
- `ComparisonSection.tsx` - Master selection and comparison workflow
- `AnomalyTable.tsx` - Table display with checkbox selection
- `Index.tsx` - Main orchestration page

**Services:**

- `api.ts` - Axios HTTP client with typed endpoints

## Setup Instructions

### Prerequisites

- Python 3.9+
- Node.js 18+
- Google Gemini API key
- Bun (recommended) or npm

### Backend Setup

1. **Navigate to backend directory:**
   ```bash
   cd data-backend
   ```

2. **Create virtual environment:**
   ```bash
   python -m venv venv
   source venv/Scripts/activate  # Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install fastapi uvicorn python-multipart google-generativeai python-dotenv pandas
   ```

4. **Create `.env` file:**
   ```bash
   echo "GEMINI_API_KEY=your_key_here" > .env
   ```

5. **Run server:**
   ```bash
   uvicorn main:app --reload
   ```

   Server runs on `http://127.0.0.1:8000`

### Frontend Setup

1. **Navigate to frontend directory:**
   ```bash
   cd data-frontend
   ```

2. **Install dependencies:**
   ```bash
   bun install
   # or: npm install
   ```

3. **Create `.env` file:**
   ```bash
   cp .env.example .env
   ```

4. **Run development server:**
   ```bash
   bun run dev
   # or: npm run dev
   ```

   Frontend runs on `http://localhost:5173`

## Usage Flow

### 1. Upload Datasets (Tab: Upload Data)

- **Given Database**: The dataset you want to validate and correct
- **Master Database 1**: Primary reference database
- **Master Database 2**: Secondary reference database (for recommendations)

All three CSV files must have matching column names.

### 2. Compare & Fix (Tab: Compare & Fix)

1. Select preferred master database (Master 1 or Master 2)
2. Click "Compare" button
3. AI analyzes the data and identifies discrepancies
4. Review the anomaly table showing:
   - **Record ID**: Which row has the issue
   - **Field**: Which column has the problem
   - **Given Value**: Current (incorrect) value shown in red
   - **Correct Value**: Suggested correction shown in green
   - **Reason**: Why it's flagged (typo, mismatch, etc.)
   - **Recommendations**: Alternative values from secondary master

### 3. Select & Apply Fixes

1. Check the checkbox for each anomaly you want to fix
2. Click "Apply Fixes" button
3. Confirm in the dialog
4. The Given database is updated server-side
5. Corrected rows are removed from the table

## Data Format

### CSV Requirements

- UTF-8 encoding
- Column headers in first row
- Consistent data types per column
- No special characters that break parsing

### Example CSV Structure

```csv
record_id,name,university_name,email
1,John Doe,University of Texxas,john@example.com
2,Jane Smith,MIT,jane@example.com
```

### API Response Format

```json
{
  "anomalies": [
    {
      "record_id": 1,
      "field": "university_name",
      "given_value": "University of Texxas",
      "correct_value": "University of Texas",
      "reason": "Spelling error",
      "recommendations": ["University of Texas at Austin"]
    }
  ]
}
```

## LLM Prompt Engineering

The Gemini prompt is designed to:
- Compare values semantically (not just string matching)
- Detect typos and spelling errors
- Identify formatting inconsistencies
- Provide alternative recommendations from secondary database
- Return strictly formatted JSON

**Location:** [data-backend/main.py](main.py) - `/compare` endpoint

You can customize the prompt to:
- Adjust sensitivity to changes
- Add domain-specific rules
- Modify recommendation logic

## Error Handling

The system handles:
- Missing files or datasets
- Invalid CSV format
- Network timeouts
- LLM API failures
- Invalid JSON responses from LLM

All errors are displayed to the user with actionable messages.

## State Management

**Frontend State:**
- Upload status for each dataset
- Selected fixes (Set<string> of "record_id-field" keys)
- Anomalies list
- Loading/error states

**Backend State:**
- In-memory DataFrames for given, master1, master2
- Persists until server restart

## Performance Considerations

- Large datasets (>10,000 rows) may take longer to analyze
- LLM API calls add latency (~5-30 seconds)
- Frontend maintains virtualized list for large tables
- Consider pagination for very large result sets

## Extending the System

### Add New Master Databases
Modify `/compare` endpoint to support more than 2 masters:
```python
@app.post("/compare-multi")
async def compare_multi(preferred_master: str, secondary_masters: List[str]):
    # Compare against multiple secondaries for richer recommendations
```

### Database Persistence
Store corrected datasets in PostgreSQL/MongoDB instead of memory:
```python
# Replace datasets dict with database operations
async def store_fixes(dataset_type: str, corrected_data: DataFrame):
    # Save to persistent storage
```

### Export Functionality
Add endpoint to download corrected CSV:
```python
@app.get("/download/{dataset_type}")
async def download_data(dataset_type: str):
    # Return CSV file with corrections applied
```

## Troubleshooting

### CORS Errors
- Ensure backend has correct frontend origin in CORS middleware
- Check `http://127.0.0.1:8000` is accessible from frontend

### LLM API Errors
- Verify `GEMINI_API_KEY` in `.env` is valid
- Check API quota usage on Google Cloud Console
- Ensure internet connectivity

### Upload Failures
- Verify CSV format is valid
- Check file size (< 50MB recommended)
- Ensure column names match across all CSVs

### Checkbox Not Selected
- Browser cache issue - do hard refresh (Ctrl+Shift+R)
- Check browser console for JavaScript errors

## API Testing with cURL

```bash
# Upload Given Database
curl -X POST "http://127.0.0.1:8000/upload/given" \
  -F "file=@given.csv"

# Upload Master Databases
curl -X POST "http://127.0.0.1:8000/upload/master1" \
  -F "file=@master1.csv"

curl -X POST "http://127.0.0.1:8000/upload/master2" \
  -F "file=@master2.csv"

# Check Status
curl "http://127.0.0.1:8000/status"

# Compare Datasets
curl -X POST "http://127.0.0.1:8000/compare?preferred_master=master1"

# Apply Fixes
curl -X POST "http://127.0.0.1:8000/apply-fixes" \
  -H "Content-Type: application/json" \
  -d '[
    {
      "record_id": 1,
      "field": "university_name",
      "correct_value": "University of Texas"
    }
  ]'
```

## Project Structure

```
Data Disperancy/
├── data-backend/
│   ├── main.py                 # FastAPI app
│   ├── .env                    # API keys
│   └── requirements.txt        # Python dependencies
│
└── data-frontend/
    ├── src/
    │   ├── components/
    │   │   ├── FileUploader.tsx
    │   │   ├── ComparisonSection.tsx
    │   │   ├── AnomalyTable.tsx
    │   │   └── ui/             # shadcn/ui components
    │   ├── lib/
    │   │   ├── api.ts          # API service layer
    │   │   └── types.ts
    │   ├── pages/
    │   │   └── Index.tsx       # Main page
    │   ├── App.tsx
    │   └── main.tsx
    ├── .env                    # Frontend config
    ├── package.json
    └── vite.config.ts
```

## Tech Stack

**Backend:**
- FastAPI (web framework)
- Pandas (data processing)
- Google Generative AI (LLM)
- Uvicorn (ASGI server)

**Frontend:**
- React 18 (UI framework)
- TypeScript (type safety)
- Vite (build tool)
- Tailwind CSS (styling)
- Shadcn/UI (components)
- Axios (HTTP client)

## Contributing

To extend this system:
1. Create feature branches
2. Follow TypeScript/Python naming conventions
3. Add error handling for all API calls
4. Test with sample CSV files
5. Update documentation

## License

[Specify your license here]

## Support

For issues, questions, or feature requests:
- Check troubleshooting section above
- Review API endpoint documentation
- Check browser console for errors
- Enable verbose logging in backend

---

**Last Updated:** February 2026
