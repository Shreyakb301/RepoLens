import { proxyToBackend } from "../_proxy";

export const dynamic = "force-dynamic";

export function POST(request: Request) {
  return proxyToBackend(request, "/api/analyze");
}
