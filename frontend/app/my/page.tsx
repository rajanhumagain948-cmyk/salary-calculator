"use client";

import AuthGuard from "@/components/auth/AuthGuard";

export default function MyPage() {
  return (
    <AuthGuard allow={["employee"]}>
      <main style={{ padding: 24 }}>
        <div
          style={{
            color: "#45e0a8",
            fontSize: 11,
            fontWeight: 800,
            letterSpacing: ".12em",
          }}
        >
          従業員側
        </div>

        <h1 style={{ margin: "7px 0 5px", fontSize: 30 }}>
          マイページ
        </h1>

        <p style={{ margin: 0, color: "#8298ae", fontSize: 12 }}>
          自分の勤怠・シフト・給与明細・有給をここから確認できます。
        </p>
      </main>
    </AuthGuard>
  );
}
