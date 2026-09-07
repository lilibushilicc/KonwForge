import { useQuery } from "@tanstack/react-query";
import { Card, Col, Empty, Row, Statistic, Typography } from "antd";
import {
  BookOutlined,
  BulbOutlined,
  FireOutlined,
  RiseOutlined,
  WarningOutlined,
} from "@ant-design/icons";

import { PageHeader } from "../../components/common/PageHeader";
import { statsApi, type StatsOut } from "../../api/stats";

/** 横向条形（按百分比），暗色友好：用 CSS 变量着色。 */
function Bar({
  label,
  value,
  total,
  suffix = "%",
}: {
  label: string;
  value: number;
  total: number;
  suffix?: string;
}) {
  const pct = total > 0 ? Math.round((value / total) * 100) : 0;
  return (
    <div style={{ marginBottom: 10 }}>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13 }}>
        <span>{label}</span>
        <span style={{ color: "var(--text-secondary)" }}>
          {suffix === "%" ? `${pct}%` : `${value}`}
          {suffix === "%" ? "" : ` / ${total}`}
        </span>
      </div>
      <div style={{ height: 8, background: "var(--bg-soft)", borderRadius: 4, overflow: "hidden" }}>
        <div
          style={{
            width: `${pct}%`,
            height: "100%",
            background: "var(--accent, #4A6FA5)",
            borderRadius: 4,
            transition: "width .3s",
          }}
        />
      </div>
    </div>
  );
}

function DailyChart({ data }: { data: StatsOut["daily"] }) {
  const max = Math.max(1, ...data.map((d) => d.attempts));
  return (
    <div style={{ display: "flex", alignItems: "flex-end", gap: 2, height: 120, paddingTop: 8 }}>
      {data.map((d) => (
        <div
          key={d.date}
          title={`${d.date}：作答 ${d.attempts} / 正确 ${d.correct}`}
          style={{
            flex: 1,
            height: `${(d.attempts / max) * 100}%`,
            background: d.attempts ? "var(--accent, #4A6FA5)" : "var(--bg-soft)",
            borderRadius: "2px 2px 0 0",
            minHeight: d.attempts ? 3 : 2,
          }}
        />
      ))}
    </div>
  );
}

export default function Stats() {
  const { data, isLoading } = useQuery({ queryKey: ["stats"], queryFn: statsApi.summary });

  if (!data && !isLoading) return <Empty style={{ marginTop: 80 }} />;

  const s = data?.summary;
  const cards = [
    { title: "题目总数", value: s?.total_questions ?? 0, icon: <BookOutlined />, color: "#4A6FA5" },
    { title: "总作答数", value: s?.total_attempts ?? 0, icon: <RiseOutlined />, color: "#3F8F6B" },
    { title: "练习会话", value: s?.total_sessions ?? 0, icon: <FireOutlined />, color: "#C97B2B" },
    {
      title: "活跃错题",
      value: s?.active_mistakes ?? 0,
      icon: <WarningOutlined />,
      color: "#C94B4B",
    },
    {
      title: "总正确率",
      value: s?.overall_accuracy ?? 0,
      suffix: "%",
      icon: <BulbOutlined />,
      color: "#7B5BC9",
    },
    { title: "平均掌握度", value: s?.avg_mastery ?? 0, icon: <FireOutlined />, color: "#2B8FC9" },
  ];

  return (
    <>
      <PageHeader title="统计" sub="基于你的练习记录：正确率、掌握度与近期活跃" />

      <Row gutter={[16, 16]}>
        {cards.map((c) => (
          <Col xs={12} sm={8} md={4} key={c.title}>
            <Card>
              <Statistic
                title={c.title}
                value={c.value}
                suffix={"suffix" in c ? (c as any).suffix : undefined}
                prefix={<span style={{ color: c.color }}>{c.icon}</span>}
              />
            </Card>
          </Col>
        ))}
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} lg={12}>
          <Card title="按题型正确率">
            {data?.by_type?.map((t) => (
              <Bar key={t.type} label={t.label} value={t.correct} total={t.attempted} />
            ))}
            {(!data?.by_type || data.by_type.length === 0) && (
              <Typography.Text type="secondary">还没有作答记录</Typography.Text>
            )}
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title="按分类正确率（有作答的）">
            {data?.by_category
              ?.filter((c) => c.attempted > 0)
              .map((c) => (
                <Bar key={c.category_id} label={c.name} value={c.correct} total={c.attempted} />
              ))}
            {(!data?.by_category ||
              data.by_category.filter((c) => c.attempted > 0).length === 0) && (
              <Typography.Text type="secondary">还没有作答记录</Typography.Text>
            )}
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} lg={12}>
          <Card title="掌握度分布">
            <div style={{ display: "flex", gap: 8 }}>
              {data?.mastery?.map((m) => (
                <div key={m.level} style={{ flex: 1, textAlign: "center" }}>
                  <div
                    style={{
                      height: 90,
                      display: "flex",
                      alignItems: "flex-end",
                      justifyContent: "center",
                    }}
                  >
                    <div
                      style={{
                        width: "70%",
                        height: `${Math.max(4, (m.count / Math.max(1, ...(data.mastery?.map((x) => x.count) ?? [1]))) * 100)}%`,
                        background: m.level >= 4 ? "#3F8F6B" : m.level >= 1 ? "#4A6FA5" : "#C94B4B",
                        borderRadius: "4px 4px 0 0",
                      }}
                    />
                  </div>
                  <Typography.Text type="secondary" style={{ fontSize: 12 }}>
                    L{m.level} · {m.count}
                  </Typography.Text>
                </div>
              ))}
            </div>
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title="近 30 天作答活跃度">
            {data?.daily && <DailyChart data={data.daily} />}
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>
              每根柱子代表一天的作答量，越高的日子练得越多。
            </Typography.Text>
          </Card>
        </Col>
      </Row>
    </>
  );
}
