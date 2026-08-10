from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.models import CodeChunk
from app.retrieval import HybridRetriever


FIXTURES = {
    "sample": [
        CodeChunk("auth", "services/auth.py", "Python", "function", "login_user", 1, 12, "def login_user(email, password): validate password and create access token"),
        CodeChunk("billing", "services/billing.py", "Python", "function", "create_invoice", 1, 10, "def create_invoice(customer): calculate invoice total and charge card"),
        CodeChunk("health", "routes/health.py", "Python", "function", "health_check", 1, 8, "@router.get('/health')\ndef health_check(): return service status"),
    ]
}


def evaluate(dataset: Path, k: int = 3) -> dict[str, float]:
    cases = [json.loads(line) for line in dataset.read_text().splitlines() if line.strip()]
    hits = 0
    reciprocal_rank = 0.0
    for case in cases:
        ranked = HybridRetriever(FIXTURES[case["fixture"]]).search(case["question"], limit=k)
        paths = [chunk.path for chunk, _ in ranked]
        ranks = [paths.index(path) + 1 for path in case["expected_paths"] if path in paths]
        if ranks: hits += 1; reciprocal_rank += 1 / min(ranks)
    total = max(len(cases), 1)
    return {f"recall_at_{k}": hits / total, "mrr": reciprocal_rank / total, "cases": len(cases)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run RepoLens retrieval quality checks")
    parser.add_argument("--dataset", type=Path, default=Path(__file__).with_name("golden.jsonl"))
    parser.add_argument("--min-recall", type=float, default=.80)
    args = parser.parse_args()
    metrics = evaluate(args.dataset)
    print(json.dumps(metrics, indent=2))
    raise SystemExit(0 if metrics["recall_at_3"] >= args.min_recall else 1)

