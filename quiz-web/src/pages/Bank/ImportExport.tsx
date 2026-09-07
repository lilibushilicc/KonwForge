import { useState } from "react";
import {
  Alert,
  Button,
  Card,
  Collapse,
  Input,
  Modal,
  Radio,
  Space,
  Typography,
  Upload,
  App,
} from "antd";
import {
  DownloadOutlined,
  ImportOutlined,
  InboxOutlined,
  QuestionCircleOutlined,
} from "@ant-design/icons";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import { PageHeader } from "../../components/common/PageHeader";
import { questionsApi } from "../../api/questions";

const { TextArea } = Input;
const { Dragger } = Upload;

type Conflict = "skip" | "overwrite" | "rename";

function download(filename: string, content: string, mime: string) {
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function F({ name, desc, ex }: { name: string; desc: string; ex?: string }) {
  return (
    <div style={{ marginBottom: 6 }}>
      <Typography.Text code>{name}</Typography.Text>
      <span> — {desc}</span>
      {ex ? (
        <>
          <br />
          <Typography.Text type="secondary" style={{ fontFamily: "monospace", fontSize: 12 }}>
            {ex}
          </Typography.Text>
        </>
      ) : null}
    </div>
  );
}

export default function ImportExport() {
  const { message } = App.useApp();
  const qc = useQueryClient();
  const [text, setText] = useState("");
  const [conflict, setConflict] = useState<Conflict>("skip");
  const [helpOpen, setHelpOpen] = useState(false);

  const exportMut = useMutation({
    mutationFn: () => questionsApi.exportJsonData(),
    onSuccess: (data) => {
      download("questions.json", JSON.stringify(data, null, 2), "application/json");
      message.success(`已导出 ${(data as any[]).length} 题`);
    },
    onError: (e: any) => message.error(e?.message ?? "导出失败"),
  });

  const importMut = useMutation({
    mutationFn: (items: unknown[]) => questionsApi.importJson(items, conflict),
    onSuccess: (res: any) => {
      message.success(`导入完成：新增 ${res.created} · 更新 ${res.updated} · 跳过 ${res.skipped}`);
      if (res.errors?.length) {
        message.warning(`${res.errors.length} 条解析失败已忽略`);
      }
      setText("");
      qc.invalidateQueries({ queryKey: ["questions"] });
    },
    onError: (e: any) => message.error(e?.message ?? "导入失败"),
  });

  const onImport = () => {
    let parsed: unknown;
    try {
      parsed = JSON.parse(text);
    } catch {
      message.error("JSON 解析失败，请检查格式");
      return;
    }
    const items = Array.isArray(parsed)
      ? parsed
      : parsed && Array.isArray((parsed as any).questions)
        ? (parsed as any).questions
        : null;
    if (!items) {
      message.error("根节点需为题目数组 [ ... ] 或 { questions: [ ... ] }");
      return;
    }
    importMut.mutate(items);
  };

  const onFile = (file: File) => {
    const reader = new FileReader();
    reader.onload = () => setText(String(reader.result ?? ""));
    reader.onerror = () => message.error("文件读取失败");
    reader.readAsText(file);
    return false; // 阻止自动上传
  };

  return (
    <>
      <PageHeader title="导入 / 导出" sub="题库批量迁移：JSON 数组格式" />

      <Space direction="vertical" size={16} style={{ width: "100%" }}>
        <Card
          size="small"
          title={
            <>
              <DownloadOutlined /> 导出
            </>
          }
        >
          <Space direction="vertical" style={{ width: "100%" }}>
            <Typography.Text type="secondary">
              导出当前题库全部有效题目。JSON 走 API 拉取（已解信封），CSV 走直链下载。
            </Typography.Text>
            <Space>
              <Button
                type="primary"
                icon={<DownloadOutlined />}
                loading={exportMut.isPending}
                onClick={() => exportMut.mutate()}
              >
                导出 JSON
              </Button>
              <Button icon={<DownloadOutlined />} href={questionsApi.exportUrl("csv")} download>
                导出 CSV
              </Button>
            </Space>
          </Space>
        </Card>

        <Card
          size="small"
          title={
            <Space size={4}>
              <ImportOutlined />
              <span>导入</span>
              <Button
                type="text"
                size="small"
                icon={<QuestionCircleOutlined />}
                aria-label="导入详细说明"
                onClick={() => setHelpOpen(true)}
              />
            </Space>
          }
        >
          <Space direction="vertical" size={12} style={{ width: "100%" }}>
            <Alert
              type="info"
              showIcon
              message="每条题目需包含 type / stem / difficulty / payload / answer 字段；code 可省略（服务端自动生成）"
            />

            <Space wrap>
              <Button icon={<DownloadOutlined />} href="/import-example.json" download>
                下载完整示例 (JSON)
              </Button>
              <Button icon={<DownloadOutlined />} href="/import-syntax.md" download>
                下载格式语法 (MD)
              </Button>
              <Typography.Text type="secondary">
                把示例交给 Agent，附上知识点即可批量生成题目
              </Typography.Text>
            </Space>

            <Dragger
              accept=".json,.txt"
              maxCount={1}
              showUploadList={false}
              beforeUpload={(f) => onFile(f as unknown as File)}
            >
              <p className="ant-upload-drag-icon">
                <InboxOutlined />
              </p>
              <p className="ant-upload-text">点击或拖拽 JSON 文件到此处</p>
              <p className="ant-upload-hint">仅读取到下方文本框，不会自动上传</p>
            </Dragger>

            <div>
              <Typography.Text type="secondary">JSON 内容</Typography.Text>
              <TextArea
                value={text}
                onChange={(e) => setText(e.target.value)}
                autoSize={{ minRows: 8 }}
                placeholder='[ { "type": "single_choice", "stem": "...", "difficulty": 3, "payload": {...}, "answer": {...} } ]'
                style={{ fontFamily: "monospace" }}
              />
            </div>

            <Space>
              <Typography.Text>冲突策略：</Typography.Text>
              <Radio.Group
                value={conflict}
                onChange={(e) => setConflict(e.target.value)}
                optionType="button"
                buttonStyle="solid"
              >
                <Radio.Button value="skip">跳过</Radio.Button>
                <Radio.Button value="overwrite">覆盖</Radio.Button>
                <Radio.Button value="rename">改名新建</Radio.Button>
              </Radio.Group>
            </Space>

            <Space>
              <Button
                type="primary"
                icon={<ImportOutlined />}
                loading={importMut.isPending}
                disabled={!text.trim()}
                onClick={onImport}
              >
                开始导入
              </Button>
              <Button onClick={() => setText("")} disabled={!text}>
                清空
              </Button>
            </Space>
          </Space>
        </Card>
      </Space>

      <Modal
        title="导入详细说明"
        open={helpOpen}
        footer={null}
        onCancel={() => setHelpOpen(false)}
        width={620}
      >
        <Typography.Paragraph>
          <Typography.Text strong>支持的文件格式</Typography.Text>
        </Typography.Paragraph>
        <Typography.Paragraph type="secondary" style={{ marginTop: -8 }}>
          · 拖拽或选择 <Typography.Text code>.json</Typography.Text> /{" "}
          <Typography.Text code>.txt</Typography.Text> 文件，也可直接在文本框粘贴 JSON。
          <br /> · 离线转换器与 API 使用{" "}
          <Typography.Text code>{'{"questions": [...]}'}</Typography.Text>{" "}
          包裹；本页面粘贴/拖拽「裸数组」或「包裹格式」均可（自动识别）。
        </Typography.Paragraph>

        <Typography.Paragraph>
          <Typography.Text strong>导入步骤</Typography.Text>
        </Typography.Paragraph>
        <Typography.Paragraph type="secondary" style={{ marginTop: -8 }}>
          1. 准备题目 JSON，每条含{" "}
          <Typography.Text code>type / stem / difficulty / payload / answer</Typography.Text>。
          <br />
          2. 粘贴到文本框，或拖拽文件到上传区（仅读取，不会自动上传）。
          <br />
          3. 选择冲突策略：跳过 / 覆盖 / 改名新建。
          <br />
          4. 点击「开始导入」，等待「新增 / 更新 / 跳过」结果提示。
        </Typography.Paragraph>

        <Typography.Paragraph>
          <Typography.Text strong>通用字段（每条题目顶层）</Typography.Text>
        </Typography.Paragraph>
        <div style={{ marginTop: -8 }}>
          <F
            name="type"
            desc="题型号（必填）：single_choice / multiple_choice / fill_blank / coding / essay"
          />
          <F name="stem" desc="题干文本（必填，非空）" />
          <F name="difficulty" desc="难度 1–5（可选，默认 3）" />
          <F name="category_id" desc="分类 id（可选）" />
          <F name="tags" desc='标签数组，如 ["函数","闭包"]（可选）' />
          <F name="analysis" desc="解析文本（可选）" />
          <F name="source" desc="来源说明（可选，≤128 字）" />
          <F name="payload" desc="呈现数据，随题型不同（见下方分题型）" />
          <F name="answer" desc="标准答案 / 判分依据（见下方分题型）" />
          <F name="judge_config" desc="判分参数（可选，见下方分题型）" />
          <F name="code" desc="题号，可省略，服务端自动生成" />
          <Typography.Paragraph type="secondary" style={{ marginTop: 4 }}>
            查询参数 <Typography.Text code>conflict</Typography.Text> ={" "}
            <Typography.Text code>skip（默认）</Typography.Text> /{" "}
            <Typography.Text code>overwrite</Typography.Text> /{" "}
            <Typography.Text code>rename</Typography.Text>，用于同 code 冲突时策略。
          </Typography.Paragraph>
        </div>

        <Typography.Paragraph>
          <Typography.Text strong>分题型参数明细</Typography.Text>
        </Typography.Paragraph>
        <Collapse
          size="small"
          style={{ marginTop: -8 }}
          items={[
            {
              key: "single",
              label: "single_choice 单选",
              children: (
                <div>
                  <Typography.Text strong>payload</Typography.Text>
                  <F
                    name="options"
                    desc="选项数组 [{ key, text }]"
                    ex='options: [{ "key": "A", "text": "..." }]'
                  />
                  <Typography.Text strong>answer</Typography.Text>
                  <F name="correct" desc="正确选项键" ex='{ "correct": "B" }' />
                  <Typography.Text strong>作答 response</Typography.Text>
                  <F name="choice" desc="所选选项键" ex='{ "choice": "B" }' />
                  <Typography.Text strong>judge_config</Typography.Text>
                  <F name="aliases" desc='同义替换表（可选），如 { "TCP/IP": "tcpip" }' />
                  <Typography.Paragraph type="secondary" style={{ marginTop: 4 }}>
                    判分：response.choice 与 answer.correct 归一化比对（忽略大小写 / 别名）。
                  </Typography.Paragraph>
                </div>
              ),
            },
            {
              key: "multiple",
              label: "multiple_choice 多选",
              children: (
                <div>
                  <Typography.Text strong>payload</Typography.Text>
                  <F
                    name="options"
                    desc="选项数组 [{ key, text }]"
                    ex='options: [{ "key": "A", "text": "..." }]'
                  />
                  <Typography.Text strong>answer</Typography.Text>
                  <F name="correct" desc="正确选项键数组" ex='{ "correct": ["A", "B"] }' />
                  <Typography.Text strong>作答 response</Typography.Text>
                  <F name="choices" desc="所选选项键数组" ex='{ "choices": ["A", "B"] }' />
                  <Typography.Text strong>judge_config</Typography.Text>
                  <F name="partial_credit" desc="是否部分给分（默认 true）" />
                  <F name="partial_ratio" desc="漏选得分比例（默认 0.5）" />
                  <F name="allow_extra" desc="是否允许错选仍给分（默认 false）" />
                  <F name="aliases" desc="同义替换表（可选）" />
                  <Typography.Paragraph type="secondary" style={{ marginTop: 4 }}>
                    判分：全对满分；漏选且 partial_credit → 得 partial_ratio 比例；错选且
                    allow_extra=false → 0 分。
                  </Typography.Paragraph>
                </div>
              ),
            },
            {
              key: "fill",
              label: "fill_blank 填空",
              children: (
                <div>
                  <Typography.Text strong>payload</Typography.Text>
                  <F
                    name="blanks"
                    desc="空位定义数组 [{ id, hint, placeholder }]"
                    ex='blanks: [{ "id": 1, "hint": "协议名", "placeholder": "" }]'
                  />
                  <Typography.Text strong>answer</Typography.Text>
                  <F
                    name="blanks"
                    desc="每个空的判分规格：accepted / regex / case_sensitive / numeric_tolerance"
                    ex='blanks: [{ "id": 1, "accepted": ["tcp","TCP"], "regex": null, "case_sensitive": false, "numeric_tolerance": 0.001 }]'
                  />
                  <Typography.Text strong>作答 response</Typography.Text>
                  <F
                    name="blanks"
                    desc="以空 id 为键的用户填写值"
                    ex='{ "blanks": { "1": "tcp", "2": "80" } }'
                  />
                  <Typography.Text strong>judge_config</Typography.Text>
                  <F name="ordered" desc="是否按序匹配（默认 true；false 时乱序二分匹配）" />
                  <F name="aliases" desc="同义替换表（可选）" />
                  <Typography.Paragraph type="secondary" style={{ marginTop: 4 }}>
                    判分：逐空比对，支持多解、正则、数值容差、大小写；ordered=false 支持乱序填答。
                  </Typography.Paragraph>
                </div>
              ),
            },
            {
              key: "coding",
              label: "coding 代码",
              children: (
                <div>
                  <Typography.Text strong>payload</Typography.Text>
                  <F name="language" desc="编程语言（默认 python）" />
                  <F name="template" desc="代码模板（作答区预填）" />
                  <F
                    name="testcases"
                    desc="测试用例 [{ input, expected, hidden }]"
                    ex='testcases: [{ "input": "2", "expected": "4", "hidden": false }]'
                  />
                  <Typography.Text strong>answer</Typography.Text>
                  <F name="reference_code" desc="参考实现代码" />
                  <F name="complexity" desc="时间/空间复杂度说明（如 O(n)）" />
                  <Typography.Text strong>judge_config</Typography.Text>
                  <F name="sandbox" desc="沙箱判分（默认关闭 → need_manual 标记人工判分）" />
                  <Typography.Paragraph type="secondary" style={{ marginTop: 4 }}>
                    判分：沙箱未启用时为人工判分；启用后按 testcases 跑分。
                  </Typography.Paragraph>
                </div>
              ),
            },
            {
              key: "essay",
              label: "essay 简答",
              children: (
                <div>
                  <Typography.Text strong>payload</Typography.Text>
                  <F name="max_chars" desc="作答字数上限（可选）" />
                  <Typography.Text strong>answer</Typography.Text>
                  <F name="reference_answer" desc="参考答案文本" />
                  <F
                    name="keywords"
                    desc="关键词数组，或带权重 [{ word, weight }]"
                    ex='keywords: ["tcp", { "word": "握手", "weight": 2 }]'
                  />
                  <F name="min_chars" desc="最少字数（可选）" />
                  <Typography.Text strong>作答 response</Typography.Text>
                  <F name="text" desc="作答文本" ex='{ "text": "..." }' />
                  <Typography.Text strong>judge_config</Typography.Text>
                  <F name="aliases" desc="同义替换表（可选）" />
                  <Typography.Paragraph type="secondary" style={{ marginTop: 4 }}>
                    判分：默认不自动给分（人工）；启用时为 0.6×关键词覆盖 + 0.4×TF-IDF 相似度。
                  </Typography.Paragraph>
                </div>
              ),
            },
          ]}
        />

        <Typography.Paragraph style={{ marginTop: 12 }}>
          <Typography.Text strong>注意事项</Typography.Text>
        </Typography.Paragraph>
        <Typography.Paragraph type="secondary" style={{ marginTop: -8 }}>
          · <Typography.Text code>code</Typography.Text> 可省略，服务端自动生成。
          <br />· <Typography.Text code>type</Typography.Text> 仅支持上述 5
          种；自定义题型需改后端代码。
          <br />· <Typography.Text code>payload</Typography.Text> /{" "}
          <Typography.Text code>answer</Typography.Text> 需匹配题型结构，否则判分异常。
          <br />· 单条解析失败会被忽略并提示数量，不影响其余题目导入。
        </Typography.Paragraph>
      </Modal>
    </>
  );
}
