from app.models import CodeChunk
from app.retrieval import HybridRetriever


def chunk(identifier: str, path: str, content: str) -> CodeChunk:
    return CodeChunk(identifier, path, "Python", "function", identifier, 1, 8, content)


def test_hybrid_search_prioritizes_matching_symbol_and_path():
    chunks = [
        chunk("login", "services/auth.py", "def login_user(email, password): validate password and create access token"),
        chunk("invoice", "services/billing.py", "def create_invoice(customer): calculate price and charge card"),
        chunk("health", "routes/health.py", "def health_check(): return service status"),
    ]
    results = HybridRetriever(chunks).search("Where is login password authentication handled?")
    assert results
    assert results[0][0].path == "services/auth.py"


def test_empty_index_returns_no_evidence():
    assert HybridRetriever([]).search("anything") == []


def test_unrelated_chunks_are_not_presented_as_evidence():
    chunks = [
        chunk("vector", "src/gesture.ts", "const dy = point.y - previous.y"),
        chunk("words", "server/gameDataStore.js", "const words = []"),
        chunk("provider", "server/aiGuessEval.js", "export function isFatalProviderError(error)"),
    ]
    assert HybridRetriever(chunks).search("Where does authentication happen?") == []


def test_database_question_expands_to_storage_vocabulary():
    chunks = [
        chunk("save", "server/gameDataStore.js", "persist completed games through postgres storage"),
        chunk("canvas", "src/canvas.ts", "render each drawing stroke"),
    ]
    results = HybridRetriever(chunks).search("How does a request reach the database?")
    assert results[0][0].path == "server/gameDataStore.js"


def test_endpoint_question_prefers_request_router_over_fetch_response_noise():
    chunks = [
        chunk("response", "scripts/download.js", "const response = await fetch(remoteUrl)"),
        chunk("http", "server/index.js", "if (request.method === 'POST' and request.url === '/api/feedback') sendJson(response, 200)"),
    ]
    results = HybridRetriever(chunks).search("Where would I add a new API endpoint?")
    assert results[0][0].path == "server/index.js"


def test_drawing_flow_prefers_socket_messages():
    chunks = [
        chunk("client", "server/redis.js", "let client = null"),
        chunk("stroke", "src/App.tsx", "socket.emit('room_message', { type: 'drawing_stroke', stroke })"),
    ]
    results = HybridRetriever(chunks).search("How does drawing data move from the client to the server?")
    assert results[0][0].path == "src/App.tsx"


def test_unsupported_payment_question_has_no_evidence():
    chunks = [chunk("gesture", "src/types/drawing.ts", "export interface HandTrackingFrame { processed: boolean }")]
    assert HybridRetriever(chunks).search("How are subscription payments processed?") == []


def test_project_overview_question_prioritizes_readme():
    chunks = [
        chunk("fragment", "src/math.py", "let u, v, r; calculate internal vectors"),
        chunk("readme", "README.md", "A collaborative browser drawing and guessing game for friends and AI players."),
    ] + [chunk(f"noise-{index}", f"src/noise{index}.py", "what project code repository does internal helper") for index in range(30)]
    results = HybridRetriever(chunks).search("What does this project do?")
    assert results[0][0].path == "README.md"
