import { NextRequest } from "next/server";

async function proxy(request: NextRequest, context: { params: Promise<{ path?: string[] }> }) {
  const { path = [] } = await context.params;
  if (path.some(segment => !/^[a-zA-Z0-9_-]+$/.test(segment))) {
    return Response.json({ reason: "INVALID_PATH" }, { status: 400 });
  }
  const target = new URL("/proposal" + (path.length ? "/" + path.join("/") : ""), process.env.CAPABILITY_API_ORIGIN ?? process.env.API_ORIGIN ?? "http://127.0.0.1:8000");
  target.search = request.nextUrl.search;
  try {
    const text = request.method === "POST" ? await request.text() : undefined;
    if (text && text.length > 128000) return Response.json({ reason: "INVALID_REQUEST" }, { status: 413 });
    const upstream = await fetch(target, {
      method: request.method,
      headers: {
        "Content-Type": "application/json",
        "Cookie": request.headers.get("cookie") ?? "",
        "Origin": request.headers.get("origin") ?? "",
      },
      body: text,
      cache: "no-store",
      signal: AbortSignal.timeout(10000),
    });
    const headers = new Headers();
    for (const name of ["content-type", "set-cookie", "content-disposition", "x-content-type-options", "content-security-policy"]) {
      const value = upstream.headers.get(name);
      if (value) headers.set(name, value);
    }
    headers.set("Cache-Control", "no-store");
    return new Response(await upstream.arrayBuffer(), { status: upstream.status, headers });
  } catch {
    return Response.json({ reason: "API_UNAVAILABLE" }, { status: 502 });
  }
}

export const GET = proxy;
export const POST = proxy;
