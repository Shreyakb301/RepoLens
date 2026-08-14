import { proxyToBackend } from "../_proxy";

export const dynamic = "force-dynamic";

export function GET(request: Request) {
  return proxyToBackend(request, "/api/health");
}
