import { create } from "zustand";
import type { ListQuery, QuestionType } from "../types/question";

interface BankState {
  filters: ListQuery;
  selectedRowKeys: number[];
  setFilters: (patch: Partial<ListQuery>) => void;
  resetFilters: () => void;
  setSelected: (keys: number[]) => void;
}

const DEFAULT_FILTERS: ListQuery = {
  keyword: "",
  type: undefined,
  category_id: undefined,
  tag_ids: undefined,
  difficulty: undefined,
  status: "active",
  order_by: "created_at",
  desc: true,
  page: 1,
  page_size: 20,
};

export const useBankStore = create<BankState>((set) => ({
  filters: DEFAULT_FILTERS,
  selectedRowKeys: [],
  setFilters: (patch) => set((s) => ({ filters: { ...s.filters, ...patch } })),
  resetFilters: () => set({ filters: DEFAULT_FILTERS }),
  setSelected: (keys) => set({ selectedRowKeys: keys }),
}));

export const TYPE_LABELS: Record<QuestionType, string> = {
  single_choice: "单选",
  multiple_choice: "多选",
  fill_blank: "填空",
  coding: "代码",
  essay: "简答",
};

export const DIFFICULTY_OPTIONS = [1, 2, 3, 4, 5];
