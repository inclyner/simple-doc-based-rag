# Developer Log

This developer log includes the main decisions and reasoning behind them.

---

## Initial Setup

### Decisions

* Start with a simple FastAPI setup without Docker during early development.

### Trade-offs

* Faster iteration during development.
* Delayed containerization means slightly less portability early on.
* Planned to install FastAPI and add Docker after the core system was stable.
* Update: To keep things simple, the project currently runs directly with Uvicorn. Dockerization was postponed but remains possible.

---

## API Design

FastAPI is installed. Designed the main REST API endpoints:

* **GET /health** – Health check endpoint
* **POST /files** – Upload a knowledge file
* **DELETE /files/{doc_id}** – Delete a knowledge file
* **POST /ask** – Query the LLM with context retrieval

---

## Technology Choices

### Decisions

* Use LangChain for core RAG functionality.
* Avoid LangGraph for now to reduce complexity.

### Trade-offs

* Faster development speed and fewer moving parts.
* Might require future refactoring to handle complex workflow logic or retries.
  Using **LangChain** to avoid reinventing common RAG components:
* Document loading
* Text splitting
* Embeddings
* Vector store
* Retrieval-Augmented QA chain

Considered using **LangGraph** but decided it would be overkill for now. Might revisit later if retry logic or more complex flows are needed.

---

## Test Strategy (Before Implementation)

### Decisions

* Define unit tests early to guide implementation.

### Trade-offs

* More upfront work, but prevents fragile RAG behavior.
* Ensures system remains deterministic and reliable.
  Planned unit tests to anticipate common failure cases in RAG systems:
* Upload file → Should create a folder, store file and metadata
* Delete file → Folder must be removed and ChromaDB cleaned
* Contradictory knowledge → If a document says "the sky is green", response must follow context
* Out-of-scope query → Must return: `"this information is not available in my current knowledge base."`
* Bad embeddings → Synonyms must still work (e.g. „car” vs „automobile”)
* Deleted docs → Queries should not return removed content

These tests should cover around 80 percent of common RAG issues.

---

## files.py Development

### Decisions

* Use E5 base embeddings (HuggingFace) and ChromaDB as persistent vector store.

### Trade-offs

* CPU-friendly and free.
* No advanced features like hybrid search or vector compression yet.
* Selected embedding model: `intfloat/e5-base-v2` (fast, accurate, CPU-friendly).
* Using **ChromaDB** as the local vector database. Works offline and supports metadata filters.
* LangChain's Chroma integration made it simple to read/write chunks.
* Created two documents with artificial facts to test contradiction handling.

---

## ask.py Development

### Decisions

* Use OpenRouter + DeepSeek R1T2 Chimera (free model).
* Strict RAG behavior enforced with temperature 0.

### Trade-offs

* Zero-cost inference during development.
* Deterministic output but may lack creativity for some domains.
* Selected model: **TNG: DeepSeek R1T2 Chimera (free)** from OpenRouter (fast and free).
* Retrieval uses **top 4 most relevant chunks (K=4)**. If data becomes dense, this might be reduced.
* Set **temperature = 0** for deterministic responses.

Endpoint is complete and responds strictly based on provided context. Started writing tests.

After noticing that temperature 0 always returns the same output, the 100x consistency test became unnecessary and was removed.

The synonym test initially failed, so enabled **HuggingFaceEmbeddings normalize embeddings** option.

---

## Next Steps

* Conduct market research for industries where this technology can be applied.
* Build frontend guided by industry UX expectations.
* Improve scalability and add streaming responses.
* Research cost-effective model options for production.