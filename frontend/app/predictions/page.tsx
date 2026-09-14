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
    } catch {
      setError("予測データの取得中にエラーが発生しました。");
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthGuard allow={["admin"]}>
      <main style={{ padding: 24 }}>
        <div style={{ color: "#8390ff", fontSize: 12, fontWeight: 800 }}>
          会社側・参考予測
        </div>

        <h1>予測</h1>

        <p style={{ color: "#8fa6bf", lineHeight: 1.7 }}>
          勤怠実績と確定シフトをもとに、月末の残業時間の着地を参考予測します。
        </p>

        <p style={{ color: "#fbbf24" }}>
          予測値は参考情報です。給与計算・給与確定には使用しません。
        </p>

        <form onSubmit={loadPredictions}>
          <label style={{ marginRight: 12 }}>
            対象月
            <input
              type="month"
              value={yearMonth}
              onChange={(e) => setYearMonth(e.target.value)}
              required
              style={{ marginLeft: 8 }}
            />
          </label>

          <label style={{ marginRight: 12 }}>
            基準日
            <input
              type="date"
              value={asOf}
              onChange={(e) => setAsOf(e.target.value)}
              required
              style={{ marginLeft: 8 }}
            />
          </label>

          <button type="submit" disabled={loading}>
            {loading ? "予測中…" : "残業予測を表示"}
          </button>
        </form>

        {error && <p style={{ color: "#ff9d9d" }}>{error}</p>}

        {!error && (
          <div style={{ marginTop: 20 }}>
            <div style={{ color: "#fbbf24", marginBottom: 8 }}>
              勤怠要確認: {attendanceReviews.length}名
            </div>

            {attendanceReviews.map((review) => (
              <div
                key={review.employee_id}
                style={{
                  marginBottom: 10,
                  padding: 14,
                  border: "1px solid rgba(251,191,36,0.18)",
                  borderRadius: 12,
                }}
              >
                <strong>
                  {review.employee_id} / {review.employee_name}
                </strong>

                {review.warnings.map((warning) => (
                  <div
                    key={warning.work_date}
                    style={{ marginTop: 8, color: "#c7d2e3" }}
                  >
                    {warning.work_date}: {warning.messages.join(" / ")}
                  </div>
                ))}
              </div>
            ))}
          </div>
        )}

        {!error && payrollSummary && (
          <div
            style={{
              marginTop: 24,
              padding: 16,
              border: "1px solid rgba(129,140,248,0.22)",
              borderRadius: 14,
            }}
          >
            <div style={{ color: "#8fa6bf", fontSize: 13 }}>
              総支給参考額
            </div>
            <div style={{ marginTop: 6, fontSize: 24, fontWeight: 800 }}>
              {Number(payrollSummary.gross_pay_reference_total).toLocaleString()}円
            </div>
            <div style={{ marginTop: 6, color: "#8fa6bf", fontSize: 12 }}>
              集計対象 {payrollSummary.included_count}名 / 対象外{" "}
              {payrollSummary.excluded_count}名
            </div>
          </div>
        )}

        {!error && payrollMethod && (
          <div style={{ marginTop: 20 }}>
            <p style={{ margin: 0, color: "#8fa6bf" }}>
              給与参考試算方法: {payrollMethod}
            </p>
            <p style={{ margin: "6px 0 0", color: "#fbbf24" }}>
              この金額は基準日時点の参考試算です。
              将来の勤務を含む月末確定額ではありません。
            </p>
          </div>
        )}

        {!error && payrollEstimates.length > 0 && (
          <div style={{ marginTop: 24 }}>
            <div style={{ color: "#a5b4fc", marginBottom: 10 }}>
              給与参考試算:{" "}
              {payrollEstimates.filter((item) => item.status === "参考試算").length}名
              {" / "}
              確定済:{" "}
              {payrollEstimates.filter((item) => item.status === "確定済").length}名
              {" / "}
              計算不可:{" "}
              {payrollEstimates.filter((item) => item.status === "計算不可").length}名
            </div>

            <div style={{ display: "grid", gap: 10 }}>
              {payrollEstimates.map((item) => (
                <div
                  key={item.employee_id}
                  style={{
                    padding: 14,
                    border: "1px solid rgba(129,140,248,0.18)",
                    borderRadius: 12,
                  }}
                >
                  <strong>
                    {item.employee_id} / {item.employee_name}
                  </strong>
                  <span style={{ marginLeft: 10, color: "#a5b4fc" }}>
                    {item.status}
                  </span>

                  {item.status === "参考試算" && (
                    <span
                      style={{
                        marginLeft: 10,
                        color: item.forecastable ? "#86efac" : "#fbbf24",
                      }}
                    >
                      {item.forecastable ? "予測可能" : "要設定確認"}
                    </span>
                  )}

                  {item.status === "計算不可" ? (
                    <div style={{ marginTop: 8, color: "#ff9d9d" }}>
                      {item.error ?? "計算できませんでした。"}
                    </div>
                  ) : (
                    <>
                      <div style={{ marginTop: 8 }}>
                        総支給: {item.gross_pay}円 / 控除:{" "}
                        {item.total_deductions}円 / 手取り: {item.net_pay}円
                      </div>

                      {(item.warnings?.length ?? 0) > 0 && (
                        <div style={{ marginTop: 6, color: "#fbbf24" }}>
                          warning: {item.warnings?.join(" / ")}
                        </div>
                      )}

                      {(item.blocking_issues?.length ?? 0) > 0 && (
                        <div style={{ marginTop: 6, color: "#fb7185" }}>
                          blocking: {item.blocking_issues?.join(" / ")}
                        </div>
                      )}
                    </>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {!error && method && (
          <p style={{ marginTop: 20, color: "#8fa6bf" }}>
            予測方法: {method}
          </p>
        )}

        {!error && items.length > 0 && (
          <div
            style={{
              display: "grid",
              gap: 12,
              marginTop: 24,
            }}
          >
            <div style={{ color: "#8fa6bf" }}>
              予測対象: {items.length}名
            </div>

            {items.map((item) => (
              <div
                key={item.employee_id}
                style={{
                  padding: 16,
                  border: "1px solid rgba(148,180,216,0.16)",
                  borderRadius: 14,
                }}
              >
                <strong>
                  {item.employee_id} / {item.employee_name}
                </strong>

                <div style={{ marginTop: 10 }}>
                  実績残業: {formatMinutes(item.actual_overtime_minutes)}
                </div>
                <div>
                  着地予測: {formatMinutes(item.forecast_overtime_minutes)}
                </div>
                <div style={{ color: "#8fa6bf" }}>
                  今後の確定シフト: {item.future_confirmed_shift_days}日
                </div>
              </div>
            ))}
          </div>
        )}
      </main>
    </AuthGuard>
  );
}
