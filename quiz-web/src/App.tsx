import { useEffect } from "react";
import { ConfigProvider, App as AntApp } from "antd";
import zhCN from "antd/locale/zh_CN";

import { AppLayout } from "./components/layout/AppLayout";
import { AppRoutes } from "./router";
import { useUiStore } from "./stores/uiStore";
import { getAppTheme } from "./styles/theme";

export default function App() {
  const theme = useUiStore((s) => s.theme);

  // 同步到 <html data-theme>，供 global.css 的 CSS 变量与原生滚动条配色使用
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
  }, [theme]);

  return (
    <ConfigProvider theme={getAppTheme(theme)} locale={zhCN}>
      <AntApp>
        <AppLayout>
          <AppRoutes />
        </AppLayout>
      </AntApp>
    </ConfigProvider>
  );
}
