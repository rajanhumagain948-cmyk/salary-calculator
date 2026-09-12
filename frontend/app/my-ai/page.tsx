"use client";

import { useEffect, useState } from "react";
import AuthGuard from "@/components/auth/AuthGuard";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export default function MyAiPage() {
  const [aiStatus, setAiStatus] = useState<{
    model: string;
    local: boolean;
    available: boolean;
  } | null>(null);

  useEffect(() => {
    async function loadAiStatus() {
      try {
        const res = await fetch(`${API_BASE}/my/ai/status`, {
          credentials: "include",
          cache: "no-store",
        });

        if (!res.ok) {
          return;
        }

        setAiStatus(await res.json());
      } catch {
        setAiStatus(null);
      }
    }

    void loadAiStatus();
  }, []);

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

        <div
          style={{
            display: "inline-flex",
            gap: 8,
            marginTop: 8,
            padding: "7px 12px",
            borderRadius: 999,
            background: aiStatus?.available
              ? "rgba(52,211,153,0.11)"
              : "rgba(248,113,113,0.10)",
            color: aiStatus?.available ? "#86efac" : "#fca5a5",
          }}
        >
          {aiStatus === null
            ? "○ AI接続確認中"
            : aiStatus.available
              ? `● 接続済み ${aiStatus.model}`
              : "● AIオフライン"}
        </div>
      </main>
    </AuthGuard>
  );
}
