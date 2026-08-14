import { proxyToBackend } from "../../../_proxy";

export const dynamic = "force-dynamic";

export async function POST(request: Request, context: { params: Promise<{ analysisId: string }> }) {
  const { analysisId } = await context.params;
  return proxyToBackend(request, `/api/repos/${encodeURIComponent(analysisId)}/ask`);
}
