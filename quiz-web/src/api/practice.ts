import { http, buildQuery } from "./client";

export type SessionMode = "practice" | "exam" | "mistake" | "category";
export type SessionStatus = "active" | "paused" | "submitted" | "abandoned";

export interface SessionFilter {
  category_ids?: number[];
  types?: string[];
  difficulties?: number[];
  tags?: string[];
}

export interface PracticeSessionCreate {
  mode?: SessionMode;
  title?: string | null;
  count?: number;
  duration_limit_sec?: number | null;
  filter?: SessionFilter;
}

export interface QuestionPlay {
  id: number;
  code: string;
  type: string;
  stem: string;
  difficulty: number;
  category_id?: number | null;
  category_name?: string | null;
  tags: string[];
  payload: Record<string, any>;
  status: string;
  source?: string | null;
  version: number;
  created_at: string;
  updated_at: string;
}

export interface SessionItem {
  id: number;
  session_id: number;
  question_id: number;
  seq: number;
  score_weight: number;
  flagged: boolean;
  answered: boolean;
  is_correct?: boolean | null;
  score?: number | null;
  spent_sec: number;
  question: QuestionPlay;
  reveal?: Record<string, any> | null;
}

export interface PracticeSession {
  id: number;
  code: string;
  title?: string | null;
  mode: SessionMode;
  status: SessionStatus;
  total_count: number;
  duration_limit_sec?: number | null;
  elapsed_sec: number;
  started_at?: string | null;
  last_active_at?: string | null;
  submitted_at?: string | null;
  score?: number | null;
  correct_count?: number | null;
  accuracy?: number | null;
  items: SessionItem[];
}

export interface PracticeSessionListItem {
  id: number;
  code: string;
  title?: string | null;
  mode: SessionMode;
  status: SessionStatus;
  total_count: number;
  correct_count?: number | null;
  accuracy?: number | null;
  started_at?: string | null;
  submitted_at?: string | null;
}

export interface AnswerSubmit {
  item_id: number;
  response: Record<string, any>;
  duration_sec?: number | null;
  self_eval?: "mastered" | "fuzzy" | "unknown" | null;
}

export interface AnswerBatchResult {
  item_id: number;
  ok: boolean;
  is_correct?: boolean | null;
  correct?: boolean;
  error?: string;
}

export interface AnswerResult {
  item_id: number;
  is_correct?: boolean | null;
  correct: boolean;
  score: number;
  max_score: number;
  judge_detail: Record<string, any>;
  need_manual: boolean;
  feedback?: string | null;
  reveal: Record<string, any>;
  progress: { answered: number; total: number; correct_count: number };
}

export interface SessionSubmitResult {
  id: number;
  status: SessionStatus;
  score?: number | null;
  correct_count: number;
  accuracy?: number | null;
  total_count: number;
  elapsed_sec: number;
}

export interface SessionListPage {
  items: PracticeSessionListItem[];
  total: number;
  page: number;
  page_size: number;
}

export const practiceApi = {
  create: (d: PracticeSessionCreate) => http.post<PracticeSession>("/practice/sessions", d),
  list: (q: { mode?: string; status?: string; page?: number; page_size?: number } = {}) =>
    http.get<SessionListPage>(`/practice/sessions${buildQuery(q as Record<string, unknown>)}`),
  get: (id: number) => http.get<PracticeSession>(`/practice/sessions/${id}`),
  patch: (id: number, d: { status?: SessionStatus; elapsed_sec?: number }) =>
    http.patch<PracticeSession>(`/practice/sessions/${id}`, d),
  answer: (id: number, d: AnswerSubmit) =>
    http.post<AnswerResult>(`/practice/sessions/${id}/answer`, d),
  answerBatch: (id: number, items: AnswerSubmit[]) =>
    http.post<{ results: AnswerBatchResult[] }>(`/practice/sessions/${id}/answer-batch`, {
      items,
    }),
  submit: (id: number) => http.post<SessionSubmitResult>(`/practice/sessions/${id}/submit`),
};
