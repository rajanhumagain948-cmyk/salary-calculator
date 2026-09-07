"use client";

import { useEffect, useState } from "react";
import AuthGuard from "@/components/auth/AuthGuard";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

type Me = {
  username: string;
  role: "admin" | "employee";
  employee_id: string | null;
};

type PayrollResult = {
  employee_id: string;
  year_month: string;
  payments: Record<string, string>;
  deductions: Record<string, string>;
  gross_pay: string;
  total_deductions: string;
  net_pay: string;
  finalized: boolean;
  company_name: string;
};

function currentYearMonth() {
  const now = new Date();

  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(
    2,
    "0"
  )}`;
}

function money(value: string) {
  return `${Number(value).toLocaleString("ja-JP")}円`;
}

export default function PayslipsPage() {
  const [yearMonth, setYearMonth] = useState(currentYearMonth);
  const [employeeId, setEmployeeId] = useState<string | null>(null);
  const [result, setResult] = useState<PayrollResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadMe() {
      setLoading(true);
      setError("");

      try {
        const res = await fetch(`${API_BASE}/me`, {
          credentials: "include",
          cache: "no-store",
        });

        if (!res.ok) {
          setError("ログイン情報を取得できませんでした。");
          return;
        }

        const me: Me = await res.json();

        if (!me.employee_id) {
          setError("従業員情報が設定されていません。");
          return;
        }

        setEmployeeId(me.employee_id);
      } catch {
        setError("ログイン情報の取得中に通信エラーが発生しました。");
      } finally {
        setLoading(false);
      }
    }

    loadMe();
  }, []);

  useEffect(() => {
    if (!employeeId) return;

    async function loadPayslip() {
      setLoading(true);
      setError("");
      setResult(null);

      try {
        const res = await fetch(
          `${API_BASE}/payroll/${yearMonth}/${encodeURIComponent(
            employeeId!
          )}`,
          {
            credentials: "include",
            cache: "no-store",
          }
        );

        if (res.status === 404) {
          return;
        }

        if (!res.ok) {
          setError(`給与明細を取得できませんでした: ${res.status}`);
          return;
        }

        const data: PayrollResult = await res.json();

        if (data.finalized) {
          setResult(data);
        }
      } catch {
        setError("給与明細の取得中に通信エラーが発生しました。");
      } finally {
        setLoading(false);
      }
    }

    loadPayslip();
  }, [employeeId, yearMonth]);

  async function downloadPdf() {
    if (!employeeId || !result) return;

    setError("");

    try {
      const res = await fetch(
        `${API_BASE}/payroll/${yearMonth}/${encodeURIComponent(
          employeeId
        )}/pdf`,
        {
          credentials: "include",
        }
      );

      if (!res.ok) {
        setError(`PDFをダウンロードできませんでした: ${res.status}`);
        return;
      }

      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");

      link.href = url;
      link.download = `payslip_${yearMonth}_${employeeId}.pdf`;
      document.body.appendChild(link);
      link.click();
      link.remove();

      URL.revokeObjectURL(url);
    } catch {
      setError("PDFのダウンロード中に通信エラーが発生しました。");
    }
  }

  return (
    <AuthGuard allow={["employee"]}>
      <main
        style={{
          maxWidth: 1180,
          margin: "0 auto",
          padding: "30px 24px 50px",
        }}
      >
        <header
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "end",
            gap: 20,
            marginBottom: 24,
          }}
        >
          <div>
            <div
              style={{
                color: "#45e0a8",
                fontSize: 12,
                fontWeight: 800,
              }}
            >
              給与
            </div>

            <h1 style={{ margin: "7px 0 5px" }}>給与明細</h1>

            <p style={{ margin: 0, color: "#8fa6bf" }}>
              確定済みの給与明細を確認できます。
            </p>
          </div>

          <input
            type="month"
            value={yearMonth}
            onChange={(event) => setYearMonth(event.target.value)}
            style={{
              height: 42,
              padding: "0 12px",
            }}
          />
        </header>

        {error && (
          <div
            style={{
              padding: 14,
              marginBottom: 16,
              border: "1px solid rgba(255,100,100,.25)",
              borderRadius: 12,
              color: "#ff9b9b",
              background: "rgba(255,80,80,.07)",
            }}
          >
            {error}
          </div>
        )}

        {loading ? (
          <section style={panelStyle}>読み込み中...</section>
        ) : !result ? (
          <section
            style={{
              ...panelStyle,
              minHeight: 240,
              display: "grid",
              placeItems: "center",
              textAlign: "center",
            }}
          >
            <div>
              <div
                style={{
                  fontSize: 32,
                  color: "#71879d",
                  marginBottom: 12,
                }}
              >
                ¥
              </div>

              <strong>確定済みの給与明細はありません</strong>

              <p style={{ color: "#71879d", fontSize: 12 }}>
                {yearMonth} の給与が確定すると、ここに表示されます。
              </p>
            </div>
          </section>
        ) : (
          <>
            <section
              style={{
                ...panelStyle,
                marginBottom: 14,
              }}
            >
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  gap: 16,
                  alignItems: "center",
                }}
              >
                <div>
                  <div style={{ color: "#8298ae", fontSize: 11 }}>
                    {result.company_name}
                  </div>
                  <h2 style={{ margin: "5px 0" }}>
                    {result.year_month} 給与明細
                  </h2>
                  <div style={{ color: "#45e0a8", fontSize: 11 }}>
                    確定済み
                  </div>
                </div>

                <button
                  onClick={downloadPdf}
                  style={{
                    padding: "10px 16px",
                    color: "#fff",
                    border: "1px solid rgba(109,124,255,.35)",
                    borderRadius: 10,
                    background:
                      "linear-gradient(135deg, #6d7cff, #5164e8)",
                    cursor: "pointer",
                    fontWeight: 800,
                  }}
                >
                  PDFをダウンロード
                </button>
              </div>
            </section>

            <div
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                gap: 14,
                marginBottom: 14,
              }}
            >
              <section style={panelStyle}>
                <h3 style={{ marginTop: 0 }}>支給</h3>

                {Object.entries(result.payments).map(([name, amount]) => (
                  <Row key={name} label={name} value={money(amount)} />
                ))}

                <Row
                  label="総支給額"
                  value={money(result.gross_pay)}
                  strong
                />
              </section>

              <section style={panelStyle}>
                <h3 style={{ marginTop: 0 }}>控除</h3>

                {Object.entries(result.deductions).map(([name, amount]) => (
                  <Row key={name} label={name} value={money(amount)} />
                ))}

                <Row
                  label="控除合計"
                  value={money(result.total_deductions)}
                  strong
                />
              </section>
            </div>

            <section
              style={{
                ...panelStyle,
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
              }}
            >
              <strong>差引支給額</strong>
              <strong
                style={{
                  color: "#45e0a8",
                  fontSize: 26,
                }}
              >
                {money(result.net_pay)}
              </strong>
            </section>
          </>
        )}
      </main>
    </AuthGuard>
  );
}

function Row({
  label,
  value,
  strong = false,
}: {
  label: string;
  value: string;
  strong?: boolean;
}) {
  return (
    <div
      style={{
        display: "flex",
        justifyContent: "space-between",
        gap: 15,
        padding: "10px 0",
        borderBottom: "1px solid rgba(148,180,216,.09)",
        fontWeight: strong ? 800 : 400,
      }}
    >
      <span style={{ color: strong ? "#fff" : "#8fa6bf" }}>{label}</span>
      <span>{value}</span>
    </div>
  );
}

const panelStyle = {
  padding: 20,
  border: "1px solid rgba(148,180,216,.12)",
  borderRadius: 14,
  background: "rgba(8,19,33,.55)",
};
