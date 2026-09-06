"use client";

import { useEffect, useMemo, useState } from "react";
import AuthGuard from "@/components/auth/AuthGuard";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

type AttendanceEvent = {
  event_id: number;
  employee_id: string;
  event_at: string;
  event_type: "clock_in" | "break_start" | "break_end" | "clock_out";
  method: string;
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

function time(minute: number) {
  const h = Math.floor(minute / 60);
  const m = minute % 60;
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`;
}

function duration(minute: number) {
  const h = Math.floor(minute / 60);
  const m = minute % 60;
  return `${h}時間${m ? `${m}分` : ""}`;
}

function dateLabel(value: string) {
  const d = new Date(`${value}T00:00:00`);
  const [, month, day] = value.split("-");
  const week = ["日", "月", "火", "水", "木", "金", "土"][d.getDay()];
  return `${Number(month)}月${Number(day)}日（${week}）`;
}

export default function MyAttendancePage() {
  const [yearMonth, setYearMonth] = useState(currentYearMonth);
  const [records, setRecords] = useState<WorkRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [todayEvents, setTodayEvents] = useState<AttendanceEvent[]>([]);
  const [clocking, setClocking] = useState(false);
  const [clockMessage, setClockMessage] = useState("");

  async function loadTodayEvents() {
    try {
      const res = await fetch(`${API_BASE}/attendance/today/events`, {
        credentials: "include",
        cache: "no-store",
      });

      if (!res.ok) return;

      const data = await res.json();
      setTodayEvents(data.events ?? []);
    } catch {
      // 月間勤怠の表示は継続する
    }
  }

  async function loadAttendance(month = yearMonth) {
    setLoading(true);
    setError("");

    try {
      const res = await fetch(`${API_BASE}/attendance/${month}`, {
        credentials: "include",
        cache: "no-store",
      });

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

  async function clock(
    eventType: AttendanceEvent["event_type"]
  ) {
    setClocking(true);
    setError("");
    setClockMessage("");

    try {
      const form = new FormData();
      form.append("event_type", eventType);

      const res = await fetch(`${API_BASE}/attendance/clock`, {
        method: "POST",
        credentials: "include",
        body: form,
      });

      if (!res.ok) {
        const body = await res.json().catch(() => null);
        setError(
          body?.detail
            ? `打刻できませんでした: ${body.detail}`
            : `打刻できませんでした: ${res.status}`
        );
        return;
      }

      const labels: Record<AttendanceEvent["event_type"], string> = {
        clock_in: "出勤しました。",
        break_start: "休憩を開始しました。",
        break_end: "休憩を終了しました。",
        clock_out: "退勤しました。",
      };

      setClockMessage(labels[eventType]);

      await loadTodayEvents();

      if (eventType === "clock_out") {
        await loadAttendance(yearMonth);
      }
    } catch {
      setError("打刻中に通信エラーが発生しました。");
    } finally {
      setClocking(false);
    }
  }

  useEffect(() => {
    loadTodayEvents();
    loadAttendance(yearMonth);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [yearMonth]);

  const lastEvent =
    todayEvents.length > 0
      ? todayEvents[todayEvents.length - 1]
      : null;

  const attendanceStatus =
    !lastEvent
      ? "before"
      : lastEvent.event_type === "clock_out"
        ? "finished"
        : lastEvent.event_type === "break_start"
          ? "break"
          : "working";

  const summary = useMemo(() => {
    const total = records.reduce(
      (sum, record) => sum + record.work_minutes,
      0
    );

    const holidayCount = records.filter(
      (record) => record.is_holiday
    ).length;

    return {
      days: records.length,
      minutes: total,
      holidayCount,
    };
  }, [records]);

  return (
    <AuthGuard allow={["employee"]}>
      <main
        style={{
          maxWidth: 1180,
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
            marginBottom: 26,
          }}
        >
          <div>
            <div
              style={{
                color: "#45e0a8",
                fontSize: 11,
                fontWeight: 800,
                letterSpacing: ".12em",
              }}
            >
              勤怠
            </div>

            <h1 style={{ margin: "7px 0 5px", fontSize: 30 }}>
              自分の勤怠
            </h1>

            <p style={{ margin: 0, color: "#8298ae", fontSize: 12 }}>
              出勤・退勤・休憩時間と月間の勤務実績を確認できます。
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

        <section
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: 20,
            flexWrap: "wrap",
            padding: 20,
            marginBottom: 18,
            border: "1px solid rgba(69,224,168,.18)",
            borderRadius: 17,
            background:
              "linear-gradient(135deg, rgba(69,224,168,.07), rgba(16,31,51,.78))",
          }}
        >
          <div>
            <div
              style={{
                color: "#8298ae",
                fontSize: 10,
                fontWeight: 700,
                marginBottom: 7,
              }}
            >
              今日の勤務状況
            </div>

            <strong
              style={{
                display: "block",
                fontSize: 22,
              }}
            >
              {attendanceStatus === "before" && "まだ出勤していません"}
              {attendanceStatus === "working" && "勤務中"}
              {attendanceStatus === "break" && "休憩中"}
              {attendanceStatus === "finished" && "本日の勤務終了"}
            </strong>

            {lastEvent && (
              <div
                style={{
                  marginTop: 6,
                  color: "#8298ae",
                  fontSize: 11,
                }}
              >
                最終打刻{" "}
                {new Date(lastEvent.event_at).toLocaleTimeString("ja-JP", {
                  hour: "2-digit",
                  minute: "2-digit",
                })}
              </div>
            )}
          </div>

          <div
            style={{
              display: "flex",
              gap: 9,
              flexWrap: "wrap",
            }}
          >
            {attendanceStatus === "before" && (
              <button
                onClick={() => clock("clock_in")}
                disabled={clocking}
                style={primaryClockButton}
              >
                ◷ 出勤
              </button>
            )}

            {attendanceStatus === "working" && (
              <>
                <button
                  onClick={() => clock("break_start")}
                  disabled={clocking}
                  style={secondaryClockButton}
                >
                  休憩開始
                </button>

                <button
                  onClick={() => clock("clock_out")}
                  disabled={clocking}
                  style={dangerClockButton}
                >
                  退勤
                </button>
              </>
            )}

            {attendanceStatus === "break" && (
              <button
                onClick={() => clock("break_end")}
                disabled={clocking}
                style={primaryClockButton}
              >
                休憩終了
              </button>
            )}

            {attendanceStatus === "finished" && (
              <span
                style={{
                  padding: "9px 13px",
                  color: "#65e6b5",
                  border: "1px solid rgba(69,224,168,.18)",
                  borderRadius: 10,
                  background: "rgba(69,224,168,.07)",
                  fontSize: 11,
                  fontWeight: 750,
                }}
              >
                ✓ 打刻完了
              </span>
            )}
          </div>

          {clockMessage && (
            <div
              style={{
                width: "100%",
                color: "#65e6b5",
                fontSize: 11,
              }}
            >
              {clockMessage}
            </div>
          )}
        </section>

        <section
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(3, minmax(0, 1fr))",
            gap: 12,
            marginBottom: 24,
          }}
        >
          <StatCard title="勤務日数" value={`${summary.days}日`} />
          <StatCard title="実働時間" value={duration(summary.minutes)} />
          <StatCard title="休日勤務" value={`${summary.holidayCount}日`} />
        </section>

        {error && (
          <div
            style={{
              marginBottom: 16,
              padding: 13,
              color: "#ff9aa6",
              border: "1px solid rgba(255,107,122,.2)",
              borderRadius: 11,
              background: "rgba(255,107,122,.06)",
            }}
          >
            {error}
          </div>
        )}

        <section
          style={{
            overflow: "hidden",
            border: "1px solid rgba(148,180,216,.14)",
            borderRadius: 17,
            background: "rgba(12,25,43,.66)",
          }}
        >
          <div
            style={{
              padding: "17px 20px",
              borderBottom: "1px solid rgba(148,180,216,.11)",
            }}
          >
            <strong>月間勤怠</strong>
          </div>

          {loading ? (
            <div style={emptyStyle}>読み込み中...</div>
          ) : records.length === 0 ? (
            <div style={emptyStyle}>
              <div style={{ fontSize: 28, marginBottom: 10 }}>◷</div>
              <strong>この月の勤怠はありません</strong>
              <p style={{ color: "#758da5", fontSize: 11 }}>
                勤怠が登録されるとここに表示されます。
              </p>
            </div>
          ) : (
            <div style={{ padding: 12 }}>
              {records.map((record) => (
                <article
                  key={record.record_id}
                  style={{
                    display: "grid",
                    gridTemplateColumns:
                      "180px minmax(200px, 1fr) 120px 120px",
                    alignItems: "center",
                    gap: 14,
                    padding: "13px 15px",
                    marginBottom: 7,
                    border: "1px solid rgba(148,180,216,.10)",
                    borderRadius: 12,
                    background: "rgba(9,20,35,.62)",
                  }}
                >
                  <strong>{dateLabel(record.work_date)}</strong>

                  <div style={{ fontSize: 17, fontWeight: 750 }}>
                    {time(record.start_minute)}
                    <span style={{ color: "#536b83", margin: "0 9px" }}>
                      →
                    </span>
                    {time(record.end_minute)}
                  </div>

                  <span style={{ color: "#879db3", fontSize: 11 }}>
                    休憩 {record.break_total_minutes}分
                  </span>

                  <div style={{ textAlign: "right" }}>
                    <strong>{duration(record.work_minutes)}</strong>

                    {record.is_holiday && (
                      <div
                        style={{
                          marginTop: 3,
                          color: "#f6c85f",
                          fontSize: 9,
                        }}
                      >
                        休日勤務
                      </div>
                    )}
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>
      </main>
    </AuthGuard>
  );
}

const primaryClockButton = {
  minWidth: 110,
  height: 44,
  padding: "0 18px",
  border: "1px solid rgba(69,224,168,.30)",
  borderRadius: 11,
  color: "#07151a",
  background: "linear-gradient(135deg, #45e0a8, #38d9c4)",
  cursor: "pointer",
  fontWeight: 800,
} as const;

const secondaryClockButton = {
  minWidth: 110,
  height: 44,
  padding: "0 18px",
  border: "1px solid rgba(246,200,95,.28)",
  borderRadius: 11,
  color: "#f7d98b",
  background: "rgba(246,200,95,.08)",
  cursor: "pointer",
  fontWeight: 750,
} as const;

const dangerClockButton = {
  minWidth: 100,
  height: 44,
  padding: "0 18px",
  border: "1px solid rgba(255,107,122,.25)",
  borderRadius: 11,
  color: "#ff9aa6",
  background: "rgba(255,107,122,.08)",
  cursor: "pointer",
  fontWeight: 750,
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
  padding: 55,
  textAlign: "center",
  color: "#8298ae",
} as const;

function StatCard({
  title,
  value,
}: {
  title: string;
  value: string;
}) {
  return (
    <div
      style={{
        padding: 18,
        border: "1px solid rgba(148,180,216,.13)",
        borderRadius: 15,
        background:
          "linear-gradient(145deg, rgba(16,31,51,.78), rgba(10,22,38,.7))",
      }}
    >
      <span style={{ color: "#8298ae", fontSize: 10 }}>{title}</span>

      <strong
        style={{
          display: "block",
          marginTop: 9,
          fontSize: 22,
        }}
      >
        {value}
      </strong>
    </div>
  );
}
