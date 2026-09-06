"use client";

import AuthGuard from "@/components/auth/AuthGuard";

export default function MyPage() {
  return (
    <AuthGuard allow={["employee"]}>
      <main style={{ padding: 24 }}>
        <div
          style={{
            color: "#45e0a8",
            fontSize: 12,
            fontWeight: 800,
          }}
        >
          従業員側
        </div>

        <h1>マイページ</h1>

        <p style={{ color: "#8fa6bf" }}>
          自分の勤怠・シフト・給与明細・有給をここから確認できます。
        </p>
      </main>
    </AuthGuard>
  );
}
