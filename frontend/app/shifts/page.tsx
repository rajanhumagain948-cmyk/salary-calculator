"use client";

import { useEffect, useState } from "react";

const API_BASE = "http://localhost:8000";

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

export default function ShiftsPage() {
  const [yearMonth, setYearMonth] = useState("2026-08");
  const [employeeId, setEmployeeId] = useState("");
  const [shifts, setShifts] = useState<Shift[]>([]);
  const [error, setError] = useState("");

  async function load() {
    setError("");
    setShifts([]);

    const params = employeeId ? `?employee_id=${encodeURIComponent(employeeId)}` : "";
    const res = await fetch(`${API_BASE}/shifts/${yearMonth}${params}`, {
      credentials: "include",
    });

    if (!res.ok) {
      setError(`取得失敗: ${res.status}`);
      return;
    }

    setShifts(await res.json());
  }

  useEffect(() => {
    // 初回は手動更新でもOK。自動で読みたいなら load() を呼ぶ。
  }, []);

  return (
    <main style={{ maxWidth: 900, margin: "6vh auto", fontFamily: "system-ui" }}>
      <h1>シフト</h1>

      <div style={{ display: "flex", gap: 12, alignItems: "end", marginTop: 12 }}>
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
            style={{ width: 180, padding: 8, display: "block" }}
          />
        </label>

        <button onClick={load} style={{ padding: "10px 14px", fontWeight: 700 }}>
          取得
        </button>
      </div>

      {error && <p style={{ color: "crimson", marginTop: 12 }}>{error}</p>}

      <table style={{ width: "100%", marginTop: 16, borderCollapse: "collapse" }}>
        <thead>
          <tr>
            {["日付", "開始", "終了", "休憩", "メモ", "確定"].map((h) => (
              <th key={h} style={{ textAlign: "left", borderBottom: "1px solid #ddd", padding: 8 }}>
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {shifts.map((s) => (
            <tr key={s.shift_id ?? `${s.employee_id}-${s.shift_date}`}>
              <td style={{ padding: 8, borderBottom: "1px solid #eee" }}>{s.shift_date}</td>
              <td style={{ padding: 8, borderBottom: "1px solid #eee" }}>{Math.floor(s.start_minute / 60).toString().padStart(2, "0")}:{(s.start_minute % 60).toString().padStart(2, "0")}</td>
              <td style={{ padding: 8, borderBottom: "1px solid #eee" }}>{Math.floor(s.end_minute / 60).toString().padStart(2, "0")}:{(s.end_minute % 60).toString().padStart(2, "0")}</td>
              <td style={{ padding: 8, borderBottom: "1px solid #eee" }}>{s.break_minutes}</td>
              <td style={{ padding: 8, borderBottom: "1px solid #eee" }}>{s.note}</td>
              <td style={{ padding: 8, borderBottom: "1px solid #eee" }}>{s.confirmed ? "○" : ""}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </main>
  );
}
