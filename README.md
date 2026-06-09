# BioSeek — Agentic Biomedical RAG Assistant

> **A multimodal AI research assistant that combines vector search, cross-encoder re-ranking, and Gemini 2.5 Flash to answer scientific questions grounded in a curated biomedical knowledge base.**

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Configuration](#configuration)
  - [Running the App](#running-the-app)
- [How It Works](#how-it-works)
  - [Two-Stage Retrieval](#two-stage-retrieval)
  - [Agentic Function Calling](#agentic-function-calling)
  - [Multimodal Input](#multimodal-input)
- [API Reference](#api-reference)
- [Qdrant Collections](#qdrant-collections)
- [Frontend](#frontend)

---

## Overview

BioSeek is an agentic RAG (Retrieval-Augmented Generation) system built for biomedical research assistance. It gives Google Gemini 2.5 Flash access to a Qdrant vector database containing biomedical knowledge, and lets the model decide autonomously when and what to retrieve — producing answers that are grounded in verifiable source material rather than model hallucinations.

**What it can do:**

- Answer biomedical and clinical questions using knowledge stored in Qdrant
- Accept image uploads (microscopy, gel electrophoresis, spectral data) for multimodal analysis
- Retrieve and surface relevant reference images from the knowledge base alongside text answers
- Render responses in formatted Markdown directly in the chat UI
- Run entirely as a single-server app — FastAPI serves both the backend API and the static frontend

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                          BioSeek Pipeline                            │
├───────────────────┬──────────────────────────────────────────────────┤
│                   │                                                  │
│   BROWSER         │             FASTAPI SERVER (backend.py)          │
│                   │                                                  │
│  ┌─────────────┐  │  POST         ┌──────────────────────────────┐  │
│  │  index.html │  │─/ask_multi──► │  /ask_multimodal endpoint    │  │
│  │  script.js  │  │  modal        │                              │  │
│  │  style.css  │◄─│───────────────│  1. Parse question + image   │  │
│  └─────────────┘  │  JSON resp.   │  2. Build prompt parts       │  │
│                   │               │  3. Start Gemini Chat         │  │
│                   │               └──────────┬───────────────────┘  │
│                   │                          │ auto function call    │
│                   │               ┌──────────▼───────────────────┐  │
│                   │               │  search_medical_database()    │  │
│                   │               │                              │  │
│                   │               │  ┌────────────────────────┐  │  │
│                   │               │  │ SentenceTransformer    │  │  │
│                   │               │  │ encode(search_term)    │  │  │
│                   │               │  └──────────┬─────────────┘  │  │
│                   │               │             │ 128/768D vector │  │
│                   │               │  ┌──────────▼─────────────┐  │  │
│                   │               │  │ Qdrant Vector Search   │  │  │
│                   │               │  │ bio_knowledge_base → 10│  │  │
│                   │               │  │ bio_images        → 3  │  │  │
│                   │               │  └──────────┬─────────────┘  │  │
│                   │               │             │ candidates      │  │
│                   │               │  ┌──────────▼─────────────┐  │  │
│                   │               │  │ CrossEncoder Re-Rank   │  │  │
│                   │               │  │ 10 candidates → top 3  │  │  │
│                   │               │  └──────────┬─────────────┘  │  │
│                   │               │             │ top context     │  │
│                   │               └─────────────┼────────────────┘  │
│                   │                             │                    │
│                   │               ┌─────────────▼────────────────┐  │
│                   │               │  Gemini 2.5 Flash            │  │
│                   │               │  Synthesizes final answer    │  │
│                   │               │  in Markdown                 │  │
│                   │               └──────────────────────────────┘  │
│                   │                                                  │
└───────────────────┴──────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Web Framework | FastAPI + Uvicorn |
| AI Agent | Google Gemini 2.5 Flash (`gemini-2.5-flash`) |
| Vector Database | Qdrant Cloud |
| Embedding Model | SentenceTransformer (configured in `config.py`) |
| Re-Ranking | CrossEncoder — `cross-encoder/ms-marco-MiniLM-L-6-v2` |
| Image Processing | Pillow (PIL) |
| Frontend | HTML5 + CSS3 + Vanilla JavaScript |
| Markdown Rendering | marked.js |
| Icons | Font Awesome 6 |
| Config Management | python-dotenv |
| File Uploads | python-multipart |

---

## Project Structure

```
BioSeek/
│
├── backend.py          # FastAPI app — agent, RAG pipeline, API endpoints
├── index.html          # Chat UI (served by FastAPI)
├── script.js           # Frontend logic — fetch, DOM manipulation, Markdown
├── style.css           # UI styles (glassmorphism dark theme)
├── requirements.txt    # Python dependencies
├── .env                # API keys — Qdrant + Gemini (never commit this)
├── .gitignore
│
└── static/
    └── images/         # Temporary storage for uploaded images (auto-created)
```

> **Note:** `config.py` (imported by `backend.py`) is excluded from version control via `.gitignore`. Create it locally — see [Configuration](#configuration).

---

## Getting Started

### Prerequisites

- Python 3.10+
- A [Qdrant Cloud](https://cloud.qdrant.io) account with a cluster and two collections pre-populated (`bio_knowledge_base`, `bio_images`)
- A [Google AI Studio](https://aistudio.google.com) API key with Gemini 2.5 Flash access

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/<your-username>/BioSeek.git
cd BioSeek

# 2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt
```

> **Note:** `sentence-transformers` will download model weights (~90 MB) on first run. `cross-encoder/ms-marco-MiniLM-L-6-v2` (~85 MB) is downloaded separately. Ensure you have a stable internet connection.

### Configuration

Create a `config.py` file at the root of the project:

```python
# config.py

QDRANT_URL     = "https://your-cluster-url.qdrant.io"
QDRANT_API_KEY = "your-qdrant-api-key"
GEMINI_API_KEY = "your-gemini-api-key"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"   # or any SentenceTransformer model
```

Alternatively, copy `.env` and fill in your keys — then load them in `config.py` via `python-dotenv`:

```python
from dotenv import load_dotenv
import os
load_dotenv()

QDRANT_URL      = os.getenv("QDRANT_URL")
QDRANT_API_KEY  = os.getenv("QDRANT_API_KEY")
GEMINI_API_KEY  = os.getenv("GEMINI_API_KEY")
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
```

### Running the App

```bash
python backend.py
```

Then open your browser at: **`http://127.0.0.1:8000`**

FastAPI serves the frontend (`index.html`, `style.css`, `script.js`) directly — no separate web server needed.

---

## How It Works

### Two-Stage Retrieval

Naive vector search returns the top-N most similar documents by embedding distance — but similarity in embedding space does not always equal relevance to the specific question. BioSeek uses a **two-stage pipeline** to improve precision:

**Stage 1 — Broad recall (Qdrant ANN search)**
The query is encoded into a dense vector by `SentenceTransformer`. Qdrant returns the 10 nearest neighbours from `bio_knowledge_base` (approximate nearest neighbour search). This is fast but imprecise.

**Stage 2 — Precision re-ranking (CrossEncoder)**
The `CrossEncoder` takes the original query and each of the 10 candidate texts as a pair and scores their relevance jointly. Unlike bi-encoders (which encode query and document independently), a cross-encoder sees both at once — producing a more accurate relevance score. The top 3 candidates are kept and passed to Gemini as context.

```
Query ──► SentenceTransformer ──► Qdrant (top 10) ──► CrossEncoder ──► Top 3 ──► Gemini
          (bi-encoder, fast)       (ANN search)        (rerank, precise)
```

### Agentic Function Calling

The Gemini agent is initialized with `enable_automatic_function_calling=True`. This means Gemini autonomously decides:

- **When** to call `search_medical_database` (not every message requires a DB lookup)
- **What** search term to use (it may rephrase the user's question for better retrieval)
- **How many times** to call it (it can make multiple calls if needed)

The tool returns a structured text block of the top-3 re-ranked knowledge snippets plus any image metadata from `bio_images`. Gemini then synthesizes a final Markdown-formatted answer.

The agent's system instruction enforces grounding:

> *"Si l'outil ne renvoie rien, dis que tu ne sais pas. N'invente pas."*

### Multimodal Input

Users can attach an image (JPEG, PNG, etc.) alongside their question. The image is:

1. Saved temporarily to `static/images/` with a UUID filename
2. Opened with Pillow and passed as a native image part in the Gemini API request
3. Analysed in conjunction with the text question and any retrieved knowledge

This enables queries like: *"What does this gel band pattern indicate?"* with an actual gel image attached.

---

## API Reference

### `POST /ask_multimodal`

The main endpoint. Accepts `multipart/form-data`.

| Field | Type | Required | Description |
|---|---|---|---|
| `question` | `string` | Yes | User's biomedical question |
| `file` | `UploadFile` | No | Image file (gel, microscopy, spectra, etc.) |

**Response:**

```json
{
  "answer": "**Réponse Markdown formatée...**",
  "db_images": [
    {
      "url": "https://...",
      "desc": "Gel électrophorèse protéine X",
      "source": "Base de Données",
      "caption": "Gel électrophorèse protéine X"
    }
  ]
}
```

`db_images` contains visual references retrieved from the `bio_images` Qdrant collection and rendered in the chat alongside the text answer.

---

### Static File Routes

| Route | Returns |
|---|---|
| `GET /` | `index.html` |
| `GET /style.css` | `style.css` |
| `GET /script.js` | `script.js` |

---

## Qdrant Collections

BioSeek expects two collections to exist in your Qdrant instance before running.

### `bio_knowledge_base`

Stores text chunks from biomedical literature, protocols, or research notes.

| Payload field | Type | Description |
|---|---|---|
| `text` | string | The knowledge chunk (paragraph, abstract, etc.) |

### `bio_images`

Stores metadata for biomedical reference images (gel results, spectra, microscopy).

| Payload field | Type | Description |
|---|---|---|
| `caption` | string | Image description |
| `image_url` | string | Publicly accessible image URL |

Both collections must use vectors of the same dimensionality as the configured `EMBEDDING_MODEL`.

---

## Frontend

The chat interface is a single-page vanilla JS application served by FastAPI.

**Key behaviours:**

- **Enter** sends the message; **Shift+Enter** inserts a newline
- The paperclip button opens a file picker for image attachments; a green badge confirms a file is selected
- AI responses are parsed and rendered as Markdown using `marked.js` (bold, lists, headings, etc.)
- Reference images retrieved from `bio_images` appear below the text answer with their captions
- A spinning loader icon is shown while the backend processes the request
- The connection indicator in the sidebar shows backend status on port 8000

**Libraries loaded via CDN:**

```html
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
```
