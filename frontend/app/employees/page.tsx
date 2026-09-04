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

const emptyEmployee: Employee = {
  employee_id: "",
  name: "",
  employment_type: "正社員",
  hire_date: new Date().toISOString().slice(0, 10),
  pay_type: "月給",
  hourly_rate: "0",
  monthly_salary: "0",
  weekly_hours: "40",
  weekly_days: 5,
  contract_months: null,
  workplace_size: 0,
  is_student: false,
  dependents: 0,
  tax_category: "甲",
  birth_date: null,
  termination_date: null,
  prefecture: "東京都",
  resident_tax_monthly: "0",
  resident_tax_method: "特別徴収",
  standard_monthly_remuneration: "0",
};

export default function EmployeesPage() {
  const [employees, setEmployees] = useState<EmployeeSummary[]>([]);
  const [selected, setSelected] = useState<Employee | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState<Employee>({ ...emptyEmployee });
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");

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

  async function createEmployee() {
    setError("");
    setMessage("");

    if (!form.employee_id.trim() || !form.name.trim() || !form.hire_date) {
      setError("社員番号・氏名・入社日は必須です。");
      return;
    }

    setSaving(true);

    try {
      const data = new FormData();

      data.append("employee_id", form.employee_id.trim());
      data.append("name", form.name.trim());
      data.append("employment_type", form.employment_type);
      data.append("hire_date", form.hire_date);
      data.append("pay_type", form.pay_type);
      data.append("hourly_rate", form.hourly_rate || "0");
      data.append("monthly_salary", form.monthly_salary || "0");
      data.append("weekly_hours", form.weekly_hours || "0");
      data.append("weekly_days", String(form.weekly_days));
      data.append(
        "contract_months",
        form.contract_months === null ? "" : String(form.contract_months)
      );
      data.append("workplace_size", String(form.workplace_size));
      data.append("is_student", form.is_student ? "1" : "0");
      data.append("dependents", String(form.dependents));
      data.append("tax_category", form.tax_category);
      data.append("birth_date", form.birth_date ?? "");
      data.append("termination_date", form.termination_date ?? "");
      data.append("prefecture", form.prefecture);
      data.append("resident_tax_monthly", form.resident_tax_monthly || "0");
      data.append("resident_tax_method", form.resident_tax_method);
      data.append(
        "standard_monthly_remuneration",
        form.standard_monthly_remuneration || "0"
      );

      const res = await fetch(`${API_BASE}/employees`, {
        method: "POST",
        credentials: "include",
        body: data,
      });

      if (!res.ok) {
        const body = await res.json().catch(() => null);

        if (res.status === 409) {
          setError("その社員番号はすでに登録されています。");
        } else {
          setError(
            body?.detail
              ? `登録に失敗しました: ${body.detail}`
              : `登録に失敗しました: ${res.status}`
          );
        }
        return;
      }

      const result = await res.json();

      setForm({ ...emptyEmployee });
      setSelected(result.employee);
      setMessage("従業員を登録しました。");
      await loadEmployees();
    } catch {
      setError("従業員の登録中に通信エラーが発生しました。");
    } finally {
      setSaving(false);
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

      <section
        style={{
          border: "1px solid #555",
          borderRadius: 8,
          padding: 20,
          marginBottom: 24,
        }}
      >
        <h2 style={{ marginTop: 0 }}>新規従業員登録</h2>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
            gap: 12,
          }}
        >
          <label>
            社員番号 *
            <input
              value={form.employee_id}
              onChange={(e) =>
                setForm({ ...form, employee_id: e.target.value })
              }
              style={{ display: "block", width: "100%", padding: 8 }}
            />
          </label>

          <label>
            氏名 *
            <input
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              style={{ display: "block", width: "100%", padding: 8 }}
            />
          </label>

          <label>
            雇用形態
            <select
              value={form.employment_type}
              onChange={(e) =>
                setForm({ ...form, employment_type: e.target.value })
              }
              style={{ display: "block", width: "100%", padding: 8 }}
            >
              <option value="正社員">正社員</option>
              <option value="契約社員">契約社員</option>
              <option value="パート">パート</option>
              <option value="アルバイト">アルバイト</option>
            </select>
          </label>

          <label>
            入社日 *
            <input
              type="date"
              value={form.hire_date}
              onChange={(e) =>
                setForm({ ...form, hire_date: e.target.value })
              }
              style={{ display: "block", width: "100%", padding: 8 }}
            />
          </label>

          <label>
            給与形態
            <select
              value={form.pay_type}
              onChange={(e) =>
                setForm({ ...form, pay_type: e.target.value })
              }
              style={{ display: "block", width: "100%", padding: 8 }}
            >
              <option value="月給">月給</option>
              <option value="時給">時給</option>
            </select>
          </label>

          {form.pay_type === "月給" ? (
            <label>
              月給（円）
              <input
                type="number"
                min="0"
                value={form.monthly_salary}
                onChange={(e) =>
                  setForm({ ...form, monthly_salary: e.target.value })
                }
                style={{ display: "block", width: "100%", padding: 8 }}
              />
            </label>
          ) : (
            <label>
              時給（円）
              <input
                type="number"
                min="0"
                value={form.hourly_rate}
                onChange={(e) =>
                  setForm({ ...form, hourly_rate: e.target.value })
                }
                style={{ display: "block", width: "100%", padding: 8 }}
              />
            </label>
          )}

          <label>
            週所定時間
            <input
              type="number"
              min="0"
              step="0.5"
              value={form.weekly_hours}
              onChange={(e) =>
                setForm({ ...form, weekly_hours: e.target.value })
              }
              style={{ display: "block", width: "100%", padding: 8 }}
            />
          </label>

          <label>
            週所定日数
            <input
              type="number"
              min="0"
              max="7"
              value={form.weekly_days}
              onChange={(e) =>
                setForm({
                  ...form,
                  weekly_days: Number(e.target.value),
                })
              }
              style={{ display: "block", width: "100%", padding: 8 }}
            />
          </label>
        </div>

        <button
          onClick={createEmployee}
          disabled={saving}
          style={{
            marginTop: 16,
            padding: "10px 18px",
            fontWeight: 700,
          }}
        >
          {saving ? "登録中..." : "従業員を登録"}
        </button>

        {message && (
          <p style={{ color: "#5ee28a", marginBottom: 0 }}>{message}</p>
        )}
      </section>

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
