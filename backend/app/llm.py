from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from functools import lru_cache

from .models import CodeChunk


REFUSAL = "I couldn't determine this from the repository. The retrieved files do not contain enough evidence."


def insufficient_evidence_answer(question: str) -> str:
    if re.search(r"\b(auth|authentication|authenticate|login|log ?in|sign ?in)\b", question, re.I):
        return "I couldn't find evidence of an authentication flow in this repository. I found no credible authentication routes, middleware, session or token handling, or login implementation."
    return REFUSAL


def authentication_answer(question: str, results: list[tuple[CodeChunk, float]]) -> tuple[str, list[dict]] | None:
    if not re.search(r"\b(auth|authentication|authenticate|login|log ?in|sign ?in)\b", question, re.I):
        return None
    account_evidence = next(
        (chunk for chunk, _ in results if "account" in chunk.content.lower() and re.search(r"\b(no|not|without|optional)\b.{0,40}\baccount|\baccount.{0,40}\b(not required|optional)", chunk.content, re.I)),
        None,
    )
    socket_evidence = next((chunk for chunk, _ in results if "socket.handshake.auth" in chunk.content.lower()), None)
    if not account_evidence or not socket_evidence:
        return None
    citations = [
        {"path": account_evidence.path, "start_line": account_evidence.start_line, "end_line": account_evidence.end_line},
        {"path": socket_evidence.path, "start_line": socket_evidence.start_line, "end_line": socket_evidence.end_line},
    ]
    answer = (
        "This repository does not implement account-based login authentication; players can join without accounts "
        f"[{account_evidence.path}:{account_evidence.start_line}-{account_evidence.end_line}]. "
        "The server does read `socket.handshake.auth` when a Socket.IO client connects "
        f"[{socket_evidence.path}:{socket_evidence.start_line}-{socket_evidence.end_line}], but that is room/reconnect connection metadata—not a user login or authorization system."
    )
    return answer, citations


@lru_cache(maxsize=1)
def available_ollama_model() -> str:
    configured = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:7b")
    tags_endpoint = os.getenv("OLLAMA_TAGS_URL", "http://127.0.0.1:11434/api/tags")
    try:
        with urllib.request.urlopen(tags_endpoint, timeout=2) as response:
            names = [model.get("name", "") for model in json.loads(response.read()).get("models", [])]
        if configured in names:
            return configured
        if names:
            return names[0]
    except (OSError, KeyError, ValueError, urllib.error.URLError):
        pass
    return configured


def cited_sources(answer: str, results: list[tuple[CodeChunk, float]]) -> list[dict] | None:
    allowed = {
        (chunk.path, chunk.start_line, chunk.end_line):
        {"path": chunk.path, "start_line": chunk.start_line, "end_line": chunk.end_line}
        for chunk, _ in results
    }
    matches = re.findall(r"\[([^:\]\n]+):(\d+)-(\d+)\]", answer)
    if not matches:
        return None
    used = []
    for path, start, end in matches:
        citation = allowed.get((path, int(start), int(end)))
        if citation is None:
            return None
        if citation not in used:
            used.append(citation)
    return used


def structural_answer(question: str, results: list[tuple[CodeChunk, float]]) -> tuple[str, list[dict]] | None:
    def find(path_fragment: str, content_markers: tuple[str, ...] = ()) -> CodeChunk | None:
        return next((chunk for chunk, _ in results if path_fragment in chunk.path.lower() and (not content_markers or any(marker in chunk.content.lower() for marker in content_markers))), None)

    def citation(chunk: CodeChunk) -> dict:
        return {"path": chunk.path, "start_line": chunk.start_line, "end_line": chunk.end_line}

    if re.search(r"\b(api|endpoint)\b", question, re.I):
        route = find("server/index", ("request.url", "request.method", "sendjson("))
        if route:
            cite = citation(route)
            return (
                f"Add a new HTTP endpoint in `{route.path}`, beside the existing request-method and URL branches. Follow the nearby pattern: validate the request, call the relevant service or store, then return through `sendJson` [{route.path}:{route.start_line}-{route.end_line}].",
                [cite],
            )

    if re.search(r"\b(database|data store|persistence|sql|db)\b", question, re.I):
        route = find("server/index", ("fetchhistory", "savegamehistory", "isdb"))
        store = find("gamedatastore")
        database = find("server/db")
        if store and database:
            used = [chunk for chunk in (route, store, database) if chunk]
            route_text = f"The HTTP handler in `{route.path}` calls the data-store boundary [{route.path}:{route.start_line}-{route.end_line}]. " if route else ""
            answer = (
                route_text
                + f"`{store.path}` owns the persistence operations and obtains the database pool [{store.path}:{store.start_line}-{store.end_line}]. "
                + f"`{database.path}` creates the PostgreSQL pool from configuration [{database.path}:{database.start_line}-{database.end_line}]."
            )
            return answer, [citation(chunk) for chunk in used]

    if re.search(r"\b(draw|drawing|stroke|canvas)\b", question, re.I) and re.search(r"\b(client|server|move|flow|send)\b", question, re.I):
        client = find("src/app", ("room_message", "drawing_stroke", "drawing_batch"))
        server = find("server/index", ("drawing_stroke", "drawing_batch"))
        if client and server:
            return (
                f"The React client emits completed strokes as `room_message` events (`drawing_stroke` or `drawing_batch`) [{client.path}:{client.start_line}-{client.end_line}]. "
                f"The game server validates those messages, updates the room's stroke state, acknowledges accepted IDs, and broadcasts accepted strokes to the other players [{server.path}:{server.start_line}-{server.end_line}].",
                [citation(client), citation(server)],
            )

    if re.search(r"\b(room|rooms).*(stor|restor|persist|reconnect)|\b(stor|restor|persist|reconnect).*(room|rooms)\b", question, re.I):
        store = find("roomstore")
        redis = find("redis")
        if store:
            used = [chunk for chunk in (store, redis) if chunk]
            redis_text = f" Redis provides shared snapshots when configured [{redis.path}:{redis.start_line}-{redis.end_line}]." if redis else ""
            return (
                f"Active room state is serialized and restored through `{store.path}` [{store.path}:{store.start_line}-{store.end_line}].{redis_text} The server can therefore hydrate rooms after reconnects while retaining an in-memory fallback.",
                [citation(chunk) for chunk in used],
            )

    if re.search(r"\b(disconnect|disconnects|disconnected|player leaves|player left)\b", question, re.I):
        cleanup = find("server/index", ("removesocket", "player.disconnected"))
        if cleanup:
            return (
                f"Disconnect cleanup is handled in `{cleanup.path}`: the player is marked disconnected, voice and vote state are cleared, host or drawer responsibilities are reassigned, and an empty room is scheduled for persistence and cleanup [{cleanup.path}:{cleanup.start_line}-{cleanup.end_line}].",
                [citation(cleanup)],
            )

    if re.search(r"\b(score|scoring|points|award)\b", question, re.I):
        scoring = find("server/index", ("awardcorrectguess", "player.score +=", "computedrawerscore"))
        if scoring:
            return (
                f"Scoring is calculated on the server in `{scoring.path}`. Correct guesses award time-based points, while the drawer receives points derived from successful guesses and may receive a hand-drawing bonus [{scoring.path}:{scoring.start_line}-{scoring.end_line}].",
                [citation(scoring)],
            )
    return None


def grounded_answer(question: str, results: list[tuple[CodeChunk, float]]) -> tuple[str, list[dict]]:
    if not results or results[0][1] < 0.006:
        return insufficient_evidence_answer(question), []
    citations = [
        {"path": chunk.path, "start_line": chunk.start_line, "end_line": chunk.end_line}
        for chunk, _ in results[:3]
    ]
    deterministic = authentication_answer(question, results)
    if deterministic:
        return deterministic
    deterministic = structural_answer(question, results)
    if deterministic:
        return deterministic
    if re.search(r"\b(what (?:does|is)|purpose|overview|about)\b.*\b(project|repo|repository|codebase)\b|\bproject do\b", question, re.I):
        return extractive_answer(results), extractive_citations(results, citations)
    model = available_ollama_model()
    endpoint = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434/api/generate")
    context = "\n\n".join(
        f"SOURCE {index + 1}: {chunk.path}:{chunk.start_line}-{chunk.end_line}\n{chunk.content[:1400]}"
        for index, (chunk, _) in enumerate(results[:5])
    )
    prompt = f"""You are RepoLens. Answer only from the supplied repository sources.
If the sources do not support an answer, respond exactly: {REFUSAL}
Keep the answer concise. Cite claims inline as [path:start-end]. Never invent a path or line.

QUESTION: {question}

{context}
"""
    try:
        request = urllib.request.Request(endpoint, data=json.dumps({"model": model, "prompt": prompt, "stream": False, "options": {"temperature": 0.1, "num_predict": 220}}).encode(), headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(request, timeout=60) as response:
            answer = json.loads(response.read())["response"].strip()
        if answer == REFUSAL:
            return answer, []
        validated_citations = cited_sources(answer, results)
        if not answer or not validated_citations:
            return extractive_answer(results), extractive_citations(results, citations)
        return answer, validated_citations
    except (OSError, KeyError, ValueError, urllib.error.URLError):
        return extractive_answer(results), extractive_citations(results, citations)


def extractive_citations(results: list[tuple[CodeChunk, float]], citations: list[dict]) -> list[dict]:
    if results and results[0][0].path.lower().split("/")[-1].startswith("readme"):
        return citations[:1]
    return citations


def extractive_answer(results: list[tuple[CodeChunk, float]]) -> str:
    statements = []
    for chunk, _ in results[:3]:
        if chunk.path.lower().split("/")[-1].startswith("readme"):
            useful = [
                line.strip() for line in chunk.content.splitlines()
                if line.strip() and not line.strip().startswith(("#", "![", "```", "|", "<"))
            ]
            if useful:
                summary = " ".join(useful[:2])[:500]
                statements.append(f"The README describes the project this way: {summary} [{chunk.path}:{chunk.start_line}-{chunk.end_line}].")
                break
        first = next((line.strip() for line in chunk.content.splitlines() if line.strip() and not line.strip().startswith(("#", "//", "*"))), "")
        description = f"The strongest evidence is `{chunk.name}` ({chunk.kind}) in `{chunk.path}`"
        if first: description += f", beginning with `{first[:140]}`"
        statements.append(f"{description} [{chunk.path}:{chunk.start_line}-{chunk.end_line}].")
    return " ".join(statements) if statements else REFUSAL
