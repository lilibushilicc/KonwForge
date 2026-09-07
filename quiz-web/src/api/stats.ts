import { http } from "./client";

export interface StatsSummary {
  total_questions: number;
  total_attempts: number;
  total_sessions: number;
  total_mistakes: number;
  active_mistakes: number;
  overall_accuracy: number | null;
  avg_mastery: number | null;
  mastered_count: number;
  learning_count: number;
  new_count: number;
}

export interface TypeAccuracy {
  type: string;
  label: string;
  attempted: number;
  correct: number;
  accuracy: number;
}

export interface CategoryAccuracy {
  category_id: number;
  name: string;
  question_count: number;
  attempted: number;
  correct: number;
  accuracy: number;
}

export interface MasteryBucket {
  level: number;
  count: number;
}

export interface DailyActivity {
  date: string;
  attempts: number;
  correct: number;
}

export interface StatsOut {
  summary: StatsSummary;
  by_type: TypeAccuracy[];
  by_category: CategoryAccuracy[];
  mastery: MasteryBucket[];
  daily: DailyActivity[];
}

export const statsApi = {
  summary: () => http.get<StatsOut>("/stats/summary"),
};
