from __future__ import annotations

import ast
import hashlib
import json
import re
import time
from collections import Counter
from pathlib import Path
from typing import Iterable

from .ingestion import indexable_files
from .models import AnalysisRecord, Citation, CodeChunk, FileFact
from .security import safe_text


LANGUAGES = {
    ".py": "Python", ".js": "JavaScript", ".jsx": "JavaScript", ".ts": "TypeScript",
    ".tsx": "TypeScript", ".java": "Java", ".go": "Go", ".rs": "Rust", ".rb": "Ruby",
    ".php": "PHP", ".cs": "C#", ".cpp": "C++", ".cc": "C++", ".c": "C",
    ".h": "C/C++", ".swift": "Swift", ".kt": "Kotlin", ".scala": "Scala",
    ".sql": "SQL", ".css": "CSS", ".scss": "SCSS", ".html": "HTML",
    ".md": "Markdown", ".yml": "YAML", ".yaml": "YAML", ".json": "JSON",
    ".toml": "TOML", ".sh": "Shell", ".vue": "Vue", ".svelte": "Svelte",
}
SOURCE_LANGUAGES = {"Python", "JavaScript", "TypeScript", "Java", "Go", "Rust", "Ruby", "PHP", "C#", "C++", "C", "Swift", "Kotlin", "Scala", "Vue", "Svelte"}
ENTRY_NAMES = {"main.py", "app.py", "server.py", "manage.py", "index.js", "index.ts", "server.js", "server.ts", "main.go", "main.rs", "program.cs", "page.tsx"}
ROLE_RULES = [
    (re.compile(r"(^|/)(test|tests|spec|specs)(/|$)|(^test_|_test\.)", re.I), "Tests"),
    (re.compile(r"(^|/)(routes?|controllers?|api)(/|$)", re.I), "API routes"),
    (re.compile(r"(^|/)(models?|entities|schema)(/|$)", re.I), "Data model"),
    (re.compile(r"(^|/)(services?|usecases?)(/|$)", re.I), "Business logic"),
    (re.compile(r"(^|/)(auth|security)(/|\.)", re.I), "Authentication"),
    (re.compile(r"(^|/)(components?|views?|pages?|app)(/|$)", re.I), "Interface"),
    (re.compile(r"(config|settings|\.ya?ml$|\.toml$)", re.I), "Configuration"),
    (re.compile(r"readme", re.I), "Documentation"),
]


def language_for(path: Path) -> str:
    return LANGUAGES.get(path.suffix.lower(), "Text")


def file_role(relative: str) -> str:
    for pattern, role in ROLE_RULES:
        if pattern.search(relative):
            return role
    if Path(relative).name.lower() in ENTRY_NAMES:
        return "Entry point"
    return "Source" if language_for(Path(relative)) in SOURCE_LANGUAGES else "Project file"


def python_chunks(relative: str, text: str) -> tuple[list[CodeChunk], list[str], list[str]]:
    chunks: list[CodeChunk] = []
    imports: list[str] = []
    symbols: list[str] = []
    lines = text.splitlines()
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return generic_chunks(relative, text, "Python"), imports, symbols
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            if isinstance(node, ast.ImportFrom) and node.module:
                imports.append(node.module)
            elif isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            start = max(1, getattr(node, "lineno", 1))
            end = max(start, getattr(node, "end_lineno", start))
            kind = "class" if isinstance(node, ast.ClassDef) else "function"
            symbols.append(node.name)
            content = "\n".join(lines[start - 1:end])
            chunks.append(make_chunk(relative, "Python", kind, node.name, start, end, content, imports))
    if not chunks or len(lines) > sum(c.end_line - c.start_line + 1 for c in chunks) * 2:
        chunks.extend(generic_chunks(relative, text, "Python", existing=chunks))
    return dedupe_chunks(chunks), sorted(set(imports)), symbols


def generic_chunks(relative: str, text: str, language: str, existing: list[CodeChunk] | None = None) -> list[CodeChunk]:
    lines = text.splitlines()
    chunks: list[CodeChunk] = []
    # Generic languages do not have an AST here, so index top-level declarations.
    # Matching indented `const`/`let` declarations split JavaScript functions at
    # their first local variable and produced misleading one- or two-line chunks.
    pattern = re.compile(r"^(?:export\s+)?(?:async\s+)?(?:def|class|function|interface|type|const|let|var|func|fn|public\s+class|private\s+|public\s+)\s+([A-Za-z_$][\w$]*)", re.M)
    starts = [(text[:m.start()].count("\n") + 1, m.group(1)) for m in pattern.finditer(text)]
    if starts:
        for index, (start, name) in enumerate(starts):
            end = min(len(lines), starts[index + 1][0] - 1 if index + 1 < len(starts) else start + 119)
            chunks.append(make_chunk(relative, language, "symbol", name, start, end, "\n".join(lines[start - 1:end]), []))
    covered = {(c.start_line, c.end_line) for c in (existing or []) + chunks}
    for start in range(1, len(lines) + 1, 100):
        end = min(len(lines), start + 119)
        if any(a <= start <= b or start <= a <= end for a, b in covered):
            continue
        chunks.append(make_chunk(relative, language, "section", Path(relative).name, start, end, "\n".join(lines[start - 1:end]), []))
    return chunks


def make_chunk(path: str, language: str, kind: str, name: str, start: int, end: int, content: str, imports: list[str]) -> CodeChunk:
    digest = hashlib.sha1(f"{path}:{start}:{end}".encode()).hexdigest()[:14]
    return CodeChunk(digest, path, language, kind, name, start, end, content[:12000], list(imports))


def dedupe_chunks(chunks: list[CodeChunk]) -> list[CodeChunk]:
    seen: set[tuple[str, int, int]] = set()
    result: list[CodeChunk] = []
    for chunk in chunks:
        key = (chunk.path, chunk.start_line, chunk.end_line)
        if key not in seen and chunk.content.strip():
            seen.add(key); result.append(chunk)
    return result


def js_imports(text: str) -> list[str]:
    patterns = [r"(?:import[^'\"]*from\s*|require\s*\()['\"]([^'\"]+)", r"import\s*\(['\"]([^'\"]+)"]
    return sorted({match for pattern in patterns for match in re.findall(pattern, text)})


def detect_routes(relative: str, text: str) -> list[dict]:
    routes: list[dict] = []
    patterns = [
        re.compile(r"@(?:app|router|blueprint)\.(get|post|put|patch|delete)\s*\(\s*['\"]([^'\"]+)['\"]", re.I),
        re.compile(r"(?:app|router)\.(get|post|put|patch|delete)\s*\(\s*['\"]([^'\"]+)['\"]", re.I),
    ]
    lines = text.splitlines()
    for pattern in patterns:
        for match in pattern.finditer(text):
            line = text[:match.start()].count("\n") + 1
            handler = "handler"
            for following in lines[line:min(line + 3, len(lines))]:
                found = re.search(r"(?:def|function|const)\s+([\w$]+)", following)
                if found: handler = found.group(1); break
            routes.append({"method": match.group(1).upper(), "path": match.group(2), "handler": handler, "citation": {"path": relative, "start_line": line, "end_line": min(line + 2, len(lines))}})
    return routes


def detect_stack(root: Path, file_names: set[str], contents: dict[str, str]) -> list[str]:
    stack: list[str] = []
    combined_manifests = "\n".join(contents.get(name, "") for name in ("package.json", "pyproject.toml", "requirements.txt", "Cargo.toml", "go.mod"))
    rules = {
        "Next.js": r'"next"', "React": r'"react"', "Vue": r'"vue"', "Svelte": r'"svelte"',
        "FastAPI": r"fastapi", "Django": r"django", "Flask": r"flask", "Express": r"express",
        "TypeScript": r"typescript", "Tailwind CSS": r"tailwind", "SQLAlchemy": r"sqlalchemy",
        "Prisma": r"prisma", "PostgreSQL": r"postgres", "SQLite": r"sqlite", "Ollama": r"ollama",
        "Rust": r"\[package\]", "Go": r"^module\s+",
    }
    for name, pattern in rules.items():
        if re.search(pattern, combined_manifests, re.I | re.M): stack.append(name)
    if "Dockerfile" in file_names: stack.append("Docker")
    if any(name.startswith(".github/workflows/") for name in file_names): stack.append("GitHub Actions")
    return list(dict.fromkeys(stack))[:12]


def analyze_repository(root: Path, owner: str, repo: str, url: str, branch: str) -> AnalysisRecord:
    started = time.perf_counter()
    paths, warnings = indexable_files(root)
    facts: list[FileFact] = []
    chunks: list[CodeChunk] = []
    routes: list[dict] = []
    language_lines: Counter[str] = Counter()
    contents_by_name: dict[str, str] = {}
    total_lines = 0
    imports_by_file: dict[str, list[str]] = {}

    for path in paths:
        text = safe_text(path)
        if text is None: continue
        relative = path.relative_to(root).as_posix()
        language = language_for(path)
        lines = max(1, text.count("\n") + 1)
        total_lines += lines
        language_lines[language] += lines
        contents_by_name[relative] = text
        contents_by_name[path.name] = text
        if language == "Python": file_chunks, imports, symbols = python_chunks(relative, text)
        else:
            imports = js_imports(text) if language in {"JavaScript", "TypeScript", "Vue", "Svelte"} else []
            symbols = [m.group(1) for m in re.finditer(r"(?:class|function|interface|func|fn)\s+([\w$]+)", text)][:30]
            file_chunks = generic_chunks(relative, text, language)
        chunks.extend(file_chunks)
        imports_by_file[relative] = imports
        routes.extend(detect_routes(relative, text))
        role = file_role(relative)
        score = importance_score(relative, role, imports, symbols, text)
        summary = summarize_file(relative, role, symbols, imports)
        facts.append(FileFact(relative, language, role, lines, score, summary, imports, symbols))

    inbound = Counter()
    for imports in imports_by_file.values():
        for item in imports:
            stem = item.split("/")[-1].split(".")[-1]
            for fact in facts:
                if Path(fact.path).stem == stem: inbound[fact.path] += 1
    for fact in facts:
        fact.score = round(min(1.0, fact.score + min(inbound[fact.path], 8) * .035), 3)

    important = sorted(facts, key=lambda item: (-item.score, item.path))[:18]
    entries = entry_points(facts, contents_by_name)
    stack = detect_stack(root, set(contents_by_name), contents_by_name)
    architecture = architecture_map(facts, imports_by_file, stack)
    repo_health = repository_health(facts, contents_by_name)
    summary = repo_summary(repo, stack, facts, routes)
    record_id = hashlib.sha256(f"{owner}/{repo}/{branch}".encode()).hexdigest()[:16]
    languages = {name: count for name, count in language_lines.most_common() if name != "Text"}
    return AnalysisRecord(
        id=record_id,
        repo={"name": repo, "owner": owner, "url": url.removesuffix(".git"), "default_branch": branch},
        summary=summary,
        stats={"files": len(facts), "lines": total_lines, "languages": languages, "indexed_chunks": len(chunks)},
        stack=stack or [name for name, _ in language_lines.most_common(4)],
        entry_points=entries,
        important_files=important,
        reading_order=reading_order(facts, entries),
        routes=routes[:80], architecture=architecture, warnings=warnings, repo_health=repo_health,
        elapsed_ms=int((time.perf_counter() - started) * 1000), chunks=chunks,
    )


def repository_health(facts: list[FileFact], contents: dict[str, str]) -> dict:
    """Build a conservative, deterministic engineering-health snapshot."""
    source_files = [fact for fact in facts if fact.language in SOURCE_LANGUAGES and fact.role != "Tests"]
    test_files = [fact for fact in facts if fact.role == "Tests"]
    readmes = [fact for fact in facts if Path(fact.path).name.lower().startswith("readme")]
    docs = [fact for fact in facts if fact.path.lower().startswith("docs/") or fact.role == "Documentation"]
    workflows = [fact for fact in facts if fact.path.lower().startswith(".github/workflows/")]
    large_files = sorted((fact for fact in source_files if fact.lines >= 800), key=lambda fact: -fact.lines)
    package = next((fact for fact in facts if fact.path == "package.json"), None)
    package_text = contents.get("package.json", "")
    runtime_pins = {".nvmrc", ".node-version", ".python-version", ".tool-versions"}
    has_runtime_pin = any(fact.path in runtime_pins for fact in facts) or '"engines"' in package_text

    test_ratio = len(test_files) / max(len(source_files), 1)
    testing_score = 92 if test_ratio >= .12 else 62 if test_files else 25
    documentation_score = 92 if readmes and len(docs) > len(readmes) else 78 if readmes else 25
    automation_score = 90 if workflows else 48
    maintainability_score = 35 if large_files and large_files[0].lines >= 1500 else 62 if large_files else 90
    setup_score = 88 if has_runtime_pin else 55 if package else 75

    categories = [
        {"name": "Testing", "score": testing_score, "detail": f"{len(test_files)} test file{'s' if len(test_files) != 1 else ''} detected for {len(source_files)} source files."},
        {"name": "Documentation", "score": documentation_score, "detail": "README and supporting documentation detected." if readmes else "No README was detected in the indexed repository."},
        {"name": "Automation", "score": automation_score, "detail": f"{len(workflows)} continuous-integration workflow{'s' if len(workflows) != 1 else ''} detected." if workflows else "No continuous-integration workflow was detected."},
        {"name": "Maintainability", "score": maintainability_score, "detail": f"{len(large_files)} source file{'s' if len(large_files) != 1 else ''} exceed 800 lines." if large_files else "No source files exceed the 800-line review threshold."},
        {"name": "Setup", "score": setup_score, "detail": "A project runtime version is pinned." if has_runtime_pin else "The project runtime version is not pinned." if package else "No JavaScript runtime pin is required."},
    ]

    findings: list[dict] = []
    if not test_files:
        findings.append({
            "id": "missing-tests", "severity": "warning", "title": "No automated tests detected",
            "summary": "Changes cannot be checked against a repository-owned test suite.",
            "explanation": "RepoLens did not find files in common test or specification locations. This increases regression risk and makes contributor feedback slower.",
            "fix": ["Add one focused test around the most important user or API flow.", "Run that test in continuous integration.", "Document the test command in the README."],
            "citations": [],
        })
    elif test_ratio < .12:
        test = test_files[0]
        findings.append({
            "id": "thin-test-surface", "severity": "optional", "title": "Thin test surface",
            "summary": f"Only {len(test_files)} test files cover {len(source_files)} source files.",
            "explanation": "File counts are only a signal, but this repository may have important behaviors without focused regression coverage.",
            "fix": ["Identify the highest-risk untested service or route.", "Add behavior-level tests before broad coverage work.", "Track coverage trends in CI rather than chasing a single percentage."],
            "citations": [{"path": test.path, "start_line": 1, "end_line": min(test.lines, 20)}],
        })
    if not workflows:
        findings.append({
            "id": "missing-ci", "severity": "optional", "title": "No continuous integration detected",
            "summary": "Repository checks may depend on contributors running commands manually.",
            "explanation": "No workflow files were found under .github/workflows. Automated checks make contribution quality more consistent.",
            "fix": ["Add a workflow for the existing test command.", "Include type checking or linting when those commands already exist.", "Require the workflow before merging changes."],
            "citations": [],
        })
    if not readmes:
        findings.append({
            "id": "missing-readme", "severity": "warning", "title": "No README detected",
            "summary": "New contributors have no obvious starting document.",
            "explanation": "A concise README should explain the repository purpose, prerequisites, setup, and validation commands.",
            "fix": ["Add a short purpose statement.", "Document the minimal setup and run commands.", "Include the test command and links to deeper documentation."],
            "citations": [],
        })
    for index, fact in enumerate(large_files[:2]):
        findings.append({
            "id": f"large-file-{index}", "severity": "warning" if fact.lines >= 1500 else "optional", "title": f"Large {fact.role.lower()} file",
            "summary": f"{fact.path} contains {fact.lines:,} lines and may combine several responsibilities.",
            "explanation": "Large files are not automatically defective, but they increase navigation cost and make isolated changes harder to review and test.",
            "fix": ["Identify cohesive responsibilities inside the file.", "Extract one boundary at a time while preserving behavior.", "Add focused tests before moving high-risk logic."],
            "citations": [{"path": fact.path, "start_line": 1, "end_line": fact.lines}],
        })
    if package and not has_runtime_pin:
        findings.append({
            "id": "runtime-not-pinned", "severity": "warning", "title": "Runtime version is not pinned",
            "summary": "Contributors may install dependencies with different Node.js versions.",
            "explanation": "A pinned runtime reduces environment-specific installation, build, and test failures.",
            "fix": ["Add engines.node to package.json.", "Commit a .nvmrc or .node-version file.", "Use the same version in continuous integration."],
            "citations": [{"path": package.path, "start_line": 1, "end_line": min(package.lines, 40)}],
        })

    score = round(sum(category["score"] for category in categories) / len(categories))
    label = "Healthy" if score >= 80 else "Needs attention" if score >= 60 else "At risk"
    priority_count = sum(finding["severity"] == "warning" for finding in findings)
    summary = f"{priority_count} priority finding{'s' if priority_count != 1 else ''} and {len(findings) - priority_count} improvement opportunit{'ies' if len(findings) - priority_count != 1 else 'y'} were identified from static repository evidence."
    return {"score": score, "label": label, "summary": summary, "categories": categories, "findings": findings[:6]}


def importance_score(path: str, role: str, imports: list[str], symbols: list[str], text: str) -> float:
    score = .25
    name = Path(path).name.lower()
    if name in ENTRY_NAMES: score += .35
    if role in {"Entry point", "API routes", "Business logic", "Data model", "Authentication"}: score += .18
    if name.startswith("readme"): score += .22
    if name in {"package.json", "pyproject.toml", "requirements.txt", "cargo.toml", "go.mod"}: score += .22
    score += min(len(imports), 10) * .012 + min(len(symbols), 15) * .008
    if re.search(r"create_app|FastAPI\(|express\(|ReactDOM|if __name__|func main", text): score += .16
    if min(path.lower().count("test"), 1): score -= .12
    return round(max(.05, min(score, 1.0)), 3)


def summarize_file(path: str, role: str, symbols: list[str], imports: list[str]) -> str:
    details = []
    if symbols: details.append("defines " + ", ".join(symbols[:3]))
    if imports: details.append("connects to " + ", ".join(imports[:2]))
    return f"{role} file" + ("; " + "; ".join(details) if details else ".")


def entry_points(facts: list[FileFact], contents: dict[str, str]) -> list[dict]:
    candidates = [f for f in facts if Path(f.path).name.lower() in ENTRY_NAMES or f.role == "Entry point"]
    if not candidates:
        candidates = sorted(facts, key=lambda f: -f.score)[:2]
    result = []
    for fact in sorted(candidates, key=lambda f: -f.score)[:5]:
        text = contents.get(fact.path, "")
        line = 1
        for marker in ("FastAPI(", "create_app", "if __name__", "ReactDOM", "func main"):
            index = text.find(marker)
            if index >= 0: line = text[:index].count("\n") + 1; break
        result.append({"path": fact.path, "reason": fact.summary, "citation": {"path": fact.path, "start_line": line, "end_line": min(line + 12, fact.lines)}})
    return result


def reading_order(facts: list[FileFact], entries: list[dict]) -> list[FileFact]:
    by_path = {f.path: f for f in facts}
    ordered: list[FileFact] = []
    readmes = sorted((f for f in facts if Path(f.path).name.lower().startswith("readme")), key=lambda f: len(f.path))
    manifests = [f for f in facts if Path(f.path).name.lower() in {"package.json", "pyproject.toml", "requirements.txt", "cargo.toml", "go.mod"}]
    for fact in readmes + [by_path[e["path"]] for e in entries if e["path"] in by_path] + manifests + sorted(facts, key=lambda f: -f.score):
        if fact.path not in {item.path for item in ordered}: ordered.append(fact)
    return ordered[:12]


def architecture_kind(fact: FileFact) -> str:
    path = fact.path.lower()
    name = Path(path).name
    if re.search(r"(^|/)(ai|ml|models?|inference|asl)(/|$)|aiworker|sketchrnn|hugging", path):
        return "ai"
    if re.search(r"(^|/)(db|database|storage|stores?|repositories)(/|\.)|redis|postgres|sqlite", path):
        return "data"
    if re.search(r"(^|/)server/(index|main)\.", path) or fact.role == "API routes":
        return "api"
    if path.startswith("src/") and (fact.role == "Interface" or name in {"app.tsx", "app.jsx", "main.tsx", "main.jsx"}):
        return "frontend"
    if re.search(r"(^|/)(services?|server|hooks|utils)(/|$)", path) or fact.role in {"Business logic", "Authentication"}:
        return "service"
    return "module"


def architecture_label(fact: FileFact, kind: str) -> str:
    path = fact.path.lower()
    if path.endswith("src/app.tsx") or path.endswith("src/app.jsx"): return "React application"
    if re.search(r"(^|/)server/index\.[jt]s$", path): return "Game server"
    if "aiworkerpool" in path: return "AI worker pool"
    if "gamedatastore" in path: return "Game data store"
    if Path(path).stem in {"db", "database", "storage", "redis"}: return Path(path).stem.replace("_", " ").title()
    stem = Path(fact.path).stem
    words = re.sub(r"(?<!^)(?=[A-Z])", " ", stem).replace("_", " ").replace("-", " ")
    return words[:1].upper() + words[1:]


def architecture_map(facts: list[FileFact], imports: dict[str, list[str]], stack: list[str]) -> dict[str, list[dict[str, str]]]:
    layers = ["frontend", "api", "service", "data", "ai", "module"]
    grouped: dict[str, list[FileFact]] = {layer: [] for layer in layers}
    for fact in facts:
        if fact.language not in SOURCE_LANGUAGES or fact.role == "Tests": continue
        grouped[architecture_kind(fact)].append(fact)

    selected: list[FileFact] = []
    for layer in layers:
        candidates = sorted(
            grouped[layer],
            key=lambda fact: (
                -int(Path(fact.path).name.lower() in ENTRY_NAMES),
                -int(any(token in fact.path.lower() for token in ("app.", "index.", "storage", "store", "worker", "db."))),
                -fact.score,
                fact.path,
            ),
        )
        selected.extend(candidates[:2 if layer in {"frontend", "service", "data", "ai"} else 1])
    selected = selected[:10]
    nodes = [
        {"id": hashlib.md5(fact.path.encode()).hexdigest()[:8], "label": architecture_label(fact, architecture_kind(fact)), "kind": architecture_kind(fact), "file": fact.path}
        for fact in selected
    ]
    by_path = {fact.path: node for fact, node in zip(selected, nodes)}
    edges: list[dict[str, str]] = []
    seen_edges: set[tuple[str, str]] = set()
    for source in selected:
        source_node = by_path[source.path]
        for imported in imports.get(source.path, []):
            token = imported.removesuffix(".js").removesuffix(".ts").removesuffix(".tsx").split("/")[-1].lower()
            for target in selected:
                if target.path == source.path: continue
                if Path(target.path).stem.lower() != token: continue
                target_node = by_path[target.path]
                key = (source_node["id"], target_node["id"])
                if key not in seen_edges:
                    seen_edges.add(key)
                    edges.append({"source": key[0], "target": key[1], "relation": "imports"})
    frontend = next((fact for fact in selected if architecture_kind(fact) == "frontend" and any("socket.io-client" in item for item in imports.get(fact.path, []))), None)
    api = next((fact for fact in selected if architecture_kind(fact) == "api" and any("socket.io" in item for item in imports.get(fact.path, []))), None)
    if frontend and api:
        key = (by_path[frontend.path]["id"], by_path[api.path]["id"])
        if key not in seen_edges:
            edges.append({"source": key[0], "target": key[1], "relation": "socket connection"})
    return {"nodes": nodes, "edges": edges[:16]}


def repo_summary(repo: str, stack: list[str], facts: list[FileFact], routes: list[dict]) -> str:
    roles = Counter(f.role for f in facts)
    core = ", ".join(stack[:4]) if stack else "multiple source languages"
    detail = f" It exposes {len(routes)} detected HTTP route{'s' if len(routes) != 1 else ''}." if routes else ""
    dominant = roles.most_common(1)[0][0].lower() if roles else "source"
    return f"{repo} is a {dominant}-oriented codebase built with {core}.{detail} This overview is derived from repository files and static structure."
