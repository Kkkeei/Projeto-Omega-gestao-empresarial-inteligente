export const API_URL = (import.meta.env.VITE_API_URL || "")
  .replace(/\/$/, "")
  .replace(/\/api\/v1\/?$/, "");

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

export type ApiRequestInit = RequestInit & { timeoutMs?: number };

export async function apiFetch<T>(path: string, options: ApiRequestInit = {}): Promise<T> {
  const token = localStorage.getItem("omega_access_token");
  const { timeoutMs = 20000, headers: customHeaders, ...restOptions } = options;
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs);
  const headers = new Headers(customHeaders || {});
  if (!headers.has("Content-Type") && !(restOptions.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  if (token) headers.set("Authorization", `Bearer ${token}`);

  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      ...restOptions,
      headers,
      signal: restOptions.signal || controller.signal,
    });
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new Error(`O backend demorou mais de ${Math.round(timeoutMs / 1000)} segundos para responder a ${path}. Verifique o FastAPI e o banco omega.db.`);
    }
    throw new Error(`Não foi possível conectar ao backend em ${API_URL || window.location.origin}. Verifique se o FastAPI está em execução.`);
  } finally {
    window.clearTimeout(timeoutId);
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

export async function apiFetchBlob(path: string, options: ApiRequestInit = {}): Promise<{ blob: Blob; contentDisposition: string }> {
  const token = localStorage.getItem("omega_access_token");
  const { timeoutMs = 30000, headers: customHeaders, ...restOptions } = options;
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs);
  const headers = new Headers(customHeaders || {});
  if (token) headers.set("Authorization", `Bearer ${token}`);
  try {
    const response = await fetch(`${API_URL}${path}`, {
      ...restOptions,
      headers,
      signal: restOptions.signal || controller.signal,
    });
    if (response.status === 401) {
      localStorage.removeItem("omega_access_token");
      throw new Error("Sua sessão não está autenticada. Faça login novamente na ÔMEGA.");
    }
    if (!response.ok) {
      let detail = `Erro HTTP ${response.status}`;
      try {
        const ct = response.headers.get("content-type") || "";
        if (ct.includes("application/json")) {
          const data = await response.json();
          detail = errorMessage(data, response.status);
        }
      } catch {
        // mantém a mensagem genérica
      }
      throw new Error(detail);
    }
    return {
      blob: await response.blob(),
      contentDisposition: response.headers.get("content-disposition") || "",
    };
  } finally {
    window.clearTimeout(timeoutId);
  }
}
