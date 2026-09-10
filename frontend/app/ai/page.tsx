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
  const [messages, setMessages] = useState<
    { role: "user" | "assistant"; content: string }[]
  >([]);
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

    try {
      const form = new FormData();
      form.append("message", question);
      form.append("year_month", yearMonth);

      if (messages.length > 0) {
        form.append("history", JSON.stringify(messages));
      }

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

      setMessages((current) => [
        ...current,
        { role: "user", content: question },
        { role: "assistant", content: data.answer ?? "" },
      ]);
      setMessage("");
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

          <div
            style={{
              display: "flex",
              flexWrap: "wrap",
              gap: 8,
              marginTop: 12,
            }}
          >
            <span
              style={{
                padding: "5px 10px",
                borderRadius: 999,
                background: "rgba(100,116,255,0.18)",
                color: "#b7c0ff",
                fontSize: 12,
              }}
            >
              ローカルAI
            </span>
            <span
              style={{
                padding: "5px 10px",
                borderRadius: 999,
                background: "rgba(72,187,120,0.14)",
                color: "#9ae6b4",
                fontSize: 12,
              }}
            >
              読み取り専用
            </span>
          </div>
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

            <div style={{ marginBottom: 16 }}>
              <div
                style={{
                  marginBottom: 8,
                  color: "#8fa6bf",
                  fontSize: 13,
                }}
              >
                質問例
              </div>
              <div
                style={{
                  display: "flex",
                  flexWrap: "wrap",
                  gap: 8,
                }}
              >
                {[
                  "今月の給与処理状況をまとめて",
                  "今月誰を確認すればいい？",
                  "有給の承認待ちは誰？",
                ].map((example) => (
                  <button
                    key={example}
                    type="button"
                    onClick={() => setMessage(example)}
                    disabled={sending}
                    style={{
                      padding: "8px 12px",
                      borderRadius: 999,
                      cursor: sending ? "wait" : "pointer",
                    }}
                  >
                    {example}
                  </button>
                ))}
              </div>
            </div>

            <label style={{ display: "block" }}>
              質問
              <textarea
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                onKeyDown={(e) => {
                  if (
                    e.key === "Enter" &&
                    !e.shiftKey &&
                    !e.nativeEvent.isComposing
                  ) {
                    e.preventDefault();
                    e.currentTarget.form?.requestSubmit();
                  }
                }}
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

          {messages.length > 0 && (
            <div
              style={{
                display: "grid",
                gap: 12,
                marginTop: 24,
              }}
            >
              {messages.map((item, index) => (
                <div
                  key={`${item.role}-${index}`}
                  style={{
                    justifySelf:
                      item.role === "user" ? "end" : "start",
                    maxWidth: "85%",
                    padding: "12px 16px",
                    borderRadius: 14,
                    background:
                      item.role === "user"
                        ? "rgba(100,116,255,0.24)"
                        : "rgba(0,0,0,0.18)",
                    whiteSpace: "pre-wrap",
                    lineHeight: 1.7,
                  }}
                >
                  <strong>
                    {item.role === "user" ? "あなた" : "AI"}
                  </strong>
                  <div style={{ marginTop: 6 }}>{item.content}</div>
                </div>
              ))}
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
