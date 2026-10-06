# LifeOps AI

> **A Personal Life Decision and Action Intelligence System using Explainable Retrieval-Augmented Generation**

---

## 1. Project Overview

**LifeOps AI** is an intelligent personal operations platform that helps individuals make high-stakes daily, academic, and career decisions grounded in their own documents, constraints, and goals.

Unlike generic chatbots or surface-level PDF summarizers, LifeOps AI functions as an **operations intelligence engine**:
- **Document-Grounded**: Ingests personal documents (syllabi, assignment rubrics, exam schedules, internship JDs, offers, budgets).
- **Explainable RAG**: Every recommendation and action plan is linked to verifiable document citations with relevance metrics.
- **Constraint-Aware Decision Intelligence**: Compares competing paths (e.g., *“Interview Prep”* vs *“ML Assignment”*) against available hours, deadlines, and skill prerequisites.
- **What-If Scenario Simulation**: Enables non-destructive counterfactual simulation (e.g., modifying daily study hours or shifting deadlines) to observe how recommendations change.
- **Strict Grounding & Conflict Detection**: Identifies contradictory documents without silent guessing and clearly signals insufficient evidence.

---

## 2. Core Architecture

The system enforces a strict end-to-end processing pipeline:

```
USER ACTION
    ↓
FRONTEND (React 19 + TypeScript + Vite + Tailwind CSS)
    ↓
HTTP REST API (/api/* via Vite proxy)
    ↓
FASTAPI APPLICATION (Python 3.13)
    ↓
DATA VALIDATION (Pydantic v2)
    ↓
BUSINESS LOGIC SERVICES
    ↓
RELATIONAL DATABASE (SQLite / PostgreSQL-ready SQLAlchemy)
    + VECTOR DATABASE (Persistent ChromaDB)
    ↓
RETRIEVAL-AUGMENTED GENERATION (RAG)
    ↓
LLM REASONING (Google Gemini via Provider Abstraction)
    ↓
STRUCTURED ANALYSIS & EVIDENCE MAPPING
    ↓
FRONTEND TELEMETRY & PERSISTENCE
```

---

## 3. Technology Stack

| Layer | Technology | Rationale |
|---|---|---|
| **Frontend** | React 19, TypeScript, Vite 8, Tailwind CSS v4, Lucide Icons | Responsive, high-performance dashboard with live backend telemetry |
| **Backend API** | Python 3.13, FastAPI, Uvicorn | High-throughput async REST API with automatic OpenAPI documentation |
| **Relational Storage** | SQLAlchemy 2.0, SQLite (PostgreSQL compatible) | Persistent transactional storage with foreign key constraints |
| **Vector Storage** | ChromaDB (Persistent client) | Semantic vector indexing, chunk filtering, and deterministic document versioning |
| **Document Processing** | PyPDF, python-docx, CSV, Markdown, TXT | Robust text extraction, metadata extraction, and chunking |
| **LLM Provider** | Google Gemini (`google-genai` SDK) | Structured JSON reasoning behind an extensible provider abstraction |
| **Testing** | Pytest, FastAPI TestClient, Vitest/TSC | Comprehensive unit and integration verification |

---

## 4. Repository Structure

```
LifeOPS/
├── .env.example              # Environment variables template
├── .env                      # Local environment configuration
├── .gitignore                # Git ignore rules for venv, node_modules, data
├── README.md                 # Project documentation and guide
│
├── backend/                  # Python FastAPI service
│   ├── requirements.txt      # Backend Python dependencies
│   ├── venv/                 # Local Python virtual environment
│   └── app/
│       ├── main.py           # Application entrypoint & lifespan
│       ├── api/
│       │   ├── router.py     # Main API router (/api)
│       │   └── health.py     # Health telemetry route (/api/health)
│       ├── core/
│       │   └── config.py     # Pydantic Settings configuration
│       ├── database/
│       │   ├── base.py       # SQLAlchemy Base
│       │   └── session.py    # Database engine & session management
│       ├── schemas/
│       │   └── health.py     # Health response schemas
│       ├── models/           # SQLAlchemy entity models (Phase 2)
│       └── services/         # Business logic services (Phase 3+)
│
├── frontend/                 # React + TypeScript frontend
│   ├── package.json          # Frontend dependencies & scripts
│   ├── vite.config.ts        # Vite configuration with API proxy
│   ├── src/
│   │   ├── main.tsx          # React application root
│   │   ├── App.tsx           # Application shell & telemetry dashboard
│   │   ├── index.css         # Tailwind CSS v4 design tokens
│   │   ├── types/            # TypeScript interfaces & types
│   │   └── services/         # API services
│   └── dist/                 # Production build bundle
│
├── data/                     # Persistent local storage
│   ├── lifeops.db            # SQLite database file
│   ├── uploads/              # Raw document storage directory
│   └── chroma/               # ChromaDB vector index directory
│
└── tests/                    # Test suites
    ├── unit/
    │   └── test_health.py    # Backend API unit tests
    ├── integration/          # Integration test suites
    └── e2e/                  # End-to-end workflow verification
```

---

## 5. Getting Started & Installation

### Prerequisites
- Python 3.11+ (Python 3.13 tested)
- Node.js v20+ and npm v10+

### Step 1: Clone and Configure Environment

```bash
cp .env.example .env
```

Edit `.env` to configure your settings:
```env
APP_NAME=LifeOps AI
APP_ENV=development
DATABASE_URL=sqlite:///./data/lifeops.db
UPLOAD_DIRECTORY=./data/uploads
CHROMA_PERSIST_DIRECTORY=./data/chroma
GEMINI_API_KEY=your_gemini_api_key_here
```

### Step 2: Backend Setup & Testing

```powershell
# Activate backend virtual environment
.\backend\venv\Scripts\Activate.ps1

# Verify dependencies
pip install -r backend/requirements.txt

# Run backend unit tests
$env:PYTHONPATH="backend"
pytest tests/unit/test_health.py -v
```

### Step 3: Start Backend Server

```powershell
# From project root
$env:PYTHONPATH="backend"
.\backend\venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
- API Docs: `http://127.0.0.1:8000/docs`
- Health Telemetry: `http://127.0.0.1:8000/api/health`

### Step 4: Frontend Setup & Start

```bash
cd frontend
npm install
npm run build   # Verify compilation
npm run dev     # Start development server
```
- Access the dashboard at `http://localhost:5173`

---

## 6. Development Status

- [x] **Phase 1: Foundation & Application Shell** (Completed)
  - Project directories and Git repository configured
  - Python FastAPI backend with configuration management and health check API
  - React 19 + TypeScript + Vite + Tailwind CSS shell with real-time backend connection telemetry
  - SQLite persistent database engine configured with foreign keys enabled
  - Storage directories (`data/uploads`, `data/chroma`) created and tracked
  - Unit tests verified passing (`pytest`)
  - Frontend production build verified (`npm run build`)
- [ ] **Phase 2: Database & Relational Models** (Next)
- [ ] **Phase 3: Multi-Format Document Ingestion & Chunking**
- [ ] **Phase 4: ChromaDB Persistent Vector Indexing**
- [ ] **Phase 5: Semantic Retrieval & Grounded RAG**
- [ ] **Phase 6: Gemini LLM Integration with Structured Outputs**
- [ ] **Phase 7: Decision Workspace & Option Analyzer**
- [ ] **Phase 8: What-If Scenario Simulation Engine**
- [ ] **Phase 9: Frontend Feature Integration**
- [ ] **Phase 10: Evidence Explorer & Conflict Resolution**
- [ ] **Phase 11: End-to-End System Validation**
