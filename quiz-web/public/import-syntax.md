# 题库导入格式语法说明

本说明描述通过「导入 / 导出」页或 `POST /api/v1/questions/import` 批量导入题目的 JSON 格式。
请求体结构为：

```json
{ "questions": [ /* 题目对象数组 */ ] }
```

冲突策略通过查询参数指定：`?conflict=skip`（默认）| `overwrite` | `rename`。

---

## 一、通用顶层字段（每条题目）

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `type` | 是 | 题型：`single_choice` / `multiple_choice` / `fill_blank` / `coding` / `essay` |
| `stem` | 是 | 题干文本（非空） |
| `difficulty` | 否 | 难度 1–5，默认 3 |
| `category_id` | 否 | 分类 id（缺省不入分类） |
| `tags` | 否 | 标签数组，如 `["函数","闭包"]` |
| `analysis` | 否 | 解析文本 |
| `source` | 否 | 来源说明（≤128 字） |
| `payload` | 是 | 呈现数据，随题型不同而不同（见下） |
| `answer` | 是 | 标准答案 / 判分依据（见下） |
| `judge_config` | 否 | 判分参数（见下） |
| `code` | 否 | 题号；省略时由服务端自动生成 |

---

## 二、分题型结构

### 1. single_choice 单选
- `payload.options`：`[{ "key": "A", "text": "..." }]`
- `answer.correct`：正确选项键，如 `"B"`
- 作答 `response`：`{ "choice": "B" }`
- `judge_config.aliases`：同义替换表（可选），如 `{ "TCP/IP": "tcpip" }`
- 判分：`response.choice` 与 `answer.correct` 归一化比对（忽略大小写 / 别名）。

### 2. multiple_choice 多选
- `payload.options`：`[{ "key": "A", "text": "..." }]`
- `answer.correct`：正确选项键数组，如 `["A","B"]`
- 作答 `response`：`{ "choices": ["A","B"] }`
- `judge_config`：`partial_credit`（默认 true）、`partial_ratio`（默认 0.5）、`allow_extra`（默认 false）、`aliases`
- 判分：全对满分；漏选且 `partial_credit` → 得 `partial_ratio` 比例；错选且 `allow_extra=false` → 0 分。

### 3. fill_blank 填空
- `payload.blanks`：`[{ "id": 1, "hint": "提示", "placeholder": "" }]`
- `answer.blanks`：每个空的判分规格
  - `id`：与 payload 对应
  - `accepted`：可接受答案数组（支持多解）
  - `regex`：正则（可选，如 `^\d+$`）
  - `case_sensitive`：是否区分大小写（默认 false）
  - `numeric_tolerance`：数值容差（默认 0.001）
- 作答 `response`：`{ "blanks": { "1": "用户填", "2": "..." } }`
- `judge_config.ordered`：是否按序匹配（默认 true；false 时乱序二分匹配）
- `judge_config.aliases`：同义替换表（可选）
- 判分：逐空比对，支持多解 / 正则 / 数值容差 / 大小写；`ordered=false` 支持乱序填答。

### 4. coding 代码
- `payload.language`：编程语言（默认 `python`）
- `payload.template`：代码模板（作答区预填）
- `payload.testcases`：`[{ "input": "...", "expected": "...", "hidden": false }]`
- `answer.reference_code`：参考实现代码
- `answer.complexity`：时间 / 空间复杂度说明（如 `O(n)`）
- `judge_config.sandbox`：沙箱判分（默认关闭 → 标记 `need_manual` 人工判分）
- 判分：沙箱未启用时为人工判分；启用后按 `testcases` 跑分。

### 5. essay 简答
- `payload.max_chars`：作答字数上限（可选）
- `answer.reference_answer`：参考答案文本
- `answer.keywords`：关键词数组，或带权重 `[{ "word": "递归", "weight": 2 }]`
- `answer.min_chars`：最少字数（可选）
- 作答 `response`：`{ "text": "..." }`
- `judge_config.aliases`：同义替换表（可选）
- 判分：默认不自动给分（人工）；启用时为 `0.6×关键词覆盖 + 0.4×TF-IDF` 相似度。

---

## 三、完整示例

见同目录 `import-example.json`（含全部 5 种题型的真实可导入样例）。
将该文件内容粘贴到「导入」文本框，或直接拖拽导入即可。

> 提示：把本格式交给 AI Agent，并附上你的知识点清单，Agent 可按此结构批量生成题目 JSON，
> 你再粘贴 / 拖拽导入题库。
