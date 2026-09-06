"use client";

import AuthGuard from "@/components/auth/AuthGuard";

export default function DashboardPage() {
  return (
    <AuthGuard allow={["admin"]}>
      <main style={{ padding: 24 }}>
        <div
          style={{
            color: "#8390ff",
            fontSize: 12,
            fontWeight: 800,
          }}
        >
          会社側
        </div>

        <h1>管理ダッシュボード</h1>

        <p style={{ color: "#8fa6bf" }}>
          従業員・勤怠・給与・有給など、会社全体の状況をここから管理します。
        </p>
      </main>
    </AuthGuard>
  );
}
