"use client";

import { useEffect, useState } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

type Me = {
  username: string;
  role: "admin" | "employee";
  employee_id: string | null;
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

function fmtMinute(m: number) {
  const h = Math.floor(m / 60)
    .toString()
    .padStart(2, "0");
  const mm = (m % 60).toString().padStart(2, "0");
  return `${h}:${mm}`;
}

function toMinute(hhmm: string) {
  const [h, m] = hhmm.split(":").map((x) => parseInt(x, 10));
  return h * 60 + m;
}

export default function ShiftsPage() {
  const [me, setMe] = useState<Me | null>(null);
  const [yearMonth, setYearMonth] = useState("2026-08");
  const [employeeId, setEmployeeId] = useState(""); // adminのみ使用
  const [shifts, setShifts] = useState<Shift[]>([]);
  const [error, setError] = useState("");

  // --- 追加フォーム（管理者用） ---
  const [newDate, setNewDate] = useState("2026-08-29"); // YYYY-MM-DD
  const [newStart, setNewStart] = useState("09:00");
  const [newEnd, setNewEnd] = useState("18:00");
  const [newBreak, setNewBreak] = useState(60);
  const [newNote, setNewNote] = useState("web-ui");
  const [newConfirmed, setNewConfirmed] = useState(true);

  async function loadMe() {
    setError("");
    const res = await fetch(`${API_BASE}/me`, { credentials: "include" });
    if (!res.ok) {
      setMe(null);
      setError("未ログインです。トップでログインしてください。");
      return;
    }
    setMe(await res.json());
  }

  async function loadShifts() {
    setError("");
    setShifts([]);

    // adminのみ employee_id をクエリに付ける
    const params =
      me?.role === "admin" && employeeId
        ? `?employee_id=${encodeURIComponent(employeeId)}`
        : "";

    const res = await fetch(`${API_BASE}/shifts/${yearMonth}${params}`, {
      credentials: "include",
    });

    if (!res.ok) {
      setError(`取得失敗: ${res.status}`);
      return;
    }

    setShifts(await res.json());
  }

  async function addShift() {
    setError("");

    if (!me) {
      setError("未ログインです。");
      return;
    }
    if (me.role !== "admin") {
      setError("管理者のみ追加できます。");
      return;
    }
    if (!employeeId) {
      setError("管理者は employee_id を入力してください（例: W250651）");
      return;
    }

    const body = new URLSearchParams({
      employee_id: employeeId,
      shift_date: newDate,
      start_minute: String(toMinute(newStart)),
      end_minute: String(toMinute(newEnd)),
      break_minutes: String(newBreak),
      note: newNote,
      confirmed: newConfirmed ? "1" : "0",
    });

    const res = await fetch(`${API_BASE}/shifts`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: body.toString(),
      credentials: "include",
    });

    if (!res.ok) {
      setError(`追加失敗: ${res.status}`);
      return;
    }

    await loadShifts();
  }

  useEffect(() => {
    loadMe();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <main style={{ maxWidth: 980, margin: "6vh auto", fontFamily: "system-ui" }}>
      <h1>シフト</h1>

      <div style={{ marginTop: 8, color: "#444" }}>
        {me ? (
          <span>
            ログイン中: {me.username}（{me.role}
            {me.employee_id ? ` / ${me.employee_id}` : ""}）
          </span>
        ) : (
          <span>ログイン状態を確認中…</span>
        )}
      </div>

      <div
        style={{
          display: "flex",
          gap: 12,
          alignItems: "end",
          marginTop: 16,
          flexWrap: "wrap",
        }}
      >
        <label>
          対象年月 (YYYY-MM)
          <input
            value={yearMonth}
            onChange={(e) => setYearMonth(e.target.value)}
            style={{ width: 140, padding: 8, display: "block" }}
          />
        </label>

        <label>
          employee_id（管理者のみ）
          <input
            value={employeeId}
            onChange={(e) => setEmployeeId(e.target.value)}
            placeholder="W250651 など"
            disabled={me?.role !== "admin"}
            style={{ width: 180, padding: 8, display: "block" }}
          />
        </label>

        <button
          onClick={loadShifts}
          style={{ padding: "10px 14px", fontWeight: 700 }}
        >
          取得
        </button>
      </div>

      {me?.role === "admin" && (
        <section
          style={{
            marginTop: 18,
            padding: 12,
            border: "1px solid #ddd",
            borderRadius: 8,
          }}
        >
          <h2 style={{ margin: "0 0 10px", fontSize: 16 }}>
            シフト追加（管理者）
          </h2>

          <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
            <label>
              日付 (YYYY-MM-DD)
              <input
                value={newDate}
                onChange={(e) => setNewDate(e.target.value)}
                style={{ width: 150, padding: 8, display: "block" }}
              />
            </label>

            <label>
              開始 (HH:MM)
              <input
                value={newStart}
                onChange={(e) => setNewStart(e.target.value)}
                style={{ width: 110, padding: 8, display: "block" }}
              />
            </label>

            <label>
              終了 (HH:MM)
              <input
                value={newEnd}
                onChange={(e) => setNewEnd(e.target.value)}
                style={{ width: 110, padding: 8, display: "block" }}
              />
            </label>

            <label>
              休憩(分)
              <input
                value={newBreak}
                onChange={(e) => setNewBreak(parseInt(e.target.value || "0", 10))}
                style={{ width: 100, padding: 8, display: "block" }}
              />
            </label>

            <label style={{ flex: "1 1 240px" }}>
              メモ
              <input
                value={newNote}
                onChange={(e) => setNewNote(e.target.value)}
                style={{ width: "100%", padding: 8, display: "block" }}
              />
            </label>

            <label style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <input
                type="checkbox"
                checked={newConfirmed}
                onChange={(e) => setNewConfirmed(e.target.checked)}
              />
              確定
            </label>

            <button
              onClick={addShift}
              style={{ padding: "10px 14px", fontWeight: 700 }}
            >
              追加
            </button>
          </div>

          <p style={{ marginTop: 8, color: "#666" }}>
            ※ employee_id を入力してから追加してください（例: W250651）
          </p>
        </section>
      )}

      {error && <p style={{ color: "crimson", marginTop: 14 }}>{error}</p>}

      <table style={{ width: "100%", marginTop: 16, borderCollapse: "collapse" }}>
        <thead>
          <tr>
            {["日付", "開始", "終了", "休憩", "メモ", "確定"].map((h) => (
              <th
                key={h}
                style={{ textAlign: "left", borderBottom: "1px solid #ddd", padding: 8 }}
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {shifts.map((s) => (
            <tr key={s.shift_id ?? `${s.employee_id}-${s.shift_date}`}>
              <td style={{ padding: 8, borderBottom: "1px solid #eee" }}>
                {s.shift_date}
              </td>
              <td style={{ padding: 8, borderBottom: "1px solid #eee" }}>
                {fmtMinute(s.start_minute)}
              </td>
              <td style={{ padding: 8, borderBottom: "1px solid #eee" }}>
                {fmtMinute(s.end_minute)}
              </td>
              <td style={{ padding: 8, borderBottom: "1px solid #eee" }}>
                {s.break_minutes}
              </td>
              <td style={{ padding: 8, borderBottom: "1px solid #eee" }}>
                {s.note}
              </td>
              <td style={{ padding: 8, borderBottom: "1px solid #eee" }}>
                {s.confirmed ? "○" : ""}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <div style={{ marginTop: 14 }}>
        <a href="/" style={{ color: "#2563eb" }}>
          ← ログイン画面へ
        </a>
      </div>
    </main>
  );
}