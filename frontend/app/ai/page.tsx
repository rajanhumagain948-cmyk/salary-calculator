"use client";

import { FormEvent, useState } from "react";
import AuthGuard from "@/components/auth/AuthGuard";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

function currentYearMonth() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
}

export default function AiPage() {
  const [yearMonth, setYearMonth] = useState(currentYearMonth);
  const [message, setMessage] = useState("");
  const [answer, setAnswer] = useState("");
  const [error, setError] = useState("");
  const [sending, setSending] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();

    const question = message.trim();
    if (!question || sending) {
      return;
    }

    setSending(true);
    setError("");
    setAnswer("");

    try {
      const form = new FormData();
      form.append("message", question);
      form.append("year_month", yearMonth);

      const res = await fetch(`${API_BASE}/ai/chat`, {
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
    } catch {
      setError("AIとの通信中にエラーが発生しました。");
    } finally {
      setSending(false);
    }
  }

  return (
    <AuthGuard allow={["admin"]}>
      <main
        style={{
          maxWidth: 900,
          margin: "0 auto",
          padding: "28px 16px",
        }}
      >
        <div style={{ marginBottom: 24 }}>
          <div
            style={{
              color: "#8390ff",
              fontSize: 12,
              fontWeight: 800,
              letterSpacing: "0.12em",
            }}
          >
            AI ASSISTANT
          </div>

          <h1 style={{ margin: "6px 0" }}>AIアシスタント</h1>

          <p style={{ color: "#8fa6bf", margin: 0 }}>
            給与・有給の月次状況について、ローカルAIに質問できます。
          </p>
        </div>

        <section
          style={{
            padding: 24,
            border: "1px solid rgba(148,180,216,0.16)",
            borderRadius: 18,
            background: "rgba(14,27,46,0.72)",
          }}
        >
          <form onSubmit={submit}>
            <label style={{ display: "block", marginBottom: 18 }}>
              対象月
              <input
                type="month"
                value={yearMonth}
                onChange={(e) => setYearMonth(e.target.value)}
                required
                style={{
                  display: "block",
                  marginTop: 8,
                  padding: "10px 12px",
                }}
              />
            </label>

            <label style={{ display: "block" }}>
              質問
              <textarea
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                placeholder="例: 今月の給与処理状況を教えて"
                rows={5}
                style={{
                  display: "block",
                  width: "100%",
                  marginTop: 8,
                  padding: 12,
                  resize: "vertical",
                }}
              />
            </label>

            <button
              type="submit"
              disabled={sending || !message.trim()}
              style={{
                marginTop: 16,
                padding: "10px 18px",
                cursor: sending ? "wait" : "pointer",
              }}
            >
              {sending ? "AIが確認中..." : "AIに質問"}
            </button>
          </form>

          {error && (
            <p style={{ color: "#ff9d9d", marginTop: 20 }}>
              {error}
            </p>
          )}

          {answer && (
            <div
              style={{
                marginTop: 24,
                padding: 18,
                borderRadius: 14,
                background: "rgba(0,0,0,0.18)",
                whiteSpace: "pre-wrap",
                lineHeight: 1.7,
              }}
            >
              <strong>AIからの回答</strong>
              <div style={{ marginTop: 10 }}>{answer}</div>
            </div>
          )}
        </section>

        <p
          style={{
            marginTop: 16,
            color: "#8fa6bf",
            fontSize: 13,
          }}
        >
          AIは読み取り専用です。給与確定・勤怠修正・有給承認などの操作は行いません。
        </p>
      </main>
    </AuthGuard>
  );
}
