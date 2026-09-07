import { http } from "./client";

export interface Category {
  id: number;
  name: string;
  parent_id?: number | null;
  sort_order: number;
  created_at: string;
}
export interface Tag {
  id: number;
  name: string;
  color?: string | null;
  question_count?: number;
}

export const categoriesApi = {
  list: () => http.get<Category[]>("/categories"),
  create: (d: { name: string; parent_id?: number | null; sort_order?: number }) =>
    http.post<Category>("/categories", d),
  update: (
    id: number,
    d: Partial<{ name: string; parent_id: number | null; sort_order: number }>,
  ) => http.patch<Category>(`/categories/${id}`, d),
  remove: (id: number) => http.delete<{ ok: boolean }>(`/categories/${id}`),
};

export const tagsApi = {
  list: () => http.get<Tag[]>("/tags"),
  create: (d: { name: string; color?: string | null }) => http.post<Tag>("/tags", d),
  update: (id: number, d: Partial<{ name: string; color: string | null }>) =>
    http.patch<Tag>(`/tags/${id}`, d),
  remove: (id: number) => http.delete<{ ok: boolean }>(`/tags/${id}`),
};
