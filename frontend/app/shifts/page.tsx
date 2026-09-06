"use client";

import { useEffect, useMemo, useState } from "react";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

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

function currentYearMonth() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
}

function moveMonth(yearMonth: string, amount: number) {
  const [year, month] = yearMonth.split("-").map(Number);
  const date = new Date(year, month - 1 + amount, 1);

  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(
    2,
    "0"
  )}`;
}

function minuteToTime(value: number) {
  const hour = Math.floor(value / 60);
  const minute = value % 60;

  return `${String(hour).padStart(2, "0")}:${String(minute).padStart(2, "0")}`;
}

function formatMinutes(value: number) {
  const hours = Math.floor(value / 60);
  const minutes = value % 60;

  if (hours === 0) return `${minutes}分`;
  if (minutes === 0) return `${hours}時間`;

  return `${hours}時間${minutes}分`;
}

function weekday(dateString: string) {
  const date = new Date(`${dateString}T00:00:00`);
  return ["日", "月", "火", "水", "木", "金", "土"][date.getDay()];
}

function formatDate(dateString: string) {
  const [, month, day] = dateString.split("-");
  return `${Number(month)}月${Number(day)}日`;
}

export default function EmployeeShiftsPage() {
  const [me, setMe] = useState<Me | null>(null);
  const [yearMonth, setYearMonth] = useState(currentYearMonth);
  const [shifts, setShifts] = useState<Shift[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function loadMe() {
    const res = await fetch(`${API_BASE}/me`, {
      credentials: "include",
      cache: "no-store",
    });

    if (!res.ok) {
      setError("ログイン情報を取得できませんでした。");
      return null;
    }

    const user: Me = await res.json();
    setMe(user);
    return user;
  }

  async function loadShifts(targetMonth: string) {
    setLoading(true);
    setError("");

    try {
      const res = await fetch(`${API_BASE}/shifts/${targetMonth}`, {
        credentials: "include",
        cache: "no-store",
      });

      if (!res.ok) {
        const body = await res.json().catch(() => null);
        setError(
          body?.detail
            ? `シフトを取得できませんでした: ${body.detail}`
            : `シフトを取得できませんでした: ${res.status}`
        );
        return;
      }

      setShifts(await res.json());
    } catch {
      setError("シフトの取得中に通信エラーが発生しました。");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    async function initialize() {
      try {
        const user = await loadMe();

        if (user?.role === "employee") {
          await loadShifts(yearMonth);
        } else {
          setLoading(false);
        }
      } catch {
        setError("画面の読み込みに失敗しました。");
        setLoading(false);
      }
    }

    initialize();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (me?.role === "employee") {
      loadShifts(yearMonth);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [yearMonth]);

  const summary = useMemo(() => {
    const workMinutes = shifts.reduce((total, shift) => {
      return (
        total +
        Math.max(
          0,
          shift.end_minute -
            shift.start_minute -
            shift.break_minutes
        )
      );
    }, 0);

    return {
      workDays: shifts.length,
      workMinutes,
      confirmed: shifts.filter((shift) => shift.confirmed).length,
    };
  }, [shifts]);

  return (
    <main
      style={{
        maxWidth: 1180,
        margin: "0 auto",
        padding: "30px 20px 50px",
      }}
    >
      <div
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
            MY SHIFT
          </div>

          <h1
            style={{
              margin: "7px 0 5px",
              fontSize: 30,
              letterSpacing: "-.03em",
            }}
          >
            自分のシフト
          </h1>

          <div style={{ color: "#8298ae", fontSize: 12 }}>
            {me?.employee_id
              ? `社員番号 ${me.employee_id}`
              : "シフトを確認できます"}
          </div>
        </div>

        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 7,
            flexWrap: "wrap",
          }}
        >
          <button
            onClick={() => setYearMonth(moveMonth(yearMonth, -1))}
            style={navButtonStyle}
          >
            ← 前月
          </button>

          <button
            onClick={() => setYearMonth(currentYearMonth())}
            style={navButtonStyle}
          >
            今月
          </button>

          <button
            onClick={() => setYearMonth(moveMonth(yearMonth, 1))}
            style={navButtonStyle}
          >
            次月 →
          </button>

          <input
            type="month"
            value={yearMonth}
            onChange={(event) => setYearMonth(event.target.value)}
            style={{
              height: 39,
              padding: "0 11px",
              marginLeft: 3,
            }}
          />
        </div>
      </div>

      <section
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(3, minmax(0, 1fr))",
          gap: 12,
          marginBottom: 25,
        }}
      >
        <SummaryCard
          label="勤務予定日"
          value={`${summary.workDays}日`}
          accent="#8290ff"
          icon="▦"
        />

        <SummaryCard
          label="予定実働時間"
          value={formatMinutes(summary.workMinutes)}
          accent="#45e0a8"
          icon="◷"
        />

        <SummaryCard
          label="確定済み"
          value={`${summary.confirmed} / ${summary.workDays}`}
          accent="#38d9f5"
          icon="✓"
        />
      </section>

      {error && (
        <div
          style={{
            padding: 13,
            marginBottom: 18,
            border: "1px solid rgba(255,107,122,.2)",
            borderRadius: 11,
            color: "#ff9aa6",
            background: "rgba(255,107,122,.06)",
          }}
        >
          {error}
        </div>
      )}

      <section
        style={{
          border: "1px solid rgba(148,180,216,.14)",
          borderRadius: 17,
          background: "rgba(12,25,43,.66)",
          overflow: "hidden",
        }}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            padding: "17px 20px",
            borderBottom: "1px solid rgba(148,180,216,.11)",
          }}
        >
          <div>
            <strong style={{ fontSize: 14 }}>月間シフト</strong>
            <div
              style={{
                marginTop: 3,
                color: "#758da5",
                fontSize: 10,
              }}
            >
              {yearMonth.replace("-", "年")}月
            </div>
          </div>

          <span
            style={{
              color: "#7e96ad",
              fontSize: 10,
            }}
          >
            {shifts.length}件
          </span>
        </div>

        {loading ? (
          <div
            style={{
              padding: 50,
              textAlign: "center",
              color: "#8298ae",
            }}
          >
            シフトを読み込んでいます...
          </div>
        ) : shifts.length === 0 ? (
          <div
            style={{
              padding: "64px 20px",
              textAlign: "center",
            }}
          >
            <div
              style={{
                width: 48,
                height: 48,
                display: "grid",
                placeItems: "center",
                margin: "0 auto 14px",
                borderRadius: 14,
                color: "#8390ff",
                background: "rgba(109,124,255,.10)",
                fontSize: 21,
              }}
            >
              ▦
            </div>

            <strong>この月のシフトはありません</strong>

            <p
              style={{
                margin: "7px 0 0",
                color: "#758da5",
                fontSize: 11,
              }}
            >
              シフトが登録されると、ここに表示されます。
            </p>
          </div>
        ) : (
          <div style={{ padding: 12 }}>
            {shifts.map((shift) => {
              const day = weekday(shift.shift_date);
              const weekend = day === "土" || day === "日";

              return (
                <article
                  key={shift.shift_id ?? shift.shift_date}
                  style={{
                    display: "grid",
                    gridTemplateColumns:
                      "140px minmax(190px, 1fr) 120px minmax(120px, 1fr)",
                    alignItems: "center",
                    gap: 16,
                    minHeight: 72,
                    padding: "10px 14px",
                    marginBottom: 7,
                    border: "1px solid rgba(148,180,216,.10)",
                    borderRadius: 12,
                    background: "rgba(9,20,35,.62)",
                  }}
                >
                  <div>
                    <strong
                      style={{
                        color:
                          day === "日"
                            ? "#ff9aa6"
                            : day === "土"
                              ? "#8eb8ff"
                              : "#edf5ff",
                        fontSize: 13,
                      }}
                    >
                      {formatDate(shift.shift_date)}（{day}）
                    </strong>

                    {weekend && (
                      <div
                        style={{
                          marginTop: 3,
                          color: "#667f98",
                          fontSize: 9,
                        }}
                      >
                        週末
                      </div>
                    )}
                  </div>

                  <div>
                    <strong
                      style={{
                        fontSize: 18,
                        letterSpacing: ".02em",
                      }}
                    >
                      {minuteToTime(shift.start_minute)}
                      <span
                        style={{
                          margin: "0 9px",
                          color: "#536b83",
                          fontWeight: 400,
                        }}
                      >
                        →
                      </span>
                      {minuteToTime(shift.end_minute)}
                    </strong>
                  </div>

                  <div
                    style={{
                      color: "#879db3",
                      fontSize: 11,
                    }}
                  >
                    休憩 {shift.break_minutes}分
                  </div>

                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "flex-end",
                      gap: 12,
                    }}
                  >
                    {shift.note && (
                      <span
                        title={shift.note}
                        style={{
                          maxWidth: 150,
                          overflow: "hidden",
                          textOverflow: "ellipsis",
                          whiteSpace: "nowrap",
                          color: "#7e96ad",
                          fontSize: 10,
                        }}
                      >
                        {shift.note}
                      </span>
                    )}

                    <span
                      style={{
                        padding: "5px 9px",
                        borderRadius: 999,
                        color: shift.confirmed
                          ? "#67e7b8"
                          : "#f6c85f",
                        border: shift.confirmed
                          ? "1px solid rgba(69,224,168,.2)"
                          : "1px solid rgba(246,200,95,.2)",
                        background: shift.confirmed
                          ? "rgba(69,224,168,.07)"
                          : "rgba(246,200,95,.07)",
                        fontSize: 9,
                        fontWeight: 750,
                      }}
                    >
                      {shift.confirmed ? "✓ 確定" : "未確定"}
                    </span>
                  </div>
                </article>
              );
            })}
          </div>
        )}
      </section>
    </main>
  );
}

const navButtonStyle = {
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

function SummaryCard({
  label,
  value,
  accent,
  icon,
}: {
  label: string;
  value: string;
  accent: string;
  icon: string;
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
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <span
          style={{
            color: "#8298ae",
            fontSize: 10,
            fontWeight: 700,
          }}
        >
          {label}
        </span>

        <span
          style={{
            width: 28,
            height: 28,
            display: "grid",
            placeItems: "center",
            borderRadius: 8,
            color: accent,
            background: `${accent}12`,
          }}
        >
          {icon}
        </span>
      </div>

      <strong
        style={{
          display: "block",
          marginTop: 10,
          fontSize: 22,
        }}
      >
        {value}
      </strong>
    </div>
  );
}
