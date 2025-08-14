# Real-Time AI Knowledge Mapper — POC Implementation Spec (for CodeGen AI)

**Owner:** Chris Sorel  
**Audience:** Senior full‑stack engineer / CodeGen AI  
**Goal:** Ship a demo‑ready, live **interactive knowledge graph** that converts arbitrary text into entities + relations, renders them in 3D, and supports QA with citations — all in **15 minutes of stage time**.

---

## 0) Scope

### In-Scope
- Paste text → chunk → LLM IE → canonicalize → store triples & vectors → stream nodes/edges as they’re discovered.
- Interactive 3D/2D graph with tooltips, side panel summaries, evidence quotes, and expand-neighborhood.
- Question input → retrieve relevant subgraph → grounded answer with citations.
- Minimal orchestration (FastAPI), in-memory/single-node stores OK for POC.

### Out-of-Scope (POC)
- Multi-user auth, RBAC, persistence guarantees, long-running jobs, elaborate retry queues.
- Document uploads beyond plain text (optional OCR stretch).
- Production SLOs / cost optimizations.

---

## 1) Architecture

```
              ┌────────────┐        ┌──────────────┐
   Text --->  │  Ingestion │ -----> │  LLM (IE)    │
 (paste/API)  └─────┬──────┘        └─────┬────────┘
                    │       ┌──────────────▼───────────────┐
                    │       │ Canonicalize (Qdrant ANN)     │
                    │       └──────────────┬───────────────┘
                    │                      │
                    │           ┌──────────▼─────────┐
                    ├──────────▶│  Oxigraph (RDF)    │   triples
                    │           └──────────┬─────────┘
                    │                      │
                    │           ┌──────────▼─────────┐
                    └──────────▶│  Qdrant (Vectors)  │   embeddings
                                └──────────┬─────────┘
                                           │
                              ┌────────────▼─────────────┐
                              │ FastAPI + WebSocket (WS) │
                              └────────────┬─────────────┘
                                           │ stream nodes/edges
                               ┌───────────▼───────────┐
                               │  React UI (3D Graph)  │
                               └───────────────────────┘
```

**Tech Stack**
- **Backend:** Python 3.11, FastAPI, Uvicorn, Pydantic, asyncio
- **LLM:** GPT‑4o-class (JSON mode), Embeddings: `text-embedding-3-large`
- **Stores:** Oxigraph (triples), Qdrant (vectors)
- **Frontend:** React + Vite, `react-force-graph-3d` (or Cytoscape.js 2D), Tailwind, Zustand, `react-use-websocket`
- **Build polish:** Framer Motion for panels; optional Highlight.js for evidence.

---

## 2) Data Model

### 2.1 Node (entity)
```json
{
  "id": "sha256(name|type)",
  "name": "Transformer",
  "type": "Concept|Library|Person|Org|Paper|System|Metric",
  "aliases": ["Transformers", "Attention-based models"],
  "embedding": [0.01, ...],
  "salience": 0.0,
  "source_spans": [
    { "doc_id": "docA", "start": 120, "end": 180 }
  ],
  "created_at": "iso-8601",
  "updated_at": "iso-8601"
}
```

### 2.2 Edge (relation)
```json
{
  "from": "node_id",
  "to": "node_id",
  "predicate": "depends_on|is_part_of|implements|compares_with|improves|causes|measures|trained_on",
  "confidence": 0.0,
  "evidence": [
    { "doc_id": "docA", "quote": "verbatim quote ≤200 chars", "offset": 345 }
  ],
  "directional": true
}
```

### 2.3 RDF Predicates (IRIs)
Use `<urn:kg:predicate:*>` e.g. `<urn:kg:predicate:depends_on>`. Nodes use `<urn:kg:node:{id}>`.

---

## 3) API Spec (FastAPI)

### 3.1 POST `/ingest`
**Body**
```json
{
  "doc_id": "string",
  "text": "raw text to map"
}
```
**Behavior**
- Split `text` into chunks (≤ ~1800 tokens, keep paragraph boundaries).
- For each chunk:
  1. Call IE LLM (strict JSON).
  2. For each entity: embed → ANN search in Qdrant → **merge** if cosine ≥ 0.86 or alias overlap or acronym equality (e.g., LoRA).
  3. Upsert node vectors; write triples for relations to Oxigraph.
  4. Generate micro-summary (≤30 words) per node from local evidence.
  5. **Broadcast** WS message with newly added/updated nodes/edges.
- Return `{"status":"ok","chunks":N}`.

### 3.2 WS `/stream`
**Server-to-client message (NDJSON lines over WS)**
```json
{"type":"upsert_nodes","nodes":[{...}]}
{"type":"upsert_edges","edges":[{...}]}
{"type":"status","stage":"chunked","count":12}
```

### 3.3 GET `/neighbors`
**Query:** `node_id: string`, `hops: int=1`, `limit: int=200`  
**Return:** `{ "nodes": [...], "edges": [...] }` (merged metadata, summaries)

### 3.4 GET `/search`
**Query:** `q: string`, `k: int=8`  
Vector search over Qdrant + name fuzzy → returns candidate nodes.

### 3.5 GET `/ask`
**Query:** `q: string`  
**Flow:**  
- Embed `q` → top‑k nodes (k=12).  
- SPARQL expand 1 hop neighborhood.  
- Build **grounded context** (node summaries + evidence quotes).  
- Call LLM QA → return `{ "answer": string, "citations": [{node_id, quote, doc_id}] }`.

### 3.6 GET `/graph/export`
Exports current graph as JSON for offline demo.

---

## 4) LLM Prompts

### 4.1 Information Extraction (chunk-level)
```
SYSTEM: You extract a typed knowledge graph from ONE chunk of text.

USER: Return STRICT JSON only:

{
  "entities": [
    {"name": "...", "type": "Concept|Library|Person|Org|Paper|System|Metric", "aliases": ["...","..."]}
  ],
  "relations": [
    {"from": "entity_name", "predicate": "depends_on|is_part_of|implements|compares_with|improves|causes|measures|trained_on",
     "to": "entity_name", "confidence": 0-1, "evidence_quotes": ["verbatim ≤200 chars"]}
  ],
  "salience": [{"entity": "entity_name", "score": 0-1}]
}

Rules:
- Use only entities explicit in text or obvious aliases.
- Keep relations atomic; no conjunctions inside a single edge.
- Include ≥1 evidence quote per relation.
- Prefer canonical names; add aliases.
- If nothing found, return empty arrays.
```

### 4.2 Node Micro-summary
```
SYSTEM: Summarize the node for tooltips using only provided evidence.

USER: In ≤30 words, describe what {name} ({type}) is and its role in this context. No claims without evidence. One sentence.
```

### 4.3 Grounded QA
```
SYSTEM: Answer using ONLY the provided snippets. Be concise and cite node_ids and verbatim quotes.

USER:
Question: "{q}"

Context:
- Nodes: {list of (node_id, name, type, summary)}
- Evidence: {list of (node_id, quote, doc_id)}

Return JSON:
{"answer":"...", "citations":[{"node_id":"...", "quote":"...", "doc_id":"..."}]}
```

---

## 5) Algorithms & Heuristics

- **Chunking:** split on headings/paragraphs; ensure ≤1800 tokens; keep sentence boundaries.
- **Merge (canonicalization):**
  - Cosine ≥ **0.86** on embeddings OR
  - Alias overlap (case-insensitive exact) OR
  - Acronym equality (e.g., “Low-Rank Adaptation” ⇄ “LoRA”) OR
  - Levenshtein distance ≤ 2 for short names (≤12 chars).
- **Edge acceptance:** keep iff `confidence ≥ 0.55` AND ≥1 evidence quote of ≥60 chars.
- **Salience:** `max(TF-IDF_zscore, sum(edge.confidence))` clamped [0,1].
- **Layout signals to UI:** `node.size = 8 + 12*salience`; `link.strength = confidence`.

---

## 6) Backend Skeleton (illustrative)

```python
# requirements:
# fastapi uvicorn pydantic qdrant-client oxigraph-python numpy websockets httpx

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams
from oxigraph import Store, NamedNode, Literal
import hashlib, json, asyncio, numpy as np

app = FastAPI()
store = Store()  # in-memory
qdrant = QdrantClient(":memory:")
COLL = "kg_nodes"

# init collection
def _init_qdrant():
    try:
        qdrant.get_collection(COLL)
    except:
        qdrant.recreate_collection(
            collection_name=COLL,
            vectors_config=VectorParams(size=3072, distance=Distance.COSINE)
        )
_init_qdrant()

class IngestReq(BaseModel):
    doc_id: str
    text: str

clients=set()

@app.websocket("/stream")
async def stream(ws: WebSocket):
    await ws.accept()
    clients.add(ws)
    try:
        while True:
            await ws.receive_text()  # ignore client messages
    except WebSocketDisconnect:
        clients.remove(ws)

async def broadcast(payload: dict):
    dead=[]
    m = json.dumps(payload)
    for c in list(clients):
        try:
            await c.send_text(m)
        except:
            dead.append(c)
    for d in dead:
        clients.discard(d)

def node_id(name: str, type_: str):
    return hashlib.sha256(f"{name}|{type_}".encode()).hexdigest()[:16]

@app.post("/ingest")
async def ingest(req: IngestReq):
    chunks = list(chunk_text(req.text))
    for i, chunk in enumerate(chunks):
        ie = await llm_extract(chunk)  # TODO: implement with JSON-mode LLM
        nodes, edges = await upsert_ie(req.doc_id, ie)
        await broadcast({"type":"upsert_nodes","nodes":nodes})
        await broadcast({"type":"upsert_edges","edges":edges})
        await broadcast({"type":"status","stage":"chunked","count":i+1})
    return {"status":"ok","chunks":len(chunks)}

# TODO: implement chunk_text, llm_extract, embed, ann_merge, upsert_ie, SPARQL queries, /neighbors, /ask
```

---

## 7) Frontend Spec (React)

### 7.1 Pages & Components
- `App`: layout (graph left, side panel right, top bar with search + question box).
- `Graph3D`: `react-force-graph-3d` canvas; subscribes to WS; renders nodes/links.
- `SidePanel`: shows node details (name, type, summary, evidence quotes, Expand 1‑hop).
- `SearchBox`: calls `/search` then centers + highlights selection.
- `QuestionBox`: hits `/ask`, displays answer with citations; emits “reweight” event.
- `State`: `zustand` store for nodes/edges maps, selection, answer.

### 7.2 WS Message Handling
```ts
type msg =
 | {type:"upsert_nodes", nodes: UINode[]}
 | {type:"upsert_edges", edges: UIEdge[]}
 | {type:"status", stage: "chunked"|"done", count: number}
```

### 7.3 Rendering Rules
- Node color by `type`; size by `salience`.
- Link width by `confidence` (min 0.5 px, max 3 px).
- Hover shows tooltip: name, type, top evidence quote.
- Click selects node and loads `/neighbors?node_id=...&hops=1`.

### 7.4 Minimal Styles
- Tailwind base; cards with `rounded-2xl`, shadows, padding >= `p-3`.
- Framer Motion for panel slide-in/out.

---

## 8) Local Dev

### 8.1 Backend
```bash
python -m venv .venv && source .venv/bin/activate
pip install fastapi uvicorn pydantic qdrant-client oxigraph-python numpy httpx websockets
uvicorn server:app --reload --port 8000
```

### 8.2 Frontend
```bash
npm create vite@latest knowledge-mapper -- --template react-ts
cd knowledge-mapper
npm i react-force-graph-3d three tailwindcss zustand react-use-websocket framer-motion
npm run dev
```

---

## 9) Demo Script (15 minutes)

1. **Cold open (1 min):** paste a dense paragraph (e.g., ML paper intro) into a text box that hits `/ingest`.
2. **Watch it grow (3 min):** nodes/edges animate in; call out typed predicates & confidence-weighted links.
3. **Click through (3 min):** show summaries and inline evidence quotes (hover).
4. **Ask a question (3 min):** “What improvements does Method X claim over Y?” → reweight center nodes; show citations.
5. **Second doc (3 min):** paste a conflicting article; highlight `compares_with` edges & merges.

**Offline fallback:** preload `/graph/export` JSON; render without backend if Wi-Fi dies.

---

## 10) Quality & Guardrails

- Display evidence quotes by default to deter hallucinations.
- Hard thresholds: `merge_cosine ≥ 0.86`, `edge_conf ≥ 0.55`, `quote_len ≥ 60`.
- Clamp new nodes per chunk to 80; cluster low-salience nodes into “constellations.”
- Backpressure: limit concurrent LLM calls to 2; stream results per-chunk.

---

## 11) Minimal Test Plan

- **IE JSON validity:** 50 random chunks → 100% parseable.
- **Merge correctness:** synthetic aliases converge; acronym mapping works.
- **Edge acceptance:** low‑confidence relations filtered.
- **API smoke:** `/ingest` streams updates; `/search` returns top‑k; `/neighbors` returns bounded subgraph; `/ask` returns citations.
- **UI:** hover/click tooltips; expand 1‑hop; question reweight visual.

---

## 12) Stretch Goals (Optional)

- Cross‑doc coref in background.
- Graph diff view: show only edges added by last document.
- Temporal replay slider.
- Image to KG: OCR → same pipeline.

---

## 13) Env Vars

```
OPENAI_API_KEY=...
EMBED_MODEL=text-embedding-3-large
LLM_MODEL=gpt-4o
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY= (optional)
OXIGRAPH_DIR=./oxigraph-data (or in-memory)
```

---

## 14) Acceptance Criteria (Demo-Ready)

- Paste text → see nodes/edges within 5 seconds for first chunk.
- Clicking a node shows a 30‑word summary and ≥1 evidence quote.
- Asking a question returns an answer and ≥2 citations in ≤5 seconds (for small graphs).
- Export/import graph works for offline demo.

---

## 15) Seed Data (Optional)
Provide a `seed/` folder with 2–3 short ML intros (e.g., transformers, LoRA, RAG). A CLI script posts them to `/ingest` sequentially to prewarm the demo.

---

## 16) File Layout (suggested)

```
/server
  server.py
  llm.py
  ie_schema.py
  storage/
    qdrant.py
    oxigraph.py
  util/
    chunk.py
    id.py
/client
  src/
    App.tsx
    components/
      Graph3D.tsx
      SidePanel.tsx
      SearchBox.tsx
      QuestionBox.tsx
    state/useStore.ts
  index.css
/docs
  demo-script.md
  api.md
```

---

## 17) Notes for CodeGen AI
- Enforce **strict JSON** responses; reject LLM outputs with trailing prose.
- Guard all network calls with timeouts/retries; surface user-friendly toasts in UI.
- Keep the system **stateless enough** that a single `Ctrl+C` and restart recovers without data loss (use export/import if needed).
