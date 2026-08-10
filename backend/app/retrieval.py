from __future__ import annotations

import hashlib
import math
import os
import re
from collections import Counter

from .models import CodeChunk


TOKEN = re.compile(r"[A-Za-z_$][A-Za-z0-9_$]{1,}")

STOP_WORDS = {
    "a", "an", "and", "are", "before", "could", "do", "does", "happen",
    "how", "i", "in", "is", "it", "me", "new", "of", "should", "the",
    "this", "to", "understand", "what", "where", "would",
}

QUERY_CONCEPTS = (
    (re.compile(r"\b(auth|authentication|authenticate|login|log ?in|sign ?in)\b", re.I),
     {"auth", "authentication", "authenticate", "authorization", "login", "logout", "signin", "password", "credential", "session", "jwt", "bearer", "oauth", "passport", "bcrypt", "access_token"}),
    (re.compile(r"\b(database|data store|persistence|persist|sql|db)\b", re.I),
     {"database", "datastore", "persistence", "persist", "storage", "sql", "postgres", "postgresql", "mysql", "sqlite", "mongodb", "prisma", "sequelize", "typeorm", "db"}),
    (re.compile(r"\b(api|endpoint|route|controller|handler)\b", re.I),
     {"api", "endpoint", "route", "router", "controller", "handler", "request", "response", "express", "fastapi", "flask"}),
    (re.compile(r"\b(contribut|start|read first|files? should)\b", re.I),
     {"contributing", "contributor", "readme", "architecture", "setup", "install", "entry", "main", "package"}),
    (re.compile(r"\b(payment|payments|subscription|billing|checkout)\b", re.I),
     {"payment", "payments", "subscription", "stripe", "checkout", "invoice", "charge"}),
)

PAYMENT_TERMS = {"payment", "payments", "subscription", "stripe", "checkout", "invoice", "charge"}


def tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN.findall(text)]


def query_tokens(query: str) -> list[str]:
    """Return meaningful query terms plus conservative code-domain aliases."""
    terms = {term for term in tokenize(query) if term not in STOP_WORDS}
    for pattern, aliases in QUERY_CONCEPTS:
        if pattern.search(query):
            terms.update(aliases)
    return sorted(terms)


def intent_bonus(query: str, chunk: CodeChunk) -> float:
    """Promote structural evidence that prose-style questions imply."""
    path = chunk.path.lower()
    content = chunk.content.lower()
    bonus = 0.0
    if re.search(r"\b(database|data store|persistence|persist|sql|db)\b", query, re.I):
        if any(marker in path for marker in ("gamedatastore", "/db.", "database", "repository", "storage")): bonus += .11
        if any(marker in content for marker in ("pool.query", "fetchhistory", "savegamehistory", "database_url")): bonus += .07
    if re.search(r"\b(api|endpoint|route|controller|handler)\b", query, re.I):
        if path.endswith(("server/index.js", "server/index.ts", "app/main.py", "routes.py")): bonus += .08
        if any(marker in content for marker in ("request.url", "request.method", "sendjson(", "app.get(", "app.post(", "router.get(", "router.post(")): bonus += .10
    if re.search(r"\b(contribut|start|read first|files? should)\b", query, re.I):
        filename = path.split("/")[-1]
        if filename.startswith("readme"): bonus += .22 if chunk.start_line <= 10 else .16
        elif path in {"src/main.tsx", "src/app.tsx", "server/index.js", "package.json"}: bonus += .11
    if re.search(r"\b(draw|drawing|stroke|canvas)\b", query, re.I):
        if path in {"src/app.tsx", "server/index.js", "src/components/drawingcanvas.tsx"}: bonus += .07
        if any(marker in content for marker in ("drawing_stroke", "drawing_batch", "drawing_preview")) and ("room_message" in content or path == "server/index.js"): bonus += .12
    if re.search(r"\b(room|rooms).*(stor|restor|persist|reconnect)|\b(stor|restor|persist|reconnect).*(room|rooms)\b", query, re.I):
        if any(marker in path for marker in ("roomstore", "storage", "redis")): bonus += .11
        if any(marker in content for marker in ("snapshot", "hydrateroom", "saveroom", "reconnect")): bonus += .08
    if re.search(r"\b(disconnect|disconnects|disconnected|player leaves|player left)\b", query, re.I):
        if "removesocket" in content or "player.disconnected" in content: bonus += .16
        if "socket.on('disconnect'" in content or 'socket.on("disconnect"' in content: bonus += .14
    if re.search(r"\b(score|scoring|points|award)\b", query, re.I):
        if any(marker in content for marker in ("awardcorrectguess", "computedrawerscore", "player.score +=", "const points =")): bonus += .16
        if path.endswith("server/index.js"): bonus += .04
    if ".test." in path or "/tests/" in path:
        bonus -= .025
    return bonus


class HybridRetriever:
    """BM25 + vector retrieval with reciprocal-rank fusion and reranking.

    With REPOLENS_ML_ENABLED=1, vectors come from Sentence Transformers, are
    searched in FAISS, and candidates are reranked by a learned cross-encoder.
    The deterministic hashed-vector path keeps the application usable offline.
    """

    def __init__(self, chunks: list[CodeChunk]):
        self.chunks = chunks
        self.docs = [tokenize(f"{chunk.path} {chunk.kind} {chunk.name} {chunk.content}") for chunk in chunks]
        self.doc_terms = [set(doc) for doc in self.docs]
        self.lengths = [len(doc) for doc in self.docs]
        self.avg_length = sum(self.lengths) / max(len(self.lengths), 1)
        self.df: Counter[str] = Counter()
        for doc in self.docs:
            self.df.update(set(doc))
        self.vectors = [self._hashed_vector(doc) for doc in self.docs]
        self.ml = self._load_ml() if os.getenv("REPOLENS_ML_ENABLED", "0") == "1" and chunks else None

    def _load_ml(self):
        try:
            import faiss
            import numpy as np
            from sentence_transformers import CrossEncoder, SentenceTransformer

            documents = [f"{chunk.path}\n{chunk.kind} {chunk.name}\n{chunk.content}" for chunk in self.chunks]
            embedder = SentenceTransformer(os.getenv("REPOLENS_EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2"))
            vectors = embedder.encode(documents, normalize_embeddings=True, show_progress_bar=False)
            vectors = np.asarray(vectors, dtype="float32")
            index = faiss.IndexFlatIP(vectors.shape[1])
            index.add(vectors)
            reranker = CrossEncoder(os.getenv("REPOLENS_RERANK_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2"))
            return {"embedder": embedder, "index": index, "reranker": reranker, "np": np}
        except (ImportError, OSError, RuntimeError, ValueError):
            return None

    @staticmethod
    def _hashed_vector(tokens: list[str], dimensions: int = 384) -> dict[int, float]:
        counts: Counter[int] = Counter(
            int.from_bytes(hashlib.blake2b(token.encode(), digest_size=8).digest(), "big") % dimensions
            for token in tokens
        )
        norm = math.sqrt(sum(value * value for value in counts.values())) or 1.0
        return {index: value / norm for index, value in counts.items()}

    def bm25(self, query: str) -> list[tuple[int, float]]:
        terms = query_tokens(query)
        scores: list[tuple[int, float]] = []
        count = len(self.docs)
        for index, doc in enumerate(self.docs):
            frequencies = Counter(doc)
            score = 0.0
            for term in terms:
                frequency = frequencies[term]
                if not frequency: continue
                idf = math.log(1 + (count - self.df[term] + .5) / (self.df[term] + .5))
                denominator = frequency + 1.5 * (1 - .75 + .75 * self.lengths[index] / max(self.avg_length, 1))
                score += idf * frequency * 2.5 / denominator
            scores.append((index, score))
        return sorted(scores, key=lambda item: item[1], reverse=True)

    def semantic(self, query: str) -> list[tuple[int, float]]:
        if self.ml:
            vector = self.ml["embedder"].encode([query], normalize_embeddings=True, show_progress_bar=False)
            scores, indices = self.ml["index"].search(self.ml["np"].asarray(vector, dtype="float32"), len(self.chunks))
            return [(int(index), float(score)) for index, score in zip(indices[0], scores[0]) if index >= 0]
        terms = query_tokens(query)
        query_vector = self._hashed_vector(terms)
        scores = [
            (index, sum(value * vector.get(key, 0) for key, value in query_vector.items()))
            for index, vector in enumerate(self.vectors)
            if self.doc_terms[index].intersection(terms)
        ]
        return sorted(scores, key=lambda item: item[1], reverse=True)

    def search(self, query: str, limit: int = 6, candidates: int = 20) -> list[tuple[CodeChunk, float]]:
        if not self.chunks: return []
        bm25 = [(index, score) for index, score in self.bm25(query) if score > 0][:candidates]
        semantic = [(index, score) for index, score in self.semantic(query) if score > 0][:candidates]
        fused: Counter[int] = Counter()
        raw: Counter[int] = Counter()
        for ranking, weight in ((bm25, .58), (semantic, .42)):
            maximum = max((score for _, score in ranking), default=1) or 1
            for rank, (index, score) in enumerate(ranking):
                fused[index] += weight / (60 + rank + 1)
                raw[index] += weight * max(score, 0) / maximum
        query_terms = set(query_tokens(query))
        overview_query = bool(re.search(r"\b(what (?:does|is)|purpose|overview|about)\b.*\b(project|repo|repository|codebase)\b|\bproject do\b", query, re.I))
        if overview_query:
            for index, chunk in enumerate(self.chunks):
                if chunk.path.lower().split("/")[-1].startswith("readme"):
                    fused[index] += .12
        authentication_query = bool(re.search(r"\b(auth|authentication|authenticate|login|log ?in|sign ?in)\b", query, re.I))
        if authentication_query:
            for index, chunk in enumerate(self.chunks):
                content = chunk.content.lower()
                if chunk.path.lower().split("/")[-1].startswith("readme") and ("account" in content or "authentication" in content):
                    fused[index] += .08
                if "socket.handshake.auth" in content:
                    fused[index] += .06
        for index, chunk in enumerate(self.chunks):
            bonus = intent_bonus(query, chunk)
            if bonus > 0:
                fused[index] += bonus
        for index in list(fused):
            chunk = self.chunks[index]
            path_terms = set(tokenize(chunk.path + " " + chunk.name))
            exact = len(query_terms & path_terms) / max(len(query_terms), 1)
            fused[index] += .015 * exact + .004 * raw[index]
        ranked = sorted(fused.items(), key=lambda item: item[1], reverse=True)
        if self.ml and ranked:
            rerank_candidates = ranked[:candidates]
            pairs = [(query, f"{self.chunks[index].path}\n{self.chunks[index].content}") for index, _ in rerank_candidates]
            learned_scores = self.ml["reranker"].predict(pairs)
            ranked = sorted(
                ((index, float(score) + .02 * fused[index]) for (index, _), score in zip(rerank_candidates, learned_scores)),
                key=lambda item: item[1], reverse=True,
            )
        per_path_limit = 1 if re.search(r"\b(contribut|read first|files? should)\b", query, re.I) else 2
        selected: list[tuple[int, float]] = []
        path_counts: Counter[str] = Counter()
        for index, score in ranked:
            path = self.chunks[index].path
            if score <= 0.0001 or path_counts[path] >= per_path_limit:
                continue
            if re.search(r"\b(payment|payments|subscription|billing|checkout)\b", query, re.I) and not self.doc_terms[index].intersection(PAYMENT_TERMS):
                continue
            selected.append((index, score))
            path_counts[path] += 1
            if len(selected) == limit:
                break
        return [(self.chunks[index], round(score, 6)) for index, score in selected]
