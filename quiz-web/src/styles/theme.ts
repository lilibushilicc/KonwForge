import { theme as antdTheme, type ThemeConfig } from "antd";

import type { ThemeMode } from "../stores/uiStore";

// 高级简约：低饱和主色 + 8px 圆角 + 克制的边框与分割线，去重阴影
const sharedToken: ThemeConfig["token"] = {
  colorPrimary: "#4A6FA5",
  colorInfo: "#4A6FA5",
  colorSuccess: "#3F8F6B",
  colorWarning: "#C9942B",
  colorError: "#C0563F",
  borderRadius: 8,
  fontSize: 14,
  wireframe: false,
  fontFamily:
    "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif",
};

/** 按模式返回 AntD 主题配置：亮色 = 原视觉；暗色 = darkAlgorithm + 暗面层色。 */
export function getAppTheme(mode: ThemeMode): ThemeConfig {
  if (mode === "dark") {
    return {
      algorithm: antdTheme.darkAlgorithm,
      token: { ...sharedToken, colorBgLayout: "#0F1115" },
      components: {
        Layout: { bodyBg: "#0F1115", siderBg: "#161A22", headerBg: "#161A22" },
        Card: { boxShadow: "0 1px 2px rgba(0,0,0,0.35)" },
        Table: { headerBg: "#1A1F28", rowHoverBg: "#20242C" },
        Menu: { itemSelectedBg: "#22303F", itemSelectedColor: "#7FA3D4" },
      },
    };
  }
  return {
    algorithm: antdTheme.defaultAlgorithm,
    token: { ...sharedToken, colorBgLayout: "#F7F8FA" },
    components: {
      Layout: { bodyBg: "#F7F8FA", siderBg: "#FFFFFF", headerBg: "#FFFFFF" },
      Card: { boxShadow: "0 1px 2px rgba(0,0,0,0.04)" },
      Table: { headerBg: "#FAFBFC", rowHoverBg: "#F4F7FB" },
      Menu: { itemSelectedBg: "#EEF3F9", itemSelectedColor: "#4A6FA5" },
    },
  };
}
