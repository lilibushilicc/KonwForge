import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { PracticeSession } from "../api/practice";

/**
 * 单题作答草稿（顺序练习里含即时判分结果，考试模式含答案与自评）
 */
export interface AnswerDraft {
  response: Record<string, any>;
  self_eval?: string;
  /** 顺序练习「提交本题」后的即时判分结果（含 reveal），切回时展示 */
  result?: any;
}

/**
 * 进行中的练习会话镜像（按 item.id 索引），持久化到 localStorage。
 * 刷新页面 / 短暂断网后可「继续上次」，不丢失已答状态。
 */
export interface PracticeDraft {
  session: PracticeSession;
  responses: Record<number, AnswerDraft>;
  /** 顺序练习当前题号（0-based） */
  idx: number;
  /** 考试模式标记题 */
  flagged: Record<number, boolean>;
  updatedAt: number;
}

interface PracticeStoreState {
  draft: PracticeDraft | null;
  setDraft: (d: PracticeDraft | null) => void;
  patchDraft: (p: Partial<PracticeDraft>) => void;
  clear: () => void;
}

/**
 * 全局答题会话草稿（persist 到 localStorage key: knowforge-practice）。
 * 所有答题页状态（session、逐题答案、题号、标记）都从这一个 store 读写，
 * 既保证「切题不丢答案」，也保证「刷新/断网可续答」。
 */
export const usePracticeStore = create<PracticeStoreState>()(
  persist(
    (set) => ({
      draft: null,
      setDraft: (draft) => set({ draft }),
      patchDraft: (p) =>
        set((s) =>
          s.draft ? { draft: { ...s.draft, ...p, updatedAt: Date.now() } } : {},
        ),
      clear: () => set({ draft: null }),
    }),
    { name: "knowforge-practice" },
  ),
);

/** 是否存在可继续的会话（active/paused 且未被提交/放弃） */
export function hasResumableDraft(): boolean {
  const d = usePracticeStore.getState().draft;
  return !!d && (d.session.status === "active" || d.session.status === "paused");
}
