# 个人在线答题练习网站 · 技术设计方案

> 定位：个人自用、单机/小服务器部署、数据自主可控。
> 目标：题目自录入 → 组卷练习 → 自动判分 → 错题沉淀 → 错题重做，形成闭环。

---

## 0. 技术选型

| 层 | 选型 | 理由 |
|---|---|---|
| 前端框架 | React 18 + TypeScript + Vite | 生态成熟、启动快、单人开发心智负担低 |
| UI 组件库 | Ant Design 5（ConfigProvider 定制 token）+ CSS Modules | 表格/表单/标签/抽屉等后台组件齐全，主题 token 可一键切暗色，配合少量自定义 CSS 即可做到"高级简约" |
| 路由 | React Router 6 | — |
| 服务端状态 | TanStack Query v5 | 请求缓存、失败重试、乐观更新，天然适配"自动保存" |
| 客户端状态 | Zustand（+ persist 中间件） | 答题会话状态重、更新频繁，Zustand 比 Redux 轻，比 Context 性能可控 |
| 图表 | Recharts（学习趋势） | 体积小 |
| 后端 | FastAPI + SQLAlchemy 2.0 + Alembic + Pydantic v2 | 单文件服务可跑，异步 + 自动 OpenAPI 文档；判题/导入导出用 Python 写策略最省事 |
| 数据库 | SQLite（默认，`data/quiz.db`）可切 PostgreSQL | 个人量级（万级题目）SQLite 完全够；SQLAlchemy 层屏蔽差异，换 PG 只改 DSN |
| 代码题沙箱 | 可选 Docker（`python:3.12-alpine` 无网容器），可关闭 | 个人自用的安全底线：不执行不可信代码时默认关闭 |
| 部署 | 本地 `uvicorn` + Nginx 反代 / 或单机 Docker Compose | — |

**为什么不用 Spring Boot**：功能全部是 CRUD + 判分策略 + 会话状态机，Java 侧的工程收益（企业级事务、复杂权限）用不上，反而拖慢迭代。若后续要接 JVM 生态再迁。

---

## 1. 整体架构

```
┌──────────────────────────────────────────────────────────────┐
│  Browser (React SPA)                                         │
│  ┌────────────┬────────────┬────────────┬─────────────────┐  │
│  │ 题库管理页 │ 答题会话页 │ 记录/报告页│ 错题本页        │  │
│  └─────┬──────┴─────┬──────┴─────┬──────┴────────┬────────┘  │
│        │            │            │               │           │
│  ┌─────▼────────────▼────────────▼───────────────▼────────┐  │
│  │ Zustand: bankStore / practiceStore / recordStore        │  │
│  │ (practiceStore 落 localStorage 镜像 → 断网也能续答)      │  │
│  └──────────────────────────┬──────────────────────────────┘  │
│                             │ TanStack Query + fetch          │
└─────────────────────────────┼────────────────────────────────┘
                              │  REST / JSON  (/api/v1)
┌─────────────────────────────▼────────────────────────────────┐
│  FastAPI                                                     │
│  ┌──────────┬──────────┬──────────┬──────────┬────────────┐  │
│  │questions │sessions  │mistakes  │judge     │import/exp  │  │
│  └────┬─────┴────┬─────┴────┬─────┴────┬─────┴──────┬─────┘  │
│       │          │          │          │            │         │
│  ┌────▼──────────▼──────────▼──────────▼────────────▼─────┐  │
│  │ Service 层（业务编排 / 事务边界）                        │  │
│  └────┬──────────────┬───────────────┬────────────────────┘  │
│       │              │               │                        │
│  ┌────▼──────┐ ┌─────▼────────┐ ┌────▼─────────────────────┐ │
│  │QuestionTyp│ │Judge Registry│ │Sandbox Runner (optional) │ │
│  │e Registry │ │(策略模式)     │ │Docker / subprocess       │ │
│  └────┬──────┘ └─────┬────────┘ └──────────────────────────┘ │
│       │              │                                        │
│  ┌────▼──────────────▼──────────────────────────────────┐    │
│  │ SQLAlchemy 2.0 ORM  →  SQLite / PostgreSQL            │    │
│  └──────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────┘
```

关键设计：**题型注册表 + 判分策略注册表**。新增题型只需登记 4 处（Pydantic 载荷模型、判分策略、前端渲染组件、前端录入表单），主流程零改动。

---

## 2. 项目目录结构

### 2.1 后端 `quiz-server/`

```
quiz-server/
├── pyproject.toml
├── alembic/
│   ├── env.py
│   └── versions/
├── data/                          # SQLite 数据文件、导入导出暂存
├── app/
│   ├── main.py                    # FastAPI 应用装配、全局异常、CORS
│   ├── core/
│   │   ├── config.py              # pydantic-settings，读取 .env
│   │   ├── logging.py
│   │   └── deps.py                # get_db / get_pagination 等依赖注入
│   ├── db/
│   │   ├── base.py                # DeclarativeBase + 公共 Mixin(id/created_at/updated_at)
│   │   └── session.py             # engine / SessionLocal
│   ├── models/                    # ORM（仅结构，无业务）
│   │   ├── category.py  tag.py  question.py  question_stat.py
│   │   ├── practice_session.py  session_item.py  attempt.py  mistake.py
│   ├── schemas/                   # Pydantic v2 出入参
│   │   ├── common.py              # Page[T] / ORMBase
│   │   ├── question.py  session.py  attempt.py  mistake.py  judge.py
│   │   └── enums.py               # QuestionType / SessionMode / SessionStatus
│   ├── question_types/            # ★ 题型插件层
│   │   ├── registry.py            # register_type(schema, judge, meta)
│   │   └── defs/
│   │       ├── single_choice.py
│   │       ├── multiple_choice.py
│   │       ├── fill_blank.py
│   │       ├── coding.py
│   │       └── essay.py
│   ├── judging/
│   │   ├── base.py                # JudgeResult / JudgeStrategy Protocol
│   │   ├── normalizer.py          # 文本归一化（NFKC/空白/标点/大小写/全角）
│   │   ├── registry.py            # get_strategy(type)
│   │   ├── similarity.py          # 余弦/TF-IDF，用于简答
│   │   └── sandbox.py             # Docker 执行器（可开关）
│   ├── services/                  # 业务编排，事务边界在这一层
│   │   ├── question_service.py
│   │   ├── session_service.py     # 组卷 / 恢复 / 暂停 / 提交 / 心跳
│   │   ├── mistake_service.py     # 错题入本 / 清除 / 掌握度
│   │   └── import_export_service.py
│   ├── api/v1/
│   │   ├── router.py
│   │   ├── questions.py  categories.py  tags.py
│   │   ├── sessions.py  attempts.py  mistakes.py
│   │   ├── judge.py  stats.py  import_export.py
│   └── utils/                     # code_gen(Q-2026-000123) / time / file
└── tests/
    ├── test_judge_choice.py  test_judge_fill_blank.py
    ├── test_session_flow.py  test_import_export.py
```

### 2.2 前端 `quiz-web/`

```
quiz-web/
├── index.html
├── vite.config.ts
├── src/
│   ├── main.tsx  App.tsx
│   ├── router/index.tsx           # 路由表 + 懒加载
│   ├── api/                       # 纯 fetch 封装，无状态
│   │   ├── client.ts              # 拦截器：错误提示、baseURL
│   │   ├── questions.ts  sessions.ts  mistakes.ts  stats.ts  judge.ts
│   ├── types/                     # 与后端 schemas 对齐的 TS 类型
│   │   ├── question.ts  session.ts  judge.ts
│   ├── stores/
│   │   ├── practiceStore.ts       # ★ 答题会话（核心）
│   │   ├── bankStore.ts           # 列表筛选条件、选中项
│   │   ├── mistakeStore.ts
│   │   └── uiStore.ts             # 主题、侧边栏、全局 loading
│   ├── hooks/
│   │   ├── useTimer.ts            # 可暂停累加计时器
│   │   ├── useAutoSave.ts         # 防抖保存 + 页面隐藏强制 flush
│   │   ├── usePauseOnLeave.ts     # visibilitychange/pagehide → 暂停
│   │   └── useHotkeys.ts          # 1-4 选选项、F 标记、← → 切题
│   ├── components/
│   │   ├── common/                # EmptyState / PageHeader / MarkdownView / DifficultyTag
│   │   ├── question/
│   │   │   ├── registry.ts        # type → { Renderer, Editor, icon, label }
│   │   │   └── renderers/         # SingleChoice / MultipleChoice / FillBlank
│   │   │       └── editors/       # Coding / Essay（含代码编辑器、字数统计）
│   │   ├── practice/
│   │   │   ├── QuestionNav.tsx    # 题号宫格：已答/待定/当前/未答 四态
│   │   │   ├── TimerBadge.tsx
│   │   │   ├── FlagButton.tsx
│   │   │   └── SubmitConfirmModal.tsx  # 未答/待定提醒
│   │   └── layout/AppLayout.tsx
│   ├── pages/
│   │   ├── Dashboard/             # 今日练习、连续天数、正确率趋势、快捷入口
│   │   ├── Bank/
│   │   │   ├── QuestionList.tsx   # 表格 + 多维筛选 + 批量操作
│   │   │   ├── QuestionEditor.tsx # 抽屉/整页编辑，按题型动态渲染表单
│   │   │   └── ImportExport.tsx   # 上传/下载、校验预览、冲突策略
│   │   ├── Practice/
│   │   │   ├── Setup.tsx          # 组卷：范围/题型/难度/数量/顺序/限时
│   │   │   ├── Session.tsx        # 答题页
│   │   │   └── Report.tsx         # 成绩 + 逐题解析
│   │   ├── Records/
│   │   │   ├── HistoryList.tsx    # 时间 / 正确率 / 用时 / 模式
│   │   │   └── HistoryDetail.tsx
│   │   ├── Mistakes/
│   │   │   ├── MistakeList.tsx    # 错题本
│   │   │   └── MistakePractice.tsx# 错题重做（复用 Session 页）
│   │   └── Settings/              # 主题、判分偏好、沙箱开关、数据备份
│   ├── styles/
│   │   ├── theme.ts               # AntD token：圆角 8、主色低饱和、无重阴影
│   │   └── global.css             # 排版基线、间距节奏、内容区最大宽度
└── .env
```

---

## 3. 数据库设计

> 以 SQLite 语法给出；切 PostgreSQL 时：自增主键换 `BIGSERIAL/IDENTITY`，`JSON` 换 `JSONB`，其余不变。

### 3.1 ER 概览

```
category ─┐                                    practice_session ─┬─ session_item ── attempt
          │  ┌─ question_tag ─┐                                  │        │
tag ──────┼──┘                ├─ question ── question_stat       │        │
          └───────────────────┘      │                           │        │
                                     └──── mistake ──────────────┘────────┘
```

### 3.2 表结构

**题目主表采用"公共列 + JSON 载荷"混合模型**：检索/筛选字段（编号、类型、难度、分类）作为真实列保证查询性能与索引；题型专属内容（选项、空格、代码模板、测试用例）放 `payload/answer/judge_config` 三个 JSON 列，新增题型不改表。

```sql
-- 分类（多级树）
CREATE TABLE category (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  name        TEXT    NOT NULL,
  parent_id   INTEGER REFERENCES category(id) ON DELETE SET NULL,
  sort_order  INTEGER NOT NULL DEFAULT 0,
  created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE tag (
  id    INTEGER PRIMARY KEY AUTOINCREMENT,
  name  TEXT NOT NULL UNIQUE,
  color TEXT                      -- UI 展示色，可空
);

CREATE TABLE question (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  code         TEXT    NOT NULL UNIQUE,          -- 业务唯一编号 Q-2026-000123
  type         TEXT    NOT NULL,                 -- single_choice|multiple_choice|fill_blank|coding|essay
  stem         TEXT    NOT NULL,                 -- 题干（Markdown + $LaTeX$）
  analysis     TEXT,                             -- 解析（Markdown）
  difficulty   SMALLINT NOT NULL DEFAULT 3,      -- 1..5
  category_id  INTEGER REFERENCES category(id) ON DELETE SET NULL,
  payload      JSON    NOT NULL DEFAULT '{}',    -- 题型专属题目内容
  answer       JSON    NOT NULL DEFAULT '{}',    -- 题型专属标准答案
  judge_config JSON    NOT NULL DEFAULT '{}',    -- 判分参数（见 §6）
  status       TEXT    NOT NULL DEFAULT 'active',-- active | archived（软删除）
  source       TEXT,                             -- 来源备注/导入批次号
  version      INTEGER NOT NULL DEFAULT 1,
  created_at   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_q_type ON question(type);
CREATE INDEX idx_q_cat  ON question(category_id);
CREATE INDEX idx_q_diff ON question(difficulty);
CREATE INDEX idx_q_status ON question(status);

CREATE TABLE question_tag (
  question_id INTEGER NOT NULL REFERENCES question(id) ON DELETE CASCADE,
  tag_id      INTEGER NOT NULL REFERENCES tag(id)      ON DELETE CASCADE,
  PRIMARY KEY (question_id, tag_id)
);

-- 冗余统计：支撑掌握度 / SRS 调度 / 错题重做排序，避免每次聚合 attempt
CREATE TABLE question_stat (
  question_id     INTEGER PRIMARY KEY REFERENCES question(id) ON DELETE CASCADE,
  attempt_count   INTEGER NOT NULL DEFAULT 0,
  wrong_count     INTEGER NOT NULL DEFAULT 0,
  last_attempt_at TIMESTAMP,
  last_result     SMALLINT,                     -- 0 错 / 1 对
  mastery         SMALLINT NOT NULL DEFAULT 0,  -- 0..5，用于错题优先级
  streak          INTEGER NOT NULL DEFAULT 0    -- 连续答对次数
);

CREATE TABLE practice_session (
  id                 INTEGER PRIMARY KEY AUTOINCREMENT,
  code               TEXT NOT NULL UNIQUE,       -- S-2026-000001
  title              TEXT,
  mode               TEXT NOT NULL,              -- practice | exam | mistake
  status             TEXT NOT NULL,              -- active | paused | submitted | abandoned
  total_count        INTEGER NOT NULL,
  duration_limit_sec INTEGER,                    -- NULL = 不限时
  elapsed_sec        INTEGER NOT NULL DEFAULT 0, -- 服务端权威累计用时（暂停时由客户端上报累加）
  question_ids       JSON NOT NULL DEFAULT '[]', -- 组卷结果快照（顺序即题号）
  filter_snapshot    JSON NOT NULL DEFAULT '{}', -- 组卷条件（组卷来源可复现）
  started_at         TIMESTAMP,
  last_active_at     TIMESTAMP,                  -- 心跳；超时由服务端自动置 paused
  submitted_at       TIMESTAMP,
  score              NUMERIC(6,2),
  correct_count      INTEGER,
  accuracy           NUMERIC(5,2)
);

CREATE TABLE session_item (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id   INTEGER NOT NULL REFERENCES practice_session(id) ON DELETE CASCADE,
  question_id  INTEGER NOT NULL REFERENCES question(id),
  seq          INTEGER NOT NULL,                 -- 题号 1..N
  score_weight NUMERIC(5,2) NOT NULL DEFAULT 1,  -- 分值权重
  flagged      BOOLEAN NOT NULL DEFAULT FALSE,   -- 标记待定
  answered     BOOLEAN NOT NULL DEFAULT FALSE,
  is_correct   BOOLEAN,
  score        NUMERIC(6,2),
  spent_sec    INTEGER NOT NULL DEFAULT 0,
  UNIQUE (session_id, question_id),
  UNIQUE (session_id, seq)
);

-- 作答明细：append-only，支持一次会话内多次改答与错题重做的历史追溯
CREATE TABLE attempt (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id   INTEGER NOT NULL REFERENCES practice_session(id) ON DELETE CASCADE,
  item_id      INTEGER NOT NULL REFERENCES session_item(id)     ON DELETE CASCADE,
  question_id  INTEGER NOT NULL REFERENCES question(id),
  response     JSON    NOT NULL,                 -- 用户答案（题型专属结构）
  is_correct   BOOLEAN,
  score        NUMERIC(6,2),
  max_score    NUMERIC(6,2) NOT NULL DEFAULT 1,
  judge_detail JSON,                             -- 逐空/逐用例判分明细
  submitted_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  duration_sec INTEGER
);
CREATE INDEX idx_att_q  ON attempt(question_id);
CREATE INDEX idx_att_s  ON attempt(session_id);

CREATE TABLE mistake (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  question_id     INTEGER NOT NULL REFERENCES question(id) ON DELETE CASCADE,
  first_wrong_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  last_wrong_at   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  wrong_count     INTEGER NOT NULL DEFAULT 1,
  cleared_count   INTEGER NOT NULL DEFAULT 0,    -- 连续答对次数，达阈值自动 mastered
  mastered        BOOLEAN NOT NULL DEFAULT FALSE,
  removed         BOOLEAN NOT NULL DEFAULT FALSE,-- 手动移除（软删，可恢复）
  note            TEXT,                          -- 个人错因笔记
  UNIQUE (question_id)
);
```

**单用户说明**：当前不建 `user` 表。`practice_session` / `mistake` 预留 `user_id INTEGER NULL DEFAULT 1` 字段即可无痛升级多用户，索引加在最右侧。

### 3.3 题型载荷约定（`payload` / `answer`）

| 题型 | `payload` | `answer` | `response`（用户提交） |
|---|---|---|---|
| 单选 | `{options:[{key:"A",text:"..."}], shuffle:false}` | `{correct:"B"}` | `{choice:"B"}` |
| 多选 | `{options:[{key:"A",text:"..."}], min_select:2}` | `{correct:["A","C"]}` | `{choices:["A","C"]}` |
| 填空 | `{blanks:[{id:1,hint:"",placeholder:""}]}` | `{blanks:[{id:1, accepted:["...","..."], regex:null, case_sensitive:false, numeric_tolerance:0.001}]}` | `{blanks:{1:"..."}}` |
| 代码 | `{language:"python", template:"", testcases:[{input,expected,hidden:false}]}` | `{reference_code:"", complexity:"O(n)"}` | `{code:"...", language:"python"}` |
| 简答 | `{word_limit:[100,500], hints:[]}` | `{reference:"...", keywords:[{word,weight}], rubric:[{point,score}]}` | `{text:"..."}` |

---

## 4. 后端核心 API（`/api/v1`）

统一响应：`{ code: 0, message: "ok", data: ... }`；分页：`{ items: [...], total, page, page_size }`。

### 4.1 题库

| Method | Path | 说明 |
|---|---|---|
| GET | `/questions` | 分页列表。查询参数：`keyword`(编号/题干模糊)、`code`、`type[]`、`category_id`(含子分类)、`tag_ids[]`、`difficulty[]`、`status`、`order_by`(created_at/difficulty/code)、`page`、`page_size` |
| GET | `/questions/{id}` | 详情（含 tags、stat） |
| POST | `/questions` | 新建，服务端生成 `code` |
| PATCH | `/questions/{id}` | 局部更新（改 `answer/payload` 时 `version+1`） |
| DELETE | `/questions/{id}` | 软删（`status=archived`） |
| DELETE | `/questions/{id}/hard` | 物理删除（需确认，级联 attempt） |
| POST | `/questions/batch` | 批量：`{"action":"delete\|set_category\|add_tags\|set_difficulty","ids":[...],"payload":{}}` |
| GET | `/questions/export` | 按当前筛选导出，返回 JSON 文件；`?format=json\|csv\|xlsx` |
| POST | `/questions/import` | 上传文件/JSON，返回 `{total, created, updated, skipped, errors:[{row,reason}]}`；支持 `conflict=skip\|overwrite` |
| GET | `/questions/template` | 下载导入模板（CSV/XLSX） |

### 4.2 分类与标签

`GET/POST/PATCH/DELETE /categories`、`GET/POST/DELETE /tags`（标准 CRUD，略）。

### 4.3 练习会话（★ 核心状态机）

| Method | Path | 说明 |
|---|---|---|
| POST | `/sessions` | 组卷。body：`{mode, title, filter:{category_ids,tag_ids,types,difficulties,only_mistakes}, count, order:"random\|seq\|difficulty_asc", duration_limit_sec, mistake_ids?}` → 返回会话 + 题目快照 |
| GET | `/sessions/{id}` | **恢复会话**：返回 status、elapsed_sec、items 及每题已存 `response`/`flagged`/`spent_sec` |
| POST | `/sessions/{id}/start` | 首次进入，置 `active`，写 `started_at` |
| PATCH | `/sessions/{id}/heartbeat` | 每 15s：`{elapsed_sec, items_delta:[{item_id, response, spent_sec, flagged}]}`。**仅增量**，幂等 |
| PATCH | `/sessions/{id}/status` | `{status:"paused"\|"active", elapsed_sec}` —— 退出/切后台/手动暂停 |
| POST | `/sessions/{id}/items/{item_id}/answer` | 单题交卷并即时判分（练习模式），返回 `JudgeResult` |
| POST | `/sessions/{id}/items/{item_id}/flag` | 切换待定标记 |
| POST | `/sessions/{id}/submit` | 提交：服务端对全部 items 做**权威判分** → 写 attempt → 更新 session 成绩 → 更新 question_stat → 写/清 mistake |
| GET | `/sessions` | 历史记录：`{page, mode, from, to}` → 时间、题数、正确率、用时 |
| GET | `/sessions/{id}/report` | 成绩报告：逐题（你的答案、正确答案、解析、判分明细、用时） |
| DELETE | `/sessions/{id}` | 放弃/删除会话 |

### 4.4 判分

| Method | Path | 说明 |
|---|---|---|
| POST | `/judge/preview` | `{question_id, response}` → 客观题即时判分并返回结果（**不写库**，供练习模式"做一题判一题"） |
| POST | `/judge/essay/self` | 简答自评：`{question_id, response, level:"mastered\|fuzzy\|unknown"}` → 记录但不算分 |

### 4.5 错题本

| Method | Path | 说明 |
|---|---|---|
| GET | `/mistakes` | 列表：`{mastered, removed, category_id, tag_ids[], sort:"last_wrong_at\|wrong_count"}` |
| PATCH | `/mistakes/{id}` | 编辑笔记 / 恢复 / 标记掌握 |
| DELETE | `/mistakes/{id}` | 移出错题本（`removed=true`） |
| POST | `/mistakes/redo` | `{ids? , count}` → 直接创建 `mode=mistake` 的新会话 |

### 4.6 统计

`GET /stats/overview` → `{total_questions, total_sessions, avg_accuracy, total_duration_sec, streak_days, daily:[{date,count,accuracy}], type_distribution, weakness_tags[]}`。

---

## 5. 前端关键页面与状态管理

### 5.1 页面清单

| 路由 | 页面 | 关键交互 |
|---|---|---|
| `/` | Dashboard | 今日/连续天数/正确率趋势、快捷组卷、继续上次未完成的会话 |
| `/bank` | QuestionList | 左侧分类树 + 顶部多维筛选 + 表格（编号/题型/难度/标签/统计）+ 批量操作条 |
| `/bank/new`、`/bank/:id/edit` | QuestionEditor | 左侧「题干+解析」公共区，右侧按题型动态挂载表单；Markdown 实时预览 |
| `/bank/import` | ImportExport | 拖拽上传 → 解析预览表（错误行高亮）→ 冲突策略 → 导入报告 |
| `/practice/setup` | Setup | 范围/题型/难度/数量/顺序/限时，保存为常用方案 |
| `/practice/:id` | **Session** | 题号宫格导航、计时器、标记待定、暂停、自动保存、续答 |
| `/practice/:id/report` | Report | 总分/正确率/用时 + 逐题解析 + 「加入错题本」「再来一组」 |
| `/records`、`/records/:id` | History | 列表 + 详情 |
| `/mistakes` | MistakeList | 错题卡片/表格、笔记、重做、移除 |

### 5.2 `practiceStore`（核心）

```ts
// src/stores/practiceStore.ts
interface SessionItem {
  itemId: number;
  seq: number;
  questionId: number;
  type: QuestionType;
  stem: string;
  payload: unknown;
  analysis?: string;
  difficulty: number;
}

interface PracticeState {
  sessionId: number | null;
  status: 'idle' | 'active' | 'paused' | 'submitted';
  items: SessionItem[];
  currentIndex: number;
  responses:  Record<number, unknown>;   // itemId -> response
  flags:      Record<number, boolean>;   // itemId -> 待定
  spentMs:    Record<number, number>;    // 每题累计停留
  elapsedMs:  number;                    // 总用时（仅 active 时累加）
  dirtyItems: Set<number>;               // 待同步到服务端
  lastSyncedAt: number | null;

  // actions
  hydrate(session: SessionDetailDTO): void;   // GET /sessions/{id} 恢复
  setResponse(itemId: number, resp: unknown): void;
  toggleFlag(itemId: number): void;
  goto(index: number): void;
  tick(deltaMs: number): void;
  pause(): void;  resume(): void;
  flush(): Promise<void>;                      // 增量上报 heartbeat
}
```

要点：

1. **Zustand + `persist`**：把 `responses/flags/spentMs/elapsedMs` 镜像到 `localStorage`（key = `practice:${sessionId}`）。即使刷新/断网，进入页面先本地恢复、再与服务端合并（服务端 `updated_at` 更新者胜）。
2. **计时器**采用"增量累加"而非 `setInterval` 自增：
   ```ts
   let last = performance.now();
   const loop = () => {
     const now = performance.now();
     if (get().status === 'active') get().tick(now - last);
     last = now;
     raf = requestAnimationFrame(loop);
   };
   ```
   切后台时浏览器会降频，因此**权威值以服务端 `elapsed_sec` 为准**，`usePauseOnLeave` 在 `visibilitychange/pagehide` 时立即 `pause()` 并 `flush()`，`resume` 时重新对时。
3. **自动保存**：`setResponse` 打标 dirty → `useAutoSave` 800ms 防抖调用 `PATCH /sessions/{id}/heartbeat`（只带 dirty 项）→ 成功后清 dirty。另外每 15s 定期 flush、以及在 `pagehide` 用 `navigator.sendBeacon` 兜底。
4. **暂停语义**：不是"关掉计时"，而是把会话推入 `paused` 并落库。下次从 Dashboard「继续上次」→ `GET /sessions/{id}` 全量恢复（题序、已答、待定、用时）。
5. **题号宫格**：由 `items + responses + flags` 派生，四态色块（已答=主色实心 / 待定=橙边框 / 当前=高亮环 / 未答=灰）。支持键盘：`←/→` 切题、`1~4` 选选项、`F` 标记、`Ctrl+Enter` 提交。
6. **提交拦截**：`SubmitConfirmModal` 列出未答/待定题号，一键跳转，避免误交。

### 5.3 表单与录入

`QuestionEditor` 通过 `question/registry.ts` 查表渲染：

```ts
export const QUESTION_REGISTRY: Record<QuestionType, {
  label: string; icon: ReactNode;
  Renderer: React.FC<{ payload: any; value: any; onChange: (v:any)=>void; mode:'answer'|'review'; disabled?: boolean }>;
  Editor:  React.FC<{ value: any; onChange: (v:any)=>void }>;
  emptyPayload: () => any;
  emptyAnswer:  () => any;
}> = { /* single_choice, multiple_choice, fill_blank, coding, essay */ };
```

新增题型 = 往这张表加一项 + 后端加一个 `question_types/defs/*.py`，两端都不改主流程。

---

## 6. 判题逻辑

### 6.1 判分抽象

```python
# app/judging/base.py
@dataclass
class JudgeResult:
    is_correct: bool | None      # 主观题为 None
    score: float                 # 实得分
    max_score: float             # 满分（= score_weight）
    detail: dict                 # 逐空/逐用例明细
    feedback: str | None         # 提示语
    need_manual: bool = False    # 需人工/自评

class JudgeStrategy(Protocol):
    type: str
    def judge(self, *, payload: dict, answer: dict, config: dict,
              response: dict, max_score: float) -> JudgeResult: ...
```

```python
# app/judging/registry.py
_STRATEGIES: dict[str, JudgeStrategy] = {}
def register(s): _STRATEGIES[s.type] = s
def get_strategy(t: str) -> JudgeStrategy:
    if t not in _STRATEGIES: raise UnsupportedQuestionType(t)
    return _STRATEGIES[t]
```

**判分时机**：
- 练习模式：客户端提交单题 → `POST /judge/preview` 即时出对错（不写库）→ 会话提交时服务端全量**权威复核**并落 attempt。
- 考试模式：全程不判，提交后统一判。
- 即使用户在前端改了 JS，最终成绩以服务端判定为准。

### 6.2 文本归一化（填空/简答共用）

```python
# app/judging/normalizer.py
import re, unicodedata
_PUNCT = re.compile(r"[\s，。、；：？！,.;:?!\"'`~()（）\[\]【】{}<>_—\-]+")

def normalize(text: str, *, case_sensitive=False, ignore_punct=True) -> str:
    s = unicodedata.normalize("NFKC", text or "")   # 全角→半角、㍿ 等兼容字符展开
    s = s.replace("\u00a0", " ")
    if not case_sensitive: s = s.casefold()
    if ignore_punct:       s = _PUNCT.sub("", s)
    else:                  s = re.sub(r"\s+", " ", s).strip()
    return s

def numeric_equal(a: str, b: str, tol: float = 1e-6) -> bool:
    try: return abs(float(a) - float(b)) <= tol
    except ValueError: return False
```
另配 `alias.json` 做同义映射（`TCP/IP` → `tcpip`、`O(nlogn)` → `O(n log n)` 等），按题目 `judge_config.aliases` 追加。

### 6.3 各题型策略

**单选（single_choice）**
```python
correct = answer["correct"]
got = response.get("choice")
ok = normalize(got) == normalize(correct)
score = max_score if ok else 0.0
```

**多选（multiple_choice）**
```python
correct, got = set(answer["correct"]), set(response.get("choices") or [])
partial  = bool(config.get("partial_credit", True))
ratio    = float(config.get("partial_ratio", 0.5))
missing  = correct - got
extra    = got - correct

if not extra and not missing:                 # 全对
    score = max_score
elif extra and not config.get("allow_extra"): # 有错选 → 0 分
    score = 0.0
elif partial and correct:                     # 只漏选：按比例给分
    score = max_score * ratio * (len(correct & got) / len(correct))
else:
    score = 0.0
is_correct = (score >= max_score)
detail = {"missing": sorted(missing), "extra": sorted(extra), "rule": "partial" if partial else "all_or_nothing"}
```

**填空（fill_blank）**：逐空独立判分，分值 = `max_score / 空数`；`judge_config.ordered=False` 时支持"乱序匹配"（把用户答案与标准空做二分图最大匹配，避免"空 1 填到空 2"误判）。
```python
def match_blank(spec, user_text):
    if spec.get("regex"):
        return bool(re.fullmatch(spec["regex"], user_text.strip(), re.I if not spec.get("case_sensitive") else 0))
    for cand in spec["accepted"]:
        if spec.get("numeric_tolerance") and numeric_equal(user_text, cand, spec["numeric_tolerance"]):
            return True
        if normalize(user_text, case_sensitive=spec.get("case_sensitive", False)) == \
           normalize(cand,     case_sensitive=spec.get("case_sensitive", False)):
            return True
    return False
```

**代码（coding）**：
```python
async def judge(self, *, payload, answer, config, response, max_score):
    if not config.get("sandbox", False) or not settings.SANDBOX_ENABLED:
        return JudgeResult(None, 0.0, max_score,
                           {"mode": "manual"},
                           "沙箱未启用，请对照参考实现与复杂度自评", need_manual=True)
    cases = [c for c in payload.get("testcases", [])]
    res = await sandbox.run(
        code=response["code"], language=response.get("language", payload["language"]),
        cases=cases, timeout_ms=config.get("timeout_ms", 2000),
        memory_mb=config.get("memory_mb", 128), network=False)
    passed = sum(1 for r in res if r.passed)
    score = max_score * (passed / len(cases)) if cases else 0.0
    return JudgeResult(passed == len(cases), score, max_score,
                       {"mode": "sandbox", "cases": [asdict(r) for r in res if not r.hidden_visible]})
```
沙箱约束：一次性容器 `--network=none --pids-limit 64 --memory 128m --cpus 0.5`，挂载只读目录，`run` 结束后强制 kill + 删除；超时/超内存/OOM 记为该用例失败并回传 stderr（截断 2KB）。可见用例直接展示 diff，隐藏用例只回传通过与否。

**简答（essay）**：默认**不自动给分**，走"参考解析 + 自评"三段式：
```python
kw_hit, kw_total = 0.0, 0.0
for k in answer.get("keywords", []):
    kw_total += (w := k.get("weight", 1))
    if normalize(k["word"]) in normalize(response.get("text", "")): kw_hit += w
coverage = kw_hit / kw_total if kw_total else 0.0
sim = cosine_tfidf(response.get("text",""), answer.get("reference",""))   # 0..1
ref_score = max_score * (0.6 * coverage + 0.4 * sim)        # 仅作"参考分"
return JudgeResult(None, round(ref_score,2), max_score,
                   {"coverage": coverage, "similarity": sim,
                    "reference": answer.get("reference"), "rubric": answer.get("rubric")},
                   need_manual=True)
```
前端呈现：参考答案 + 评分要点 rubric + 关键词命中高亮 + 三档自评按钮（已掌握/模糊/不会）。自评"不会"直接写入错题本；`config.mode="llm"` 时可接大模型按 rubric 打分（结果标注为 AI 参考分，仍不覆盖自评结论）。

### 6.4 判分后的副作用（提交时统一执行）

```python
with db.begin():
    for item in session.items:
        r = get_strategy(q.type).judge(...)
        db.add(Attempt(...))
        item.score, item.is_correct = r.score, r.is_correct
        stat.attempt_count += 1
        if r.is_correct is False:
            stat.wrong_count += 1; stat.streak = 0
            upsert_mistake(question_id)            # 错题入本/累加
        elif r.is_correct is True:
            stat.streak += 1
            if stat.streak >= settings.CLEAR_STREAK:   # 默认 2
                clear_or_master(question_id)           # 从错题本清除
    session.score = sum(i.score for i in items)
    session.accuracy = correct_count / total * 100
    session.status = "submitted"
```

---

## 7. 导入导出格式

```json
{
  "version": 1,
  "exported_at": "2026-09-06T20:00:00+08:00",
  "questions": [
    {
      "code": "Q-2026-000123",
      "type": "single_choice",
      "stem": "下列关于 B+ 树的说法，**错误**的是：",
      "analysis": "B+ 树的非叶子节点只存索引，不存数据……",
      "difficulty": 3,
      "category": "数据库/索引",
      "tags": ["B+树", "MySQL"],
      "payload": { "options": [{"key":"A","text":"..."}] },
      "answer":  { "correct": "D" },
      "judge_config": {}
    }
  ]
}
```
- CSV/XLSX 为扁平化模板：一行一题，选项列 `A/B/C/D`，多选答案用 `|` 分隔，填空用 `||` 分隔多空；导出时反向展开。
- 导入三步：解析 → **逐行校验**（题型 schema 校验、答案必须在选项内、编号冲突）→ 预览表（错误行红标 + 原因）→ 确认后按 `conflict` 策略写入。
- 编号冲突：文件内带 `code` 则尝试更新，重复/不存在则按 `skip|overwrite|rename` 处理。

---

## 8. 关键交互细节约定

| 场景 | 处理 |
|---|---|
| 退出/切后台 | `visibilitychange`(hidden) 与 `pagehide` → `pause()` + 立即 flush；`sendBeacon` 兜底 |
| 恢复 | `GET /sessions/{id}` 返回全量；本地 localStorage 与服务端按时间戳合并 |
| 服务端兜底 | 心跳超时 5 分钟未活跃 → 定时任务把 `active` 会话置 `paused`（防止浏览器崩溃后计时虚高） |
| 限时模式 | 倒计时归零 → 前端自动 `submit`；服务端校验 `elapsed_sec <= duration_limit_sec + 30` 宽容窗口 |
| 题号导航 | 宫格 + 键盘；当前题高亮，待定题橙色边框，未答灰色 |
| 答题数据一致性 | 所有判分以服务端为准；前端 preview 仅作即时反馈 |
| 安全 | 代码题沙箱默认关闭；开启需显式配置且仅限本机可信输入 |

---

## 9. 实施里程碑

| 阶段 | 内容 | 产出 |
|---|---|---|
| M1 骨架 | 后端工程 + Alembic + 全部表 + 题目 CRUD + 分类标签 | OpenAPI 可调通 |
| M2 录入 | 前端脚手架 + AntD 主题 + 题库列表/编辑器（5 种题型）+ 导入导出 | 能录入并管理题库 |
| M3 判分 | 判分策略层 + 归一化 + 单测（覆盖边界：全角、大小写、漏选、乱序填空） | 客观题判分可靠 |
| M4 练习 | 组卷 + 答题页（导航/计时/标记/暂停/续答）+ 报告页 | 完整练习闭环 |
| M5 沉淀 | 错题本 + 学习记录 + Dashboard 统计 + 代码题沙箱（可选） | 闭环成型 |

---

## 10. 扩展新题型的标准动作（示例：加"判断题"）

1. 后端新建 `app/question_types/defs/true_false.py`：`payload/answer` Pydantic 模型 + `judge()` 策略 + `@register`。
2. `enums.QuestionType` 加枚举，`registry` 自动装载。
3. 前端 `components/question/registry.ts` 加 `true_false: { Renderer, Editor, ... }`。
4. `types/question.ts` 联合类型加分支。
主流程（列表、筛选、会话、判分调度、导入导出）**零改动**。
