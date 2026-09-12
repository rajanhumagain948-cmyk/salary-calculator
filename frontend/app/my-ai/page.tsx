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
  const [messages, setMessages] = useState<
    {
      role: "user" | "assistant";
      content: string;
      sources?: string[];
    }[]
  >([]);
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

  async function sendQuestion(rawQuestion: string) {
    const question = rawQuestion.trim();
    if (!question || sending) return;

    setSending(true);
    setError("");

    try {
      const form = new FormData();
      form.append("message", question);
      form.append("year_month", yearMonth);

      if (messages.length > 0) {
        form.append(
          "history",
          JSON.stringify(
            messages
              .slice(-20)
              .map(({ role, content }) => ({ role, content }))
          )
        );
      }

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

      setMessages((current) => [
        ...current,
        { role: "user", content: question },
        {
          role: "assistant",
          content: data.answer ?? "",
          sources: Array.isArray(data.sources) ? data.sources : [],
        },
      ]);
      setMessage("");
    } catch {
      setError("AIとの通信中にエラーが発生しました。");
    } finally {
      setSending(false);
    }
  }

  async function submit(e: FormEvent) {
    e.preventDefault();
    await sendQuestion(message);
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

        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            gap: 8,
            marginBottom: 18,
          }}
        >
          {[
            "今月の勤務日数は？",
            "今月の手取りはいくら？",
            "有給はあと何日？",
          ].map((question) => (
            <button
              key={question}
              type="button"
              disabled={sending}
              onClick={() => void sendQuestion(question)}
              style={{ padding: "8px 12px" }}
            >
              {question}
            </button>
          ))}
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
                  marginLeft: item.role === "user" ? "15%" : 0,
                  marginRight: item.role === "assistant" ? "15%" : 0,
                  padding: 16,
                  border: "1px solid rgba(148,180,216,0.16)",
                  borderRadius: 14,
                  whiteSpace: "pre-wrap",
                  lineHeight: 1.7,
                }}
              >
                <strong>
                  {item.role === "user" ? "YOU" : "LOCAL AI"}
                </strong>
                <div>{item.content}</div>

                {item.role === "assistant" &&
                  item.sources &&
                  item.sources.length > 0 && (
                    <div style={{ marginTop: 10, color: "#8fa6bf" }}>
                      参照: {item.sources.join(" / ")}
                    </div>
                  )}
              </div>
            ))}
          </div>
        )}
      </main>
    </AuthGuard>
  );
}
