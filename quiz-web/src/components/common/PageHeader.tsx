import type { ReactNode } from "react";

export function PageHeader({
  title,
  sub,
  extra,
}: {
  title: string;
  sub?: string;
  extra?: ReactNode;
}) {
  return (
    <div
      className="page-header"
      style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end" }}
    >
      <div>
        <h2>{title}</h2>
        {sub && <div className="sub">{sub}</div>}
      </div>
      {extra}
    </div>
  );
}
