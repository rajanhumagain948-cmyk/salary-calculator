"use client";

import { FormEvent, useEffect, useState } from "react";
import AuthGuard from "@/components/auth/AuthGuard";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

type CompanySettings = {
  hourly_paid_leave_enabled: boolean;
  hourly_paid_leave_unit_hours: number;
};

type LeaveBalance = {
  granted_days: string;
  used_days: string;
  pending_days: string;
  remaining_days: string;
  available_days: string;
  next_grant_date: string;
  next_grant_days: string;
};

type LeaveRequest = {
  request_id: number;
  employee_id: string;
  leave_date: string;
  reason: string;
  status: "申請中" | "承認" | "却下";
  leave_unit: "全日" | "半日" | "時間";
  half_day_period: "午前" | "午後" | null;
  start_minute: number | null;
  end_minute: number | null;
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
  const [balance, setBalance] = useState<LeaveBalance | null>(null);
  const [leaveDate, setLeaveDate] = useState(today);
  const [leaveType, setLeaveType] = useState<
    "全日" | "午前半日" | "午後半日" | "時間"
  >("全日");
  const [reason, setReason] = useState("");
  const [startTime, setStartTime] = useState("09:00");
  const [endTime, setEndTime] = useState("10:00");
  const [companySettings, setCompanySettings] =
    useState<CompanySettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  async function loadCompanySettings() {
    try {
      const res = await fetch(`${API_BASE}/company`, {
        credentials: "include",
        cache: "no-store",
      });

      if (res.ok) {
        setCompanySettings(await res.json());
      }
    } catch {
      // 全日・半日の申請は利用可能にする
    }
  }

  async function loadBalance() {
    try {
      const res = await fetch(
        `${API_BASE}/my/leave-balance?as_of=${today()}`,
        {
          credentials: "include",
          cache: "no-store",
        }
      );

      if (!res.ok) return;

      setBalance(await res.json());
    } catch {
      // 申請履歴はそのまま利用可能にする
    }
  }

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

      if (leaveType === "全日") {
        form.append("leave_unit", "全日");
      } else if (leaveType === "時間") {
        form.append("leave_unit", "時間");
        form.append("start_time", startTime);
        form.append("end_time", endTime);
      } else {
        form.append("leave_unit", "半日");
        form.append(
          "half_day_period",
          leaveType === "午前半日" ? "午前" : "午後"
        );
      }

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
      await loadBalance();
    } catch {
      setError("有給申請中に通信エラーが発生しました。");
    } finally {
      setSubmitting(false);
    }
  }

  useEffect(() => {
    loadRequests();
    loadBalance();
    loadCompanySettings();
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

        {balance && (
          <section
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(5, minmax(0, 1fr))",
              gap: 12,
              marginBottom: 18,
            }}
          >
            <BalanceCard
              label="有給残日数"
              value={balance.remaining_days}
              color="#65e6b5"
            />
            <BalanceCard
              label="付与日数"
              value={balance.granted_days}
              color="#9ba5ff"
            />
            <BalanceCard
              label="使用済み"
              value={balance.used_days}
              color="#8fa6bf"
            />
            <BalanceCard
              label="申請中"
              value={balance.pending_days}
              color="#f6c85f"
            />
            <BalanceCard
              label="申請可能"
              value={balance.available_days}
              color="#45e0a8"
            />
          </section>
        )}

        {balance && (
          <section
            style={{
              ...panelStyle,
              marginBottom: 18,
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              gap: 15,
            }}
          >
            <div>
              <div
                style={{
                  color: "#8298ae",
                  fontSize: 10,
                  marginBottom: 5,
                }}
              >
                次回有給付与予定
              </div>

              <strong style={{ fontSize: 16 }}>
                {balance.next_grant_date}
              </strong>
            </div>

            <div style={{ textAlign: "right" }}>
              <div
                style={{
                  color: "#8298ae",
                  fontSize: 10,
                  marginBottom: 5,
                }}
              >
                付与予定日数
              </div>

              <strong
                style={{
                  color: "#9ba5ff",
                  fontSize: 20,
                }}
              >
                {Number(balance.next_grant_days).toLocaleString("ja-JP")}日
              </strong>
            </div>
          </section>
        )}

        <section style={{ ...panelStyle, marginBottom: 18 }}>
          <h2 style={{ marginTop: 0, fontSize: 17 }}>
            新しい申請
          </h2>

          <form
            onSubmit={submit}
            style={{
              display: "grid",
              gridTemplateColumns: "180px 180px minmax(0, 1fr) auto",
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
              <span style={labelStyle}>取得単位</span>
              <select
                value={leaveType}
                onChange={(event) =>
                  setLeaveType(
                    event.target.value as
                      | "全日"
                      | "午前半日"
                      | "午後半日"
                      | "時間"
                  )
                }
                style={fieldStyle}
              >
                <option value="全日">全日</option>
                <option value="午前半日">午前半日</option>
                <option value="午後半日">午後半日</option>
                {companySettings?.hourly_paid_leave_enabled && (
                  <option value="時間">時間単位</option>
                )}
              </select>
            </label>

            {leaveType === "時間" && (
              <>
                <label>
                  <span style={labelStyle}>開始時刻</span>
                  <input
                    type="time"
                    value={startTime}
                    step={3600}
                    onChange={(e) => setStartTime(e.target.value)}
                    style={fieldStyle}
                    required
                  />
                </label>

                <label>
                  <span style={labelStyle}>終了時刻</span>
                  <input
                    type="time"
                    value={endTime}
                    step={3600}
                    onChange={(e) => setEndTime(e.target.value)}
                    style={fieldStyle}
                    required
                  />
                </label>
              </>
            )}

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
              disabled={
                submitting ||
                !balance ||
                Number(balance.available_days) <= 0
              }
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
              {submitting
                ? "申請中..."
                : balance && Number(balance.available_days) <= 0
                  ? "申請可能日数なし"
                  : "申請する"}
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
                    <th style={cellStyle}>取得単位</th>
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
                        {item.leave_unit === "半日"
                          ? `${item.half_day_period ?? ""}半日`
                          : item.leave_unit === "時間" &&
                              item.start_minute !== null &&
                              item.end_minute !== null
                            ? `${String(Math.floor(item.start_minute / 60)).padStart(2, "0")}:${String(item.start_minute % 60).padStart(2, "0")}〜${String(Math.floor(item.end_minute / 60)).padStart(2, "0")}:${String(item.end_minute % 60).padStart(2, "0")}`
                            : item.leave_unit}
                      </td>
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

function BalanceCard({
  label,
  value,
  color,
}: {
  label: string;
  value: string;
  color: string;
}) {
  return (
    <div style={panelStyle}>
      <div
        style={{
          color: "#8298ae",
          fontSize: 10,
          marginBottom: 8,
        }}
      >
        {label}
      </div>

      <strong
        style={{
          color,
          fontSize: 25,
        }}
      >
        {Number(value).toLocaleString("ja-JP")}日
      </strong>
    </div>
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
