# Deployment Guide (Full Project)

This project has two deployable apps:
- `data-backend` (FastAPI + Gemini + pandas + Chroma)
- `data-frontend` (Vite React static app)

Recommended stack:
- Backend on Render (Web Service)
- Frontend on Vercel (Static)

You can also use Railway/Fly/EC2, but the steps below are production-safe for this repository.

## 1) Pre-Deploy Checklist

1. Push latest code to GitHub.
2. Confirm backend reads the correct API key env variable:
   - Code uses `GOOGLE_API_KEY` in `data-backend/main.py`.
3. Confirm CORS is configured for your deployed frontend domain:
   - Set `FRONTEND_ORIGINS` in backend env.
4. Decide persistence needs:
   - `data-backend/chroma_data` (vector store)
   - `data-backend/outputs` (fixed CSV exports)
   - `Data Analyze/anomaly_memory.csv` and `Data Analyze/anomaly_model.pkl`
   Use persistent disk/volume if you need data retained across redeploys.

## 2) Backend Deployment (Render)

Create a new **Web Service** from your GitHub repo.

### Backend Settings

- Root Directory: `data-backend`
- Runtime: Python
- Build Command:

```bash
pip install -r requirements.txt
```

- Start Command:

```bash
uvicorn main:app --host 0.0.0.0 --port $PORT
```

### Backend Environment Variables

Add these in Render dashboard:

```env
GOOGLE_API_KEY=your_google_gemini_key
FRONTEND_ORIGINS=https://your-frontend-domain.vercel.app
```

If you have multiple frontend domains (preview + prod), comma-separate:

```env
FRONTEND_ORIGINS=https://your-frontend-domain.vercel.app,https://your-custom-domain.com
```

### Persistent Disk (Important)

If you want model/chroma/output persistence, mount a disk and point app paths there (or keep current paths and mount repo working dir). At minimum, persist:
- `data-backend/chroma_data`
- `data-backend/outputs`
- `Data Analyze/` ML artifacts

If you skip persistence, deploy still works, but artifacts reset on restart/redeploy.

## 3) Frontend Deployment (Vercel)

Create a new Vercel project from same repo.

### Frontend Settings

- Framework Preset: `Vite`
- Root Directory: `data-frontend`
- Install Command:

```bash
npm install
```

- Build Command:

```bash
npm run build
```

- Output Directory:

```bash
dist
```

### Frontend Environment Variable

```env
VITE_API_URL=https://your-backend-service.onrender.com
```

Redeploy frontend after setting this.

## 4) Post-Deploy Validation

1. Open frontend URL.
2. Upload files in both flows:
   - Data Discrepancy flow (`given/master1/master2`)
   - Data Inspector flow (single file analyze)
3. Confirm backend health:
   - `GET https://your-backend-service.onrender.com/`
4. Confirm CORS works from frontend domain.
5. Test `Apply Fixes` and CSV download endpoint.

## 5) Production Notes

- **Cold start**: free plans may sleep.
- **File size**: large CSV/Excel can hit memory/time limits.
- **Concurrency**: backend stores uploaded datasets in memory (`datasets` dict), so very high traffic should move to DB/object storage.
- **Secrets**: never commit `.env`.

## 6) Alternative: Single-Server Deploy (Docker + Nginx)

If you want one VM with both apps behind one domain:
- Build frontend static bundle.
- Run backend with Uvicorn/Gunicorn.
- Serve frontend via Nginx.
- Reverse-proxy `/api` to backend.

This is best when you want full control and persistent local volumes.
