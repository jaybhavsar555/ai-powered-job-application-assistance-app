import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";
export const maxDuration = 300;

const API = process.env.BACKEND_URL || "http://127.0.0.1:8001";

/**
 * Dedicated proxy for Discovery — board fetch + LLM score often exceeds
 * the default Next rewrite proxy timeout (client sees HTTP 500).
 */
export async function POST(req: NextRequest) {
  const auth = req.headers.get("authorization") || "";
  const body = await req.text();

  try {
    const upstream = await fetch(`${API}/api/v1/workflows/discover`, {
      method: "POST",
      headers: {
        Authorization: auth,
        "Content-Type": "application/json",
      },
      body,
      signal: AbortSignal.timeout(300_000),
    });

    const text = await upstream.text();
    return new NextResponse(text, {
      status: upstream.status,
      headers: {
        "Content-Type":
          upstream.headers.get("content-type") || "application/json",
      },
    });
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    return NextResponse.json(
      {
        detail:
          `Discovery proxy failed: ${message}. ` +
          "API may still be scoring — wait and retry, or check Docker :8001 / Token Harbor.",
      },
      { status: 502 }
    );
  }
}
