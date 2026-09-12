"use client";

import { FormEvent, useEffect, useState } from "react";
import AuthGuard from "@/components/auth/AuthGuard";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

function currentYearMonth() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
}

export default function MyAiPage() {
  const [yearMonth, setYearMonth] = useState(currentYearMonth);
  const [message, setMessage] = useState("");
  const [answer, setAnswer] = useState("");
  const [error, setError] = useState("");
  const [sending, setSending] = useState(false);
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

        if (!res.ok) return;
        setAiStatus(await res.json());
      } catch {
        setAiStatus(null);
      }
    }

    void loadAiStatus();
  }, []);

  async function submit(e: FormEvent) {
    e.preventDefault();

    const question = message.trim();
    if (!question || sending) return;

    setSending(true);
    setError("");

    try {
      const form = new FormData();
      form.append("message", question);
      form.append("year_month", yearMonth);

      const res = await fetch(`${API_BASE}/my/ai/chat`, {
        method: "POST",
        credentials: "include",
        body: form,
      });
      const data = await res.json().catch(() => null);

      if (!res.ok) {
        setError(
          data?.detail
            ? `AIに質問できませんでした: ${data.detail}`
            : `AIに質問できませんでした: ${res.status}`
        );
        return;
      }

      setAnswer(data.answer ?? "");
      setMessage("");
    } catch {
      setError("AIとの通信中にエラーが発生しました。");
    } finally {
      setSending(false);
    }
  }

  return (
    <AuthGuard allow={["employee"]}>
      <main style={{ maxWidth: 900, margin: "0 auto", padding: "28px 16px" }}>
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
            marginBottom: 22,
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

        <form onSubmit={submit}>
          <label style={{ display: "block", marginBottom: 16 }}>
            対象月
            <input
              type="month"
              value={yearMonth}
              onChange={(e) => setYearMonth(e.target.value)}
              required
              style={{ display: "block", marginTop: 8, padding: "10px 12px" }}
            />
          </label>

          <textarea
            aria-label="AIへの質問"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder="自分の給与・勤怠・有給について質問してください..."
            rows={3}
            style={{ width: "100%", padding: 12 }}
          />

          <button
            type="submit"
            disabled={sending || !message.trim()}
            style={{ marginTop: 10, padding: "10px 16px" }}
          >
            {sending ? "送信中…" : "AIに質問する"}
          </button>
        </form>

        {error && <p style={{ color: "#ff9d9d" }}>{error}</p>}

        {answer && (
          <div
            style={{
              marginTop: 24,
              padding: 16,
              border: "1px solid rgba(148,180,216,0.16)",
              borderRadius: 14,
              whiteSpace: "pre-wrap",
              lineHeight: 1.7,
            }}
          >
            {answer}
          </div>
        )}
      </main>
    </AuthGuard>
  );
}
