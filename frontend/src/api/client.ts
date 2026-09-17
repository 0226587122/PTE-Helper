/** Small fetch wrapper. All calls use relative /api URLs so the same build works locally and on App Platform. */

export class ApiError extends Error {
  status: number;
  details: string[];

  constructor(status: number, message: string, details: string[] = []) {
    super(message);
    this.status = status;
    this.details = details;
  }
}

function messageFrom(status: number, body: unknown): { message: string; details: string[] } {
  const detail = (body as { detail?: unknown } | null)?.detail;
  if (typeof detail === "string") return { message: detail, details: [] };
  if (detail && typeof detail === "object" && !Array.isArray(detail)) {
    const d = detail as { message?: string; errors?: string[] };
    return { message: d.message ?? "Something went wrong.", details: d.errors ?? [] };
  }
  if (Array.isArray(detail)) {
    // FastAPI validation errors
    const details = detail.map((e: { loc?: unknown[]; msg?: string }) => {
      const field = Array.isArray(e.loc) ? e.loc[e.loc.length - 1] : "";
      return `${field}: ${e.msg}`;
    });
    return { message: "Please check the form and try again.", details };
  }
  if (status >= 500) return { message: "The server had a problem. Please try again in a moment.", details: [] };
  return { message: "Something went wrong. Please try again.", details: [] };
}

export async function api<T>(path: string, options: { method?: string; body?: unknown } = {}): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`/api${path}`, {
      method: options.method ?? "GET",
      credentials: "same-origin",
      headers: options.body !== undefined ? { "Content-Type": "application/json" } : undefined,
      body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
    });
  } catch {
    throw new ApiError(0, "We couldn't reach the server. Check your internet connection and try again.");
  }
  if (response.status === 204) return undefined as T;
  const text = await response.text();
  let body: unknown = null;
  try {
    body = text ? JSON.parse(text) : null;
  } catch {
    body = null;
  }
  if (!response.ok) {
    const { message, details } = messageFrom(response.status, body);
    throw new ApiError(response.status, message, details);
  }
  return body as T;
}
