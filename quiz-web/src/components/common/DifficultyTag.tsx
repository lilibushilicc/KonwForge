import { Tag } from "antd";

const COLORS = ["default", "cyan", "green", "orange", "red"];
const LABELS = ["", "入门", "简单", "中等", "较难", "困难"];

export function DifficultyTag({ level }: { level: number }) {
  const i = Math.max(1, Math.min(5, level));
  return <Tag color={COLORS[i]}>{LABELS[i]}</Tag>;
}
