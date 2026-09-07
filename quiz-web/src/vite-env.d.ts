/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** 生产前端调用后端的根路径；本地开发留空走 /api/v1 + Vite 代理 */
  readonly VITE_API_BASE?: string;
  /** 本地开发时 Vite 代理转发到的后端地址 */
  readonly VITE_PROXY_TARGET?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
