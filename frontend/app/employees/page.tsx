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
  const [editForm, setEditForm] = useState<Employee | null>(null);
  const [updating, setUpdating] = useState(false);
  const [search, setSearch] = useState("");
  const [showCreateForm, setShowCreateForm] = useState(false);

  const filteredEmployees = employees.filter((employee) => {
    const q = search.trim().toLowerCase();
    if (!q) return true;

    return (
      employee.employee_id.toLowerCase().includes(q) ||
      employee.name.toLowerCase().includes(q)
    );
  });

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

      const employee: Employee = await res.json();
      setSelected(employee);
      setEditForm({ ...employee });
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
      setShowCreateForm(false);
      setSelected(result.employee);
      setMessage("従業員を登録しました。");
      await loadEmployees();
    } catch {
      setError("従業員の登録中に通信エラーが発生しました。");
    } finally {
      setSaving(false);
    }
  }

  async function updateEmployee() {
    if (!editForm) return;

    setError("");
    setMessage("");

    if (!editForm.name.trim() || !editForm.hire_date) {
      setError("氏名・入社日は必須です。");
      return;
    }

    setUpdating(true);

    try {
      const data = new FormData();

      data.append("name", editForm.name.trim());
      data.append("employment_type", editForm.employment_type);
      data.append("hire_date", editForm.hire_date);
      data.append("pay_type", editForm.pay_type);
      data.append("hourly_rate", editForm.hourly_rate || "0");
      data.append("monthly_salary", editForm.monthly_salary || "0");
      data.append("weekly_hours", editForm.weekly_hours || "0");
      data.append("weekly_days", String(editForm.weekly_days));
      data.append(
        "contract_months",
        editForm.contract_months === null
          ? ""
          : String(editForm.contract_months)
      );
      data.append("workplace_size", String(editForm.workplace_size));
      data.append("is_student", editForm.is_student ? "1" : "0");
      data.append("dependents", String(editForm.dependents));
      data.append("tax_category", editForm.tax_category);
      data.append("birth_date", editForm.birth_date ?? "");
      data.append("termination_date", editForm.termination_date ?? "");
      data.append("prefecture", editForm.prefecture);
      data.append(
        "resident_tax_monthly",
        editForm.resident_tax_monthly || "0"
      );
      data.append("resident_tax_method", editForm.resident_tax_method);
      data.append(
        "standard_monthly_remuneration",
        editForm.standard_monthly_remuneration || "0"
      );

      const res = await fetch(
        `${API_BASE}/employees/${encodeURIComponent(editForm.employee_id)}`,
        {
          method: "PUT",
          credentials: "include",
          body: data,
        }
      );

      if (!res.ok) {
        const body = await res.json().catch(() => null);
        setError(
          body?.detail
            ? `更新に失敗しました: ${body.detail}`
            : `更新に失敗しました: ${res.status}`
        );
        return;
      }

      const result = await res.json();
      setSelected(result.employee);
      setEditForm({ ...result.employee });
      setMessage("従業員情報を更新しました。");
      await loadEmployees();
    } catch {
      setError("従業員情報の更新中に通信エラーが発生しました。");
    } finally {
      setUpdating(false);
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
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 20,
          marginBottom: 26,
        }}
      >
        <div>
          <div
            style={{
              color: "#8390ff",
              fontSize: 11,
              fontWeight: 800,
              letterSpacing: "0.12em",
            }}
          >
            従業員マスター
          </div>

          <h1 style={{ margin: "6px 0 5px", fontSize: 30 }}>
            従業員管理
          </h1>

          <div style={{ color: "#8fa6bf", fontSize: 13 }}>
            登録従業員 {employees.length} 人
          </div>
        </div>

        <button
          onClick={() => setShowCreateForm((value) => !value)}
          style={{
            padding: "11px 17px",
            border: "1px solid rgba(109,124,255,.4)",
            borderRadius: 11,
            color: "#fff",
            background: showCreateForm
              ? "rgba(109,124,255,.12)"
              : "linear-gradient(135deg, #6d7cff, #5164e8)",
            fontWeight: 750,
            cursor: "pointer",
            boxShadow: showCreateForm
              ? "none"
              : "0 10px 26px rgba(81,100,232,.22)",
          }}
        >
          {showCreateForm ? "× 閉じる" : "＋ 従業員を追加"}
        </button>
      </div>

      {error && <p style={{ color: "#ff6b6b" }}>{error}</p>}

      {showCreateForm && (
      <section
        style={{
          border: "1px solid rgba(109,124,255,.22)",
          borderRadius: 16,
          padding: 22,
          marginBottom: 24,
          background:
            "linear-gradient(145deg, rgba(17,33,54,.86), rgba(10,23,40,.72))",
          boxShadow: "0 18px 50px rgba(0,0,0,.16)",
        }}
      >
        <h2 style={{ marginTop: 0 }}>新しい従業員を登録</h2>

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
      )}

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "minmax(280px, 1fr) minmax(400px, 2fr)",
          gap: 24,
        }}
      >
        <section>
          <h2>従業員一覧</h2>

          <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
            <input
              type="search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="社員番号・氏名で検索"
              style={{
                flex: 1,
                minWidth: 0,
                padding: "9px 11px",
              }}
            />

            <button onClick={loadEmployees} style={{ padding: "8px 12px" }}>
              再取得
            </button>
          </div>

          <div
            style={{
              color: "#8fa6bf",
              fontSize: 12,
              marginBottom: 8,
            }}
          >
            {filteredEmployees.length} / {employees.length} 人
          </div>

          {loading ? (
            <p>読み込み中...</p>
          ) : (
            <div
              style={{
                maxHeight: 520,
                overflowY: "auto",
                paddingRight: 5,
              }}
            >
              {filteredEmployees.map((employee) => (
                <button
                  key={employee.employee_id}
                  onClick={() => {
                    if (selected?.employee_id === employee.employee_id) {
                      setSelected(null);
                      setEditForm(null);
                    } else {
                      selectEmployee(employee.employee_id);
                    }
                  }}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 11,
                    width: "100%",
                    padding: "10px 11px",
                    marginBottom: 7,
                    textAlign: "left",
                    cursor: "pointer",
                    border:
                      selected?.employee_id === employee.employee_id
                        ? "1px solid rgba(109,124,255,.48)"
                        : "1px solid rgba(148,180,216,.12)",
                    borderRadius: 11,
                    background:
                      selected?.employee_id === employee.employee_id
                        ? "linear-gradient(90deg, rgba(109,124,255,.22), rgba(56,217,245,.08))"
                        : "rgba(14,27,46,.58)",
                    color: "#fff",
                  }}
                >
                  <span
                    style={{
                      width: 36,
                      height: 36,
                      display: "grid",
                      placeItems: "center",
                      flex: "0 0 auto",
                      borderRadius: 10,
                      color: "#dce2ff",
                      fontWeight: 800,
                      background:
                        "linear-gradient(135deg, rgba(109,124,255,.36), rgba(56,217,245,.18))",
                    }}
                  >
                    {(employee.name.trim()[0] || "?").toUpperCase()}
                  </span>

                  <span style={{ minWidth: 0 }}>
                    <strong
                      style={{
                        display: "block",
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        whiteSpace: "nowrap",
                        fontSize: 13,
                      }}
                    >
                      {employee.name}
                    </strong>

                    <span
                      style={{
                        display: "block",
                        marginTop: 3,
                        color: "#7f96ad",
                        fontSize: 10,
                        letterSpacing: ".04em",
                      }}
                    >
                      {employee.employee_id}
                    </span>
                  </span>

                  <span
                    style={{
                      marginLeft: "auto",
                      color:
                        selected?.employee_id === employee.employee_id
                          ? "#8fe9f7"
                          : "#546c84",
                    }}
                  >
                    ›
                  </span>
                </button>
              ))}

              {employees.length === 0 && (
                <p>従業員が登録されていません。</p>
              )}

              {employees.length > 0 && filteredEmployees.length === 0 && (
                <p style={{ color: "#8fa6bf" }}>
                  検索条件に一致する従業員はいません。
                </p>
              )}
            </div>
          )}
        </section>

        <section>
          <h2>従業員詳細</h2>

          {!selected || !editForm ? (
            <p>左の一覧から従業員を選択してください。</p>
          ) : (
            <div
              style={{
                border: "1px solid #555",
                borderRadius: 8,
                padding: 20,
              }}
            >
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 15,
                  paddingBottom: 18,
                  marginBottom: 20,
                  borderBottom: "1px solid rgba(148,180,216,.12)",
                }}
              >
                <div
                  style={{
                    width: 52,
                    height: 52,
                    display: "grid",
                    placeItems: "center",
                    flex: "0 0 auto",
                    borderRadius: 15,
                    color: "#fff",
                    fontSize: 20,
                    fontWeight: 850,
                    background:
                      "linear-gradient(135deg, #6475f2, #35bfd9)",
                    boxShadow:
                      "0 10px 28px rgba(83,104,230,.22)",
                  }}
                >
                  {(editForm.name.trim()[0] || "?").toUpperCase()}
                </div>

                <div style={{ minWidth: 0 }}>
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 9,
                      flexWrap: "wrap",
                    }}
                  >
                    <strong
                      style={{
                        fontSize: 19,
                        letterSpacing: "-.02em",
                      }}
                    >
                      {editForm.name || "氏名未入力"}
                    </strong>

                    <span
                      style={{
                        padding: "4px 8px",
                        borderRadius: 999,
                        color: editForm.termination_date
                          ? "#ff9aa6"
                          : "#65e6b5",
                        background: editForm.termination_date
                          ? "rgba(255,107,122,.09)"
                          : "rgba(69,224,168,.09)",
                        border: editForm.termination_date
                          ? "1px solid rgba(255,107,122,.2)"
                          : "1px solid rgba(69,224,168,.18)",
                        fontSize: 9,
                        fontWeight: 750,
                      }}
                    >
                      {editForm.termination_date ? "退職" : "在籍中"}
                    </span>
                  </div>

                  <div
                    style={{
                      display: "flex",
                      gap: 10,
                      marginTop: 5,
                      color: "#8298ae",
                      fontSize: 11,
                    }}
                  >
                    <span>{editForm.employee_id}</span>
                    <span>•</span>
                    <span>{editForm.employment_type}</span>
                    <span>•</span>
                    <span>{editForm.pay_type}</span>
                  </div>
                </div>
              </div>

              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(190px, 1fr))",
                  gap: 12,
                }}
              >
                <label>
                  氏名 *
                  <input
                    value={editForm.name}
                    onChange={(e) =>
                      setEditForm({ ...editForm, name: e.target.value })
                    }
                    style={{ display: "block", width: "100%", padding: 8 }}
                  />
                </label>

                <label>
                  雇用形態
                  <select
                    value={editForm.employment_type}
                    onChange={(e) =>
                      setEditForm({
                        ...editForm,
                        employment_type: e.target.value,
                      })
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
                    value={editForm.hire_date}
                    onChange={(e) =>
                      setEditForm({ ...editForm, hire_date: e.target.value })
                    }
                    style={{ display: "block", width: "100%", padding: 8 }}
                  />
                </label>

                <label>
                  給与形態
                  <select
                    value={editForm.pay_type}
                    onChange={(e) =>
                      setEditForm({ ...editForm, pay_type: e.target.value })
                    }
                    style={{ display: "block", width: "100%", padding: 8 }}
                  >
                    <option value="月給">月給</option>
                    <option value="時給">時給</option>
                  </select>
                </label>

                <label>
                  時給（円）
                  <input
                    type="number"
                    min="0"
                    value={editForm.hourly_rate}
                    onChange={(e) =>
                      setEditForm({ ...editForm, hourly_rate: e.target.value })
                    }
                    style={{ display: "block", width: "100%", padding: 8 }}
                  />
                </label>

                <label>
                  月給（円）
                  <input
                    type="number"
                    min="0"
                    value={editForm.monthly_salary}
                    onChange={(e) =>
                      setEditForm({
                        ...editForm,
                        monthly_salary: e.target.value,
                      })
                    }
                    style={{ display: "block", width: "100%", padding: 8 }}
                  />
                </label>

                <label>
                  週所定時間
                  <input
                    type="number"
                    min="0"
                    step="0.5"
                    value={editForm.weekly_hours}
                    onChange={(e) =>
                      setEditForm({
                        ...editForm,
                        weekly_hours: e.target.value,
                      })
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
                    value={editForm.weekly_days}
                    onChange={(e) =>
                      setEditForm({
                        ...editForm,
                        weekly_days: Number(e.target.value),
                      })
                    }
                    style={{ display: "block", width: "100%", padding: 8 }}
                  />
                </label>

                <label>
                  契約期間（月）
                  <input
                    type="number"
                    min="0"
                    value={editForm.contract_months ?? ""}
                    onChange={(e) =>
                      setEditForm({
                        ...editForm,
                        contract_months:
                          e.target.value === "" ? null : Number(e.target.value),
                      })
                    }
                    style={{ display: "block", width: "100%", padding: 8 }}
                  />
                </label>

                <label>
                  事業所規模
                  <input
                    type="number"
                    min="0"
                    value={editForm.workplace_size}
                    onChange={(e) =>
                      setEditForm({
                        ...editForm,
                        workplace_size: Number(e.target.value),
                      })
                    }
                    style={{ display: "block", width: "100%", padding: 8 }}
                  />
                </label>

                <label>
                  扶養人数
                  <input
                    type="number"
                    min="0"
                    value={editForm.dependents}
                    onChange={(e) =>
                      setEditForm({
                        ...editForm,
                        dependents: Number(e.target.value),
                      })
                    }
                    style={{ display: "block", width: "100%", padding: 8 }}
                  />
                </label>

                <label>
                  税区分
                  <select
                    value={editForm.tax_category}
                    onChange={(e) =>
                      setEditForm({
                        ...editForm,
                        tax_category: e.target.value,
                      })
                    }
                    style={{ display: "block", width: "100%", padding: 8 }}
                  >
                    <option value="甲">甲</option>
                    <option value="乙">乙</option>
                  </select>
                </label>

                <label>
                  生年月日
                  <input
                    type="date"
                    value={editForm.birth_date ?? ""}
                    onChange={(e) =>
                      setEditForm({
                        ...editForm,
                        birth_date: e.target.value || null,
                      })
                    }
                    style={{ display: "block", width: "100%", padding: 8 }}
                  />
                </label>

                <label>
                  退職日
                  <input
                    type="date"
                    value={editForm.termination_date ?? ""}
                    onChange={(e) =>
                      setEditForm({
                        ...editForm,
                        termination_date: e.target.value || null,
                      })
                    }
                    style={{ display: "block", width: "100%", padding: 8 }}
                  />
                </label>

                <label>
                  都道府県
                  <input
                    value={editForm.prefecture}
                    onChange={(e) =>
                      setEditForm({
                        ...editForm,
                        prefecture: e.target.value,
                      })
                    }
                    style={{ display: "block", width: "100%", padding: 8 }}
                  />
                </label>

                <label>
                  住民税（月額）
                  <input
                    type="number"
                    min="0"
                    value={editForm.resident_tax_monthly}
                    onChange={(e) =>
                      setEditForm({
                        ...editForm,
                        resident_tax_monthly: e.target.value,
                      })
                    }
                    style={{ display: "block", width: "100%", padding: 8 }}
                  />
                </label>

                <label>
                  住民税徴収
                  <select
                    value={editForm.resident_tax_method}
                    onChange={(e) =>
                      setEditForm({
                        ...editForm,
                        resident_tax_method: e.target.value,
                      })
                    }
                    style={{ display: "block", width: "100%", padding: 8 }}
                  >
                    <option value="特別徴収">特別徴収</option>
                    <option value="普通徴収">普通徴収</option>
                  </select>
                </label>

                <label>
                  標準報酬月額
                  <input
                    type="number"
                    min="0"
                    value={editForm.standard_monthly_remuneration}
                    onChange={(e) =>
                      setEditForm({
                        ...editForm,
                        standard_monthly_remuneration: e.target.value,
                      })
                    }
                    style={{ display: "block", width: "100%", padding: 8 }}
                  />
                </label>

                <label style={{ alignSelf: "end", paddingBottom: 8 }}>
                  <input
                    type="checkbox"
                    checked={editForm.is_student}
                    onChange={(e) =>
                      setEditForm({
                        ...editForm,
                        is_student: e.target.checked,
                      })
                    }
                  />{" "}
                  学生
                </label>
              </div>

              <div style={{ display: "flex", gap: 10, marginTop: 18 }}>
                <button
                  onClick={updateEmployee}
                  disabled={updating}
                  style={{ padding: "10px 18px", fontWeight: 700 }}
                >
                  {updating ? "更新中..." : "変更を保存"}
                </button>

                <button
                  onClick={() => setEditForm({ ...selected })}
                  disabled={updating}
                  style={{ padding: "10px 18px" }}
                >
                  変更を戻す
                </button>
              </div>
            </div>
          )}
        </section>
      </div>
    </main>
  );
}
