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
  const [attendanceReviewCount, setAttendanceReviewCount] = useState(0);
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

      setAttendanceReviewCount(
        Array.isArray(reviewData.items) ? reviewData.items.length : 0
      );
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
          <p style={{ marginTop: 20, color: "#fbbf24" }}>
            勤怠要確認: {attendanceReviewCount}名
          </p>
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
