# ScholarLens AI

**An Agentic Literature Survey and Evidence-Based Research Gap Discovery System**

ScholarLens AI is an academic research assistant that helps students and researchers:
- Analyse multiple research papers with page-level citations.
- Ask questions across papers using a RAG pipeline.
- Compare research methodologies and findings.
- Discover potential research gaps from the literature.
- Generate evidence-backed literature survey reports.

## Technology Stack

| Layer | Technology |
|---|---|
| UI | Streamlit 1.35+ |
| PDF extraction | PyMuPDF |
| Embeddings | Sentence Transformers (local) |
| Vector search | FAISS |
| LLM | Google Gemini API |
| Metadata DB | SQLite |
| Data manipulation | Pandas |

## Setup

### 1. Create and activate a virtual environment

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

```bash
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY
```

### 4. Create required data directories

```bash
mkdir -p data/uploads data/processed data/indexes data/reports
```

### 5. Run the application

```bash
streamlit run app.py
```

### 6. Run tests

```bash
pytest tests/ -v
```

## Project Structure

```
ScholarLensAI/
├── app.py                  Main Streamlit entry point
├── requirements.txt
├── .env.example
├── pages/                  One file per sidebar page
├── services/               RAG pipeline modules
├── database/               SQLite helpers
├── utils/                  Config and helpers
├── tests/                  Pytest test suite
└── data/
    ├── uploads/            User-uploaded PDFs (git-ignored)
    ├── processed/          Extracted text (git-ignored)
    ├── indexes/            FAISS vector indexes (git-ignored)
    └── reports/            Generated reports (git-ignored)
```

## Architecture Notes

- **No LangChain** — the RAG pipeline is implemented with plain Python functions.
- Embeddings are generated locally with Sentence Transformers (no API cost).
- Gemini is used only for answer generation and report summarisation.
- All secrets are loaded from `.env` via `python-dotenv`; nothing is hardcoded.
