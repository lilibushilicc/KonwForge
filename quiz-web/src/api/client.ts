// 生产构建时通过 VITE_API_BASE 指向后端（如 https://xxx.onrender.com/api/v1）；
// 本地开发与同域部署留空，走相对路径 + Vite 代理。
// 兜底：即便构建未注入 VITE_API_BASE，部署在 *.onrender.com 的静态站也会自动指向线上后端，
// 避免“前端相对路径打自己、题库空白”的回归。
const PROD_BACKEND = "https://quiz-server-83xe.onrender.com/api/v1";

function resolveBase(): string {
  const fromEnv = import.meta.env.VITE_API_BASE;
  if (fromEnv) return fromEnv;
  if (typeof window !== "undefined") {
    const h = window.location.hostname;
    // 静态站域名（quiz-web-*.onrender.com）打后端；后端自身（quiz-server-*.onrender.com）走相对
    if (h.endsWith(".onrender.com") && !h.startsWith("quiz-server")) {
      return PROD_BACKEND;
    }
  }
  return "/api/v1";
}

const BASE: string = resolveBase();

// 预连接后端域名：浏览器提前完成 TCP/TLS 握手，降低首个真实请求的延迟
// （对 Render 免费实例冷启动尤其有用，把建连开销从「点开始练习」挪到页面加载时）
if (BASE.startsWith("http")) {
  try {
    const origin = BASE.replace(/\/api\/v1\/?$/, "");
    const link = document.createElement("link");
    link.rel = "preconnect";
    link.href = origin;
    link.crossOrigin = "anonymous";
    document.head.appendChild(link);
  } catch {
    /* 忽略：preconnect 失败不影响功能 */
  }
}

export class ApiError extends Error {
  code: number;
  data?: unknown;
  constructor(code: number, message: string, data?: unknown) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.data = data;
  }
}

interface Envelope<T> {
  code: number;
  message: string;
  data: T;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(BASE + path, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  const text = await res.text();
  let body: Envelope<T> | null = null;
  try {
    body = text ? (JSON.parse(text) as Envelope<T>) : null;
  } catch {
    throw new ApiError(res.status, `响应解析失败 (${res.status})`);
  }
  if (!body) throw new ApiError(res.status, `空响应 (${res.status})`);
  if (body.code !== 0) throw new ApiError(body.code, body.message, body.data);

  if (res.status >= 400) throw new ApiError(body.code, body.message, body.data);
  return body.data;
}

export const http = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, data?: unknown) =>
    request<T>(path, { method: "POST", body: data ? JSON.stringify(data) : undefined }),
  patch: <T>(path: string, data?: unknown) =>
    request<T>(path, { method: "PATCH", body: data ? JSON.stringify(data) : undefined }),
  delete: <T>(path: string) => request<T>(path, { method: "DELETE" }),
};

export function buildQuery(params: Record<string, unknown>): string {
  const usp = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v === undefined || v === null || v === "") continue;
    if (Array.isArray(v)) v.forEach((x) => usp.append(k, String(x)));
    else usp.append(k, String(v));
  }
  const s = usp.toString();
  return s ? `?${s}` : "";
}
