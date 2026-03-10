# Quick Start Guide

Get the Data Discrepancy Detection system running in 5 minutes.

## 1. Backend Setup (Terminal 1)

```bash
# Go to backend directory
cd data-backend

# Create & activate virtual environment
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install fastapi uvicorn python-multipart google-generativeai python-dotenv pandas

# Create .env file with your Gemini API key
echo GEMINI_API_KEY=your_api_key_here > .env

# Start server
uvicorn main:app --reload
```

✅ Backend running on **http://127.0.0.1:8000**

## 2. Frontend Setup (Terminal 2)

```bash
# Go to frontend directory
cd data-frontend

# Install dependencies
bun install

# Create .env (optional - uses default localhost:8000)
echo VITE_API_URL=http://127.0.0.1:8000 > .env

# Start dev server
bun run dev
```

✅ Frontend running on **http://localhost:5173**

## 3. Test with Sample Data

Create three CSV files in a test folder:

**given.csv**
```csv
id,name,company
1,John Smith,Acme Corportaion
2,Jane Doe,Tech Innovators Inc
3,Bob Johnson,Finance Solutinos
```

**master1.csv**
```csv
id,name,company
1,John Smith,Acme Corporation
2,Jane Doe,Tech Innovators Inc
3,Bob Johnson,Finance Solutions
```

**master2.csv**
```csv
id,name,company
1,John Smith,ACME CORP
2,Jane Doe,TechInnovators
3,Bob Johnson,FS Ltd
```

## 4. Run the Application

1. Open **http://localhost:5173** in your browser
2. Click "Upload Data" tab
3. Upload the three CSV files
4. Click "Compare & Fix" tab
5. Select "Master Database 1" as preferred master
6. Click "Compare"
7. Check the checkboxes for anomalies you want to fix
8. Click "Apply Fixes"

## Common Issues

### CORS Error
- Make sure backend is on `http://127.0.0.1:8000` (not `localhost`)
- Check frontend is on `http://localhost:5173`

### API Key Error
- Get your Gemini API key from: https://aistudio.google.com/app/apikey
- Add it to `.env` in data-backend folder

### Port Already in Use
```bash
# Find process on port 8000
netstat -ano | findstr :8000

# Kill it (Windows)
taskkill /PID <PID> /F
```

### File Upload Fails
- Ensure CSV files are UTF-8 encoded
- Column names must be identical across all files
- No special characters in filenames

## File Structure Created

```
data-backend/
  ├── main.py              ✅ Complete with all endpoints
  └── .env                 (Create this with your API key)

data-frontend/
  ├── src/
  │   ├── lib/
  │   │   └── api.ts       ✅ API service layer
  │   ├── components/
  │   │   ├── AnomalyTable.tsx        ✅ Results table
  │   │   └── ComparisonSection.tsx   ✅ Comparison UI
  │   └── pages/
  │       └── Index.tsx    ✅ Main page (updated)
  └── .env.example         (Copy to .env if needed)
```

## Next Steps

1. Review [SYSTEM_DOCUMENTATION.md](../SYSTEM_DOCUMENTATION.md) for detailed architecture
2. Customize LLM prompt in `data-backend/main.py` for your use case
3. Add database persistence instead of in-memory storage
4. Implement export/download functionality
5. Add user authentication

## Support Commands

```bash
# Check if ports are available
netstat -ano | findstr :8000  # Backend
netstat -ano | findstr :5173  # Frontend

# Clear node modules cache (if issues)
cd data-frontend
rm -r node_modules
bun install

# Restart servers
# Kill and re-run the commands above
```

## API Endpoints Quick Reference

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/upload/given` | Upload Given CSV |
| POST | `/upload/master1` | Upload Master 1 CSV |
| POST | `/upload/master2` | Upload Master 2 CSV |
| POST | `/compare?preferred_master=master1` | Run comparison |
| POST | `/apply-fixes` | Apply selected fixes |
| GET | `/status` | Check upload status |
| GET | `/data/given` | Get Given dataset |

---

**You're ready to go!** 🚀

Open http://localhost:5173 and start detecting discrepancies.
