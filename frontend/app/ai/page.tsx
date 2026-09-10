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

  async function sendQuestion(rawQuestion: string) {
    const question = rawQuestion.trim();
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

  async function submit(e: FormEvent) {
    e.preventDefault();
    await sendQuestion(message);
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
        <div
          style={{
            position: "relative",
            overflow: "hidden",
            marginBottom: 24,
            padding: "30px 28px",
            border: "1px solid rgba(129,140,248,0.24)",
            borderRadius: 24,
            background:
              "linear-gradient(135deg, rgba(30,41,78,0.96), rgba(12,24,43,0.94) 55%, rgba(41,27,72,0.90))",
            boxShadow:
              "0 24px 80px rgba(0,0,0,0.24), inset 0 1px 0 rgba(255,255,255,0.05)",
          }}
        >
          <div
            style={{
              position: "absolute",
              width: 240,
              height: 240,
              right: -70,
              top: -100,
              borderRadius: "50%",
              background:
                "radial-gradient(circle, rgba(139,92,246,0.30), rgba(79,70,229,0.08) 48%, transparent 70%)",
              pointerEvents: "none",
            }}
          />

          <div
            style={{
              position: "relative",
              display: "flex",
              alignItems: "center",
              gap: 18,
            }}
          >
            <div
              style={{
                display: "grid",
                placeItems: "center",
                flex: "0 0 auto",
                width: 58,
                height: 58,
                borderRadius: 18,
                background:
                  "linear-gradient(135deg, #818cf8, #8b5cf6 55%, #c084fc)",
                color: "white",
                fontSize: 28,
                boxShadow:
                  "0 0 32px rgba(139,92,246,0.38), inset 0 1px 0 rgba(255,255,255,0.35)",
              }}
            >
              ✦
            </div>

            <div>
              <div
                style={{
                  color: "#a5b4fc",
                  fontSize: 12,
                  fontWeight: 800,
                  letterSpacing: "0.16em",
                }}
              >
                LOCAL AI ASSISTANT
              </div>

              <h1
                style={{
                  margin: "5px 0 7px",
                  fontSize: "clamp(26px, 4vw, 38px)",
                  letterSpacing: "-0.03em",
                }}
              >
                給与業務を、AIともっとスマートに。
              </h1>

              <p
                style={{
                  color: "#a9bad0",
                  margin: 0,
                  lineHeight: 1.7,
                }}
              >
                給与・勤怠・有給のデータを横断して、
                必要な情報をローカルAIがすばやく整理します。
              </p>
            </div>
          </div>

          <div
            style={{
              position: "relative",
              display: "flex",
              flexWrap: "wrap",
              gap: 9,
              marginTop: 22,
            }}
          >
            {[
              ["¥", "給与"],
              ["◷", "勤怠"],
              ["◇", "有給"],
            ].map(([icon, label]) => (
              <span
                key={label}
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 7,
                  padding: "7px 12px",
                  border: "1px solid rgba(165,180,252,0.16)",
                  borderRadius: 999,
                  background: "rgba(255,255,255,0.045)",
                  color: "#d6def0",
                  fontSize: 13,
                }}
              >
                <span style={{ color: "#a5b4fc" }}>{icon}</span>
                {label}
              </span>
            ))}

            <span
              style={{
                marginLeft: "auto",
                padding: "7px 12px",
                borderRadius: 999,
                background: "rgba(52,211,153,0.11)",
                color: "#86efac",
                fontSize: 12,
                border: "1px solid rgba(52,211,153,0.16)",
              }}
            >
              ● 読み取り専用
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

            <div style={{ marginBottom: 22 }}>
              <div
                style={{
                  marginBottom: 10,
                  color: "#9fb1c7",
                  fontSize: 13,
                  fontWeight: 700,
                }}
              >
                ✦ AIに聞いてみる
              </div>

              <div
                style={{
                  display: "grid",
                  gridTemplateColumns:
                    "repeat(auto-fit, minmax(190px, 1fr))",
                  gap: 10,
                }}
              >
                {[
                  {
                    icon: "¥",
                    title: "給与サマリー",
                    text: "今月の給与処理状況をまとめて",
                    color: "#818cf8",
                  },
                  {
                    icon: "!",
                    title: "要確認をチェック",
                    text: "今月誰を確認すればいい？",
                    color: "#fbbf24",
                  },
                  {
                    icon: "◇",
                    title: "有給申請",
                    text: "有給の承認待ちは誰？",
                    color: "#34d399",
                  },
                ].map((example) => (
                  <button
                    key={example.title}
                    type="button"
                    onClick={() => void sendQuestion(example.text)}
                    disabled={sending}
                    style={{
                      display: "flex",
                      gap: 12,
                      alignItems: "flex-start",
                      padding: 14,
                      border:
                        "1px solid rgba(148,180,216,0.14)",
                      borderRadius: 15,
                      background:
                        "linear-gradient(145deg, rgba(255,255,255,0.055), rgba(255,255,255,0.018))",
                      color: "#e6edf7",
                      textAlign: "left",
                      cursor: sending ? "wait" : "pointer",
                      boxShadow:
                        "inset 0 1px 0 rgba(255,255,255,0.035)",
                    }}
                  >
                    <span
                      style={{
                        display: "grid",
                        placeItems: "center",
                        width: 32,
                        height: 32,
                        flex: "0 0 32px",
                        borderRadius: 10,
                        background: `${example.color}18`,
                        color: example.color,
                        fontWeight: 900,
                      }}
                    >
                      {example.icon}
                    </span>

                    <span>
                      <strong
                        style={{
                          display: "block",
                          marginBottom: 4,
                          fontSize: 13,
                        }}
                      >
                        {example.title}
                      </strong>
                      <span
                        style={{
                          color: "#8fa6bf",
                          fontSize: 12,
                          lineHeight: 1.5,
                        }}
                      >
                        {example.text}
                      </span>
                    </span>
                  </button>
                ))}
              </div>
            </div>

            <div>
              <div
                style={{
                  marginBottom: 8,
                  color: "#9fb1c7",
                  fontSize: 13,
                  fontWeight: 700,
                }}
              >
                AIに質問する
              </div>

              <div
                style={{
                  display: "flex",
                  alignItems: "flex-end",
                  gap: 10,
                  padding: 10,
                  border: "1px solid rgba(129,140,248,0.22)",
                  borderRadius: 18,
                  background:
                    "linear-gradient(135deg, rgba(8,18,34,0.80), rgba(18,24,48,0.72))",
                  boxShadow:
                    "inset 0 1px 0 rgba(255,255,255,0.035), 0 10px 32px rgba(0,0,0,0.12)",
                }}
              >
                <div
                  style={{
                    display: "grid",
                    placeItems: "center",
                    width: 36,
                    height: 36,
                    flex: "0 0 36px",
                    marginBottom: 2,
                    borderRadius: 11,
                    background: "rgba(139,92,246,0.14)",
                    color: "#c4b5fd",
                  }}
                >
                  ✦
                </div>

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
                  placeholder="給与・勤怠・有給について質問してください..."
                  rows={2}
                  style={{
                    flex: 1,
                    minHeight: 46,
                    maxHeight: 150,
                    padding: "10px 4px",
                    border: 0,
                    outline: "none",
                    resize: "vertical",
                    background: "transparent",
                    color: "#e6edf7",
                    font: "inherit",
                    lineHeight: 1.6,
                  }}
                />

                <button
                  type="submit"
                  aria-label="AIに送信"
                  disabled={sending || !message.trim()}
                  style={{
                    display: "grid",
                    placeItems: "center",
                    width: 42,
                    height: 42,
                    flex: "0 0 42px",
                    border: 0,
                    borderRadius: 13,
                    background:
                      sending || !message.trim()
                        ? "rgba(129,140,248,0.16)"
                        : "linear-gradient(135deg, #6366f1, #8b5cf6)",
                    color:
                      sending || !message.trim()
                        ? "#697891"
                        : "white",
                    cursor:
                      sending || !message.trim()
                        ? "not-allowed"
                        : "pointer",
                    fontSize: 18,
                    boxShadow:
                      sending || !message.trim()
                        ? "none"
                        : "0 6px 20px rgba(99,102,241,0.28)",
                  }}
                >
                  {sending ? "…" : "↑"}
                </button>
              </div>

              <div
                style={{
                  marginTop: 7,
                  color: "#667991",
                  fontSize: 11,
                  textAlign: "right",
                }}
              >
                Enter で送信 ・ Shift + Enter で改行
              </div>
            </div>
          </form>

          {error && (
            <p style={{ color: "#ff9d9d", marginTop: 20 }}>
              {error}
            </p>
          )}

          {(messages.length > 0 || sending) && (
            <div
              style={{
                display: "grid",
                gap: 14,
                marginTop: 26,
                paddingTop: 22,
                borderTop: "1px solid rgba(148,180,216,0.12)",
              }}
            >
              {messages.map((item, index) => {
                const isUser = item.role === "user";

                return (
                  <div
                    key={`${item.role}-${index}`}
                    style={{
                      display: "flex",
                      justifyContent: isUser ? "flex-end" : "flex-start",
                      gap: 10,
                    }}
                  >
                    {!isUser && (
                      <div
                        style={{
                          display: "grid",
                          placeItems: "center",
                          width: 34,
                          height: 34,
                          flex: "0 0 34px",
                          borderRadius: 11,
                          background:
                            "linear-gradient(135deg, #818cf8, #8b5cf6)",
                          color: "white",
                          boxShadow: "0 0 20px rgba(139,92,246,0.22)",
                        }}
                      >
                        ✦
                      </div>
                    )}

                    <div
                      style={{
                        maxWidth: "82%",
                        padding: "12px 15px",
                        border: isUser
                          ? "1px solid rgba(129,140,248,0.22)"
                          : "1px solid rgba(148,180,216,0.12)",
                        borderRadius: isUser
                          ? "16px 16px 4px 16px"
                          : "4px 16px 16px 16px",
                        background: isUser
                          ? "linear-gradient(135deg, rgba(79,70,229,0.25), rgba(99,102,241,0.15))"
                          : "rgba(7,16,30,0.52)",
                        whiteSpace: "pre-wrap",
                        lineHeight: 1.75,
                        color: "#dce6f3",
                      }}
                    >
                      <div
                        style={{
                          marginBottom: 5,
                          color: isUser ? "#a5b4fc" : "#c4b5fd",
                          fontSize: 11,
                          fontWeight: 800,
                          letterSpacing: "0.08em",
                        }}
                      >
                        {isUser ? "YOU" : "LOCAL AI"}
                      </div>
                      {item.content}
                    </div>
                  </div>
                );
              })}

              {sending && (
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 10,
                    color: "#9fb1c7",
                    fontSize: 13,
                  }}
                >
                  <div
                    style={{
                      display: "grid",
                      placeItems: "center",
                      width: 34,
                      height: 34,
                      borderRadius: 11,
                      background:
                        "linear-gradient(135deg, #818cf8, #8b5cf6)",
                      color: "white",
                    }}
                  >
                    ✦
                  </div>
                  <span>AIが給与データを確認しています…</span>
                </div>
              )}
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
