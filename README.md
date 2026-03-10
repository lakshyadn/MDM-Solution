# Data Discrepancy Detection & Correction System

> An AI-powered full-stack system to detect and correct data inconsistencies across multiple database sources using Google Gemini.

## 🎯 What It Does

This system enables you to:

1. **Upload three databases** in CSV format
   - Given Database (the data you want to validate)
   - Master Database 1 (primary reference)
   - Master Database 2 (secondary reference)

2. **Detect discrepancies** using AI
   - Spelling errors and typos
   - Semantic mismatches
   - Formatting inconsistencies
   - Provides alternative suggestions

3. **Review and apply fixes**
   - Visual table with color-coded differences
   - Checkbox selection for fixes
   - One-click application to your dataset

## 🚀 Quick Start

See [QUICKSTART.md](QUICKSTART.md) for 5-minute setup.

```bash
# Terminal 1: Backend
cd data-backend
python -m venv venv && venv\Scripts\activate
pip install -r requirements.txt
echo "GEMINI_API_KEY=your_key" > .env
uvicorn main:app --reload

# Terminal 2: Frontend
cd data-frontend
bun install
bun run dev

# Open http://localhost:5173
```

## 📚 Documentation

- **[QUICKSTART.md](QUICKSTART.md)** - Get running in 5 minutes
- **[SYSTEM_DOCUMENTATION.md](SYSTEM_DOCUMENTATION.md)** - Complete architecture & setup
- **[API_EXAMPLES.md](API_EXAMPLES.md)** - Request/response examples

## 🏗️ Architecture

### Backend (FastAPI)
- RESTful API with CORS support
- In-memory dataset storage
- Google Gemini AI integration
- 6 endpoints for upload, compare, apply fixes, status

**Endpoints:**
- `POST /upload/{dataset_type}` - Upload CSV files
- `POST /compare?preferred_master=master1|master2` - Detect discrepancies
- `POST /apply-fixes` - Apply corrections
- `GET /status` - Check upload status
- `GET /data/{dataset_type}` - Retrieve datasets
- `GET /` - Health check

### Frontend (React + TypeScript)
- Modern React with TypeScript
- Axios HTTP client with typed API layer
- Tab-based workflow (Upload → Compare & Fix)
- Real-time anomaly table with checkboxes
- Loading states, error handling, validation

**Key Components:**
- `FileUploader.tsx` - Drag-and-drop upload
- `ComparisonSection.tsx` - Comparison workflow
- `AnomalyTable.tsx` - Results display
- `api.ts` - API service layer
- `Index.tsx` - Main orchestration

## 📊 Data Flow

```
User uploads CSVs
        ↓
[Upload | Upload | Upload]
        ↓
Backend validates & stores in memory
        ↓
User clicks "Compare"
        ↓
Gemini AI analyzes differences
        ↓
Returns structured anomalies
        ↓
Frontend displays table
        ↓
User selects fixes with checkboxes
        ↓
POST /apply-fixes
        ↓
Backend updates Given dataset
        ↓
UI refreshes - applied fixes removed
```

## 🛠️ Tech Stack

### Backend
```
FastAPI        - Web framework
Pandas         - Data processing
Google GenAI   - LLM for analysis
Uvicorn        - ASGI server
Python-dotenv  - Environment config
```

### Frontend
```
React 18       - UI framework
TypeScript     - Type safety
Vite           - Build tool
Tailwind CSS   - Styling
Shadcn/UI      - Component library
Axios          - HTTP client
```

## 🎯 Use Cases

**Data Quality Assurance**
- Validate customer databases
- Detect typos and errors
- Identify duplicates with variations

**Data Migration**
- Compare legacy vs new systems
- Identify mapping issues
- Batch correction of differences

**Master Data Management**
- Reconcile multiple data sources
- Create unified golden records
- Track data lineage changes

**Database Consolidation**
- Merge supplier/vendor databases
- Identify semantic differences
- Apply corrections systematically

## 💻 Sample CSV Format

**given.csv**
```csv
id,name,company,email
1,John Doe,Acme Corportaion,john@example.com
2,Jane Smith,Tech Inovators,jane@company.com
3,Bob Johnson,Finance Solutinos,bob@finance.org
```

**master1.csv** (Primary reference)
```csv
id,name,company,email
1,John Doe,Acme Corporation,john@example.com
2,Jane Smith,Tech Innovators,jane@company.com
3,Bob Johnson,Finance Solutions,bob@finance.org
```

**master2.csv** (Secondary reference - for recommendations)
```csv
id,name,company,email
1,John D.,ACME Corp,john@acme.co
2,Jane S.,TechInnov,jane@tech.co
3,Robert Johnson,FS Inc,bob@fs.org
```

## 📈 Results Example

After comparison, you'll see a table like:

| Fix | Record ID | Field | Given Value (Red) | Correct Value (Green) | Reason | Recommendations |
|-----|-----------|-------|---|---|---|---|
| ☑️ | 1 | company | Acme Corportaion | Acme Corporation | Spelling error | ACME Corp |
| ☐ | 2 | company | Tech Inovators | Tech Innovators | Typo | TechInnov |
| ☑️ | 3 | company | Finance Solutinos | Finance Solutions | Spelling error | FS Inc |

## ⚙️ Configuration

### Backend (.env)
```env
GEMINI_API_KEY=your_api_key_here
```

Get an API key: https://aistudio.google.com/app/apikey

### Frontend (.env)
```env
VITE_API_URL=http://127.0.0.1:8000
```

## 🔧 Customization

### Modify LLM Prompt
Edit `/data-backend/main.py` in the `/compare` endpoint to:
- Adjust sensitivity to changes
- Add domain-specific rules
- Change output format
- Add custom validation logic

### Add Persistence
Replace in-memory dict with database:
- PostgreSQL / MongoDB
- Save history of changes
- Track data lineage

### Export Functionality
Add download endpoint:
```python
@app.get("/download/{dataset_type}")
def download_data(dataset_type: str):
    # Return CSV with corrections applied
```

## 🐛 Troubleshooting

**CORS Issues**
- Ensure backend URL matches frontend env
- Check frontend URL in CORS middleware

**API Key Error**
- Verify `GEMINI_API_KEY` is valid
- Check Google Cloud API quota

**Upload Failures**
- CSV must be UTF-8 encoded
- Column names must match across files
- File size limit ~50MB

**Checkbox Not Working**
- Hard refresh: Ctrl+Shift+R
- Check browser console for errors

See [SYSTEM_DOCUMENTATION.md](SYSTEM_DOCUMENTATION.md) for detailed troubleshooting.

## 📁 Project Structure

```
Data Disperancy/
│
├── data-backend/
│   ├── main.py                 # FastAPI application
│   ├── .env                    # API keys (create manually)
│   └── requirements.txt        # Python dependencies
│
├── data-frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── AnomalyTable.tsx        # Anomaly display
│   │   │   ├── ComparisonSection.tsx   # Comparison UI
│   │   │   ├── FileUploader.tsx        # Upload component
│   │   │   └── ui/                    # shadcn/ui components
│   │   ├── lib/
│   │   │   ├── api.ts                 # API service layer
│   │   │   └── types.ts
│   │   ├── pages/
│   │   │   └── Index.tsx              # Main page
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── .env.example            # Frontend config template
│   └── package.json
│
├── API_EXAMPLES.md             # API request/response examples
├── SYSTEM_DOCUMENTATION.md     # Complete architecture guide
├── QUICKSTART.md              # 5-minute setup
└── README.md                  # This file
```

## 🎓 Learning Resources

- **API Layer:** Examine `src/lib/api.ts` for Axios patterns
- **State Management:** See React hooks in components
- **Type Safety:** Check TypeScript interfaces for data contracts
- **Error Handling:** Review try/catch patterns throughout

## 🤝 Contributing

To extend this system:

1. **Add new master databases** - Modify compare logic
2. **Implement persistence** - Replace in-memory dict
3. **Add export** - Create download endpoint
4. **Customize UI** - Modify React components
5. **Improve AI** - Refine Gemini prompt

Always:
- Follow TypeScript conventions
- Add error handling
- Test with sample data
- Update documentation

## 📝 API Quick Reference

```bash
# Upload files
curl -X POST "http://127.0.0.1:8000/upload/given" -F "file=@given.csv"
curl -X POST "http://127.0.0.1:8000/upload/master1" -F "file=@master1.csv"
curl -X POST "http://127.0.0.1:8000/upload/master2" -F "file=@master2.csv"

# Check status
curl "http://127.0.0.1:8000/status"

# Compare datasets
curl -X POST "http://127.0.0.1:8000/compare?preferred_master=master1"

# Apply fixes
curl -X POST "http://127.0.0.1:8000/apply-fixes" \
  -H "Content-Type: application/json" \
  -d '[{"record_id":1,"field":"name","correct_value":"John Smith"}]'

# Get data
curl "http://127.0.0.1:8000/data/given"
```

See [API_EXAMPLES.md](API_EXAMPLES.md) for detailed examples.

## ✨ Key Features

- ✅ AI-powered discrepancy detection
- ✅ Batch file upload (CSV)
- ✅ Visual anomaly table
- ✅ Checkbox selection for fixes
- ✅ One-click apply corrections
- ✅ Real-time feedback
- ✅ Error handling & validation
- ✅ Loading states
- ✅ Responsive design

## 🔐 Security Considerations

Currently:
- No authentication
- CORS allows all origins (`*`)
- In-memory storage (lost on restart)
- No rate limiting

For production:
- Add API authentication (JWT/OAuth)
- Restrict CORS to specific origins
- Implement database persistence
- Add rate limiting
- Encrypt sensitive data
- Add audit logging

## 📞 Support

For issues:
1. Check [SYSTEM_DOCUMENTATION.md](SYSTEM_DOCUMENTATION.md) troubleshooting
2. Review [API_EXAMPLES.md](API_EXAMPLES.md) for endpoint usage
3. Check browser console for errors
4. Enable verbose logging in backend

## 📄 License

[Specify your license]

## 🎉 Getting Started

1. Clone/download this repository
2. Follow [QUICKSTART.md](QUICKSTART.md)
3. Open http://localhost:5173
4. Upload your CSVs
5. Detect and fix discrepancies!

---

Built with ❤️ for data quality enthusiasts | Last Updated: February 2026
