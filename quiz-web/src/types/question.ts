export type QuestionType = "single_choice" | "multiple_choice" | "fill_blank" | "coding" | "essay";

export type QuestionStatus = "active" | "archived";

export interface QuestionStat {
  question_id: number;
  attempt_count: number;
  wrong_count: number;
  last_attempt_at?: string | null;
  last_result?: number | null;
  mastery: number;
  streak: number;
}

export interface Question {
  id: number;
  code: string;
  type: QuestionType;
  stem: string;
  analysis?: string | null;
  difficulty: number;
  category_id?: number | null;
  category_name?: string | null;
  tags: string[];
  payload: Record<string, any>;
  answer: Record<string, any>;
  judge_config: Record<string, any>;
  status: QuestionStatus;
  source?: string | null;
  version: number;
  created_at: string;
  updated_at: string;
  stat?: QuestionStat | null;
}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface BatchResult {
  action: string;
  affected: number;
}

export interface ListQuery {
  keyword?: string;
  code?: string;
  type?: QuestionType[];
  category_id?: number;
  tag_ids?: number[];
  difficulty?: number[];
  status?: QuestionStatus;
  order_by?: "created_at" | "updated_at" | "difficulty" | "code";
  desc?: boolean;
  page?: number;
  page_size?: number;
}

export interface QuestionDraft {
  type: QuestionType;
  stem: string;
  analysis?: string | null;
  difficulty: number;
  category_id?: number | null;
  tags: string[];
  payload: Record<string, any>;
  answer: Record<string, any>;
  judge_config: Record<string, any>;
  source?: string | null;
}
