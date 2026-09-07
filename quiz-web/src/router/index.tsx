import { Navigate, Route, Routes } from "react-router-dom";
import { lazy, Suspense } from "react";
import { Spin } from "antd";

const Dashboard = lazy(() => import("../pages/Dashboard/Index"));
const QuestionList = lazy(() => import("../pages/Bank/QuestionList"));
const QuestionEditor = lazy(() => import("../pages/Bank/QuestionEditor"));
const ImportExport = lazy(() => import("../pages/Bank/ImportExport"));
const Settings = lazy(() => import("../pages/Settings/Index"));
const Practice = lazy(() => import("../pages/Practice/Index"));
const Mistakes = lazy(() => import("../pages/Mistakes/Index"));
const Stats = lazy(() => import("../pages/Stats/Index"));

function fallback() {
  return (
    <div style={{ display: "grid", placeItems: "center", padding: 80 }}>
      <Spin />
    </div>
  );
}

export function AppRoutes() {
  return (
    <Suspense fallback={fallback()}>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/bank" element={<QuestionList />} />
        <Route path="/bank/new" element={<QuestionEditor />} />
        <Route path="/bank/:id/edit" element={<QuestionEditor />} />
        <Route path="/bank/import" element={<ImportExport />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="/practice" element={<Practice />} />
        <Route path="/mistakes" element={<Mistakes />} />
        <Route path="/stats" element={<Stats />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Suspense>
  );
}
