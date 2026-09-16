export const API_URL = (import.meta.env.VITE_API_URL || (import.meta.env.DEV ? "" : "http://127.0.0.1:8000")).replace(/\/$/, "");

function errorMessage(data: unknown, status: number): string {
  if (typeof data === "string" && data.trim()) return data;
  if (data && typeof data === "object") {
    const detail = (data as { detail?: unknown }).detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail.map((item) => {
        if (item && typeof item === "object") {
          const obj = item as { msg?: unknown; loc?: unknown };
          const msg = typeof obj.msg === "string" ? obj.msg : "Dados inválidos";
          const loc = Array.isArray(obj.loc) ? obj.loc.filter((x) => x !== "body").join(" → ") : "";
          return loc ? `${loc}: ${msg}` : msg;
        }
        return String(item);
      }).join("; ");
    }
  }
  return `Erro HTTP ${status}`;
}

export async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = localStorage.getItem("omega_access_token");
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}), ...(options.headers || {}) },
      ...options,
    });
  } catch {
    throw new Error(`Não foi possível conectar ao backend em ${API_URL}. Verifique se o FastAPI está em execução.`);
  }

  const contentType = response.headers.get("content-type") || "";
  const data = contentType.includes("application/json") ? await response.json() : await response.text();
  if (response.status === 401 && !path.endsWith("/auth/login")) {
    localStorage.removeItem("omega_access_token");
    if (window.location.pathname !== "/login") window.location.href = "/login";
  }
  if (!response.ok) throw new Error(errorMessage(data, response.status));
  return data as T;
}
