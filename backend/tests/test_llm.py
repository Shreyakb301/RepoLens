from app.llm import cited_sources, extractive_answer, extractive_citations, grounded_answer, structural_answer
from app.models import CodeChunk


def test_readme_overview_uses_one_matching_citation():
    readme = CodeChunk("readme", "README.md", "Markdown", "section", "README.md", 1, 40, "# App\n\nA real-time drawing game.\n\nBuilt with React.")
    code = CodeChunk("code", "src/app.ts", "TypeScript", "symbol", "start", 1, 5, "const start = true")
    results = [(readme, 0.2), (code, 0.1)]
    citations = [
        {"path": "README.md", "start_line": 1, "end_line": 40},
        {"path": "src/app.ts", "start_line": 1, "end_line": 5},
    ]
    answer = extractive_answer(results)
    assert "real-time drawing game" in answer
    assert "src/app.ts" not in answer
    assert extractive_citations(results, citations) == citations[:1]


def test_authentication_question_explains_when_no_evidence_exists():
    answer, citations = grounded_answer("Where does authentication happen?", [])
    assert "couldn't find evidence of an authentication flow" in answer
    assert citations == []


def test_account_free_socket_auth_is_explained_without_calling_it_login():
    readme = CodeChunk("readme", "README.md", "Markdown", "section", "README", 1, 20, "Players join rooms with a code. Accounts are not required for players.")
    socket = CodeChunk("socket", "server/index.js", "JavaScript", "symbol", "auth", 100, 110, "const auth = socket.handshake.auth || {}")
    answer, citations = grounded_answer("Where does authentication happen?", [(readme, .1), (socket, .09)])
    assert "does not implement account-based login authentication" in answer
    assert "connection metadata" in answer
    assert [citation["path"] for citation in citations] == ["README.md", "server/index.js"]


def test_generated_citations_must_match_retrieved_source_ranges():
    source = CodeChunk("route", "server/index.js", "JavaScript", "section", "route", 10, 20, "request.url === '/api/health'")
    results = [(source, .1)]
    assert cited_sources("See [server/index.js:10-20].", results) == [{"path": "server/index.js", "start_line": 10, "end_line": 20}]
    assert cited_sources("See [server/index.js:999-1000].", results) is None


def test_endpoint_question_gets_actionable_structural_answer():
    route = CodeChunk("route", "server/index.js", "JavaScript", "section", "http", 3800, 3900, "if (request.method === 'POST' && request.url === '/api/feedback') sendJson(response, 200)")
    answer, citations = structural_answer("Where would I add a new API endpoint?", [(route, .2)])
    assert "beside the existing request-method and URL branches" in answer
    assert citations[0]["path"] == "server/index.js"


def test_project_overview_question_uses_readme_without_generation():
    readme = CodeChunk("readme", "README.md", "Markdown", "section", "README", 1, 30, "# App\n\nA collaborative drawing game.")
    answer, citations = grounded_answer("What does this project do?", [(readme, .1)])
    assert "collaborative drawing game" in answer
    assert citations == [{"path": "README.md", "start_line": 1, "end_line": 30}]
