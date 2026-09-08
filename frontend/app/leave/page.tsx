"use client";

import { useEffect, useMemo, useState } from "react";
import AuthGuard from "@/components/auth/AuthGuard";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

type Employee = {
  employee_id: string;
  name: string;
};

type LeaveGrantCandidate = {
  employee_id: string;
  name: string;
  grant_date: string;
  days: string;
  service_months: number;
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

export default function LeaveAdminPage() {
  const [requests, setRequests] = useState<LeaveRequest[]>([]);
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [grantCandidates, setGrantCandidates] = useState<
    LeaveGrantCandidate[]
  >([]);
  const [grantingEmployeeId, setGrantingEmployeeId] = useState<
    string | null
  >(null);
  const [loading, setLoading] = useState(true);
  const [updatingId, setUpdatingId] = useState<number | null>(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  async function loadData() {
    setLoading(true);
    setError("");

    try {
      const today = new Date().toISOString().slice(0, 10);

      const [requestsRes, employeesRes, grantsRes] = await Promise.all([
        fetch(`${API_BASE}/leave-requests`, {
          credentials: "include",
          cache: "no-store",
        }),
        fetch(`${API_BASE}/employees`, {
          credentials: "include",
          cache: "no-store",
        }),
        fetch(
          `${API_BASE}/leave-grants/due?as_of=${today}`,
          {
            credentials: "include",
            cache: "no-store",
          }
        ),
      ]);

      if (!requestsRes.ok) {
        setError(`有給申請を取得できませんでした: ${requestsRes.status}`);
        return;
      }

      if (!employeesRes.ok) {
        setError(`従業員一覧を取得できませんでした: ${employeesRes.status}`);
        return;
      }

      if (!grantsRes.ok) {
        setError(
          `有給付与候補を取得できませんでした: ${grantsRes.status}`
        );
        return;
      }

      setRequests(await requestsRes.json());
      setEmployees(await employeesRes.json());
      setGrantCandidates(await grantsRes.json());
    } catch {
      setError("有給管理データの取得中に通信エラーが発生しました。");
    } finally {
      setLoading(false);
    }
  }

  async function confirmGrant(
    candidate: LeaveGrantCandidate
  ) {
    if (
      !window.confirm(
        `${candidate.name} に ${candidate.days}日の有給を付与しますか？\n` +
          `付与日: ${candidate.grant_date}\n` +
          "出勤率などの付与要件を確認してから実行してください。"
      )
    ) {
      return;
    }

    setGrantingEmployeeId(candidate.employee_id);
    setError("");
    setMessage("");

    try {
      const form = new FormData();
      form.append("employee_id", candidate.employee_id);
      form.append("as_of", new Date().toISOString().slice(0, 10));

      const res = await fetch(`${API_BASE}/leave-grants/confirm`, {
        method: "POST",
        credentials: "include",
        body: form,
      });

      if (!res.ok) {
        const body = await res.json().catch(() => null);

        setError(
          typeof body?.detail === "string"
            ? body.detail
            : `有給を付与できませんでした: ${res.status}`
        );
        return;
      }

      setMessage(
        `${candidate.name} に ${candidate.days}日の有給を付与しました。`
      );

      await loadData();
    } catch {
      setError("有給付与中に通信エラーが発生しました。");
    } finally {
      setGrantingEmployeeId(null);
    }
  }

  async function updateStatus(
    requestId: number,
    status: "承認" | "却下"
  ) {
    if (
      !window.confirm(
        `この有給申請を「${status}」にしますか？`
      )
    ) {
      return;
    }

    setUpdatingId(requestId);
    setError("");
    setMessage("");

    try {
      const form = new FormData();
      form.append("status", status);

      const res = await fetch(
        `${API_BASE}/leave-requests/${requestId}/status`,
        {
          method: "POST",
          credentials: "include",
          body: form,
        }
      );

      if (!res.ok) {
        const body = await res.json().catch(() => null);

        setError(
          typeof body?.detail === "string"
            ? body.detail
            : `更新できませんでした: ${res.status}`
        );
        return;
      }

      setMessage(`有給申請を${status}しました。`);
      await loadData();
    } catch {
      setError("承認状態の更新中に通信エラーが発生しました。");
    } finally {
      setUpdatingId(null);
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  const pendingCount = useMemo(
    () => requests.filter((item) => item.status === "申請中").length,
    [requests]
  );

  function employeeName(employeeId: string) {
    return (
      employees.find((item) => item.employee_id === employeeId)?.name ??
      employeeId
    );
  }

  function unitLabel(item: LeaveRequest) {
    if (item.leave_unit === "半日") {
      return `${item.half_day_period ?? ""}半日`;
    }

    if (
      item.leave_unit === "時間" &&
      item.start_minute !== null &&
      item.end_minute !== null
    ) {
      const time = (minute: number) =>
        `${String(Math.floor(minute / 60)).padStart(2, "0")}:${String(
          minute % 60
        ).padStart(2, "0")}`;

      return `${time(item.start_minute)}〜${time(item.end_minute)}`;
    }

    return item.leave_unit;
  }

  return (
    <AuthGuard allow={["admin"]}>
      <main
        style={{
          maxWidth: 1240,
          margin: "0 auto",
          padding: "30px 20px 50px",
        }}
      >
        <header
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "flex-end",
            gap: 20,
            marginBottom: 24,
          }}
        >
          <div>
            <div style={eyebrowStyle}>会社側</div>
            <h1 style={{ margin: "7px 0 5px", fontSize: 30 }}>
              有給管理
            </h1>
            <p style={{ margin: 0, color: "#8298ae", fontSize: 12 }}>
              従業員の有給申請を確認し、承認・却下します。
            </p>
          </div>

          <div style={summaryStyle}>
            <span style={{ color: "#8298ae", fontSize: 10 }}>
              承認待ち
            </span>
            <strong style={{ color: "#f6c85f", fontSize: 23 }}>
              {pendingCount}件
            </strong>
          </div>
        </header>

        {error && <div style={errorStyle}>{error}</div>}
        {message && <div style={successStyle}>{message}</div>}

        <section
          style={{
            ...panelStyle,
            marginBottom: 18,
          }}
        >
          <div style={{ marginBottom: 14 }}>
            <h2 style={{ margin: 0, fontSize: 17 }}>
              有給付与対象
            </h2>
            <p
              style={{
                margin: "5px 0 0",
                color: "#71879d",
                fontSize: 10,
              }}
            >
              付与予定日が到来した従業員です。出勤率などの付与要件を確認してから付与してください。
            </p>
          </div>

          {grantCandidates.length === 0 ? (
            <div style={emptyStyle}>
              現在、有給付与の確認が必要な従業員はいません。
            </div>
          ) : (
            <div style={{ overflowX: "auto" }}>
              <table style={tableStyle}>
                <thead>
                  <tr style={{ color: "#71879d", textAlign: "left" }}>
                    <th style={cellStyle}>従業員</th>
                    <th style={cellStyle}>付与予定日</th>
                    <th style={cellStyle}>付与日数</th>
                    <th style={cellStyle}>勤続期間</th>
                    <th style={cellStyle}>確認</th>
                  </tr>
                </thead>

                <tbody>
                  {grantCandidates.map((candidate) => (
                    <tr
                      key={`${candidate.employee_id}-${candidate.grant_date}`}
                      style={{
                        borderTop:
                          "1px solid rgba(148,180,216,.09)",
                      }}
                    >
                      <td style={cellStyle}>
                        <strong>{candidate.name}</strong>
                        <div style={subtleStyle}>
                          {candidate.employee_id}
                        </div>
                      </td>

                      <td style={cellStyle}>
                        {candidate.grant_date}
                      </td>

                      <td style={cellStyle}>
                        <strong style={{ color: "#9ba5ff" }}>
                          {Number(candidate.days).toLocaleString("ja-JP")}日
                        </strong>
                      </td>

                      <td style={cellStyle}>
                        {candidate.service_months}か月
                      </td>

                      <td style={cellStyle}>
                        <button
                          onClick={() => confirmGrant(candidate)}
                          disabled={
                            grantingEmployeeId === candidate.employee_id
                          }
                          style={approveButtonStyle}
                        >
                          {grantingEmployeeId === candidate.employee_id
                            ? "付与中..."
                            : "要件確認済み・付与する"}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        <section style={panelStyle}>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginBottom: 14,
            }}
          >
            <h2 style={{ margin: 0, fontSize: 17 }}>
              有給申請一覧
            </h2>

            <button
              onClick={loadData}
              disabled={loading}
              style={secondaryButtonStyle}
            >
              {loading ? "更新中..." : "一覧を更新"}
            </button>
          </div>

          {loading ? (
            <div style={emptyStyle}>読み込み中...</div>
          ) : requests.length === 0 ? (
            <div style={emptyStyle}>有給申請はありません。</div>
          ) : (
            <div style={{ overflowX: "auto" }}>
              <table style={tableStyle}>
                <thead>
                  <tr style={{ color: "#71879d", textAlign: "left" }}>
                    <th style={cellStyle}>従業員</th>
                    <th style={cellStyle}>取得日</th>
                    <th style={cellStyle}>取得単位</th>
                    <th style={cellStyle}>理由</th>
                    <th style={cellStyle}>状態</th>
                    <th style={cellStyle}>操作</th>
                  </tr>
                </thead>

                <tbody>
                  {requests.map((item) => (
                    <tr
                      key={item.request_id}
                      style={{
                        borderTop:
                          "1px solid rgba(148,180,216,.09)",
                      }}
                    >
                      <td style={cellStyle}>
                        <strong>{employeeName(item.employee_id)}</strong>
                        <div style={subtleStyle}>{item.employee_id}</div>
                      </td>

                      <td style={cellStyle}>{item.leave_date}</td>
                      <td style={cellStyle}>{unitLabel(item)}</td>
                      <td style={cellStyle}>{item.reason || "—"}</td>

                      <td style={cellStyle}>
                        <Status status={item.status} />
                      </td>

                      <td style={cellStyle}>
                        {item.status === "申請中" ? (
                          <div
                            style={{
                              display: "flex",
                              gap: 7,
                            }}
                          >
                            <button
                              disabled={updatingId === item.request_id}
                              onClick={() =>
                                updateStatus(item.request_id, "承認")
                              }
                              style={approveButtonStyle}
                            >
                              承認
                            </button>

                            <button
                              disabled={updatingId === item.request_id}
                              onClick={() =>
                                updateStatus(item.request_id, "却下")
                              }
                              style={rejectButtonStyle}
                            >
                              却下
                            </button>
                          </div>
                        ) : (
                          <span style={subtleStyle}>処理済み</span>
                        )}
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

function Status({ status }: { status: LeaveRequest["status"] }) {
  const color =
    status === "承認"
      ? "#65e6b5"
      : status === "却下"
        ? "#ff9aa6"
        : "#f6c85f";

  return <strong style={{ color }}>{status}</strong>;
}

const eyebrowStyle = {
  color: "#45e0a8",
  fontSize: 11,
  fontWeight: 800,
};

const panelStyle = {
  padding: 20,
  border: "1px solid rgba(148,180,216,.12)",
  borderRadius: 14,
  background: "rgba(8,19,33,.55)",
};

const summaryStyle = {
  display: "flex",
  flexDirection: "column" as const,
  gap: 3,
  minWidth: 110,
  padding: "11px 15px",
  border: "1px solid rgba(246,200,95,.18)",
  borderRadius: 11,
  background: "rgba(246,200,95,.05)",
};

const tableStyle = {
  width: "100%",
  borderCollapse: "collapse" as const,
  fontSize: 11,
};

const cellStyle = {
  padding: "12px 10px",
};

const subtleStyle = {
  marginTop: 3,
  color: "#71879d",
  fontSize: 9,
};

const secondaryButtonStyle = {
  padding: "8px 12px",
  border: "1px solid rgba(109,124,255,.25)",
  borderRadius: 9,
  color: "#c7ceff",
  background: "rgba(109,124,255,.08)",
  cursor: "pointer",
};

const approveButtonStyle = {
  padding: "7px 11px",
  border: "1px solid rgba(69,224,168,.25)",
  borderRadius: 8,
  color: "#65e6b5",
  background: "rgba(69,224,168,.07)",
  cursor: "pointer",
};

const rejectButtonStyle = {
  padding: "7px 11px",
  border: "1px solid rgba(255,107,122,.25)",
  borderRadius: 8,
  color: "#ff9aa6",
  background: "rgba(255,107,122,.07)",
  cursor: "pointer",
};

const emptyStyle = {
  padding: 35,
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
