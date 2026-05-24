# Grid Oracle 🏎️🔮

> **F1 race prediction web app that estimates likely top 3 drivers using race history, qualifying, sprint, practice, weather, and performance signals.**

---

## 🌐 Live Demo
- **Frontend Live URL**: https://grid-oracle-nine.vercel.app/
- **Backend Live URL**: https://grid-oracle-backend.vercel.app/

*(Note: The current backend deployment on Vercel is lightweight. Heavy machine learning and prediction logic might need a dedicated ML-friendly hosting service in the future. The `/predict` API may be placeholder or limited depending on the deployed version.)*

---

## 🏎️ Problem Statement
Formula 1 is a sport where fractions of a second matter, but predicting race outcomes is incredibly complex. Traditional predictions often rely heavily on gut feeling or simple qualifying order. They fail to account for the interplay of changing track conditions, team strategy, recent driver form, wet-weather skills, and historical data patterns.

## ✨ What the Project Does
Grid Oracle is an automated pre-race prediction system. It ingests live F1 session data and calculates the likely top 3 podium finishers before lights out. It does this by evaluating rolling driver and team statistics, qualifying lap details, track weather, and driver wet-skill ratings to produce an informed, data-driven forecast.

## 🚀 Why This Project Is Useful
This project bridges the gap between raw telemetry and fan accessibility. It provides motorsport enthusiasts, data science students, and analysts with a clear, statistically backed look at upcoming races. For developers and recruiters, it demonstrates the integration of external APIs (FastF1), machine learning pipelines, and modern web frameworks (React/FastAPI) into a unified, user-friendly application.

---

## 🌟 Key Features
- **Data-Driven Predictions**: Uses historical driver stats, qualifying lap details, and recent 2026 in-season form.
- **Advanced Feature Engineering**: Considers team strategy DNA, wet-skill ratings, and weather forecasts (rainfall flag, track temp, humidity, wind).
- **Leakage-Safe Modeling**: Strictly separates historical data to prevent future-data leakage during model training.
- **Modern Dashboard UI**: A clean, responsive frontend tailored for a premium F1 editorial feel.
- **RESTful API Backend**: A fast and lightweight Python backend to serve predictions.

---

## 🛠️ Tech Stack
- **Frontend**: React, Vite, Tailwind CSS
- **Backend**: Python 3.11, FastAPI, Uvicorn
- **Machine Learning**: scikit-learn, pandas
- **Data Source**: FastF1 API
- **Deployment**: Vercel (Frontend & Lightweight Backend)

---

## 🏗️ Project Architecture
```text
FastF1 API -> Ingestor -> Feature Store -> Model Pipeline -> REST API -> React Frontend
```

---

## 📂 Folder Structure
```text
pitwall-ai-backend/
├── frontend/             # React/Vite frontend application
├── src/                  # Heavy backend source code (models, data ingestion, api)
├── vercel_backend/       # Lightweight FastAPI application for Vercel deployment
├── data/                 # Raw and processed FastF1 parquet data & feature store
├── models/               # Trained scikit-learn joblib pipelines
├── scripts/              # Setup and pipeline scripts
├── tests/                # Unit testing
└── requirements.txt      # Python dependencies
```

---

## 💻 How to Run Locally

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```


to this:

```md
### Heavy Backend Setup (Local Machine Learning Pipeline)
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn src.api.main:app --reload
```

---

## ☁️ Deployment

### Frontend Deployment
The frontend is optimized and deployed on **Vercel**. It connects to the backend API via configured environment variables.

### Backend Deployment
The current backend is deployed as a Serverless function on **Vercel** (`vercel_backend/`). Because Vercel has limits on memory, package size, and execution time, this version of the backend is lightweight. Advanced ML model inference and data ingestion require heavier resources and may be hosted on a dedicated platform (like Render, AWS, or GCP) in the future.

---

## 🔌 API Endpoints

### `GET /`
Health check endpoint to verify that the backend is running.

### `POST /predict`
Executes a race prediction and returns the likely top 3 podium drivers based on current race weekend data. *(Note: Depending on the deployment environment, this may return placeholder data or limited results if the ML models are too heavy for serverless execution).*

---

## 🚧 Current Limitations
- **Hosting Limits**: The current Vercel backend cannot comfortably host heavy `.joblib` ML models or large `pandas` data processing due to strict serverless size and timeout constraints.
- **Cold Starts**: Serverless architecture may introduce minor latency during the first API request.
- **Real-Time Data**: Predictions rely on the timely availability of FastF1 telemetry.

---

## 🔮 Future Improvements
- Migrate the heavy machine learning pipeline to a dedicated containerized service (e.g., Docker + AWS ECS / Google Cloud Run).
- Introduce real-time live-race win probability updates.
- Expand data visualization on the frontend (e.g., track map overlays, driver momentum graphs).
- Incorporate official F1 news feeds for real-time penalty and weather adjustments.

## 👤 Author
**Nikhil Reddy**
- [GitHub Profile](https://github.com/Nikhil6750)
