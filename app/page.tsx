"use client";

import { FormEvent, useMemo, useState } from "react";

type Citation = { path: string; start_line: number; end_line: number };
type RepoFile = { path: string; language: string; role: string; lines: number; score: number; summary: string };
type ArchitectureNode = { id: string; label: string; kind: string; file: string };
type ArchitectureEdge = { source: string; target: string; relation: string };
type SetupIssue = { id: string; severity: "warning" | "optional"; title: string; summary: string; explanation: string; fix: string[]; citations: Citation[] };
type RepoHealthCategory = { name: string; score: number; detail: string };
type RepoHealth = { score: number; label: "Healthy" | "Needs attention" | "At risk" | "Unavailable"; summary: string; categories: RepoHealthCategory[]; findings: SetupIssue[] };
type GitHubActivityItem = { number: number; kind: "issue" | "pull_request"; title: string; explanation: string; url: string; author: string; labels: string[]; updated_at: string; comments: number; draft: boolean };
type GitHubActivity = { status: "available" | "unavailable"; issues: GitHubActivityItem[]; pull_requests: GitHubActivityItem[]; reason: string };
type RecentWorkCommit = { sha: string; short_sha: string; title: string; author: string; date: string; areas: string[]; files: string[]; file_count: number; explanation: string; url: string };
type RecentWorkContributor = { name: string; commits: number; areas: string[]; summary: string };
type RecentWork = { status: "available" | "unavailable"; commits: RecentWorkCommit[]; contributors: RecentWorkContributor[]; reason: string };
type Analysis = {
  id: string;
  repo: { name: string; owner: string; url: string; default_branch: string };
  summary: string;
  stats: { files: number; lines: number; languages: Record<string, number>; indexed_chunks: number };
  stack: string[];
  entry_points: { path: string; reason: string; citation: Citation }[];
  important_files: RepoFile[];
  reading_order: RepoFile[];
  routes: { method: string; path: string; handler: string; citation: Citation }[];
  architecture: { nodes: ArchitectureNode[]; edges: ArchitectureEdge[] };
  system_flow?: { label: string; detail: string; citation: Citation }[];
  key_concepts?: { title: string; detail: string; citation: Citation }[];
  watchouts?: { title: string; detail: string }[];
  setup_issues?: SetupIssue[];
  repo_health?: RepoHealth;
  github_activity?: GitHubActivity;
  recent_work?: RecentWork;
  run_steps?: string[];
  warnings: string[];
  elapsed_ms: number;
};

const demo: Analysis = {
  id: "901234a702e56cca",
  repo: { name: "Moodle", owner: "Sanjana-Gondariya", url: "https://github.com/Sanjana-Gondariya/Moodle", default_branch: "main" },
  summary: "A browser-based, real-time drawing and guessing game for friends and AI players. React powers the collaborative canvas while a Node.js and Socket.IO server synchronizes rooms, strokes, chat, timers, words, scores, and AI turns.",
  stats: { files: 166, lines: 69060, languages: { JSON: 37827, TypeScript: 12573, JavaScript: 9403, CSS: 5306, Python: 630, Markdown: 523, HTML: 426, YAML: 35 }, indexed_chunks: 3710 },
  stack: ["React", "TypeScript", "Node.js", "Socket.IO", "Redis", "PostgreSQL", "MediaPipe", "AI workers"],
  entry_points: [
    { path: "src/main.tsx", reason: "Mounts the React application in the browser.", citation: { path: "src/main.tsx", start_line: 1, end_line: 14 } },
    { path: "server/index.js", reason: "Starts the HTTP and Socket.IO game server and coordinates room messages.", citation: { path: "server/index.js", start_line: 1, end_line: 35 } },
  ],
  important_files: [
    { path: "README.md", language: "Markdown", role: "Orientation", lines: 209, score: 1, summary: "Explains the game, controls, setup, storage model, and operating modes." },
    { path: "src/App.tsx", language: "TypeScript", role: "Frontend orchestration", lines: 3510, score: .99, summary: "Owns the player experience, room connection, drawing state, chat, and turn UI." },
    { path: "server/index.js", language: "JavaScript", role: "Server entry point", lines: 4796, score: .98, summary: "Coordinates Socket.IO messages, room lifecycle, gameplay, metrics, and AI actions." },
    { path: "server/roomStore.js", language: "JavaScript", role: "Live state", lines: 256, score: .91, summary: "Maintains active room and player state with optional Redis coordination." },
    { path: "server/gameDataStore.js", language: "JavaScript", role: "Persistence boundary", lines: 214, score: .9, summary: "Persists game history and shared durable records through the database layer." },
    { path: "server/aiWorkerPool.js", language: "JavaScript", role: "AI boundary", lines: 318, score: .88, summary: "Runs AI drawing and guessing work outside the main server event loop." },
    { path: "src/components/DrawingCanvas.tsx", language: "TypeScript", role: "Drawing interface", lines: 642, score: .85, summary: "Renders strokes and translates pointer or gesture input into drawing actions." },
  ],
  reading_order: [],
  routes: [
    { method: "SOCKET", path: "connection", handler: "create player session", citation: { path: "server/index.js", start_line: 4657, end_line: 4684 } },
    { method: "SOCKET", path: "room_message", handler: "route game events", citation: { path: "server/index.js", start_line: 4684, end_line: 4699 } },
    { method: "SOCKET", path: "disconnect", handler: "remove player socket", citation: { path: "server/index.js", start_line: 4700, end_line: 4701 } },
  ],
  architecture: {
    nodes: [
      { id: "46ef2374", label: "React application", kind: "frontend", file: "src/App.tsx" },
      { id: "f3df9dfa", label: "Toolbar", kind: "frontend", file: "src/components/Toolbar.tsx" },
      { id: "0861d6d6", label: "Game server", kind: "api", file: "server/index.js" },
      { id: "abb22006", label: "Room Store", kind: "service", file: "server/roomStore.js" },
      { id: "b586a08a", label: "Game data store", kind: "service", file: "server/gameDataStore.js" },
      { id: "2e1de21c", label: "Database", kind: "data", file: "server/db.js" },
      { id: "fe30681f", label: "Redis", kind: "data", file: "server/redis.js" },
      { id: "6e87bfd7", label: "AI worker", kind: "ai", file: "server/aiWorker.js" },
      { id: "90c99d47", label: "AI worker pool", kind: "ai", file: "server/aiWorkerPool.js" },
      { id: "0adf315b", label: "Drawing types", kind: "module", file: "src/types/drawing.ts" },
    ],
    edges: [
      { source: "46ef2374", target: "f3df9dfa", relation: "imports" }, { source: "46ef2374", target: "0adf315b", relation: "imports" },
      { source: "46ef2374", target: "0861d6d6", relation: "socket connection" }, { source: "0861d6d6", target: "abb22006", relation: "imports" },
      { source: "0861d6d6", target: "b586a08a", relation: "imports" }, { source: "0861d6d6", target: "fe30681f", relation: "imports" },
      { source: "0861d6d6", target: "90c99d47", relation: "imports" }, { source: "abb22006", target: "fe30681f", relation: "imports" },
      { source: "b586a08a", target: "2e1de21c", relation: "imports" }, { source: "90c99d47", target: "6e87bfd7", relation: "dispatches" },
    ],
  },
  system_flow: [
    { label: "Player input", detail: "Mouse, touch, or hand gestures become drawing actions in the React client.", citation: { path: "src/App.tsx", start_line: 2556, end_line: 2632 } },
    { label: "Room message", detail: "The client sends drawing, chat, settings, and turn events over one Socket.IO channel.", citation: { path: "src/App.tsx", start_line: 1455, end_line: 1476 } },
    { label: "Game orchestration", detail: "The server validates messages and advances room, player, timer, word, and scoring state.", citation: { path: "server/index.js", start_line: 4657, end_line: 4701 } },
    { label: "Live state", detail: "Room Store keeps active game state and Redis coordinates shared real-time state when enabled.", citation: { path: "server/roomStore.js", start_line: 1, end_line: 80 } },
    { label: "Durable history", detail: "Completed games and related records cross the Game Data Store into the database.", citation: { path: "server/gameDataStore.js", start_line: 94, end_line: 140 } },
    { label: "AI turn", detail: "The worker pool dispatches drawing and vision-guess tasks without blocking the game server.", citation: { path: "server/aiWorkerPool.js", start_line: 1, end_line: 90 } },
  ],
  key_concepts: [
    { title: "Single event envelope", detail: "Most multiplayer actions travel as typed room_message payloads.", citation: { path: "server/index.js", start_line: 4684, end_line: 4699 } },
    { title: "Local-first gameplay", detail: "Accounts are optional; players enter a name and join or create a room.", citation: { path: "README.md", start_line: 1, end_line: 38 } },
    { title: "Optional infrastructure", detail: "Redis, database persistence, and external AI providers enhance the game but have fallbacks.", citation: { path: "README.md", start_line: 101, end_line: 156 } },
  ],
  watchouts: [
    { title: "Large server entry point", detail: "server/index.js is nearly 4,800 lines, so room protocol, metrics, AI dispatch, and HTTP concerns are tightly coupled." },
    { title: "Large client coordinator", detail: "src/App.tsx coordinates many game states and real-time effects, making targeted changes harder to isolate." },
    { title: "Optional-service branches", detail: "Behavior changes depending on Redis, database, and AI credentials; test both configured and fallback modes." },
  ],
  setup_issues: [
    {
      id: "node-version",
      severity: "warning",
      title: "Node.js version is not enforced",
      summary: "The README recommends Node 22, but the project does not pin it for contributors.",
      explanation: "Two contributors can follow the same setup steps with different Node versions and get different dependency, test, or build behavior. A recommendation is easy to miss and package managers cannot enforce it.",
      fix: ["Add Node 22 to package.json under engines.node.", "Commit a .nvmrc or .node-version containing 22.", "Make CI use the same pinned version."],
      citations: [{ path: "README.md", start_line: 160, end_line: 167 }, { path: "package.json", start_line: 1, end_line: 18 }],
    },
    {
      id: "optional-secrets",
      severity: "warning",
      title: "Optional credentials look required",
      summary: "AI keys contain placeholder values even though the README says the providers are optional.",
      explanation: "A new contributor may stop to obtain several API keys before learning that the game has local fallbacks. Placeholder secrets also make it unclear whether a value is intentionally disabled or incorrectly configured.",
      fix: ["Comment out optional keys by default or label each one OPTIONAL inline.", "Validate placeholder values and print a concise fallback message.", "Group configuration into Required and Optional sections."],
      citations: [{ path: ".env.example", start_line: 1, end_line: 17 }, { path: "README.md", start_line: 160, end_line: 167 }],
    },
    {
      id: "service-modes",
      severity: "optional",
      title: "Storage behavior changes by service",
      summary: "Redis and PostgreSQL are optional, but enabling them changes persistence and reconnect behavior.",
      explanation: "Local development works without these services, while production-like behavior uses them. Contributors may reproduce a bug in one mode but not the other unless the active mode is made explicit.",
      fix: ["Document a minimal mode and a production-like mode separately.", "Print the active Redis and PostgreSQL modes at startup.", "Add test commands for configured and fallback storage paths."],
      citations: [{ path: ".env.example", start_line: 7, end_line: 14 }, { path: "README.md", start_line: 101, end_line: 124 }],
    },
    {
      id: "split-processes",
      severity: "warning",
      title: "Local setup requires two processes",
      summary: "The frontend and game server have separate commands and ports.",
      explanation: "Running only one command can produce a page without a working real-time server, or an API with no client. This often looks like an application bug instead of an incomplete setup.",
      fix: ["Add one dev command that starts both processes.", "Keep dev and dev:api available for focused debugging.", "Show both health URLs and ports when startup completes."],
      citations: [{ path: "package.json", start_line: 6, end_line: 17 }, { path: "README.md", start_line: 160, end_line: 167 }],
    },
  ],
  repo_health: {
    score: 61,
    label: "Needs attention",
    summary: "3 priority findings and 2 improvement opportunities were identified from static repository evidence.",
    categories: [
      { name: "Testing", score: 62, detail: "Focused tests exist, but several central runtime paths remain concentrated in large files." },
      { name: "Documentation", score: 92, detail: "README and supporting setup documentation detected." },
      { name: "Automation", score: 48, detail: "No continuous-integration workflow was detected." },
      { name: "Maintainability", score: 35, detail: "Two central source files exceed 1,500 lines." },
      { name: "Setup", score: 68, detail: "Local setup works, but runtime and optional service modes need clearer enforcement." },
    ],
    findings: [],
  },
  github_activity: {
    status: "unavailable",
    issues: [],
    pull_requests: [],
    reason: "Moodle was analyzed from a private local checkout. Add a read-only GITHUB_TOKEN to include its GitHub issues and pull requests.",
  },
  recent_work: {
    status: "available",
    contributors: [{ name: "Shreyakb301", commits: 8, areas: ["ASL and gesture recognition", "AI and model pipeline", "frontend experience"], summary: "Shreyakb301 has 8 recent commits focused on ASL and gesture recognition, AI and model pipeline, and frontend experience." }],
    commits: [
      { sha: "a27677f52a67fa25ac007f872a9612d4783e6021", short_sha: "a27677f", title: "feat: integrate ASL guessing into game chat", author: "Shreyakb301", date: "2026-08-06T23:41:20-05:00", areas: ["ASL and gesture recognition", "frontend experience"], files: ["src/App.css", "src/App.tsx"], file_count: 2, explanation: "Shreyakb301 appears to be connecting ASL recognition to the main game and chat experience. This commit changes the central React application and its styling.", url: "https://github.com/Sanjana-Gondariya/Moodle/commit/a27677f52a67fa25ac007f872a9612d4783e6021" },
      { sha: "dd40bbe9fc1f8632a5e926af90e3ee5a9ce43f46", short_sha: "dd40bbe", title: "feat: expand ASL practice and word testing", author: "Shreyakb301", date: "2026-08-06T23:40:58-05:00", areas: ["ASL and gesture recognition", "frontend experience"], files: ["src/asl/AslPracticePage.tsx", "src/asl/asl.css", "src/asl/useAslPractice.ts", "src/hooks/useMediaPipeHandTracking.ts"], file_count: 4, explanation: "Shreyakb301 appears to be expanding the dedicated ASL practice flow, word testing, and hand-tracking integration.", url: "https://github.com/Sanjana-Gondariya/Moodle/commit/dd40bbe9fc1f8632a5e926af90e3ee5a9ce43f46" },
      { sha: "c6d806a6c422c56fede5bd3a75581aa64af0f522", short_sha: "c6d806a", title: "feat: add ASL motion and palm-delete gestures", author: "Shreyakb301", date: "2026-08-06T23:40:53-05:00", areas: ["ASL and gesture recognition", "tests and reliability"], files: ["src/asl/aslMotion.ts", "src/asl/palmShakeDelete.ts", "tests/aslMotion.test.ts", "tests/palmShakeDelete.test.ts"], file_count: 4, explanation: "Shreyakb301 appears to be adding motion-aware ASL input and a palm-shake deletion gesture, with focused automated tests.", url: "https://github.com/Sanjana-Gondariya/Moodle/commit/c6d806a6c422c56fede5bd3a75581aa64af0f522" },
      { sha: "2cff7c3dc58db23270ed68f2fb550826976ca9b2", short_sha: "2cff7c3", title: "feat: capture personalized ASL diagnostics", author: "Shreyakb301", date: "2026-08-06T23:40:49-05:00", areas: ["ASL and gesture recognition", "tests and reliability"], files: ["src/asl/aslDiagnosticCapture.ts", "tests/aslDiagnosticCapture.test.ts"], file_count: 2, explanation: "Shreyakb301 appears to be capturing user-specific ASL diagnostics and protecting that behavior with a dedicated test.", url: "https://github.com/Sanjana-Gondariya/Moodle/commit/2cff7c3dc58db23270ed68f2fb550826976ca9b2" },
      { sha: "1b329244b229690929678b04ce84ecbd9018512f", short_sha: "1b32924", title: "feat: run ASL landmark inference in browser", author: "Shreyakb301", date: "2026-08-06T23:40:44-05:00", areas: ["ASL and gesture recognition", "AI and model pipeline", "frontend experience"], files: ["src/utils/signLanguageGuess.ts", "tests/aslModelArtifact.test.ts"], file_count: 2, explanation: "Shreyakb301 appears to be moving landmark-model inference into the browser and validating that the required model artifact is available.", url: "https://github.com/Sanjana-Gondariya/Moodle/commit/1b329244b229690929678b04ce84ecbd9018512f" },
      { sha: "66d8bffc290cbb9625a7880081b00df83c54d919", short_sha: "66d8bff", title: "feat: add ASL landmark training pipeline", author: "Shreyakb301", date: "2026-08-06T23:40:36-05:00", areas: ["ASL and gesture recognition", "AI and model pipeline", "documentation"], files: ["docs/ASL_MODEL_TRAINING.md", "docs/asl-model-benchmark.json", "scripts/asl/asl_features.py", "scripts/asl/train_landmark_model.py"], file_count: 7, explanation: "Shreyakb301 appears to be building the data preparation, training, evaluation, and documentation workflow behind the ASL landmark model.", url: "https://github.com/Sanjana-Gondariya/Moodle/commit/66d8bffc290cbb9625a7880081b00df83c54d919" },
    ],
    reason: "",
  },
  run_steps: ["npm install", "cp .env.example .env", "npm run dev:api", "npm run dev", "Open http://127.0.0.1:5173"],
  warnings: [], elapsed_ms: 3700,
};
demo.reading_order = demo.important_files;
demo.repo_health!.findings = demo.setup_issues || [];

const architectureLayers = [
  { id: "frontend", label: "Experience", description: "Browser and interface" },
  { id: "api", label: "Transport", description: "Routes and real-time server" },
  { id: "service", label: "Application", description: "Core orchestration" },
  { id: "data", label: "Data", description: "State and persistence" },
  { id: "ai", label: "Intelligence", description: "Models and AI workers" },
  { id: "module", label: "Supporting", description: "Key shared modules" },
];

const repositoryQuestions = [
  "Where does authentication happen?",
  "How does a request reach the database?",
  "Where would I add a new API endpoint?",
  "What files should I understand before contributing?",
];

function Icon({ name }: { name: "lens" | "github" | "arrow" | "check" | "file" | "route" | "spark" | "clock" }) {
  const glyphs = { lens: "⌕", github: "◉", arrow: "→", check: "✓", file: "▤", route: "↳", spark: "✦", clock: "◷" };
  return <span aria-hidden="true" className={`icon icon-${name}`}>{glyphs[name]}</span>;
}

export default function Home() {
  const [url, setUrl] = useState("https://github.com/Sanjana-Gondariya/Moodle");
  const [sourceMode, setSourceMode] = useState<"github" | "local">("github");
  const [localPath, setLocalPath] = useState("/Users/shreyakb/Moodle");
  const [analysis, setAnalysis] = useState<Analysis | null>(demo);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<{ answer: string; citations: Citation[] } | null>(null);
  const [asking, setAsking] = useState(false);
  const [selected, setSelected] = useState<ArchitectureNode | null>(null);
  const [selectedIssueId, setSelectedIssueId] = useState<string | null>(null);
  const [selectedHealthId, setSelectedHealthId] = useState<string | null>(null);
  const [selectedActivityKey, setSelectedActivityKey] = useState<string | null>(null);
  const [selectedCommitSha, setSelectedCommitSha] = useState<string | null>(null);
  const api = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

  const languageTotal = useMemo(() => Object.values(analysis?.stats.languages || {}).reduce((a, b) => a + b, 0), [analysis]);
  const architectureNodeById = useMemo(() => Object.fromEntries((analysis?.architecture.nodes || []).map(node => [node.id, node])), [analysis]);
  const githubActivityItems = useMemo(() => [...(analysis?.github_activity?.issues || []), ...(analysis?.github_activity?.pull_requests || [])], [analysis]);

  async function analyze(e: FormEvent) {
    e.preventDefault();
    const sourceValue = sourceMode === "github" ? url.trim() : localPath.trim();
    if (!sourceValue) return;
    setLoading(true); setError(""); setAnalysis(null); setAnswer(null); setSelectedIssueId(null); setSelectedHealthId(null); setSelectedActivityKey(null); setSelectedCommitSha(null);
    try {
      const endpoint = sourceMode === "github" ? "/api/analyze" : "/api/analyze-local";
      const payload = sourceMode === "github" ? { url: sourceValue } : { path: sourceValue };
      const response = await fetch(`${api}${endpoint}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
      if (!response.ok) throw new Error((await response.json()).detail || "Analysis failed");
      setAnalysis(await response.json());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not reach the local analysis service.");
    } finally { setLoading(false); }
  }

  async function ask(e: FormEvent) {
    e.preventDefault();
    if (!analysis || !question.trim()) return;
    setAsking(true); setAnswer(null);
    try {
      const response = await fetch(`${api}/api/repos/${analysis.id}/ask`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ question: question.trim() }) });
      if (!response.ok) throw new Error((await response.json()).detail || "Question failed");
      setAnswer(await response.json());
    } catch (err) { setAnswer({ answer: err instanceof Error ? err.message : "Question failed.", citations: [] }); }
    finally { setAsking(false); }
  }

  return (
    <main>
      <nav className="nav">
        <a className="brand" href="#top" aria-label="RepoLens home"><span className="brand-mark"><Icon name="lens" /></span> RepoLens</a>
        <div className="nav-right"><span className="local-pill"><i /> Local-first</span><a className="github-link" href="https://github.com" target="_blank" rel="noreferrer"><Icon name="github" /> GitHub</a></div>
      </nav>

      <section className={`hero ${analysis ? "hero-compact" : ""}`} id="top">
        <h1>Understand any codebase.<br /><span>Follow the evidence.</span></h1>
        <p>Paste a public GitHub repository or use a local checkout. RepoLens maps the architecture, finds the important files, and explains how everything connects—with citations you can verify.</p>
        <div className="source-tabs" role="group" aria-label="Repository source">
          <button className={sourceMode === "github" ? "active" : ""} onClick={() => { setSourceMode("github"); setError(""); }}>GitHub URL</button>
          <button className={sourceMode === "local" ? "active" : ""} onClick={() => { setSourceMode("local"); setError(""); }}>Local folder</button>
        </div>
        <form className="analyze-form" onSubmit={analyze}>
          {sourceMode === "github" ?
            <label className="url-field"><Icon name="github" /><input aria-label="Public GitHub repository URL" value={url} onChange={e => setUrl(e.target.value)} placeholder="https://github.com/owner/repository" /></label> :
            <label className="url-field"><Icon name="file" /><input aria-label="Local Git repository path" value={localPath} onChange={e => setLocalPath(e.target.value)} placeholder="/Users/you/projects/repository" /></label>}
          <button disabled={loading}>{loading ? <><span className="spinner" /> Analyzing</> : <>Analyze repository <Icon name="arrow" /></>}</button>
        </form>
        <div className="trust-row"><span><Icon name="check" /> {sourceMode === "github" ? "Public repositories" : "Code stays local"}</span><span><Icon name="check" /> Never executes repository code</span><span><Icon name="check" /> Local AI with Ollama</span></div>
        {error && <div className="error"><strong>Analysis couldn’t start.</strong> {error} {sourceMode === "github" && <button onClick={() => { setSourceMode("local"); setError(""); }}>Use local checkout</button>}</div>}
      </section>

      {!analysis && !loading && <section className="preview-section">
        <div className="section-label">WHAT YOU GET</div>
        <div className="feature-grid">
          <article><span className="feature-num">01</span><h3>Orientation in minutes</h3><p>Purpose, stack, entry points, key files, and the best order to read them.</p></article>
          <article><span className="feature-num">02</span><h3>Architecture you can see</h3><p>A clickable system map built from imports, routes, and static code evidence.</p></article>
          <article><span className="feature-num">03</span><h3>Answers you can trust</h3><p>Hybrid retrieval grounds every answer in exact file and line citations.</p></article>
        </div>
        <button className="demo-button" onClick={() => setAnalysis(demo)}>Explore the interactive demo <Icon name="arrow" /></button>
      </section>}

      {loading && <section className="loading-panel">
        <div className="radar"><span /><span /><span /></div>
        <h2>Reading the repository</h2><p>Filtering files, detecting the stack, mapping symbols, and building the search index…</p>
        <div className="loading-steps"><span className="done">Repository secured</span><span className="active">Parsing code structure</span><span>Building retrieval index</span></div>
      </section>}

      {analysis && <section className="results">
        <header className="repo-header">
          <div><div className="repo-kicker"><Icon name="github" /> {analysis.repo.owner} / <span className="example-pill">Moodle example output</span></div><h2>{analysis.repo.name}</h2><p>{analysis.summary}</p></div>
          <div className="repo-meta"><span><strong>{analysis.stats.files}</strong> files</span><span><strong>{analysis.stats.lines.toLocaleString()}</strong> lines</span><span><strong>{(analysis.elapsed_ms / 1000).toFixed(1)}s</strong> indexed</span>{analysis.repo_health && <a className="health-jump" href="#repo-health">Health {analysis.repo_health.score}/100 ↓</a>}</div>
        </header>

        <div className="results-grid">
          <div className="main-column">
            <article className="panel overview-panel">
              <div className="panel-heading"><div><span className="panel-index">01</span><h3>Repository overview</h3></div><span className="confidence"><i /> Evidence mapped</span></div>
              <div className="stack-row">{analysis.stack.map(item => <span key={item}>{item}</span>)}</div>
              <div className="language-bars">{Object.entries(analysis.stats.languages).map(([name, count], index) => <div key={name} className="language-item"><div><span>{name}</span><b>{Math.round((count / Math.max(languageTotal, 1)) * 100)}%</b></div><div className="bar"><i style={{ width: `${(count / Math.max(languageTotal, 1)) * 100}%`, background: ["#6558d6", "#54a891", "#e9a23b", "#d86d70"][index % 4] }} /></div></div>)}</div>
              <h4>Start here</h4>
              {analysis.entry_points.map(entry => <div className="entry" key={entry.path}><span className="file-icon"><Icon name="file" /></span><div><code>{entry.path}</code><p>{entry.reason}</p></div><Citation citation={entry.citation} /></div>)}
            </article>

            {analysis.system_flow && <article className="panel flow-panel">
              <div className="panel-heading"><div><span className="panel-index">02</span><h3>How the system works</h3></div><span className="hint">End-to-end runtime flow</span></div>
              <div className="system-flow">{analysis.system_flow.map((step, index) => <div className="flow-step" key={step.label}><span className="flow-number">{String(index + 1).padStart(2, "0")}</span><div><strong>{step.label}</strong><p>{step.detail}</p><Citation citation={step.citation} /></div>{index < analysis.system_flow!.length - 1 && <b className="flow-arrow">↓</b>}</div>)}</div>
            </article>}

            <article className="panel">
              <div className="panel-heading"><div><span className="panel-index">03</span><h3>Architecture diagram</h3></div><span className="hint">{analysis.architecture.nodes.length} modules · {analysis.architecture.edges.length} verified links</span></div>
              <div className="architecture-diagram">
                {architectureLayers.map(layer => {
                  const nodes = analysis.architecture.nodes.filter(node => node.kind === layer.id);
                  if (!nodes.length) return null;
                  return <section className={`arch-lane lane-${layer.id}`} key={layer.id}>
                    <header><span>{layer.label}</span><small>{layer.description}</small></header>
                    <div>{nodes.map(node => <button key={node.id} onClick={() => setSelected(node)} className={`arch-node kind-${node.kind} ${selected?.id === node.id ? "selected" : ""}`}><span>{node.kind}</span><strong>{node.label}</strong><small>{node.file}</small></button>)}</div>
                  </section>;
                })}
              </div>
              {analysis.architecture.edges.length > 0 && <div className="relationship-list">
                <span className="relationship-title">Verified relationships</span>
                <div>{analysis.architecture.edges.map((edge, index) => <button key={`${edge.source}-${edge.target}-${index}`} onClick={() => setSelected(architectureNodeById[edge.source])}><code>{architectureNodeById[edge.source]?.label || edge.source}</code><b>→</b><code>{architectureNodeById[edge.target]?.label || edge.target}</code><small>{edge.relation}</small></button>)}</div>
              </div>}
              {selected && <div className="node-detail"><div><span>Selected evidence</span><strong>{selected.label}</strong></div><code>{selected.file}</code><div className="node-links">{analysis.architecture.edges.filter(edge => edge.source === selected.id || edge.target === selected.id).map((edge, i) => <small key={i}>{edge.source === selected.id ? "Uses" : "Used by"} {architectureNodeById[edge.source === selected.id ? edge.target : edge.source]?.label}</small>)}</div><button onClick={() => setSelected(null)}>Close</button></div>}
            </article>

            {analysis.repo_health && <article className="panel health-panel" id="repo-health">
              <div className="panel-heading"><div><span className="panel-index">04</span><h3>Repository health</h3></div><span className={`health-status health-${analysis.repo_health.label.toLowerCase().replaceAll(" ", "-")}`}>{analysis.repo_health.label}</span></div>
              <div className="health-summary">
                <div className="health-score" style={{ background: `conic-gradient(#5d50c8 ${analysis.repo_health.score}%, #e6e2dc 0)` }}><div><strong>{analysis.repo_health.score}</strong><span>/ 100</span></div></div>
                <div><span className="health-kicker">Engineering X-ray</span><h4>{analysis.repo_health.label === "Healthy" ? "Strong foundations" : analysis.repo_health.label === "At risk" ? "Important gaps need attention" : "A solid base with clear improvements"}</h4><p>{analysis.repo_health.summary}</p></div>
              </div>
              <div className="health-categories">{analysis.repo_health.categories.map(category => <div className="health-category" key={category.name}><div><strong>{category.name}</strong><span>{category.score}</span></div><div className="health-meter"><i style={{ width: `${category.score}%` }} /></div><p>{category.detail}</p></div>)}</div>
              <div className="health-findings-heading"><div><span>Prioritized findings</span><p>Select a finding to understand the evidence and the smallest useful fix.</p></div><b>{analysis.repo_health.findings.length}</b></div>
              {analysis.repo_health.findings.length === 0 ? <div className="health-clear"><strong>No priority findings</strong><p>The current static checks did not identify a high-impact repository health concern.</p></div> : <div className="health-findings">{analysis.repo_health.findings.map(finding => {
                const expanded = selectedHealthId === finding.id;
                return <div className={`health-finding ${expanded ? "selected" : ""}`} key={finding.id}>
                  <button type="button" aria-expanded={expanded} aria-controls={`health-detail-${finding.id}`} onClick={() => setSelectedHealthId(expanded ? null : finding.id)}><span className={`finding-level level-${finding.severity}`}>{finding.severity === "warning" ? "Priority" : "Improve"}</span><strong>{finding.title}</strong><p>{finding.summary}</p><small>{expanded ? "Close ↑" : "View recommendation →"}</small></button>
                  {expanded && <div className="health-finding-detail" id={`health-detail-${finding.id}`}><div><span>Why it matters</span><p>{finding.explanation}</p></div><div><span>Recommended next steps</span><ol>{finding.fix.map((step, index) => <li key={step}><b>{index + 1}</b>{step}</li>)}</ol></div>{finding.citations.length > 0 && <div className="health-evidence"><span>Evidence</span>{finding.citations.map((citation, index) => <Citation key={index} citation={citation} />)}</div>}</div>}
                </div>;
              })}</div>}
              <p className="health-note">Health scores are directional signals from repository structure—not a substitute for runtime testing or a security audit.</p>
            </article>}

            {analysis.setup_issues && <article className="panel setup-panel">
              <div className="panel-heading"><div><span className="panel-index">05</span><h3>Setup issues</h3></div><span className="readiness-status"><i /> Needs attention · {analysis.setup_issues.length} findings</span></div>
              <p className="setup-intro">Select an issue to see why RepoLens flagged it, how it affects contributors, and the evidence-backed fix.</p>
              <div className="issue-grid">{analysis.setup_issues.map(issue => {
                const expanded = selectedIssueId === issue.id;
                return <button type="button" className={`issue-card severity-${issue.severity} ${expanded ? "selected" : ""}`} key={issue.id} aria-expanded={expanded} aria-controls={`issue-detail-${issue.id}`} onClick={() => setSelectedIssueId(expanded ? null : issue.id)}>
                  <span className="issue-severity">{issue.severity === "warning" ? "Needs attention" : "Optional service"}</span><strong>{issue.title}</strong><p>{issue.summary}</p><small>{expanded ? "Hide explanation ↑" : "Explain this issue →"}</small>
                </button>;
              })}</div>
              {analysis.setup_issues.map(issue => selectedIssueId === issue.id && <div className="issue-detail" id={`issue-detail-${issue.id}`} key={issue.id}>
                <div className="issue-detail-copy"><span>Why this matters</span><h4>{issue.title}</h4><p>{issue.explanation}</p></div>
                <div className="issue-fix"><span>Recommended fix</span><ol>{issue.fix.map((step, index) => <li key={step}><b>{index + 1}</b><span>{step}</span></li>)}</ol></div>
                <div className="issue-evidence"><span>Evidence</span><div>{issue.citations.map((citation, index) => <Citation key={index} citation={citation} />)}</div></div>
              </div>)}
            </article>}

            <article className="panel">
              <div className="panel-heading"><div><span className="panel-index">06</span><h3>Ask the repository</h3></div><span className="confidence"><i /> Citation enforced</span></div>
              <p className="ask-intro">Ask a question in plain language. RepoLens searches the codebase and answers with file-and-line evidence.</p>
              <form className="ask-form" onSubmit={ask}><textarea aria-label="Question about the repository" value={question} onChange={e => setQuestion(e.target.value)} placeholder="Ask anything about this codebase…" /><button disabled={asking || !question.trim()}>{asking ? "Searching…" : "Ask"} <Icon name="arrow" /></button></form>
              <div className="suggestion-block">
                <span>You could ask questions like:</span>
                <div className="suggestions">{repositoryQuestions.map(q => <button type="button" key={q} onClick={() => setQuestion(q)}>“{q}”</button>)}</div>
              </div>
              {answer && <div className="answer"><div className="answer-label"><Icon name="spark" /> Grounded answer</div><p>{answer.answer}</p><div className="answer-citations">{answer.citations.map((c, i) => <Citation key={i} citation={c} />)}</div></div>}
            </article>

            {analysis.github_activity && <article className="panel activity-panel">
              <div className="panel-heading"><div><span className="panel-index">07</span><h3>GitHub issues & pull requests</h3></div>{analysis.github_activity.status === "available" && <span className="activity-counts"><b>{analysis.github_activity.issues.length}</b> issues · <b>{analysis.github_activity.pull_requests.length}</b> pull requests</span>}</div>
              {analysis.github_activity.status === "unavailable" ? <div className="activity-unavailable"><span>GitHub activity unavailable</span><p>{analysis.github_activity.reason}</p><small>Repository analysis and Q&A continue to work without GitHub activity.</small></div> : githubActivityItems.length === 0 ? <div className="activity-unavailable activity-clear"><span>No open activity</span><p>This repository has no open GitHub issues or pull requests in the retrieved activity window.</p></div> : <>
                <p className="activity-intro">Select an issue or pull request to read the author’s explanation and understand the active work around this repository.</p>
                <div className="activity-list">{githubActivityItems.map(item => {
                  const key = `${item.kind}-${item.number}`;
                  const expanded = selectedActivityKey === key;
                  return <button type="button" key={key} className={`activity-item ${expanded ? "selected" : ""}`} aria-expanded={expanded} aria-controls={`activity-detail-${key}`} onClick={() => setSelectedActivityKey(expanded ? null : key)}>
                    <span className={`activity-kind kind-${item.kind}`}>{item.kind === "issue" ? "Issue" : item.draft ? "Draft PR" : "Pull request"}</span><strong>#{item.number} {item.title}</strong><small>by {item.author} · {item.comments} comment{item.comments === 1 ? "" : "s"}</small><b>{expanded ? "↑" : "→"}</b>
                  </button>;
                })}</div>
                {githubActivityItems.map(item => {
                  const key = `${item.kind}-${item.number}`;
                  if (selectedActivityKey !== key) return null;
                  return <div className="activity-detail" id={`activity-detail-${key}`} key={key}>
                    <div><span>{item.kind === "issue" ? "Issue explanation" : "Change proposal"}</span><h4>#{item.number} {item.title}</h4><p>{item.explanation}</p></div>
                    <div className="activity-meta"><span>Opened by <b>{item.author}</b></span>{item.updated_at && <span>Updated {new Date(item.updated_at).toLocaleDateString()}</span>}<span>{item.comments} comment{item.comments === 1 ? "" : "s"}</span></div>
                    {item.labels.length > 0 && <div className="activity-labels">{item.labels.map(label => <span key={label}>{label}</span>)}</div>}
                    {item.url && <a href={item.url} target="_blank" rel="noreferrer">Open on GitHub ↗</a>}
                  </div>;
                })}
              </>}
            </article>}

          </div>

          <aside className="side-column">
            {analysis.recent_work && <article className="panel side-panel recent-work-panel">
              <div className="panel-heading"><div><span className="panel-index">08</span><h3>What people are working on</h3></div></div>
              {analysis.recent_work.status === "unavailable" ? <div className="activity-unavailable"><span>Recent work unavailable</span><p>{analysis.recent_work.reason}</p><small>RepoLens reads commit metadata and changed file paths; it never executes repository code.</small></div> : <>
                <div className="recent-work-counts"><span><b>{analysis.recent_work.commits.length}</b> commits</span><span><b>{analysis.recent_work.contributors.length}</b> contributor{analysis.recent_work.contributors.length === 1 ? "" : "s"}</span></div>
                <p className="activity-intro">Recent commit messages and changed files reveal each contributor’s current focus.</p>
                <div className="contributor-focus">{analysis.recent_work.contributors.map(contributor => <div key={contributor.name}><span>{contributor.name.slice(0, 1).toUpperCase()}</span><div><strong>{contributor.name}</strong><p>{contributor.summary}</p><small>{contributor.areas.join(" · ")}</small></div></div>)}</div>
                <div className="commit-list">{analysis.recent_work.commits.map(commit => {
                  const expanded = selectedCommitSha === commit.sha;
                  return <div className={`commit-group ${expanded ? "selected" : ""}`} key={commit.sha}>
                    <button type="button" className="commit-item" aria-expanded={expanded} aria-controls={`commit-detail-${commit.short_sha}`} onClick={() => setSelectedCommitSha(expanded ? null : commit.sha)}>
                      <code>{commit.short_sha}</code><div><strong>{commit.title}</strong><small>{commit.author} · {commit.date ? new Date(commit.date).toLocaleDateString() : "Date unavailable"} · {commit.file_count} file{commit.file_count === 1 ? "" : "s"}</small></div><b>{expanded ? "↑" : "↓"}</b>
                    </button>
                    {expanded && <div className="commit-detail" id={`commit-detail-${commit.short_sha}`}>
                      <span>Work summary</span><h4>{commit.title}</h4><p>{commit.explanation}</p>
                      <div className="commit-areas">{commit.areas.map(area => <span key={area}>{area}</span>)}</div>
                      {commit.files.length > 0 && <div className="changed-files"><strong>Changed files</strong>{commit.files.map(file => <code key={file}>{file}</code>)}</div>}
                      {commit.url && <a href={commit.url} target="_blank" rel="noreferrer">Open commit on GitHub ↗</a>}
                    </div>}
                  </div>;
                })}</div>
              </>}
            </article>}
            <article className="panel side-panel"><div className="panel-heading"><div><span className="panel-index">09</span><h3>Reading order</h3></div></div><ol className="reading-list">{analysis.reading_order.slice(0, 7).map((file, i) => <li key={file.path}><span>{String(i + 1).padStart(2, "0")}</span><div><code>{file.path}</code><p>{file.summary}</p></div></li>)}</ol></article>
            {analysis.key_concepts && <article className="panel side-panel"><div className="panel-heading"><div><span className="panel-index">10</span><h3>Key concepts</h3></div></div><div className="concept-list">{analysis.key_concepts.map(item => <div key={item.title}><strong>{item.title}</strong><p>{item.detail}</p><Citation citation={item.citation} /></div>)}</div></article>}
            <article className="panel side-panel"><div className="panel-heading"><div><span className="panel-index">11</span><h3>Interfaces & events</h3></div></div><div className="route-list">{analysis.routes.length ? analysis.routes.slice(0, 8).map((route, i) => <div key={i}><span className={`method method-${route.method.toLowerCase()}`}>{route.method}</span><div><code>{route.path}</code><small>{route.handler}</small></div></div>) : <p className="empty-state">No public interfaces detected.</p>}</div></article>
            {analysis.watchouts && <article className="panel side-panel watchout-panel"><div className="panel-heading"><div><span className="panel-index">12</span><h3>Watch closely</h3></div></div><div className="watchout-list">{analysis.watchouts.map(item => <div key={item.title}><span>!</span><div><strong>{item.title}</strong><p>{item.detail}</p></div></div>)}</div></article>}
            {analysis.run_steps && <article className="panel side-panel"><div className="panel-heading"><div><span className="panel-index">13</span><h3>Run locally</h3></div></div><ol className="run-list">{analysis.run_steps.map((step, index) => <li key={step}><span>{index + 1}</span><code>{step}</code></li>)}</ol></article>}
            <article className="metric-card"><Icon name="clock" /><div><span>Indexed chunks</span><strong>{analysis.stats.indexed_chunks}</strong></div><p>Code-aware sections available to hybrid search.</p></article>
          </aside>
        </div>
      </section>}

      <footer><a className="brand" href="#top"><span className="brand-mark"><Icon name="lens" /></span> RepoLens</a><p>Static analysis establishes facts. AI explains them.</p><span>Local-first · Open source</span></footer>
    </main>
  );
}

function Citation({ citation }: { citation: Citation }) {
  return <span className="citation" title="Source citation">{citation.path}:{citation.start_line}{citation.end_line !== citation.start_line ? `–${citation.end_line}` : ""}</span>;
}
