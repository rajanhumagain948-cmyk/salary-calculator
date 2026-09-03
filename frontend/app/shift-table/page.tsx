"use client";

import { useEffect, useMemo, useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

type Me = {
  username: string;
  role: "admin" | "employee";
  employee_id: string | null;
};

type Emp = {
  employee_id: string;
  name: string;
};

type Shift = {
  shift_id: number | null;
  employee_id: string;
  shift_date: string;
  start_minute: number;
  end_minute: number;
  break_minutes: number;
  note: string;
  confirmed: boolean;
};

type Editor = {
  employee_id: string;
  employee_name: string;
  shift_date: string;
  shift_id: number | null;
  start: string;
  end: string;
  break_minutes: string;
  note: string;
  confirmed: boolean;
};

function daysInMonth(ym: string) {
  const [y, m] = ym.split("-").map(Number);
  return new Date(y, m, 0).getDate();
}

function weekdayJP(d: Date) {
  return ["日", "月", "火", "水", "木", "金", "土"][d.getDay()];
}

function fmtMinute(m: number) {
  const h = Math.floor(m / 60).toString().padStart(2, "0");
  const mm = (m % 60).toString().padStart(2, "0");
  return `${h}:${mm}`;
}

function timeToMinute(value: string) {
  const [h, m] = value.split(":").map(Number);
  return h * 60 + m;
}

export default function ShiftTablePage() {
  const [me, setMe] = useState<Me | null>(null);
  const [yearMonth, setYearMonth] = useState("2026-08");
  const [employees, setEmployees] = useState<Emp[]>([]);
  const [shiftMap, setShiftMap] = useState<Record<string, Shift>>({});
  const [editor, setEditor] = useState<Editor | null>(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [saving, setSaving] = useState(false);

  const dayCount = useMemo(() => daysInMonth(yearMonth), [yearMonth]);

  async function loadMe() {
    const res = await fetch(`${API_BASE}/me`, { credentials: "include" });
    if (!res.ok) {
      setMe(null);
      setError("未ログインです。");
      return;
    }
    setMe(await res.json());
  }

  async function loadEmployees() {
    const res = await fetch(`${API_BASE}/employees`, {
      credentials: "include",
    });

    if (!res.ok) {
      setError(`従業員取得失敗: ${res.status}`);
      return;
    }

    setEmployees(await res.json());
  }

  async function loadShiftsForAll() {
    const map: Record<string, Shift> = {};

    for (const emp of employees) {
      const res = await fetch(
        `${API_BASE}/shifts/${yearMonth}?employee_id=${encodeURIComponent(
          emp.employee_id
        )}`,
        { credentials: "include" }
      );

      if (!res.ok) continue;

      const shifts: Shift[] = await res.json();

      for (const s of shifts) {
        map[`${s.employee_id}|${s.shift_date}`] = s;
      }
    }

    setShiftMap(map);
  }

  async function refresh() {
    setError("");
    await loadMe();
    await loadEmployees();
  }

  function openEditor(emp: Emp, dateStr: string) {
    setError("");
    setMessage("");

    const shift = shiftMap[`${emp.employee_id}|${dateStr}`];

    setEditor({
      employee_id: emp.employee_id,
      employee_name: emp.name,
      shift_date: dateStr,
      shift_id: shift?.shift_id ?? null,
      start: shift ? fmtMinute(shift.start_minute) : "09:00",
      end: shift ? fmtMinute(shift.end_minute) : "18:00",
      break_minutes: String(shift?.break_minutes ?? 60),
      note: shift?.note ?? "",
      confirmed: shift?.confirmed ?? false,
    });
  }

  async function saveShift() {
    if (!editor) return;

    setError("");
    setMessage("");

    if (!editor.start || !editor.end) {
      setError("開始時刻と終了時刻を入力してください。");
      return;
    }

    const startMinute = timeToMinute(editor.start);
    const endMinute = timeToMinute(editor.end);

    if (endMinute <= startMinute) {
      setError("終了時刻は開始時刻より後にしてください。");
      return;
    }

    setSaving(true);

    try {
      const form = new FormData();
      form.append("employee_id", editor.employee_id);
      form.append("shift_date", editor.shift_date);
      form.append("start_minute", String(startMinute));
      form.append("end_minute", String(endMinute));
      form.append("break_minutes", editor.break_minutes || "0");
      form.append("note", editor.note);
      form.append("confirmed", editor.confirmed ? "1" : "0");

      if (editor.shift_id !== null) {
        form.append("shift_id", String(editor.shift_id));
      }

      const res = await fetch(`${API_BASE}/shifts`, {
        method: "POST",
        credentials: "include",
        body: form,
      });

      if (!res.ok) {
        const text = await res.text();
        setError(`保存失敗: ${res.status} ${text}`);
        return;
      }

      await loadShiftsForAll();
      setEditor(null);
      setMessage("シフトを保存しました。");
    } catch {
      setError("保存中に通信エラーが発生しました。");
    } finally {
      setSaving(false);
    }
  }

  async function deleteShift() {
    if (!editor || editor.shift_id === null) return;

    if (!window.confirm("このシフトを削除しますか？")) return;

    setError("");
    setMessage("");
    setSaving(true);

    try {
      const form = new FormData();
      form.append("employee_id", editor.employee_id);
      form.append("shift_id", String(editor.shift_id));

      const res = await fetch(`${API_BASE}/shifts/delete`, {
        method: "POST",
        credentials: "include",
        body: form,
      });

      if (!res.ok) {
        const text = await res.text();
        setError(`削除失敗: ${res.status} ${text}`);
        return;
      }

      await loadShiftsForAll();
      setEditor(null);
      setMessage("シフトを削除しました。");
    } catch {
      setError("削除中に通信エラーが発生しました。");
    } finally {
      setSaving(false);
    }
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    setEditor(null);

    if (employees.length > 0) {
      loadShiftsForAll();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [employees, yearMonth]);

  if (me && me.role !== "admin") {
    return (
      <main style={{ maxWidth: 900, margin: "6vh auto" }}>
        管理者専用ページです。
      </main>
    );
  }

  return (
    <main style={{ padding: 16, fontFamily: "system-ui" }}>
      <h1>月間シフト表（管理者）</h1>

      <div
        style={{
          display: "flex",
          gap: 12,
          alignItems: "end",
          flexWrap: "wrap",
        }}
      >
        <label>
          対象年月（YYYY-MM）
          <input
            type="month"
            value={yearMonth}
            onChange={(e) => setYearMonth(e.target.value)}
            style={{ display: "block", padding: 8 }}
          />
        </label>

        <button
          onClick={refresh}
          style={{ padding: "10px 14px", fontWeight: 700 }}
        >
          従業員再取得
        </button>
      </div>

      {error && <p style={{ color: "#ff6b6b" }}>{error}</p>}
      {message && <p style={{ color: "#5ee28a" }}>{message}</p>}

      <div
        style={{
          overflowX: "auto",
          border: "1px solid #555",
          marginTop: 12,
        }}
      >
        <table
          style={{
            borderCollapse: "collapse",
            minWidth: 1200,
            width: "100%",
          }}
        >
          <thead>
            <tr>
              <th
                style={{
                  position: "sticky",
                  left: 0,
                  zIndex: 2,
                  background: "#111",
                  color: "#fff",
                  borderBottom: "1px solid #555",
                  padding: 6,
                }}
              >
                社員番号
              </th>

              <th
                style={{
                  position: "sticky",
                  left: 90,
                  zIndex: 2,
                  background: "#111",
                  color: "#fff",
                  borderBottom: "1px solid #555",
                  padding: 6,
                }}
              >
                氏名
              </th>

              {Array.from({ length: dayCount }).map((_, i) => {
                const day = i + 1;
                const dateStr = `${yearMonth}-${String(day).padStart(2, "0")}`;
                const d = new Date(`${dateStr}T00:00:00`);

                return (
                  <th
                    key={day}
                    style={{
                      borderBottom: "1px solid #555",
                      padding: 6,
                      whiteSpace: "nowrap",
                    }}
                  >
                    {String(day).padStart(2, "0")}({weekdayJP(d)})
                  </th>
                );
              })}
            </tr>
          </thead>

          <tbody>
            {employees.map((emp) => (
              <tr key={emp.employee_id}>
                <td
                  style={{
                    position: "sticky",
                    left: 0,
                    zIndex: 1,
                    background: "#111",
                    color: "#fff",
                    borderBottom: "1px solid #444",
                    padding: 6,
                    whiteSpace: "nowrap",
                  }}
                >
                  {emp.employee_id}
                </td>

                <td
                  style={{
                    position: "sticky",
                    left: 90,
                    zIndex: 1,
                    background: "#111",
                    color: "#fff",
                    borderBottom: "1px solid #444",
                    padding: 6,
                    whiteSpace: "nowrap",
                  }}
                >
                  {emp.name}
                </td>

                {Array.from({ length: dayCount }).map((_, i) => {
                  const day = i + 1;
                  const dateStr = `${yearMonth}-${String(day).padStart(2, "0")}`;
                  const key = `${emp.employee_id}|${dateStr}`;
                  const shift = shiftMap[key];

                  return (
                    <td
                      key={key}
                      onClick={() => openEditor(emp, dateStr)}
                      title="クリックして編集"
                      style={{
                        borderBottom: "1px solid #444",
                        borderLeft: "1px solid #333",
                        padding: 8,
                        textAlign: "center",
                        whiteSpace: "nowrap",
                        cursor: "pointer",
                        background: shift ? "#17351f" : "transparent",
                        minWidth: 105,
                      }}
                    >
                      {shift
                        ? `${fmtMinute(shift.start_minute)}-${fmtMinute(
                            shift.end_minute
                          )}`
                        : "＋"}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {editor && (
        <div
          style={{
            marginTop: 20,
            border: "1px solid #666",
            borderRadius: 8,
            padding: 16,
            maxWidth: 600,
            background: "#151515",
          }}
        >
          <h2 style={{ marginTop: 0 }}>
            {editor.employee_name} / {editor.shift_date}
          </h2>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(2, minmax(150px, 1fr))",
              gap: 12,
            }}
          >
            <label>
              開始
              <input
                type="time"
                value={editor.start}
                onChange={(e) =>
                  setEditor({ ...editor, start: e.target.value })
                }
                style={{ display: "block", padding: 8, width: "100%" }}
              />
            </label>

            <label>
              終了
              <input
                type="time"
                value={editor.end}
                onChange={(e) =>
                  setEditor({ ...editor, end: e.target.value })
                }
                style={{ display: "block", padding: 8, width: "100%" }}
              />
            </label>

            <label>
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
                style={{ display: "block", padding: 8, width: "100%" }}
              />
            </label>

            <label style={{ alignSelf: "end", paddingBottom: 8 }}>
              <input
                type="checkbox"
                checked={editor.confirmed}
                onChange={(e) =>
                  setEditor({
                    ...editor,
                    confirmed: e.target.checked,
                  })
                }
              />{" "}
              確定済み
            </label>
          </div>

          <label style={{ display: "block", marginTop: 12 }}>
            メモ
            <input
              value={editor.note}
              onChange={(e) =>
                setEditor({ ...editor, note: e.target.value })
              }
              style={{
                display: "block",
                padding: 8,
                width: "100%",
                boxSizing: "border-box",
              }}
            />
          </label>

          <div
            style={{
              display: "flex",
              gap: 10,
              marginTop: 16,
              flexWrap: "wrap",
            }}
          >
            <button
              onClick={saveShift}
              disabled={saving}
              style={{ padding: "10px 18px", fontWeight: 700 }}
            >
              {saving ? "処理中..." : "保存"}
            </button>

            {editor.shift_id !== null && (
              <button
                onClick={deleteShift}
                disabled={saving}
                style={{
                  padding: "10px 18px",
                  color: "#fff",
                  background: "#a22",
                  border: 0,
                  borderRadius: 4,
                }}
              >
                削除
              </button>
            )}

            <button
              onClick={() => setEditor(null)}
              disabled={saving}
              style={{ padding: "10px 18px" }}
            >
              キャンセル
            </button>
          </div>
        </div>
      )}

      <p style={{ marginTop: 12, color: "#aaa" }}>
        シフトのあるセルをクリックすると編集、＋のセルをクリックすると新規追加できます。
      </p>
    </main>
  );
}
