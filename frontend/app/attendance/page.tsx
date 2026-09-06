"use client";

import { useEffect, useMemo, useState } from "react";
import AuthGuard from "@/components/auth/AuthGuard";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

type AuditItem = {
  created_at: string;
  action: string;
  subject: string;
  detail: string;
};

type Employee = {
  employee_id: string;
  name: string;
};

type AttendanceForm = {
  record_id: number | null;
  work_date: string;
  start: string;
  end: string;
  break_minutes: string;
  is_holiday: boolean;
};

type WorkRecord = {
  record_id: number;
  employee_id: string;
  work_date: string;
  start_minute: number;
  end_minute: number;
  is_holiday: boolean;
  break_total_minutes: number;
  span_minutes: number;
  work_minutes: number;
};

function currentYearMonth() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
}

function moveMonth(ym: string, amount: number) {
  const [year, month] = ym.split("-").map(Number);
  const d = new Date(year, month - 1 + amount, 1);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
}

function minuteToTime(value: number) {
  return `${String(Math.floor(value / 60)).padStart(2, "0")}:${String(
    value % 60
  ).padStart(2, "0")}`;
}

function formatMinutes(value: number) {
  const hours = Math.floor(value / 60);
  const minutes = value % 60;
  return `${hours}時間${minutes ? `${minutes}分` : ""}`;
}

export default function AttendanceAdminPage() {
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [selected, setSelected] = useState<Employee | null>(null);
  const [records, setRecords] = useState<WorkRecord[]>([]);
  const [search, setSearch] = useState("");
  const [yearMonth, setYearMonth] = useState(currentYearMonth);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [editor, setEditor] = useState<AttendanceForm | null>(null);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [auditItems, setAuditItems] = useState<AuditItem[]>([]);

  async function loadAudit() {
    try {
      const res = await fetch(`${API_BASE}/audit?limit=100`, {
        credentials: "include",
        cache: "no-store",
      });

      if (!res.ok) return;

      const items: AuditItem[] = await res.json();

      setAuditItems(
        items.filter((item) =>
          ["勤怠追加", "勤怠編集", "勤怠削除", "勤怠打刻"].includes(
            item.action
          )
        )
      );
    } catch {
      // 勤怠一覧の利用は継続する
    }
  }

  async function loadEmployees() {
    try {
      const res = await fetch(`${API_BASE}/employees`, {
        credentials: "include",
        cache: "no-store",
      });

      if (!res.ok) {
        setError(`従業員一覧を取得できませんでした: ${res.status}`);
        return;
      }

      setEmployees(await res.json());
    } catch {
      setError("従業員一覧の取得中に通信エラーが発生しました。");
    }
  }

  async function loadAttendance(
    employee: Employee,
    month: string = yearMonth
  ) {
    setLoading(true);
    setError("");

    try {
      const res = await fetch(
        `${API_BASE}/attendance/${month}?employee_id=${encodeURIComponent(
          employee.employee_id
        )}`,
        {
          credentials: "include",
          cache: "no-store",
        }
      );

      if (!res.ok) {
        const body = await res.json().catch(() => null);
        setError(
          body?.detail
            ? `勤怠を取得できませんでした: ${body.detail}`
            : `勤怠を取得できませんでした: ${res.status}`
        );
        return;
      }

      setRecords(await res.json());
    } catch {
      setError("勤怠の取得中に通信エラーが発生しました。");
    } finally {
      setLoading(false);
    }
  }

  function timeToMinute(value: string) {
    const [hour, minute] = value.split(":").map(Number);
    return hour * 60 + minute;
  }

  function openNewAttendance() {
    if (!selected) return;

    setError("");
    setMessage("");

    setEditor({
      record_id: null,
      work_date: `${yearMonth}-01`,
      start: "09:00",
      end: "18:00",
      break_minutes: "60",
      is_holiday: false,
    });
  }

  function openEditAttendance(record: WorkRecord) {
    setError("");
    setMessage("");

    setEditor({
      record_id: record.record_id,
      work_date: record.work_date,
      start: minuteToTime(record.start_minute),
      end: minuteToTime(record.end_minute),
      break_minutes: String(record.break_total_minutes),
      is_holiday: record.is_holiday,
    });
  }

  async function saveAttendance() {
    if (!selected || !editor) return;

    setSaving(true);
    setError("");
    setMessage("");

    try {
      const form = new FormData();
      form.append("employee_id", selected.employee_id);
      form.append("work_date", editor.work_date);
      form.append("start_minute", String(timeToMinute(editor.start)));
      form.append("end_minute", String(timeToMinute(editor.end)));
      form.append("break_minutes", editor.break_minutes || "0");
      form.append("is_holiday", editor.is_holiday ? "1" : "0");

      if (editor.record_id !== null) {
        form.append("record_id", String(editor.record_id));
      }

      const res = await fetch(`${API_BASE}/attendance`, {
        method: "POST",
        credentials: "include",
        body: form,
      });

      if (!res.ok) {
        const body = await res.json().catch(() => null);
        setError(
          body?.detail
            ? `保存できませんでした: ${body.detail}`
            : `保存できませんでした: ${res.status}`
        );
        return;
      }

      setEditor(null);
      setMessage("勤怠を保存しました。");
      await loadAttendance(selected, yearMonth);
      await loadAudit();
    } catch {
      setError("勤怠の保存中に通信エラーが発生しました。");
    } finally {
      setSaving(false);
    }
  }

  async function deleteAttendance(record: WorkRecord) {
    if (!selected) return;

    const confirmed = window.confirm(
      `${record.work_date} の勤怠を削除しますか？`
    );

    if (!confirmed) return;

    setError("");
    setMessage("");

    try {
      const form = new FormData();
      form.append("employee_id", selected.employee_id);
      form.append("record_id", String(record.record_id));

      const res = await fetch(`${API_BASE}/attendance/delete`, {
        method: "POST",
        credentials: "include",
        body: form,
      });

      if (!res.ok) {
        const body = await res.json().catch(() => null);
        setError(
          body?.detail
            ? `削除できませんでした: ${body.detail}`
            : `削除できませんでした: ${res.status}`
        );
        return;
      }

      if (editor?.record_id === record.record_id) {
        setEditor(null);
      }

      setMessage("勤怠を削除しました。");
      await loadAttendance(selected, yearMonth);
      await loadAudit();
    } catch {
      setError("勤怠の削除中に通信エラーが発生しました。");
    }
  }

  function selectEmployee(employee: Employee) {
    if (selected?.employee_id === employee.employee_id) {
      setSelected(null);
      setRecords([]);
      return;
    }

    setSelected(employee);
    loadAttendance(employee);
  }

  useEffect(() => {
    loadEmployees();
    loadAudit();
  }, []);

  useEffect(() => {
    if (selected) {
      loadAttendance(selected, yearMonth);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [yearMonth]);

  const filteredEmployees = useMemo(() => {
    const q = search.trim().toLowerCase();

    if (!q) return employees;

    return employees.filter(
      (employee) =>
        employee.employee_id.toLowerCase().includes(q) ||
        employee.name.toLowerCase().includes(q)
    );
  }, [employees, search]);

  const summary = useMemo(() => {
    return {
      days: records.length,
      workMinutes: records.reduce(
        (sum, record) => sum + record.work_minutes,
        0
      ),
      holidayDays: records.filter((record) => record.is_holiday).length,
    };
  }, [records]);

  return (
    <AuthGuard allow={["admin"]}>
      <main
        style={{
          maxWidth: 1250,
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
            flexWrap: "wrap",
            marginBottom: 25,
          }}
        >
          <div>
            <div
              style={{
                color: "#8390ff",
                fontSize: 11,
                fontWeight: 800,
                letterSpacing: ".12em",
              }}
            >
              会社側
            </div>

            <h1 style={{ margin: "7px 0 5px", fontSize: 30 }}>
              勤怠管理
            </h1>

            <p style={{ margin: 0, color: "#8298ae", fontSize: 12 }}>
              従業員ごとの勤務実績を確認・管理します。
            </p>
          </div>

          <div style={{ display: "flex", gap: 7, flexWrap: "wrap" }}>
            <button
              onClick={() => setYearMonth(moveMonth(yearMonth, -1))}
              style={buttonStyle}
            >
              ← 前月
            </button>

            <button
              onClick={() => setYearMonth(currentYearMonth())}
              style={buttonStyle}
            >
              今月
            </button>

            <button
              onClick={() => setYearMonth(moveMonth(yearMonth, 1))}
              style={buttonStyle}
            >
              次月 →
            </button>

            <input
              type="month"
              value={yearMonth}
              onChange={(e) => setYearMonth(e.target.value)}
              style={{ height: 39, padding: "0 10px" }}
            />
          </div>
        </header>

        {error && (
          <div
            style={{
              marginBottom: 15,
              padding: 12,
              color: "#ff9aa6",
              border: "1px solid rgba(255,107,122,.2)",
              borderRadius: 10,
              background: "rgba(255,107,122,.06)",
            }}
          >
            {error}
          </div>
        )}

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "300px minmax(0, 1fr)",
            gap: 18,
            alignItems: "start",
          }}
        >
          <section style={panelStyle}>
            <h2 style={{ margin: "0 0 13px", fontSize: 15 }}>
              従業員
            </h2>

            <input
              type="search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="社員番号・氏名で検索"
              style={{
                width: "100%",
                padding: 10,
                marginBottom: 9,
              }}
            />

            <div
              style={{
                marginBottom: 9,
                color: "#758da5",
                fontSize: 10,
              }}
            >
              {filteredEmployees.length} / {employees.length} 人
            </div>

            <div
              style={{
                maxHeight: 560,
                overflowY: "auto",
                paddingRight: 4,
              }}
            >
              {filteredEmployees.map((employee) => {
                const active =
                  selected?.employee_id === employee.employee_id;

                return (
                  <button
                    key={employee.employee_id}
                    onClick={() => selectEmployee(employee)}
                    style={{
                      width: "100%",
                      display: "flex",
                      alignItems: "center",
                      gap: 10,
                      padding: 10,
                      marginBottom: 6,
                      textAlign: "left",
                      color: "#fff",
                      border: active
                        ? "1px solid rgba(109,124,255,.45)"
                        : "1px solid rgba(148,180,216,.10)",
                      borderRadius: 10,
                      background: active
                        ? "rgba(109,124,255,.15)"
                        : "rgba(8,19,33,.5)",
                      cursor: "pointer",
                    }}
                  >
                    <span
                      style={{
                        width: 34,
                        height: 34,
                        display: "grid",
                        placeItems: "center",
                        flex: "0 0 auto",
                        borderRadius: 9,
                        color: "#dce2ff",
                        background: "rgba(109,124,255,.18)",
                        fontWeight: 800,
                      }}
                    >
                      {employee.name.trim()[0] || "?"}
                    </span>

                    <span style={{ minWidth: 0 }}>
                      <strong
                        style={{
                          display: "block",
                          fontSize: 12,
                          overflow: "hidden",
                          textOverflow: "ellipsis",
                        }}
                      >
                        {employee.name}
                      </strong>

                      <small style={{ color: "#71879d" }}>
                        {employee.employee_id}
                      </small>
                    </span>
                  </button>
                );
              })}
            </div>
          </section>

          <section>
            {!selected ? (
              <div
                style={{
                  ...panelStyle,
                  minHeight: 350,
                  display: "grid",
                  placeItems: "center",
                  textAlign: "center",
                  color: "#8298ae",
                }}
              >
                <div>
                  <div style={{ fontSize: 28, marginBottom: 10 }}>◷</div>
                  <strong>従業員を選択してください</strong>
                  <p style={{ fontSize: 11 }}>
                    左の一覧から勤怠を確認する従業員を選択します。
                  </p>
                </div>
              </div>
            ) : (
              <>
                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(3, minmax(0, 1fr))",
                    gap: 10,
                    marginBottom: 13,
                  }}
                >
                  <Stat title="勤務日数" value={`${summary.days}日`} />
                  <Stat
                    title="実働時間"
                    value={formatMinutes(summary.workMinutes)}
                  />
                  <Stat
                    title="休日勤務"
                    value={`${summary.holidayDays}日`}
                  />
                </div>

                <div style={panelStyle}>
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      gap: 12,
                      paddingBottom: 14,
                      marginBottom: 10,
                      borderBottom:
                        "1px solid rgba(148,180,216,.10)",
                    }}
                  >
                    <div>
                      <strong>{selected.name}</strong>
                      <span
                        style={{
                          marginLeft: 9,
                          color: "#71879d",
                          fontSize: 10,
                        }}
                      >
                        {selected.employee_id}
                      </span>
                    </div>

                    <button
                      onClick={openNewAttendance}
                      style={{
                        padding: "8px 12px",
                        border:
                          "1px solid rgba(109,124,255,.32)",
                        borderRadius: 9,
                        color: "#fff",
                        background:
                          "linear-gradient(135deg, #6d7cff, #5164e8)",
                        cursor: "pointer",
                        fontSize: 10,
                        fontWeight: 750,
                      }}
                    >
                      ＋ 勤怠を追加
                    </button>
                  </div>

                  {message && (
                    <div
                      style={{
                        marginBottom: 10,
                        padding: 10,
                        color: "#65e6b5",
                        border: "1px solid rgba(69,224,168,.16)",
                        borderRadius: 9,
                        background: "rgba(69,224,168,.06)",
                        fontSize: 10,
                      }}
                    >
                      {message}
                    </div>
                  )}

                  {editor && (
                    <div
                      style={{
                        marginBottom: 14,
                        padding: 16,
                        border: "1px solid rgba(109,124,255,.22)",
                        borderRadius: 12,
                        background:
                          "linear-gradient(145deg, rgba(109,124,255,.08), rgba(8,19,33,.65))",
                      }}
                    >
                      <div
                        style={{
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "space-between",
                          gap: 10,
                          marginBottom: 13,
                        }}
                      >
                        <strong style={{ fontSize: 13 }}>
                          {editor.record_id === null
                            ? "勤怠を追加"
                            : "勤怠を編集"}
                        </strong>

                        <span
                          style={{
                            color: "#71879d",
                            fontSize: 9,
                          }}
                        >
                          {selected.name} / {selected.employee_id}
                        </span>
                      </div>

                      <div
                        style={{
                          display: "grid",
                          gridTemplateColumns:
                            "repeat(auto-fit, minmax(140px, 1fr))",
                          gap: 10,
                        }}
                      >
                        <label style={labelStyle}>
                          日付
                          <input
                            type="date"
                            value={editor.work_date}
                            onChange={(e) =>
                              setEditor({
                                ...editor,
                                work_date: e.target.value,
                              })
                            }
                            style={inputStyle}
                          />
                        </label>

                        <label style={labelStyle}>
                          出勤
                          <input
                            type="time"
                            value={editor.start}
                            onChange={(e) =>
                              setEditor({
                                ...editor,
                                start: e.target.value,
                              })
                            }
                            style={inputStyle}
                          />
                        </label>

                        <label style={labelStyle}>
                          退勤
                          <input
                            type="time"
                            value={editor.end}
                            onChange={(e) =>
                              setEditor({
                                ...editor,
                                end: e.target.value,
                              })
                            }
                            style={inputStyle}
                          />
                        </label>

                        <label style={labelStyle}>
                          休憩（分）
                          <input
                            type="number"
                            min="0"
                            value={editor.break_minutes}
                            onChange={(e) =>
                              setEditor({
                                ...editor,
                                break_minutes: e.target.value,
                              })
                            }
                            style={inputStyle}
                          />
                        </label>

                        <label
                          style={{
                            ...labelStyle,
                            display: "flex",
                            alignItems: "center",
                            gap: 8,
                            paddingTop: 22,
                          }}
                        >
                          <input
                            type="checkbox"
                            checked={editor.is_holiday}
                            onChange={(e) =>
                              setEditor({
                                ...editor,
                                is_holiday: e.target.checked,
                              })
                            }
                          />
                          休日勤務
                        </label>
                      </div>

                      <div
                        style={{
                          display: "flex",
                          gap: 8,
                          marginTop: 14,
                        }}
                      >
                        <button
                          onClick={saveAttendance}
                          disabled={saving}
                          style={{
                            padding: "8px 14px",
                            border:
                              "1px solid rgba(69,224,168,.25)",
                            borderRadius: 9,
                            color: "#07151a",
                            background:
                              "linear-gradient(135deg, #45e0a8, #38d9c4)",
                            cursor: "pointer",
                            fontWeight: 800,
                            fontSize: 10,
                          }}
                        >
                          {saving ? "保存中..." : "保存"}
                        </button>

                        <button
                          onClick={() => setEditor(null)}
                          disabled={saving}
                          style={buttonStyle}
                        >
                          キャンセル
                        </button>
                      </div>
                    </div>
                  )}

                  {loading ? (
                    <div style={emptyStyle}>読み込み中...</div>
                  ) : records.length === 0 ? (
                    <div style={emptyStyle}>
                      この月の勤怠はありません。
                    </div>
                  ) : (
                    records.map((record) => (
                      <div
                        key={record.record_id}
                        style={{
                          display: "grid",
                          gridTemplateColumns:
                            "120px minmax(170px,1fr) 90px 90px 120px",
                          gap: 12,
                          alignItems: "center",
                          padding: "12px 8px",
                          borderBottom:
                            "1px solid rgba(148,180,216,.08)",
                        }}
                      >
                        <strong style={{ fontSize: 11 }}>
                          {record.work_date}
                        </strong>

                        <span style={{ fontWeight: 700 }}>
                          {minuteToTime(record.start_minute)}
                          <span
                            style={{
                              margin: "0 8px",
                              color: "#536b83",
                            }}
                          >
                            →
                          </span>
                          {minuteToTime(record.end_minute)}
                        </span>

                        <span
                          style={{
                            color: "#8298ae",
                            fontSize: 10,
                          }}
                        >
                          休憩 {record.break_total_minutes}分
                        </span>

                        <strong style={{ textAlign: "right" }}>
                          {formatMinutes(record.work_minutes)}
                        </strong>

                        <div
                          style={{
                            display: "flex",
                            justifyContent: "flex-end",
                            gap: 6,
                          }}
                        >
                          <button
                            onClick={() => openEditAttendance(record)}
                            style={{
                              padding: "6px 9px",
                              border:
                                "1px solid rgba(109,124,255,.22)",
                              borderRadius: 7,
                              color: "#aeb7ff",
                              background: "rgba(109,124,255,.07)",
                              cursor: "pointer",
                              fontSize: 9,
                            }}
                          >
                            編集
                          </button>

                          <button
                            onClick={() => deleteAttendance(record)}
                            style={{
                              padding: "6px 9px",
                              border:
                                "1px solid rgba(255,107,122,.20)",
                              borderRadius: 7,
                              color: "#ff9aa6",
                              background: "rgba(255,107,122,.06)",
                              cursor: "pointer",
                              fontSize: 9,
                            }}
                          >
                            削除
                          </button>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </>
            )}
          </section>
        </div>

        <section
          style={{
            ...panelStyle,
            marginTop: 18,
          }}
        >
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              gap: 12,
              paddingBottom: 13,
              marginBottom: 5,
              borderBottom: "1px solid rgba(148,180,216,.10)",
            }}
          >
            <div>
              <strong style={{ fontSize: 14 }}>最近の勤怠変更履歴</strong>
              <div
                style={{
                  marginTop: 3,
                  color: "#71879d",
                  fontSize: 9,
                }}
              >
                打刻・追加・編集・削除の履歴
              </div>
            </div>

            <button
              onClick={loadAudit}
              style={buttonStyle}
            >
              再取得
            </button>
          </div>

          {auditItems.length === 0 ? (
            <div
              style={{
                padding: 30,
                textAlign: "center",
                color: "#71879d",
                fontSize: 11,
              }}
            >
              勤怠の変更履歴はまだありません。
            </div>
          ) : (
            <div
              style={{
                maxHeight: 300,
                overflowY: "auto",
              }}
            >
              {auditItems.map((item, index) => {
                const color =
                  item.action === "勤怠削除"
                    ? "#ff9aa6"
                    : item.action === "勤怠編集"
                      ? "#f6c85f"
                      : item.action === "勤怠打刻"
                        ? "#67e7b8"
                        : "#9ba5ff";

                return (
                  <div
                    key={`${item.created_at}-${item.action}-${index}`}
                    style={{
                      display: "grid",
                      gridTemplateColumns: "150px 90px 120px minmax(0,1fr)",
                      gap: 14,
                      alignItems: "center",
                      padding: "11px 7px",
                      borderBottom:
                        "1px solid rgba(148,180,216,.07)",
                    }}
                  >
                    <span
                      style={{
                        color: "#71879d",
                        fontSize: 10,
                      }}
                    >
                      {new Date(item.created_at).toLocaleString("ja-JP")}
                    </span>

                    <span
                      style={{
                        width: "max-content",
                        padding: "4px 7px",
                        color,
                        border: `1px solid ${color}33`,
                        borderRadius: 999,
                        background: `${color}0d`,
                        fontSize: 9,
                        fontWeight: 750,
                      }}
                    >
                      {item.action}
                    </span>

                    <strong style={{ fontSize: 10 }}>
                      {item.subject}
                    </strong>

                    <span
                      style={{
                        color: "#879db3",
                        fontSize: 10,
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        whiteSpace: "nowrap",
                      }}
                    >
                      {item.detail}
                    </span>
                  </div>
                );
              })}
            </div>
          )}
        </section>
      </main>
    </AuthGuard>
  );
}

const labelStyle = {
  color: "#9eb0c5",
  fontSize: 10,
  fontWeight: 700,
} as const;

const inputStyle = {
  display: "block",
  width: "100%",
  height: 38,
  marginTop: 6,
  padding: "0 9px",
} as const;

const panelStyle = {
  padding: 17,
  border: "1px solid rgba(148,180,216,.13)",
  borderRadius: 15,
  background: "rgba(12,25,43,.66)",
} as const;

const buttonStyle = {
  height: 39,
  padding: "0 12px",
  border: "1px solid rgba(148,180,216,.14)",
  borderRadius: 10,
  color: "#b8c8d8",
  background: "rgba(255,255,255,.025)",
  cursor: "pointer",
  fontSize: 11,
  fontWeight: 700,
} as const;

const emptyStyle = {
  padding: 50,
  color: "#8298ae",
  textAlign: "center",
} as const;

function Stat({ title, value }: { title: string; value: string }) {
  return (
    <div style={panelStyle}>
      <span style={{ color: "#8298ae", fontSize: 10 }}>{title}</span>
      <strong
        style={{
          display: "block",
          marginTop: 7,
          fontSize: 20,
        }}
      >
        {value}
      </strong>
    </div>
  );
}
