import type { ComponentType } from "react";
import {
  CheckCircleOutlined,
  CheckSquareOutlined,
  EditOutlined,
  CodeOutlined,
  FileTextOutlined,
} from "@ant-design/icons";

import type { QuestionType } from "../../types/question";
import type { EditProps, ViewProps } from "./types/SingleChoice";
import { SingleChoiceEditor, SingleChoiceView } from "./types/SingleChoice";
import { MultipleChoiceEditor, MultipleChoiceView } from "./types/MultipleChoice";
import { FillBlankEditor, FillBlankView } from "./types/FillBlank";
import { CodingEditor, CodingView } from "./types/Coding";
import { EssayEditor, EssayView } from "./types/Essay";

export type IconCmp = ComponentType<{ style?: React.CSSProperties }>;

export interface QuestionTypeMeta {
  type: QuestionType;
  label: string;
  icon: IconCmp;
  Editor: (p: EditProps) => React.ReactNode;
  View: (p: ViewProps) => React.ReactNode;
  /** 新建题目时该类型的默认 payload / answer 初值 */
  defaultPayload: () => Record<string, any>;
  defaultAnswer: () => Record<string, any>;
}

function keyAt(i: number) {
  return String.fromCharCode(65 + i);
}

export const QUESTION_TYPES: QuestionTypeMeta[] = [
  {
    type: "single_choice",
    label: "单选题",
    icon: CheckCircleOutlined,
    Editor: SingleChoiceEditor,
    View: SingleChoiceView,
    defaultPayload: () => ({ options: [{ key: keyAt(0), text: "" }] }),
    defaultAnswer: () => ({ correct: keyAt(0) }),
  },
  {
    type: "multiple_choice",
    label: "多选题",
    icon: CheckSquareOutlined,
    Editor: MultipleChoiceEditor,
    View: MultipleChoiceView,
    defaultPayload: () => ({ options: [{ key: keyAt(0), text: "" }] }),
    defaultAnswer: () => ({ correct: [] }),
  },
  {
    type: "fill_blank",
    label: "填空题",
    icon: EditOutlined,
    Editor: FillBlankEditor,
    View: FillBlankView,
    defaultPayload: () => ({ blanks: [{ id: 1, hint: "", placeholder: "" }] }),
    defaultAnswer: () => ({
      blanks: [
        { id: 1, accepted: [], regex: null, case_sensitive: false, numeric_tolerance: 0.001 },
      ],
    }),
  },
  {
    type: "coding",
    label: "代码题",
    icon: CodeOutlined,
    Editor: CodingEditor,
    View: CodingView,
    defaultPayload: () => ({ language: "python", template: "", testcases: [] }),
    defaultAnswer: () => ({ reference_code: "", complexity: "" }),
  },
  {
    type: "essay",
    label: "简答题",
    icon: FileTextOutlined,
    Editor: EssayEditor,
    View: EssayView,
    defaultPayload: () => ({ max_chars: null }),
    defaultAnswer: () => ({ reference_answer: "", keywords: [], min_chars: 0 }),
  },
];

export const TYPE_REGISTRY: Record<QuestionType, QuestionTypeMeta> = QUESTION_TYPES.reduce(
  (acc, m) => {
    acc[m.type] = m;
    return acc;
  },
  {} as Record<QuestionType, QuestionTypeMeta>,
);

export function getTypeMeta(type: QuestionType): QuestionTypeMeta {
  return TYPE_REGISTRY[type] ?? QUESTION_TYPES[0];
}
