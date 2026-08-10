from pathlib import Path

from app.analyzer import analyze_repository, generic_chunks


def test_analysis_extracts_routes_symbols_and_citations(tmp_path: Path):
    (tmp_path / "README.md").write_text("# Sample\nA small API.", encoding="utf-8")
    app = tmp_path / "app.py"
    app.write_text(
        "from fastapi import FastAPI\n\n"
        "app = FastAPI()\n\n"
        "@app.get('/users/{user_id}')\n"
        "def get_user(user_id: int):\n"
        "    return {'id': user_id}\n",
        encoding="utf-8",
    )
    record = analyze_repository(tmp_path, "example", "sample", "https://github.com/example/sample", "main")
    assert record.stats["files"] == 2
    assert record.routes[0]["method"] == "GET"
    assert record.routes[0]["path"] == "/users/{user_id}"
    assert record.entry_points[0]["path"] == "app.py"
    assert record.entry_points[0]["citation"]["start_line"] >= 1
    assert any(chunk.name == "get_user" for chunk in record.chunks)


def test_generated_and_secret_files_are_skipped(tmp_path: Path):
    (tmp_path / "main.py").write_text("def main():\n    return True\n", encoding="utf-8")
    (tmp_path / ".env").write_text("TOKEN=do-not-index", encoding="utf-8")
    generated = tmp_path / "node_modules"
    generated.mkdir()
    (generated / "library.js").write_text("export const ignored = true", encoding="utf-8")
    environment = tmp_path / ".asl-python"
    environment.mkdir()
    (environment / "dependency.py").write_text("def external_dependency(): pass", encoding="utf-8")
    record = analyze_repository(tmp_path, "example", "safe", "https://github.com/example/safe", "main")
    paths = {item.path for item in record.important_files}
    assert "main.py" in paths
    assert ".env" not in paths
    assert "node_modules/library.js" not in paths
    assert ".asl-python/dependency.py" not in paths


def test_architecture_diagram_uses_real_layers_and_import_edges(tmp_path: Path):
    src = tmp_path / "src"
    server = tmp_path / "server"
    src.mkdir(); server.mkdir()
    (src / "App.tsx").write_text("import { io } from 'socket.io-client'\nexport function App() { return null }", encoding="utf-8")
    (server / "index.js").write_text("import { Server } from 'socket.io'\nimport store from './gameDataStore.js'\nconst io = new Server()", encoding="utf-8")
    (server / "gameDataStore.js").write_text("import db from './db.js'\nexport function saveGame() { return db }", encoding="utf-8")
    (server / "db.js").write_text("export const db = new Map()", encoding="utf-8")
    record = analyze_repository(tmp_path, "example", "game", "https://github.com/example/game", "main")
    kinds = {node["kind"] for node in record.architecture["nodes"]}
    relations = {edge["relation"] for edge in record.architecture["edges"]}
    assert {"frontend", "api", "data"}.issubset(kinds)
    assert "socket connection" in relations
    assert "imports" in relations


def test_javascript_function_chunk_is_not_cut_at_local_const():
    text = """function removeSocket(socket) {
  const room = rooms.get(socket.roomCode)
  if (!room) return
  const player = room.players.get(socket.playerId)
  player.disconnected = true
}

function connectSocket(socket) {
  return socket.id
}
"""
    chunks = generic_chunks("server/index.js", text, "JavaScript")
    remove_socket = next(chunk for chunk in chunks if chunk.name == "removeSocket")
    assert "player.disconnected = true" in remove_socket.content
    assert remove_socket.end_line == 7


def test_repository_health_flags_missing_safety_net(tmp_path: Path):
    (tmp_path / "package.json").write_text('{"scripts":{"start":"node index.js"}}', encoding="utf-8")
    (tmp_path / "index.js").write_text("export function start() { return true }", encoding="utf-8")

    record = analyze_repository(tmp_path, "example", "health", "https://github.com/example/health", "main")

    finding_ids = {finding["id"] for finding in record.repo_health["findings"]}
    assert record.repo_health["score"] < 60
    assert {"missing-tests", "missing-ci", "missing-readme", "runtime-not-pinned"}.issubset(finding_ids)


def test_repository_health_rewards_documented_tested_automation(tmp_path: Path):
    (tmp_path / "README.md").write_text("# Healthy project", encoding="utf-8")
    (tmp_path / "package.json").write_text('{"engines":{"node":"22"}}', encoding="utf-8")
    workflow = tmp_path / ".github" / "workflows"
    workflow.mkdir(parents=True)
    (workflow / "test.yml").write_text("name: test", encoding="utf-8")
    (tmp_path / "app.js").write_text("export function app() { return true }", encoding="utf-8")
    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "app.test.js").write_text("export function testApp() { return true }", encoding="utf-8")

    record = analyze_repository(tmp_path, "example", "healthy", "https://github.com/example/healthy", "main")

    assert record.repo_health["score"] >= 80
    assert record.repo_health["label"] == "Healthy"
