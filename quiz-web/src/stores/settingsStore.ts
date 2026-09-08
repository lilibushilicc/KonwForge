import { create } from "zustand";
import { persist } from "zustand/middleware";

/**
 * 判分偏好（全局默认，persist 到 localStorage key: knowforge-settings）。
 *
 * 说明：判分以每道题的 judge_config 为准；这里的偏好作为「新建题目时的默认
 * judge_config」——在题库编辑器保存新题时合并进 judge_config，对已有题目不生效。
 */
export interface JudgePrefs {
  /** 填空题：是否允许乱序匹配（false=必须按空顺序填） */
  fill_blank_ordered: boolean;
  /** 多选题：是否部分给分 */
  mc_partial_credit: boolean;
  /** 多选题：是否允许多选超出（选了未配置选项）仍按已选部分给分 */
  mc_allow_extra: boolean;
}

interface SettingsState {
  prefs: JudgePrefs;
  setPrefs: (p: Partial<JudgePrefs>) => void;
  resetPrefs: () => void;
}

export const DEFAULT_JUDGE_PREFS: JudgePrefs = {
  fill_blank_ordered: true,
  mc_partial_credit: true,
  mc_allow_extra: false,
};

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set) => ({
      prefs: DEFAULT_JUDGE_PREFS,
      setPrefs: (p) => set((s) => ({ prefs: { ...s.prefs, ...p } })),
      resetPrefs: () => set({ prefs: DEFAULT_JUDGE_PREFS }),
    }),
    { name: "knowforge-settings" },
  ),
);

/**
 * 把判分偏好转换为某题型的 judge_config（仅取该题型支持的键）。
 * 供题库编辑器「保存新题」时使用。
 */
export function judgeConfigForType(
  type: string,
  prefs: JudgePrefs,
): Record<string, any> {
  switch (type) {
    case "fill_blank":
      return { ordered: prefs.fill_blank_ordered };
    case "multiple_choice":
      return {
        partial_credit: prefs.mc_partial_credit,
        allow_extra: prefs.mc_allow_extra,
      };
    default:
      return {};
  }
}
