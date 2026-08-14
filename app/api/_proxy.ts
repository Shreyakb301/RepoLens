const DEFAULT_BACKEND_URL = "https://repolens-6j7t.onrender.com";

export async function proxyToBackend(request: Request, path: string) {
  const backendUrl = (process.env.REPOLENS_API_URL || DEFAULT_BACKEND_URL).replace(/\/$/, "");

  try {
    const upstream = await fetch(`${backendUrl}${path}`, {
      method: request.method,
      headers: {
        "Accept": "application/json",
        "Content-Type": request.headers.get("content-type") || "application/json",
      },
      body: request.method === "GET" || request.method === "HEAD" ? undefined : await request.text(),
      cache: "no-store",
    });

    return new Response(upstream.body, {
      status: upstream.status,
      headers: { "Content-Type": upstream.headers.get("content-type") || "application/json" },
    });
  } catch {
    return Response.json(
      { detail: "The analysis service is temporarily unavailable. Please try again shortly." },
      { status: 503 },
    );
  }
}
