import { http, buildQuery } from "./client";

export interface QuestionBrief {
  id: number;
  code: string;
  type: string;
  stem: string;
  difficulty: number;
  category_id?: number | null;
  category_name?: string | null;
  tags: string[];
}

export interface Mistake {
  id: number;
  question_id: number;
  first_wrong_at: string;
  last_wrong_at: string;
  wrong_count: number;
  cleared_count: number;
  mastered: boolean;
  removed: boolean;
  note?: string | null;
  question: QuestionBrief;
}

export interface MistakeUpdate {
  mastered?: boolean | null;
  removed?: boolean | null;
  note?: string | null;
}

export interface MistakeListQuery {
  keyword?: string;
  category_id?: number;
  type?: string;
  mastered?: boolean;
  removed?: boolean;
  only_wrong?: boolean;
}

export const mistakesApi = {
  list: (q: MistakeListQuery = {}) =>
    http.get<Mistake[]>(`/mistakes${buildQuery(q as Record<string, unknown>)}`),
  update: (questionId: number, d: MistakeUpdate) =>
    http.patch<Mistake>(`/mistakes/${questionId}`, d),
};
