"use client";

import { useEffect, useState } from "react";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

type EmployeeSummary = {
  employee_id: string;
  name: string;
};

type Employee = {
  employee_id: string;
  name: string;
  employment_type: string;
  hire_date: string;
  pay_type: string;
  hourly_rate: string;
  monthly_salary: string;
  weekly_hours: string;
  weekly_days: number;
  contract_months: number | null;
  workplace_size: number;
  is_student: boolean;
  dependents: number;
  tax_category: string;
  birth_date: string | null;
  termination_date: string | null;
  prefecture: string;
  resident_tax_monthly: string;
  resident_tax_method: string;
  standard_monthly_remuneration: string;
};

export default function EmployeesPage() {
  const [employees, setEmployees] = useState<EmployeeSummary[]>([]);
  const [selected, setSelected] = useState<Employee | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  async function loadEmployees() {
    setError("");
    setLoading(true);

    try {
      const res = await fetch(`${API_BASE}/employees`, {
        credentials: "include",
      });

      if (!res.ok) {
        setError(`従業員一覧の取得に失敗しました: ${res.status}`);
        return;
      }

      setEmployees(await res.json());
    } catch {
      setError("APIに接続できませんでした。");
    } finally {
      setLoading(false);
    }
  }

  async function selectEmployee(employeeId: string) {
    setError("");

    try {
      const res = await fetch(
        `${API_BASE}/employees/${encodeURIComponent(employeeId)}`,
        { credentials: "include" }
      );

      if (!res.ok) {
        setError(`従業員詳細の取得に失敗しました: ${res.status}`);
        return;
      }

      setSelected(await res.json());
    } catch {
      setError("従業員詳細を取得できませんでした。");
    }
  }

  useEffect(() => {
    loadEmployees();
  }, []);

  return (
    <main
      style={{
        maxWidth: 1200,
        margin: "0 auto",
        padding: 24,
        fontFamily: "system-ui",
      }}
    >
      <h1>従業員管理</h1>

      {error && <p style={{ color: "#ff6b6b" }}>{error}</p>}

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "minmax(280px, 1fr) minmax(400px, 2fr)",
          gap: 24,
        }}
      >
        <section>
          <h2>従業員一覧</h2>

          <button onClick={loadEmployees} style={{ padding: "8px 12px" }}>
            再取得
          </button>

          {loading ? (
            <p>読み込み中...</p>
          ) : (
            <div style={{ marginTop: 12 }}>
              {employees.map((employee) => (
                <button
                  key={employee.employee_id}
                  onClick={() => selectEmployee(employee.employee_id)}
                  style={{
                    display: "block",
                    width: "100%",
                    padding: 12,
                    marginBottom: 8,
                    textAlign: "left",
                    cursor: "pointer",
                    border: "1px solid #555",
                    borderRadius: 6,
                    background:
                      selected?.employee_id === employee.employee_id
                        ? "#24405c"
                        : "#181818",
                    color: "#fff",
                  }}
                >
                  <strong>{employee.employee_id}</strong>
                  <br />
                  {employee.name}
                </button>
              ))}

              {employees.length === 0 && <p>従業員が登録されていません。</p>}
            </div>
          )}
        </section>

        <section>
          <h2>従業員詳細</h2>

          {!selected ? (
            <p>左の一覧から従業員を選択してください。</p>
          ) : (
            <div
              style={{
                border: "1px solid #555",
                borderRadius: 8,
                padding: 20,
              }}
            >
              <p><strong>社員番号:</strong> {selected.employee_id}</p>
              <p><strong>氏名:</strong> {selected.name}</p>
              <p><strong>雇用形態:</strong> {selected.employment_type}</p>
              <p><strong>入社日:</strong> {selected.hire_date}</p>
              <p><strong>給与形態:</strong> {selected.pay_type}</p>

              <p>
                <strong>時給:</strong>{" "}
                {Number(selected.hourly_rate).toLocaleString()} 円
              </p>

              <p>
                <strong>月給:</strong>{" "}
                {Number(selected.monthly_salary).toLocaleString()} 円
              </p>

              <p><strong>週所定時間:</strong> {selected.weekly_hours} 時間</p>
              <p><strong>週所定日数:</strong> {selected.weekly_days} 日</p>
              <p><strong>扶養人数:</strong> {selected.dependents} 人</p>
              <p><strong>税区分:</strong> {selected.tax_category}</p>
              <p><strong>都道府県:</strong> {selected.prefecture}</p>

              <p>
                <strong>住民税:</strong>{" "}
                {Number(selected.resident_tax_monthly).toLocaleString()} 円
              </p>

              <p>
                <strong>住民税徴収:</strong> {selected.resident_tax_method}
              </p>

              <p>
                <strong>標準報酬月額:</strong>{" "}
                {Number(
                  selected.standard_monthly_remuneration
                ).toLocaleString()}{" "}
                円
              </p>

              <p>
                <strong>生年月日:</strong>{" "}
                {selected.birth_date ?? "未登録"}
              </p>

              <p>
                <strong>退職日:</strong>{" "}
                {selected.termination_date ?? "在籍中"}
              </p>

              <p>
                <strong>学生:</strong>{" "}
                {selected.is_student ? "はい" : "いいえ"}
              </p>
            </div>
          )}
        </section>
      </div>
    </main>
  );
}
