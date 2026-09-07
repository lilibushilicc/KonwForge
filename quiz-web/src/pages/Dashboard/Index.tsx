import { Button, Card, Col, Row, Space, Statistic, Typography } from "antd";
import {
  BookOutlined,
  FolderOutlined,
  TagsOutlined,
  PlusOutlined,
  ImportOutlined,
  RocketOutlined,
  PlayCircleOutlined,
  AlertOutlined,
  BarChartOutlined,
} from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { PageHeader } from "../../components/common/PageHeader";
import { questionsApi } from "../../api/questions";
import { categoriesApi, tagsApi } from "../../api/categories";
import { statsApi } from "../../api/stats";

export default function Dashboard() {
  const navigate = useNavigate();

  const { data: page } = useQuery({
    queryKey: ["questions", { page: 1, page_size: 1, status: "active" }],
    queryFn: () => questionsApi.list({ page: 1, page_size: 1, status: "active" }),
  });
  const { data: cats = [] } = useQuery({ queryKey: ["categories"], queryFn: categoriesApi.list });
  const { data: tags = [] } = useQuery({ queryKey: ["tags"], queryFn: tagsApi.list });
  const { data: stats } = useQuery({ queryKey: ["stats"], queryFn: statsApi.summary });

  const total = page?.total ?? 0;
  const sum = stats?.summary;

  const statsCards = [
    { title: "题目总数", value: total, icon: <BookOutlined />, color: "#4A6FA5" },
    { title: "分类数", value: cats.length, icon: <FolderOutlined />, color: "#3F8F6B" },
    { title: "标签数", value: tags.length, icon: <TagsOutlined />, color: "#C9942B" },
    {
      title: "活跃错题",
      value: sum?.active_mistakes ?? 0,
      icon: <AlertOutlined />,
      color: "#C94B4B",
    },
    {
      title: "总正确率",
      value: sum?.overall_accuracy ?? 0,
      suffix: "%",
      icon: <BarChartOutlined />,
      color: "#7B5BC9",
    },
    {
      title: "练习会话",
      value: sum?.total_sessions ?? 0,
      icon: <RocketOutlined />,
      color: "#2B8FC9",
    },
  ];

  const actions = [
    {
      key: "practice",
      title: "开始练习",
      desc: "逐题作答 · 即时判分",
      icon: <PlayCircleOutlined />,
      path: "/practice",
    },
    {
      key: "mistakes",
      title: "错题本",
      desc: "重练薄弱点",
      icon: <AlertOutlined />,
      path: "/mistakes",
    },
    {
      key: "stats",
      title: "学习统计",
      desc: "正确率与掌握度",
      icon: <BarChartOutlined />,
      path: "/stats",
    },
    {
      key: "new",
      title: "新建题目",
      desc: "录入单选 / 多选 / 填空 / 代码 / 简答",
      icon: <PlusOutlined />,
      path: "/bank/new",
    },
    {
      key: "bank",
      title: "浏览题库",
      desc: "筛选、检索、批量管理",
      icon: <BookOutlined />,
      path: "/bank",
    },
    {
      key: "import",
      title: "导入导出",
      desc: "JSON / CSV 批量迁移",
      icon: <ImportOutlined />,
      path: "/bank/import",
    },
  ];

  return (
    <>
      <PageHeader title="仪表盘" sub="个人在线答题练习 · 概览" />

      <Row gutter={[16, 16]}>
        {statsCards.map((s) => (
          <Col xs={12} sm={8} md={4} key={s.title}>
            <Card>
              <Statistic
                title={s.title}
                value={s.value}
                suffix={"suffix" in s ? (s as any).suffix : undefined}
                prefix={<span style={{ color: s.color }}>{s.icon}</span>}
              />
            </Card>
          </Col>
        ))}
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        {actions.map((a) => (
          <Col xs={24} sm={8} md={8} key={a.key}>
            <Card hoverable onClick={() => navigate(a.path)} bodyStyle={{ minHeight: 110 }}>
              <Space direction="vertical" size={4}>
                <Typography.Title level={4} style={{ margin: 0 }}>
                  <Space>
                    <span style={{ color: "#4A6FA5" }}>{a.icon}</span>
                    {a.title}
                  </Space>
                </Typography.Title>
                <Typography.Text type="secondary">{a.desc}</Typography.Text>
              </Space>
            </Card>
          </Col>
        ))}
      </Row>

      <div style={{ marginTop: 24, textAlign: "center" }}>
        <Button
          type="primary"
          size="large"
          icon={<PlayCircleOutlined />}
          onClick={() => navigate("/practice")}
        >
          开始练习
        </Button>
      </div>
    </>
  );
}
