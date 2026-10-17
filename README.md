# Pond Health Alert (PS 1.1)

> **Phone-first early-warning advisory system for coastal Karnataka aquaculture ponds.**

Pond Health Alert transforms three field inputs (**water quality readings**, a **fish photo**, and a **daily pond check**) into a single, honest risk advisory status (**GREEN / AMBER / RED / CAN'T TELL**) with explicit reason codes in **Kannada and English**.

---

## 🔑 Core Product Rules (Non-Negotiable)

1. **Never Show a False Green:** Missing, stale (>48 h), or physically impossible data results in **CAN'T TELL** with the exact diagnostic reason.
2. **Reason Codes in Plain Language:** Every status explains the underlying factors (e.g. `LOW_DO + RISING_MORTALITY`) bilingually in Kannada (`kn`) and English (`en`).
3. **Pre-Inference Photo Quality Gate:** Blurry, underexposed, or poorly framed photos trigger an immediate retake guide and never enter model inference.
4. **Uncertainty Gating:** Low-confidence predictions (<0.65 threshold) cannot turn a pond status green.
5. **7-Day Trend Warnings:** Impending breaches (e.g., dropping DO or rising ammonia) are flagged before limits are crossed.
6. **Offline-First PWA:** Manual readings and daily checks can be submitted without signal into an IndexedDB queue with automatic background sync.
7. **No Invented Numbers:** All accuracy and lead-time metrics derive directly from verifiable test and replay runs (`DATASETS.md`, `RESULTS.md`).

---

## ⚡ 5-Minute Quick Start

### Option A: Docker Compose
```bash
# 1. Start backend API, PostgreSQL, and Web PWA
docker compose up -d

# 2. View PWA in browser
# Farmer App: http://localhost:5173
# FastAPI Swagger Docs: http://localhost:8000/docs
```

### Option B: Local Development
```bash
# 1. Backend setup & tests
pip install -e apps/api
pytest apps/api/tests -v

# 2. Run Evaluation Harness
python apps/api/services/evaluation_harness.py

# 3. Launch Services
uvicorn apps.api.main:app --reload --port 8000
cd apps/web && npm install && npm run dev
```

---

## 📁 Repository Architecture

```
Hack_s/
├── apps/
│   ├── api/                     # FastAPI backend
│   │   ├── domain/              # Pure decision engine, water rules, config loader
│   │   ├── db/                  # Async SQLAlchemy models (Pond, Reading, Check, Alert)
│   │   ├── services/            # Replay simulator, bilingual alerts, SMS adapters, eval harness
│   │   ├── tests/               # Unit tests, property-based tests (Hypothesis)
│   │   └── main.py              # OpenAPI routes
│   └── web/                     # React 19 + TypeScript + Vite PWA
│       └── src/                 # Mobile-first UI, Dexie IndexedDB, i18next (kn/en), Web Speech
├── ml/                          # OpenCV Photo Quality Gate, ONNX Classifier, Grad-CAM overlay
├── config/                      # bands.yaml (FAO citations), alert_templates.json
├── data/                        # Dataset registry & scripts (no raw data committed)
├── docs/                        # DEMO_SCRIPT.md, evaluation_results.json
├── DATASETS.md                  # Detailed data sources, licences, and limitations
├── MODEL_CARD.md                # Vision model scope, metrics, and advisory disclaimers
└── Makefile                     # Automation tasks
```
