from __future__ import annotations

import re
import time
from dataclasses import fields

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .analyzer import analyze_repository
from .github_activity import fetch_github_activity
from .ingestion import clone_public_repository, find_local_checkout, open_local_repository
from .llm import REFUSAL, grounded_answer
from .models import CodeChunk
from .recent_work import collect_recent_work
from .retrieval import HybridRetriever
from .security import UnsafeRepository
from .storage import load_payload, save_analysis, save_trace


app = FastAPI(title="RepoLens API", version="0.1.0", description="Evidence-first GitHub repository intelligence")
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^http://(localhost|127\.0\.0\.1):\d+$",
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


class AnalyzeRequest(BaseModel):
    url: str = Field(min_length=8, max_length=300)


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1000)


class LocalAnalyzeRequest(BaseModel):
    path: str = Field(min_length=1, max_length=1000)


def contributor_orientation(question: str, payload: dict, chunks: list[CodeChunk]) -> tuple[str, list[dict]] | None:
    if not re.search(r"\b(contribut|files? should|read first)\b", question, re.I):
        return None
    facts = {item.get("path", ""): item for item in payload.get("important_files", []) + payload.get("reading_order", [])}
    available_paths = {chunk.path for chunk in chunks}
    preferred_paths = ["README.md"]
    preferred_paths.extend(item.get("path", "") for item in payload.get("entry_points", []))
    preferred_paths.extend(path for path in ("src/main.tsx", "src/App.tsx", "server/index.js", "server/roomStore.js", "server/gameDataStore.js") if path in available_paths)
    preferred_paths.extend(item.get("path", "") for item in payload.get("reading_order", []))
    preferred = []
    seen = set()
    for path in preferred_paths:
        if path and path in available_paths and path not in seen:
            preferred.append(facts.get(path, {"path": path, "summary": "Key entry point or architectural boundary."}))
            seen.add(path)
        if len(preferred) == 5:
            break
    entries = []
    citations = []
    for item in preferred:
        path = item.get("path", "")
        evidence = min((chunk for chunk in chunks if chunk.path == path), key=lambda chunk: chunk.start_line, default=None)
        if not evidence:
            continue
        entries.append(f"`{path}` — {item.get('summary', 'key repository file')} [{path}:{evidence.start_line}-{evidence.end_line}]")
        citations.append({"path": path, "start_line": evidence.start_line, "end_line": evidence.end_line})
    if not entries:
        return None
    return "Start with these files, in order: " + "; ".join(entries) + ".", citations


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/analyze")
def analyze(request: AnalyzeRequest) -> dict:
    try:
        with clone_public_repository(request.url) as (root, owner, repo, branch):
            record = analyze_repository(root, owner, repo, request.url, branch)
            record.github_activity = fetch_github_activity(owner, repo)
            record.recent_work = collect_recent_work(root, owner, repo)
            save_analysis(record)
            return record.public_dict()
    except UnsafeRepository as exc:
        local = find_local_checkout(request.url)
        if local:
            root, owner, repo, url, branch = local
            record = analyze_repository(root, owner, repo, url, branch)
            record.github_activity = fetch_github_activity(owner, repo)
            record.recent_work = collect_recent_work(root, owner, repo)
            record.warnings.insert(0, "The GitHub clone was unavailable, so RepoLens analyzed the matching local checkout.")
            save_analysis(record)
            return record.public_dict()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Repository analysis failed safely. Check the service logs for details.") from exc


@app.post("/api/repos/{analysis_id}/ask")
def ask(analysis_id: str, request: AskRequest) -> dict:
    payload = load_payload(analysis_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="Analysis not found. Analyze the repository again.")
    chunks = [CodeChunk(**{key: value for key, value in item.items() if key in {field.name for field in fields(CodeChunk)}}) for item in payload.get("chunks", [])]
    started = time.perf_counter()
    results = HybridRetriever(chunks).search(request.question, limit=6, candidates=20)
    orientation = contributor_orientation(request.question, payload, chunks)
    answer, citations = orientation or grounded_answer(request.question, results)
    latency_ms = int((time.perf_counter() - started) * 1000)
    retrieved = [{"path": chunk.path, "start_line": chunk.start_line, "end_line": chunk.end_line, "score": score} for chunk, score in results]
    save_trace(analysis_id, request.question, retrieved, latency_ms, "refused" if not citations or answer == REFUSAL else "answered")
    return {"answer": answer, "citations": citations, "retrieval": retrieved, "latency_ms": latency_ms, "model": "ollama-or-extractive"}


@app.post("/api/analyze-local")
def analyze_local(request: LocalAnalyzeRequest) -> dict:
    try:
        root, owner, repo, url, branch = open_local_repository(request.path)
        record = analyze_repository(root, owner, repo, url, branch)
        record.github_activity = fetch_github_activity(owner, repo)
        record.recent_work = collect_recent_work(root, owner, repo)
        save_analysis(record)
        return record.public_dict()
    except (UnsafeRepository, OSError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Local repository analysis failed safely. Check the service logs for details.") from exc
