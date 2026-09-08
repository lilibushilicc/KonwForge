import { create } from "zustand";
import { persist } from "zustand/middleware";

export type ThemeMode = "light" | "dark";

interface UiState {
  theme: ThemeMode;
  setTheme: (t: ThemeMode) => void;
  toggleTheme: () => void;
}

/** 主题等 UI 偏好，persist 到 localStorage（key: quiz-ui）。 */
export const useUiStore = create<UiState>()(
  persist(
    (set) => ({
      theme: "light",
      setTheme: (t) => set({ theme: t }),
      toggleTheme: () => set((s) => ({ theme: s.theme === "light" ? "dark" : "light" })),
    }),
    { name: "quiz-ui" },
  ),
);
