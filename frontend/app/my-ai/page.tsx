"use client";

import AuthGuard from "@/components/auth/AuthGuard";

export default function MyAiPage() {
  return (
    <AuthGuard allow={["employee"]}>
      <main
        style={{
          maxWidth: 900,
          margin: "0 auto",
          padding: "28px 16px",
        }}
      >
        <div
          style={{
            color: "#a5b4fc",
            fontSize: 12,
            fontWeight: 800,
            letterSpacing: "0.12em",
          }}
        >
          MY LOCAL AI
        </div>

        <h1>自分専用AIアシスタント</h1>

        <p style={{ color: "#9fb1c7", lineHeight: 1.7 }}>
          自分の勤怠・確定済み給与・有給について確認できます。
          AIは読み取り専用です。
        </p>
      </main>
    </AuthGuard>
  );
}
