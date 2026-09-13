"use client";

import AuthGuard from "@/components/auth/AuthGuard";

export default function PredictionsPage() {
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
          会社側・参考予測
        </div>

        <h1>予測</h1>

        <p style={{ color: "#8fa6bf", lineHeight: 1.7 }}>
          勤怠実績と確定シフトをもとに、月末の残業時間の着地を参考予測します。
        </p>

        <p style={{ color: "#fbbf24" }}>
          予測値は参考情報です。給与計算・給与確定には使用しません。
        </p>
      </main>
    </AuthGuard>
  );
}
