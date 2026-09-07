import { useEffect, useState } from "react";
import { Layout, Menu, Space, Switch, Typography, Button, Drawer } from "antd";
import { useLocation, useNavigate } from "react-router-dom";
import type { ReactNode } from "react";
import {
  BookOutlined,
  ImportOutlined,
  MenuOutlined,
  MoonOutlined,
  PlusOutlined,
  DashboardOutlined,
  SettingOutlined,
  SunOutlined,
  PlayCircleOutlined,
  AlertOutlined,
  BarChartOutlined,
} from "@ant-design/icons";

import { useUiStore } from "../../stores/uiStore";

const { Sider, Header, Content } = Layout;

const MOBILE_QUERY = "(max-width: 767px)";

const items = [
  { key: "/", icon: <DashboardOutlined />, label: "仪表盘" },
  { key: "/practice", icon: <PlayCircleOutlined />, label: "练习" },
  { key: "/mistakes", icon: <AlertOutlined />, label: "错题本" },
  { key: "/stats", icon: <BarChartOutlined />, label: "统计" },
  { key: "/bank", icon: <BookOutlined />, label: "题库" },
  { key: "/bank/new", icon: <PlusOutlined />, label: "录题" },
  { key: "/bank/import", icon: <ImportOutlined />, label: "导入导出" },
  { key: "/settings", icon: <SettingOutlined />, label: "题库设置" },
];

export function AppLayout({ children }: { children: ReactNode }) {
  const navigate = useNavigate();
  const loc = useLocation();
  const theme = useUiStore((s) => s.theme);
  const toggleTheme = useUiStore((s) => s.toggleTheme);

  // 响应式：窄屏隐藏侧栏，改用顶部汉堡 + 抽屉导航
  const [mobile, setMobile] = useState(
    () => typeof window !== "undefined" && window.matchMedia(MOBILE_QUERY).matches,
  );
  const [drawerOpen, setDrawerOpen] = useState(false);

  useEffect(() => {
    const mq = window.matchMedia(MOBILE_QUERY);
    const handler = (e: MediaQueryListEvent) => setMobile(e.matches);
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, []);

  const selected =
    items
      .map((i) => i.key)
      .filter((k) => k !== "/" && loc.pathname.startsWith(k))
      .sort((a, b) => b.length - a.length)[0] ?? "/";

  const go = (key: string) => {
    navigate(key);
    setDrawerOpen(false);
  };

  const menu = (
    <Menu
      mode="inline"
      selectedKeys={[selected]}
      items={items}
      onClick={({ key }) => go(key)}
      style={{ borderInlineEnd: "none" }}
    />
  );

  return (
    <Layout style={{ minHeight: "100dvh" }}>
      {!mobile && (
        <Sider width={200} theme="light" style={{ borderRight: "1px solid var(--border)" }}>
          <div style={{ height: 56, display: "flex", alignItems: "center", paddingLeft: 20 }}>
            <Typography.Text strong style={{ fontSize: 16 }}>
              答题练习
            </Typography.Text>
          </div>
          {menu}
        </Sider>
      )}

      <Layout>
        <Header
          style={{
            borderBottom: "1px solid var(--border)",
            paddingInline: mobile ? 12 : 24,
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            gap: 8,
          }}
        >
          <Space size={8}>
            {mobile && (
              <Button
                type="text"
                aria-label="打开导航菜单"
                icon={<MenuOutlined />}
                onClick={() => setDrawerOpen(true)}
              />
            )}
            {mobile && (
              <Typography.Text strong style={{ fontSize: 16 }}>
                答题练习
              </Typography.Text>
            )}
            {!mobile && (
              <Typography.Text type="secondary">个人在线答题练习 · MVP</Typography.Text>
            )}
          </Space>

          <Space size={8}>
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>
              {theme === "dark" ? "暗夜" : "日间"}
            </Typography.Text>
            <Switch
              checked={theme === "dark"}
              onChange={toggleTheme}
              checkedChildren={<MoonOutlined />}
              unCheckedChildren={<SunOutlined />}
            />
          </Space>
        </Header>

        <Content>
          <div className="page">{children}</div>
        </Content>
      </Layout>

      <Drawer
        title="答题练习"
        placement="left"
        width={240}
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        styles={{ body: { padding: 0 } }}
        closable
      >
        {menu}
      </Drawer>
    </Layout>
  );
}
