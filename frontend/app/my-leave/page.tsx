"use client";

import { FormEvent, useEffect, useState } from "react";
import AuthGuard from "@/components/auth/AuthGuard";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

type LeaveRequest = {
  request_id: number;
  employee_id: string;
  leave_date: string;
  reason: string;
  status: "申請中" | "承認" | "却下";
  created_at: string | null;
};

function today() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(
    2,
    "0"
  )}-${String(now.getDate()).padStart(2, "0")}`;
}

export default function MyLeavePage() {
  const [items, setItems] = useState<LeaveRequest[]>([]);
  const [leaveDate, setLeaveDate] = useState(today);
  const [reason, setReason] = useState("");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  async function loadRequests() {
    setLoading(true);
    setError("");

    try {
      const res = await fetch(`${API_BASE}/my/leave-requests`, {
        credentials: "include",
        cache: "no-store",
      });

      if (!res.ok) {
        setError(`有給申請を取得できませんでした: ${res.status}`);
        return;
      }

      setItems(await res.json());
    } catch {
      setError("有給申請の取得中に通信エラーが発生しました。");
    } finally {
      setLoading(false);
    }
  }

  async function submit(event: FormEvent) {
    event.preventDefault();

    setSubmitting(true);
    setError("");
    setMessage("");

    try {
      const form = new FormData();
      form.append("leave_date", leaveDate);
      form.append("reason", reason);

      const res = await fetch(`${API_BASE}/my/leave-requests`, {
        method: "POST",
        credentials: "include",
        body: form,
      });

      if (!res.ok) {
        const body = await res.json().catch(() => null);

        setError(
          typeof body?.detail === "string"
            ? body.detail
            : `有給申請に失敗しました: ${res.status}`
        );
        return;
      }

      setReason("");
      setMessage("有給休暇を申請しました。");
      await loadRequests();
    } catch {
      setError("有給申請中に通信エラーが発生しました。");
    } finally {
      setSubmitting(false);
    }
  }

  useEffect(() => {
    loadRequests();
  }, []);

  return (
    <AuthGuard allow={["employee"]}>
      <main
        style={{
          maxWidth: 1180,
          margin: "0 auto",
          padding: "30px 20px 50px",
        }}
      >
        <header style={{ marginBottom: 24 }}>
          <div
            style={{
              color: "#45e0a8",
              fontSize: 11,
              fontWeight: 800,
            }}
          >
            有給休暇
          </div>

          <h1 style={{ margin: "7px 0 5px", fontSize: 30 }}>
            有給休暇申請
          </h1>

          <p style={{ margin: 0, color: "#8298ae", fontSize: 12 }}>
            有給休暇の申請と承認状況を確認できます。
          </p>
        </header>

        {error && <div style={errorStyle}>{error}</div>}
        {message && <div style={successStyle}>{message}</div>}

        <section style={{ ...panelStyle, marginBottom: 18 }}>
          <h2 style={{ marginTop: 0, fontSize: 17 }}>
            新しい申請
          </h2>

          <form
            onSubmit={submit}
            style={{
              display: "grid",
              gridTemplateColumns: "220px minmax(0, 1fr) auto",
              gap: 12,
              alignItems: "end",
            }}
          >
            <label>
              <span style={labelStyle}>取得日</span>
              <input
                type="date"
                required
                value={leaveDate}
                onChange={(event) => setLeaveDate(event.target.value)}
                style={fieldStyle}
              />
            </label>

            <label>
              <span style={labelStyle}>理由</span>
              <input
                type="text"
                value={reason}
                onChange={(event) => setReason(event.target.value)}
                placeholder="任意"
                style={fieldStyle}
              />
            </label>

            <button
              type="submit"
              disabled={submitting}
              style={{
                height: 42,
                padding: "0 20px",
                border: 0,
                borderRadius: 10,
                color: "#07151a",
                background:
                  "linear-gradient(135deg, #45e0a8, #38d9c4)",
                fontWeight: 800,
                cursor: submitting ? "wait" : "pointer",
              }}
            >
              {submitting ? "申請中..." : "申請する"}
            </button>
          </form>
        </section>

        <section style={panelStyle}>
          <h2 style={{ marginTop: 0, fontSize: 17 }}>
            申請履歴
          </h2>

          {loading ? (
            <div style={emptyStyle}>読み込み中...</div>
          ) : items.length === 0 ? (
            <div style={emptyStyle}>
              まだ有給休暇の申請はありません。
            </div>
          ) : (
            <div style={{ overflowX: "auto" }}>
              <table
                style={{
                  width: "100%",
                  borderCollapse: "collapse",
                  fontSize: 12,
                }}
              >
                <thead>
                  <tr
                    style={{
                      color: "#71879d",
                      textAlign: "left",
                    }}
                  >
                    <th style={cellStyle}>取得日</th>
                    <th style={cellStyle}>理由</th>
                    <th style={cellStyle}>状態</th>
                  </tr>
                </thead>

                <tbody>
                  {items.map((item) => (
                    <tr
                      key={item.request_id}
                      style={{
                        borderTop:
                          "1px solid rgba(148,180,216,.09)",
                      }}
                    >
                      <td style={cellStyle}>{item.leave_date}</td>
                      <td style={cellStyle}>
                        {item.reason || "—"}
                      </td>
                      <td style={cellStyle}>
                        <Status status={item.status} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </main>
    </AuthGuard>
  );
}

function Status({
  status,
}: {
  status: LeaveRequest["status"];
}) {
  const color =
    status === "承認"
      ? "#65e6b5"
      : status === "却下"
        ? "#ff9aa6"
        : "#f6c85f";

  return (
    <span style={{ color, fontWeight: 800 }}>
      {status}
    </span>
  );
}

const panelStyle = {
  padding: 20,
  border: "1px solid rgba(148,180,216,.12)",
  borderRadius: 14,
  background: "rgba(8,19,33,.55)",
};

const labelStyle = {
  display: "block",
  marginBottom: 7,
  color: "#8298ae",
  fontSize: 10,
};

const fieldStyle = {
  width: "100%",
  height: 42,
  padding: "0 11px",
};

const cellStyle = {
  padding: "12px 10px",
};

const emptyStyle = {
  padding: 30,
  textAlign: "center" as const,
  color: "#71879d",
};

const errorStyle = {
  padding: 12,
  marginBottom: 14,
  borderRadius: 10,
  color: "#ff9aa6",
  background: "rgba(255,107,122,.08)",
};

const successStyle = {
  padding: 12,
  marginBottom: 14,
  borderRadius: 10,
  color: "#65e6b5",
  background: "rgba(69,224,168,.08)",
};
