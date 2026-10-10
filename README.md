# ScholarLens AI

> Upload your research papers and instantly ask questions, compare studies, discover gaps, and generate literature survey reports — all powered by AI.
> Built for students and researchers who want smart insights from academic PDFs without the manual effort.

---

## Features

- **Research Chat** — Ask questions across uploaded papers with page-level citations
- **Paper Library** — Manage and browse all your uploaded PDFs
- **AI Screening** — Auto-screen papers for relevance to your research topic
- **Paper Comparison** — Compare methodologies and findings side by side
- **Research Gaps** — Discover potential gaps and unexplored areas in the literature
- **Dashboard** — Overview of your research collection at a glance
- **Reports** — Generate evidence-backed literature survey reports

---

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

---

## Quick Start

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

---

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

---

## Architecture Notes

- **No LangChain** — RAG pipeline built with plain Python for full control
- Embeddings generated locally with Sentence Transformers (zero API cost)
- Gemini used only for answer generation and report summarisation
- All secrets loaded from `.env` via `python-dotenv` — nothing hardcoded

---

## Deployment

Deploy for free on **[Hugging Face Spaces](https://huggingface.co/spaces)**:
1. Push this repo to GitHub
2. Create a new Space at https://huggingface.co/new-space (SDK: Streamlit)
3. Link your GitHub repository
4. Add `GEMINI_API_KEY` and `GEMINI_MODEL` in the Space secrets

---

*Made for researchers who deserve better tools.*
