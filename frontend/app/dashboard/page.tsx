"use client";

import AuthGuard from "@/components/auth/AuthGuard";

export default function DashboardPage() {
  return (
    <AuthGuard allow={["admin"]}>
      <main style={{ padding: 24 }}>
        <div
          style={{
            color: "#8390ff",
            fontSize: 11,
            fontWeight: 800,
            letterSpacing: ".12em",
          }}
        >
          会社側
        </div>

        <h1 style={{ margin: "7px 0 5px", fontSize: 30 }}>
          管理ダッシュボード
        </h1>

        <p style={{ margin: 0, color: "#8298ae", fontSize: 12 }}>
          従業員・勤怠・給与・有給など、会社全体の状況をここから管理します。
        </p>
      </main>
    </AuthGuard>
  );
}
