import { http, buildQuery } from "./client";
import type { BatchResult, ListQuery, Page, Question, QuestionDraft } from "../types/question";

export const questionsApi = {
  list: (q: ListQuery) =>
    http.get<Page<Question>>(`/questions${buildQuery(q as Record<string, unknown>)}`),
  get: (id: number) => http.get<Question>(`/questions/${id}`),
  create: (d: QuestionDraft) => http.post<Question>("/questions", d),
  update: (id: number, d: Partial<QuestionDraft>) => http.patch<Question>(`/questions/${id}`, d),
  softDelete: (id: number) => http.delete<{ ok: boolean }>(`/questions/${id}`),
  hardDelete: (id: number) => http.delete<{ ok: boolean }>(`/questions/${id}/hard`),
  batch: (action: string, ids: number[], payload: Record<string, unknown> = {}) =>
    http.post<BatchResult>("/questions/batch", { action, ids, payload }),
  exportUrl: (fmt: "json" | "csv" = "json") => `/api/v1/questions/export?format=${fmt}`,
  exportJsonData: () => http.get<unknown[]>("/questions/export?format=json"),
  importJson: (items: unknown[], conflict: "skip" | "overwrite" | "rename" = "skip") =>
    http.post<{ total: number; created: number; updated: number; skipped: number; errors: any[] }>(
      `/questions/import?conflict=${conflict}`,
      { questions: items },
    ),
};
