"use client";

import { FormEvent, useState } from "react";
import AuthGuard from "@/components/auth/AuthGuard";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

function today() {
  return new Date().toISOString().slice(0, 10);
}

function currentYearMonth() {
  return today().slice(0, 7);
}

function formatMinutes(value: number) {
  const hours = Math.floor(value / 60);
  const minutes = value % 60;
  return `${hours}時間${minutes ? `${minutes}分` : ""}`;
}

type AttendanceReview = {
  employee_id: string;
  employee_name: string;
  warning_count: number;
  warnings: {
    work_date: string;
    messages: string[];
  }[];
};

type PayrollEstimate = {
  employee_id: string;
  employee_name: string;
  status: "確定済" | "参考試算" | "計算不可";
  forecastable?: boolean;
  gross_pay?: string;
  total_deductions?: string;
  net_pay?: string;
  warnings?: string[];
  blocking_issues?: string[];
  error?: string;
};

type PayrollRisk = {
  employee_id: string;
  employee_name: string;
  level: "high" | "medium";
  reasons: string[];
};

type LeaveTrend = {
  employee_id: string;
  employee_name: string;
  approved_request_count: number;
  approved_days: string;
  monthly_approved_days: Record<string, string>;
};

type PayrollEstimateSummary = {
  gross_pay_reference_total: string;
  included_count: number;
  excluded_count: number;
};

type OvertimePrediction = {
  employee_id: string;
  employee_name: string;
  actual_overtime_minutes: number;
  future_confirmed_shift_days: number;
  forecast_overtime_minutes: number;
};

export default function PredictionsPage() {
  const [yearMonth, setYearMonth] = useState(currentYearMonth);
  const [asOf, setAsOf] = useState(today);
  const [items, setItems] = useState<OvertimePrediction[]>([]);
  const [method, setMethod] = useState("");
  const [attendanceReviews, setAttendanceReviews] = useState<
    AttendanceReview[]
  >([]);
  const [payrollEstimates, setPayrollEstimates] = useState<
    PayrollEstimate[]
  >([]);
  const [payrollMethod, setPayrollMethod] = useState("");
  const [payrollSummary, setPayrollSummary] =
    useState<PayrollEstimateSummary | null>(null);
  const [leaveTrends, setLeaveTrends] = useState<LeaveTrend[]>([]);
  const [payrollRisks, setPayrollRisks] = useState<PayrollRisk[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function loadPredictions(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      const params = new URLSearchParams({
        year_month: yearMonth,
        as_of: asOf,
      });
      const res = await fetch(
        `${API_BASE}/predictions/overtime?${params.toString()}`,
        {
          credentials: "include",
          cache: "no-store",
        }
      );
      const data = await res.json().catch(() => null);

      if (!res.ok) {
        setError(
          data?.detail
            ? `予測を取得できませんでした: ${data.detail}`
            : `予測を取得できませんでした: ${res.status}`
        );
        return;
      }

      setItems(Array.isArray(data.items) ? data.items : []);
      setMethod(typeof data.method === "string" ? data.method : "");

      const reviewParams = new URLSearchParams({
        year_month: yearMonth,
      });
      const reviewRes = await fetch(
        `${API_BASE}/predictions/attendance-review?${reviewParams.toString()}`,
        {
          credentials: "include",
          cache: "no-store",
        }
      );
      const reviewData = await reviewRes.json().catch(() => null);

      if (!reviewRes.ok) {
        setError(
          reviewData?.detail
            ? `勤怠確認候補を取得できませんでした: ${reviewData.detail}`
            : `勤怠確認候補を取得できませんでした: ${reviewRes.status}`
        );
        return;
      }

      setAttendanceReviews(
        Array.isArray(reviewData.items) ? reviewData.items : []
      );

      const payrollRes = await fetch(
        `${API_BASE}/predictions/payroll-estimate?${params.toString()}`,
        {
          credentials: "include",
          cache: "no-store",
        }
      );
      const payrollData = await payrollRes.json().catch(() => null);

      if (!payrollRes.ok) {
        setError(
          payrollData?.detail
            ? `給与参考試算を取得できませんでした: ${payrollData.detail}`
            : `給与参考試算を取得できませんでした: ${payrollRes.status}`
        );
        return;
      }

      setPayrollEstimates(
        Array.isArray(payrollData.items) ? payrollData.items : []
      );
      setPayrollMethod(
        typeof payrollData.method === "string" ? payrollData.method : ""
      );
      setPayrollSummary(payrollData.summary ?? null);

      const leaveParams = new URLSearchParams({
        year: yearMonth.slice(0, 4),
      });
      const leaveRes = await fetch(
        `${API_BASE}/predictions/leave-trend?${leaveParams.toString()}`,
        {
          credentials: "include",
          cache: "no-store",
        }
      );
      const leaveData = await leaveRes.json().catch(() => null);

      if (!leaveRes.ok) {
        setError(
          leaveData?.detail
            ? `有給取得傾向を取得できませんでした: ${leaveData.detail}`
            : `有給取得傾向を取得できませんでした: ${leaveRes.status}`
        );
        return;
      }

      setLeaveTrends(
        Array.isArray(leaveData.items) ? leaveData.items : []
      );

      const riskRes = await fetch(
        `${API_BASE}/predictions/payroll-risk?${reviewParams.toString()}`,
        {
          credentials: "include",
          cache: "no-store",
        }
      );
      const riskData = await riskRes.json().catch(() => null);

      if (!riskRes.ok) {
        setError(
          riskData?.detail
            ? `給与処理リスクを取得できませんでした: ${riskData.detail}`
            : `給与処理リスクを取得できませんでした: ${riskRes.status}`
        );
        return;
      }

      setPayrollRisks(
        Array.isArray(riskData.items) ? riskData.items : []
      );
    } catch {
      setError("予測データの取得中にエラーが発生しました。");
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthGuard allow={["admin"]}>
      <main
        style={{
          maxWidth: 1180,
          margin: "0 auto",
          padding: "28px 20px 56px",
        }}
      >
        <section
          style={{
            position: "relative",
            overflow: "hidden",
            padding: "30px 30px 26px",
            border: "1px solid rgba(129,140,248,0.22)",
            borderRadius: 24,
            background:
              "linear-gradient(135deg, rgba(16,27,55,0.98), rgba(15,30,48,0.96) 52%, rgba(42,25,72,0.94))",
            boxShadow:
              "0 24px 80px rgba(0,0,0,0.22), inset 0 1px 0 rgba(255,255,255,0.05)",
          }}
        >
          <div
            style={{
              position: "absolute",
              width: 300,
              height: 300,
              right: -70,
              top: -150,
              borderRadius: "50%",
              background:
                "radial-gradient(circle, rgba(139,92,246,0.34), rgba(59,130,246,0.10) 48%, transparent 70%)",
              pointerEvents: "none",
            }}
          />

          <div style={{ position: "relative" }}>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 10,
                color: "#a5b4fc",
                fontSize: 12,
                fontWeight: 900,
                letterSpacing: "0.14em",
              }}
            >
              <span
                style={{
                  display: "grid",
                  placeItems: "center",
                  width: 30,
                  height: 30,
                  borderRadius: 9,
                  background: "linear-gradient(135deg,#6366f1,#a855f7)",
                  color: "white",
                  fontSize: 16,
                }}
              >
                ↗
              </span>
              PREDICTION CENTER
            </div>

            <h1
              style={{
                margin: "14px 0 8px",
                fontSize: "clamp(30px, 4vw, 44px)",
                letterSpacing: "-0.04em",
              }}
            >
              月末を、先に見る。
            </h1>

            <p
              style={{
                maxWidth: 680,
                margin: 0,
                color: "#a8bad0",
                lineHeight: 1.8,
              }}
            >
              勤怠・給与・有給・確定シフトを横断して、
              今月の着地と優先して確認すべきポイントを整理します。
            </p>

            <div
              style={{
                display: "flex",
                flexWrap: "wrap",
                gap: 8,
                marginTop: 18,
              }}
            >
              {["残業着地", "給与参考", "有給傾向", "確認リスク"].map(
                (label) => (
                  <span
                    key={label}
                    style={{
                      padding: "6px 10px",
                      borderRadius: 999,
                      background: "rgba(255,255,255,0.05)",
                      border: "1px solid rgba(165,180,252,0.12)",
                      color: "#cad5e5",
                      fontSize: 12,
                    }}
                  >
                    {label}
                  </span>
                )
              )}
            </div>
          </div>

          <form
            onSubmit={loadPredictions}
            style={{
              position: "relative",
              display: "flex",
              flexWrap: "wrap",
              alignItems: "end",
              gap: 12,
              marginTop: 26,
              padding: 14,
              borderRadius: 16,
              background: "rgba(4,12,28,0.40)",
              border: "1px solid rgba(148,180,216,0.12)",
            }}
          >
            <label style={{ color: "#9fb1c7", fontSize: 12 }}>
              対象月
              <input
                type="month"
                value={yearMonth}
                onChange={(e) => setYearMonth(e.target.value)}
                required
                style={{
                  display: "block",
                  marginTop: 6,
                  padding: "9px 11px",
                }}
              />
            </label>

            <label style={{ color: "#9fb1c7", fontSize: 12 }}>
              基準日
              <input
                type="date"
                value={asOf}
                onChange={(e) => setAsOf(e.target.value)}
                required
                style={{
                  display: "block",
                  marginTop: 6,
                  padding: "9px 11px",
                }}
              />
            </label>

            <button
              type="submit"
              disabled={loading}
              style={{
                minHeight: 39,
                padding: "0 18px",
                border: 0,
                borderRadius: 11,
                background: loading
                  ? "rgba(99,102,241,0.22)"
                  : "linear-gradient(135deg,#6366f1,#8b5cf6)",
                color: "white",
                fontWeight: 800,
                cursor: loading ? "wait" : "pointer",
              }}
            >
              {loading ? "分析中…" : "↗ 予測を更新"}
            </button>

            <span
              style={{
                marginLeft: "auto",
                padding: "7px 10px",
                borderRadius: 999,
                background: "rgba(251,191,36,0.08)",
                color: "#fbbf24",
                fontSize: 11,
              }}
            >
              REFERENCE ONLY
            </span>
          </form>
        </section>

        <section
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(210px, 1fr))",
            gap: 12,
            marginTop: 16,
          }}
        >
          {[
            {
              label: "最大 残業着地",
              value:
                items.length > 0
                  ? formatMinutes(
                      Math.max(...items.map((item) => item.forecast_overtime_minutes))
                    )
                  : "—",
              sub: "確定シフトを含む参考予測",
              color: "#a78bfa",
              icon: "◷",
            },
            {
              label: "総支給参考額",
              value: payrollSummary
                ? `${Number(
                    payrollSummary.gross_pay_reference_total
                  ).toLocaleString()}円`
                : "—",
              sub: payrollSummary
                ? `集計 ${payrollSummary.included_count}名 / 対象外 ${payrollSummary.excluded_count}名`
                : "基準日時点",
              color: "#60a5fa",
              icon: "¥",
            },
            {
              label: "優先確認",
              value: `${payrollRisks.length + attendanceReviews.length}件`,
              sub: `給与 ${payrollRisks.length} / 勤怠 ${attendanceReviews.length}`,
              color: "#fb7185",
              icon: "!",
            },
            {
              label: `${yearMonth.slice(0, 4)}年 有給取得`,
              value:
                leaveTrends.length > 0
                  ? `${leaveTrends
                      .reduce(
                        (total, item) => total + Number(item.approved_days),
                        0
                      )
                      .toLocaleString()}日`
                  : "—",
              sub: "承認済み取得実績",
              color: "#34d399",
              icon: "◇",
            },
          ].map((card) => (
            <div
              key={card.label}
              style={{
                padding: 18,
                borderRadius: 17,
                border: "1px solid rgba(148,180,216,0.13)",
                background:
                  "linear-gradient(145deg, rgba(20,35,56,0.86), rgba(10,22,40,0.72))",
                boxShadow: "inset 0 1px 0 rgba(255,255,255,0.035)",
              }}
            >
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  color: "#8fa6bf",
                  fontSize: 12,
                }}
              >
                {card.label}
                <span style={{ color: card.color, fontSize: 18 }}>
                  {card.icon}
                </span>
              </div>
              <div
                style={{
                  marginTop: 8,
                  color: card.color,
                  fontSize: 25,
                  fontWeight: 900,
                  letterSpacing: "-0.02em",
                }}
              >
                {card.value}
              </div>
              <div
                style={{
                  marginTop: 5,
                  color: "#687d96",
                  fontSize: 11,
                }}
              >
                {card.sub}
              </div>
            </div>
          ))}
        </section>

        <p
          style={{
            margin: "14px 2px 0",
            color: "#7f91a8",
            fontSize: 12,
          }}
        >
          予測値は参考情報です。給与計算・給与確定には使用しません。
        </p>

        {error && <p style={{ color: "#ff9d9d" }}>{error}</p>}

        {!error && (
          <section
            style={{
              marginTop: 26,
              padding: 20,
              border: "1px solid rgba(251,113,133,0.16)",
              borderRadius: 20,
              background:
                "linear-gradient(145deg, rgba(42,20,38,0.42), rgba(12,24,42,0.76) 55%)",
            }}
          >
            <div
              style={{
                display: "flex",
                flexWrap: "wrap",
                alignItems: "center",
                justifyContent: "space-between",
                gap: 12,
                marginBottom: 16,
              }}
            >
              <div>
                <div
                  style={{
                    color: "#fb7185",
                    fontSize: 11,
                    fontWeight: 900,
                    letterSpacing: "0.14em",
                  }}
                >
                  PRIORITY REVIEW
                </div>
                <h2 style={{ margin: "5px 0 0", fontSize: 20 }}>
                  今月、先に確認するポイント
                </h2>
              </div>

              <div style={{ display: "flex", gap: 7 }}>
                <span
                  style={{
                    padding: "6px 9px",
                    borderRadius: 999,
                    background: "rgba(251,113,133,0.10)",
                    color: "#fb7185",
                    fontSize: 11,
                  }}
                >
                  HIGH{" "}
                  {payrollRisks.filter((risk) => risk.level === "high").length}
                </span>
                <span
                  style={{
                    padding: "6px 9px",
                    borderRadius: 999,
                    background: "rgba(251,191,36,0.09)",
                    color: "#fbbf24",
                    fontSize: 11,
                  }}
                >
                  MEDIUM{" "}
                  {payrollRisks.filter((risk) => risk.level === "medium").length}
                </span>
              </div>
            </div>

            {payrollRisks.length === 0 && attendanceReviews.length === 0 ? (
              <div
                style={{
                  padding: 18,
                  borderRadius: 14,
                  background: "rgba(52,211,153,0.06)",
                  color: "#86efac",
                }}
              >
                ✓ 現在、優先確認が必要な項目はありません。
              </div>
            ) : (
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns:
                    "repeat(auto-fit, minmax(300px, 1fr))",
                  gap: 12,
                }}
              >
                {payrollRisks
                  .slice()
                  .sort((a, b) =>
                    a.level === b.level ? 0 : a.level === "high" ? -1 : 1
                  )
                  .map((risk) => (
                    <div
                      key={`payroll-${risk.employee_id}`}
                      style={{
                        padding: 15,
                        borderRadius: 15,
                        border:
                          risk.level === "high"
                            ? "1px solid rgba(251,113,133,0.28)"
                            : "1px solid rgba(251,191,36,0.20)",
                        background:
                          risk.level === "high"
                            ? "rgba(127,29,29,0.10)"
                            : "rgba(120,84,20,0.08)",
                      }}
                    >
                      <div
                        style={{
                          display: "flex",
                          justifyContent: "space-between",
                          gap: 10,
                        }}
                      >
                        <strong>
                          {risk.employee_name}
                          <span
                            style={{
                              marginLeft: 7,
                              color: "#70849c",
                              fontSize: 11,
                            }}
                          >
                            {risk.employee_id}
                          </span>
                        </strong>
                        <span
                          style={{
                            color:
                              risk.level === "high" ? "#fb7185" : "#fbbf24",
                            fontSize: 11,
                            fontWeight: 900,
                          }}
                        >
                          給与 {risk.level.toUpperCase()}
                        </span>
                      </div>
                      <div
                        style={{
                          marginTop: 9,
                          color: "#c5d0df",
                          fontSize: 13,
                          lineHeight: 1.65,
                        }}
                      >
                        {risk.reasons.join(" / ")}
                      </div>
                    </div>
                  ))}

                {attendanceReviews.map((review) => (
                  <div
                    key={`attendance-${review.employee_id}`}
                    style={{
                      padding: 15,
                      borderRadius: 15,
                      border: "1px solid rgba(96,165,250,0.18)",
                      background: "rgba(30,64,175,0.07)",
                    }}
                  >
                    <div
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        gap: 10,
                      }}
                    >
                      <strong>
                        {review.employee_name}
                        <span
                          style={{
                            marginLeft: 7,
                            color: "#70849c",
                            fontSize: 11,
                          }}
                        >
                          {review.employee_id}
                        </span>
                      </strong>
                      <span
                        style={{
                          color: "#60a5fa",
                          fontSize: 11,
                          fontWeight: 900,
                        }}
                      >
                        勤怠 CHECK
                      </span>
                    </div>

                    {review.warnings.map((warning) => (
                      <div
                        key={warning.work_date}
                        style={{
                          marginTop: 9,
                          color: "#c5d0df",
                          fontSize: 13,
                          lineHeight: 1.65,
                        }}
                      >
                        <span style={{ color: "#7f94ad" }}>
                          {warning.work_date}
                        </span>
                        {" · "}
                        {warning.messages.join(" / ")}
                      </div>
                    ))}
                  </div>
                ))}
              </div>
            )}
          </section>
        )}

        {!error && leaveTrends.length > 0 && (
          <section
            style={{
              marginTop: 24,
              padding: 20,
              border: "1px solid rgba(52,211,153,0.16)",
              borderRadius: 20,
              background:
                "linear-gradient(145deg, rgba(6,78,59,0.10), rgba(10,24,40,0.72))",
            }}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "flex-start",
                gap: 12,
                marginBottom: 16,
              }}
            >
              <div>
                <div
                  style={{
                    color: "#34d399",
                    fontSize: 11,
                    fontWeight: 900,
                    letterSpacing: "0.14em",
                  }}
                >
                  LEAVE TREND
                </div>
                <h2 style={{ margin: "5px 0 0", fontSize: 20 }}>
                  有給取得トレンド
                </h2>
              </div>
              <span
                style={{
                  padding: "6px 10px",
                  borderRadius: 999,
                  background: "rgba(52,211,153,0.09)",
                  color: "#86efac",
                  fontSize: 11,
                }}
              >
                承認済み実績
              </span>
            </div>

            <div style={{ color: "#8fa6bf", fontSize: 13 }}>
              {yearMonth.slice(0, 4)}年 累計取得
            </div>
            <div style={{ marginTop: 6, fontSize: 24, fontWeight: 800 }}>
              {leaveTrends
                .reduce(
                  (total, item) => total + Number(item.approved_days),
                  0
                )
                .toLocaleString()}日
            </div>

            <div
              style={{
                display: "flex",
                flexWrap: "wrap",
                gap: 8,
                marginTop: 12,
              }}
            >
              {Object.entries(
                leaveTrends.reduce<Record<string, number>>(
                  (months, item) => {
                    for (const [month, days] of Object.entries(
                      item.monthly_approved_days
                    )) {
                      months[month] =
                        (months[month] ?? 0) + Number(days);
                    }
                    return months;
                  },
                  {}
                )
              )
                .sort(([a], [b]) => a.localeCompare(b))
                .map(([month, days]) => (
                  <span
                    key={month}
                    style={{
                      padding: "5px 9px",
                      borderRadius: 999,
                      background: "rgba(52,211,153,0.10)",
                      color: "#86efac",
                      fontSize: 12,
                    }}
                  >
                    {month}: {days}日
                  </span>
                ))}
            </div>
          </section>
        )}

        {!error && payrollSummary && (
          <section
            style={{
              marginTop: 24,
              padding: 20,
              border: "1px solid rgba(96,165,250,0.16)",
              borderRadius: 20,
              background:
                "linear-gradient(145deg, rgba(30,64,175,0.10), rgba(10,24,40,0.76))",
            }}
          >
            <div
              style={{
                display: "flex",
                flexWrap: "wrap",
                justifyContent: "space-between",
                alignItems: "flex-start",
                gap: 14,
                marginBottom: 18,
              }}
            >
              <div>
                <div
                  style={{
                    color: "#60a5fa",
                    fontSize: 11,
                    fontWeight: 900,
                    letterSpacing: "0.14em",
                  }}
                >
                  PAYROLL SNAPSHOT
                </div>
                <h2 style={{ margin: "5px 0 0", fontSize: 20 }}>
                  給与の現在地
                </h2>
              </div>

              <div style={{ textAlign: "right" }}>
                <div style={{ color: "#8094ac", fontSize: 11 }}>
                  総支給参考額
                </div>
                <div
                  style={{
                    marginTop: 3,
                    color: "#93c5fd",
                    fontSize: 25,
                    fontWeight: 900,
                  }}
                >
                  {Number(
                    payrollSummary.gross_pay_reference_total
                  ).toLocaleString()}円
                </div>
                <div style={{ color: "#667b94", fontSize: 11 }}>
                  集計 {payrollSummary.included_count}名 / 対象外{" "}
                  {payrollSummary.excluded_count}名
                </div>
              </div>
            </div>

            {payrollMethod && (
              <div
                style={{
                  marginBottom: 16,
                  padding: "10px 12px",
                  borderRadius: 12,
                  background: "rgba(251,191,36,0.055)",
                  border: "1px solid rgba(251,191,36,0.10)",
                }}
              >
                <div style={{ color: "#9aabc0", fontSize: 11 }}>
                  試算方法 · {payrollMethod}
                </div>
                <div
                  style={{
                    marginTop: 4,
                    color: "#d7ad58",
                    fontSize: 11,
                  }}
                >
                  基準日時点の参考試算です。将来勤務を含む月末確定額ではありません。
                </div>
              </div>
            )}

            <div
              style={{
                display: "flex",
                flexWrap: "wrap",
                gap: 7,
                marginBottom: 12,
              }}
            >
              {[
                [
                  "参考試算",
                  payrollEstimates.filter(
                    (item) => item.status === "参考試算"
                  ).length,
                  "#a5b4fc",
                ],
                [
                  "確定済",
                  payrollEstimates.filter(
                    (item) => item.status === "確定済"
                  ).length,
                  "#86efac",
                ],
                [
                  "計算不可",
                  payrollEstimates.filter(
                    (item) => item.status === "計算不可"
                  ).length,
                  "#fb7185",
                ],
              ].map(([label, count, color]) => (
                <span
                  key={String(label)}
                  style={{
                    padding: "5px 9px",
                    borderRadius: 999,
                    background: "rgba(255,255,255,0.04)",
                    color: String(color),
                    fontSize: 11,
                  }}
                >
                  {label} {count}名
                </span>
              ))}
            </div>

            <div
              style={{
                display: "grid",
                gridTemplateColumns:
                  "repeat(auto-fit, minmax(290px, 1fr))",
                gap: 10,
              }}
            >
              {payrollEstimates.map((item) => (
                <div
                  key={item.employee_id}
                  style={{
                    padding: 15,
                    border:
                      item.status === "計算不可" ||
                      item.forecastable === false
                        ? "1px solid rgba(251,191,36,0.18)"
                        : "1px solid rgba(96,165,250,0.13)",
                    borderRadius: 14,
                    background: "rgba(4,13,27,0.28)",
                  }}
                >
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      gap: 10,
                    }}
                  >
                    <strong>
                      {item.employee_name}
                      <span
                        style={{
                          marginLeft: 7,
                          color: "#6f839b",
                          fontSize: 11,
                        }}
                      >
                        {item.employee_id}
                      </span>
                    </strong>
                    <span
                      style={{
                        color:
                          item.status === "計算不可"
                            ? "#fb7185"
                            : item.status === "確定済"
                              ? "#86efac"
                              : item.forecastable
                                ? "#a5b4fc"
                                : "#fbbf24",
                        fontSize: 11,
                        fontWeight: 800,
                      }}
                    >
                      {item.status === "参考試算"
                        ? item.forecastable
                          ? "参考試算"
                          : "要設定確認"
                        : item.status}
                    </span>
                  </div>

                  {item.status === "計算不可" ? (
                    <div
                      style={{
                        marginTop: 10,
                        color: "#ff9d9d",
                        fontSize: 12,
                      }}
                    >
                      {item.error ?? "計算できませんでした。"}
                    </div>
                  ) : (
                    <>
                      <div
                        style={{
                          display: "grid",
                          gridTemplateColumns: "repeat(3, 1fr)",
                          gap: 6,
                          marginTop: 12,
                        }}
                      >
                        {[
                          ["総支給", item.gross_pay],
                          ["控除", item.total_deductions],
                          ["手取り", item.net_pay],
                        ].map(([label, value]) => (
                          <div key={label}>
                            <div
                              style={{
                                color: "#687d96",
                                fontSize: 10,
                              }}
                            >
                              {label}
                            </div>
                            <div
                              style={{
                                marginTop: 2,
                                fontSize: 13,
                                fontWeight: 800,
                              }}
                            >
                              {Number(value ?? 0).toLocaleString()}円
                            </div>
                          </div>
                        ))}
                      </div>

                      {(item.warnings?.length ?? 0) > 0 && (
                        <div
                          style={{
                            marginTop: 10,
                            color: "#d9ad55",
                            fontSize: 11,
                            lineHeight: 1.6,
                          }}
                        >
                          △ {item.warnings?.join(" / ")}
                        </div>
                      )}

                      {(item.blocking_issues?.length ?? 0) > 0 && (
                        <div
                          style={{
                            marginTop: 7,
                            color: "#fb7185",
                            fontSize: 11,
                            lineHeight: 1.6,
                          }}
                        >
                          ! {item.blocking_issues?.join(" / ")}
                        </div>
                      )}
                    </>
                  )}
                </div>
              ))}
            </div>
          </section>
        )}

        {!error && items.length > 0 && (
          <section
            style={{
              marginTop: 24,
              padding: 20,
              border: "1px solid rgba(167,139,250,0.16)",
              borderRadius: 20,
              background:
                "linear-gradient(145deg, rgba(76,29,149,0.10), rgba(10,24,40,0.76))",
            }}
          >
            <div
              style={{
                display: "flex",
                flexWrap: "wrap",
                justifyContent: "space-between",
                alignItems: "flex-start",
                gap: 14,
                marginBottom: 18,
              }}
            >
              <div>
                <div
                  style={{
                    color: "#a78bfa",
                    fontSize: 11,
                    fontWeight: 900,
                    letterSpacing: "0.14em",
                  }}
                >
                  OVERTIME FORECAST
                </div>
                <h2 style={{ margin: "5px 0 0", fontSize: 20 }}>
                  月末残業フォーキャスト
                </h2>
              </div>

              <span
                style={{
                  padding: "6px 10px",
                  borderRadius: 999,
                  background: "rgba(167,139,250,0.09)",
                  color: "#c4b5fd",
                  fontSize: 11,
                }}
              >
                {items.length} EMPLOYEES
              </span>
            </div>

            {method && (
              <div
                style={{
                  marginBottom: 14,
                  color: "#71859d",
                  fontSize: 11,
                }}
              >
                MODEL · {method}
              </div>
            )}

            <div style={{ display: "grid", gap: 10 }}>
              {items
                .slice()
                .sort(
                  (a, b) =>
                    b.forecast_overtime_minutes -
                    a.forecast_overtime_minutes
                )
                .map((item, index) => {
                  const increase = Math.max(
                    0,
                    item.forecast_overtime_minutes -
                      item.actual_overtime_minutes
                  );

                  return (
                    <div
                      key={item.employee_id}
                      style={{
                        display: "grid",
                        gridTemplateColumns:
                          "minmax(160px, 1.4fr) repeat(3, minmax(100px, 1fr))",
                        gap: 12,
                        alignItems: "center",
                        padding: 15,
                        border: "1px solid rgba(167,139,250,0.12)",
                        borderRadius: 14,
                        background: "rgba(4,13,27,0.26)",
                      }}
                    >
                      <div>
                        <div
                          style={{
                            color: "#6f839b",
                            fontSize: 10,
                            fontWeight: 800,
                          }}
                        >
                          #{index + 1}
                        </div>
                        <strong style={{ display: "block", marginTop: 3 }}>
                          {item.employee_name}
                        </strong>
                        <span style={{ color: "#667b94", fontSize: 11 }}>
                          {item.employee_id}
                        </span>
                      </div>

                      <div>
                        <div style={{ color: "#687d96", fontSize: 10 }}>
                          現在
                        </div>
                        <div style={{ marginTop: 3, fontWeight: 800 }}>
                          {formatMinutes(item.actual_overtime_minutes)}
                        </div>
                      </div>

                      <div>
                        <div style={{ color: "#8d79bb", fontSize: 10 }}>
                          月末着地
                        </div>
                        <div
                          style={{
                            marginTop: 3,
                            color: "#c4b5fd",
                            fontWeight: 900,
                            fontSize: 16,
                          }}
                        >
                          {formatMinutes(item.forecast_overtime_minutes)}
                        </div>
                        {increase > 0 && (
                          <div
                            style={{
                              marginTop: 2,
                              color: "#8b7aaa",
                              fontSize: 10,
                            }}
                          >
                            +{formatMinutes(increase)}
                          </div>
                        )}
                      </div>

                      <div>
                        <div style={{ color: "#687d96", fontSize: 10 }}>
                          今後の確定シフト
                        </div>
                        <div style={{ marginTop: 3, fontWeight: 800 }}>
                          {item.future_confirmed_shift_days}日
                        </div>
                      </div>
                    </div>
                  );
                })}
            </div>

            <div
              style={{
                marginTop: 14,
                color: "#657991",
                fontSize: 10,
                lineHeight: 1.6,
              }}
            >
              参考予測です。実際の勤怠・給与計算結果を確定するものではありません。
            </div>
          </section>
        )}
      </main>
    </AuthGuard>
  );
}
