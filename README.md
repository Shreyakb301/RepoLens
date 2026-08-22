# RepoLens

**Production-grade AI codebase intelligence.** RepoLens safely analyzes a public GitHub repository, maps its architecture, ranks the files worth reading, and answers questions with verifiable file/line citations.

## Why this is different

RepoLens treats static analysis as the source of truth and uses language models only to explain retrieved evidence. The current local-first release includes:

- constrained public GitHub ingestion with clone timeouts and repository size limits;
- local Git checkout analysis for private repositories without uploading code or pasting access tokens;
- open GitHub issue and pull-request summaries, with optional read-only token support for private repositories;
- recent-commit and contributor-focus summaries grounded in Git messages and changed file paths;
- filtering for dependencies, generated output, binaries, secrets, oversized files, and symlinks;
- Python AST chunks plus structural chunks for TypeScript, JavaScript, Go, Rust, Java, and other common languages;
- language, framework, route, symbol, entry-point, and file-role detection;
- BM25 + Sentence Transformers embeddings stored/searched in FAISS, reciprocal-rank fusion, and cross-encoder reranking;
- a deterministic hashed-vector and path/symbol fallback when optional ML models are disabled;
- optional Ollama generation and a zero-cost extractive fallback;
- citation enforcement and low-evidence refusal behavior;
- SQLite analysis metadata and retrieval traces;
- a responsive React analysis workspace and clickable architecture map;
- a golden retrieval dataset, Recall@3/MRR evaluator, and CI regression gate.

## Architecture

```text
GitHub URL
   -> safe recent-history clone (repository code is never executed)
   -> file policy and language detection
   -> AST/structural chunks + imports + routes + symbols
   -> BM25 search + local vector search
   -> reciprocal-rank fusion and reranking
   -> Ollama or grounded extractive answer
   -> answer + exact file/line citations
```

## Run locally

Prerequisites: Node 22+, Python 3.11+, Git, and optionally [Ollama](https://ollama.com/).

```bash
npm install
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
cp .env.example .env.local
```

For the full learned retrieval stack from the specification:

```bash
pip install -r backend/requirements-ml.txt
# Set REPOLENS_ML_ENABLED=1 in the backend environment.
```

The embedding and cross-encoder models download on first use. Leave the flag at
`0` for the lightweight, deterministic offline retrieval path.

Start the backend:

```bash
PYTHONPATH=backend uvicorn app.main:app --reload --port 8000
```

Start the frontend in another terminal:

```bash
npm run dev
```

Open the local URL printed by the frontend. The dev server proxies `/api` to the
backend on port 8000, so the frontend uses the same same-origin paths it uses in
production. If Ollama is not running, analysis and Q&A still work; answers use
cited extractive evidence.

For a private repository that already exists on your computer, choose **Local
folder** in the interface. `REPOLENS_LOCAL_ROOTS` controls which directories the
backend may read; it defaults to the current user's home directory for local
development. Use a narrower projects directory when sharing the service.

Optional Ollama setup:

```bash
ollama pull qwen2.5-coder:7b
ollama serve
```

Public repository issues and pull requests are retrieved through GitHub's
read-only REST API. Set `GITHUB_TOKEN` in the backend environment when inspecting
a private repository or when anonymous API limits are too restrictive. Use a
token with only the repository metadata, Issues read, and Pull requests read
permissions needed for the repositories you analyze. RepoLens never returns the
token to the browser or stores it in analysis records.

RepoLens also reads up to eight recent commits from the temporary clone or local
checkout. It uses commit messages, authors, dates, and changed file paths to show
what contributors appear to be working on. This is static Git metadata analysis;
repository code and hooks are never executed.

## Deployment

RepoLens deploys as a single service. `vite build` writes the SPA to
`backend/static`, and the FastAPI app in `backend/app/main.py` serves it at `/`
alongside `/api/*`. Frontend and API share one origin, so there is no proxy
layer and no CORS allowlist to keep in sync.

[`render.yaml`](render.yaml) defines the Render web service and
[`Dockerfile`](Dockerfile) builds it: a Node stage compiles the SPA, and a
Python stage installs the backend, copies the build in, and runs Uvicorn. `git`
is installed in the runtime image because the analyzer shells out to it to clone
the repositories it inspects.

To deploy, point Render at the repository as a Blueprint; it reads
`render.yaml` and builds from the Dockerfile. `GITHUB_TOKEN` is optional and
declared with `sync: false`, so set it in the Render dashboard if you want the
higher GitHub API rate limit.

Build the production image locally with:

```bash
docker build -t repolens . && docker run --rm -p 8000:8000 repolens
```

## Quality checks

```bash
PYTHONPATH=backend pytest backend/tests -q
PYTHONPATH=backend python backend/eval/run_eval.py --min-recall 0.80
npm test
```

`npm test` builds the SPA and asserts the build output.

The evaluator reports Recall@3 and mean reciprocal rank. Run it once for the fallback and once with `REPOLENS_ML_ENABLED=1` when comparing retrieval configurations. Replace the small included fixture with 50–100 questions across known open-source repositories before publishing portfolio benchmark claims.

## Security boundary

RepoLens only accepts canonical HTTPS GitHub repository URLs. It does not execute cloned code. Clones are shallow, time-limited, and temporary; symlinks are excluded; text and file counts are capped; binary, dependency, generated, credential-like, and oversized files are skipped. This reduces risk but is not a complete malware sandbox—run the service with ordinary user privileges and network/process limits in production.

## Engineering record

See [ENGINEERING_LOG.txt](./ENGINEERING_LOG.txt) for implementation decisions, failed attempts, diagnoses, corrective work, and validation results.
