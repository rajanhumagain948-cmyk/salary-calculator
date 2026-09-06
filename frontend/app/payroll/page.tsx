"use client";

import { useEffect, useMemo, useState } from "react";
import AuthGuard from "@/components/auth/AuthGuard";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

type Employee = {
  employee_id: string;
  name: string;
};

type AllowanceItem = {
  name: string;
  amount: string;
  taxable: boolean;
};

type DeductionItem = {
  name: string;
  amount: string;
};

type PayrollInputs = {
  allowances: AllowanceItem[];
  deductions: DeductionItem[];
  transport: {
    method: string;
    unit_amount: string;
    taxable: boolean;
  };
};

type PayrollResult = {
  employee_id: string;
  year_month: string;
  payments: Record<string, string>;
  deductions: Record<string, string>;
  gross_pay: string;
  total_deductions: string;
  net_pay: string;
  classification: {
    regular_minutes: number;
    overtime_minutes: number;
    night_minutes: number;
    regular_night_minutes: number;
    holiday_minutes: number;
    overtime_night_minutes: number;
    holiday_night_minutes: number;
    overtime_over_60_minutes: number;
  };
  warnings: string[];
  blocking_issues: string[];
  finalized: boolean;
  company_name: string;
};

function currentYearMonth() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
}

function money(value: string | number) {
  return `${Number(value).toLocaleString("ja-JP")}円`;
}

function minutes(value: number) {
  const h = Math.floor(value / 60);
  const m = value % 60;

  return `${h}時間${m ? `${m}分` : ""}`;
}

export default function PayrollPage() {
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [selected, setSelected] = useState<Employee | null>(null);
  const [search, setSearch] = useState("");
  const [yearMonth, setYearMonth] = useState(currentYearMonth);
  const [result, setResult] = useState<PayrollResult | null>(null);
  const [calculating, setCalculating] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [inputs, setInputs] = useState<PayrollInputs>({
    allowances: [],
    deductions: [],
    transport: {
      method: "なし",
      unit_amount: "0",
      taxable: false,
    },
  });
  const [savingInputs, setSavingInputs] = useState(false);

  async function loadEmployees() {
    try {
      const res = await fetch(`${API_BASE}/employees`, {
        credentials: "include",
        cache: "no-store",
      });

      if (!res.ok) {
        setError(`従業員一覧を取得できませんでした: ${res.status}`);
        return;
      }

      setEmployees(await res.json());
    } catch {
      setError("従業員一覧の取得中に通信エラーが発生しました。");
    }
  }

  async function loadPayrollInputs(
    employee: Employee,
    month = yearMonth
  ) {
    try {
      const res = await fetch(
        `${API_BASE}/payroll-inputs/${month}/${encodeURIComponent(
          employee.employee_id
        )}`,
        {
          credentials: "include",
          cache: "no-store",
        }
      );

      if (!res.ok) {
        setError(`月次入力を取得できませんでした: ${res.status}`);
        return;
      }

      const data = await res.json();

      setInputs({
        allowances: data.allowances ?? [],
        deductions: data.deductions ?? [],
        transport: {
          method: data.transport?.method ?? "なし",
          unit_amount: data.transport?.unit_amount ?? "0",
          taxable: data.transport?.taxable ?? false,
        },
      });
    } catch {
      setError("月次入力の取得中に通信エラーが発生しました。");
    }
  }

  async function loadExistingPayroll(
    employee: Employee,
    month = yearMonth
  ) {
    setError("");
    setMessage("");
    setResult(null);

    try {
      const res = await fetch(
        `${API_BASE}/payroll/${month}/${encodeURIComponent(
          employee.employee_id
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
        setError(`給与結果を取得できませんでした: ${res.status}`);
        return;
      }

      setResult(await res.json());
    } catch {
      setError("給与結果の取得中に通信エラーが発生しました。");
    }
  }

  async function savePayrollInputs() {
    if (!selected) return false;

    setSavingInputs(true);
    setError("");
    setMessage("");

    try {
      const form = new FormData();

      form.append("employee_id", selected.employee_id);
      form.append("year_month", yearMonth);
      form.append("allowances_json", JSON.stringify(inputs.allowances));
      form.append("deductions_json", JSON.stringify(inputs.deductions));
      form.append("transport_method", inputs.transport.method);
      form.append("transport_amount", inputs.transport.unit_amount || "0");
      form.append(
        "transport_taxable",
        inputs.transport.taxable ? "1" : "0"
      );

      const res = await fetch(`${API_BASE}/payroll-inputs`, {
        method: "POST",
        credentials: "include",
        body: form,
      });

      if (!res.ok) {
        const body = await res.json().catch(() => null);

        setError(
          body?.detail
            ? `月次入力を保存できませんでした: ${body.detail}`
            : `月次入力を保存できませんでした: ${res.status}`
        );
        return false;
      }

      setMessage("交通費・手当・控除を保存しました。");
      return true;
    } catch {
      setError("月次入力の保存中に通信エラーが発生しました。");
      return false;
    } finally {
      setSavingInputs(false);
    }
  }

  function addAllowance() {
    setInputs({
      ...inputs,
      allowances: [
        ...inputs.allowances,
        {
          name: "",
          amount: "0",
          taxable: true,
        },
      ],
    });
  }

  function addDeduction() {
    setInputs({
      ...inputs,
      deductions: [
        ...inputs.deductions,
        {
          name: "",
          amount: "0",
        },
      ],
    });
  }

  async function calculatePayroll() {
    if (!selected) return;

    setCalculating(true);
    setError("");
    setMessage("");

    try {
      const form = new FormData();
      form.append("employee_id", selected.employee_id);
      form.append("year_month", yearMonth);

      const res = await fetch(`${API_BASE}/payroll/calculate`, {
        method: "POST",
        credentials: "include",
        body: form,
      });

      if (!res.ok) {
        const body = await res.json().catch(() => null);

        setError(
          body?.detail
            ? `給与計算に失敗しました: ${
                typeof body.detail === "string"
                  ? body.detail
                  : JSON.stringify(body.detail)
              }`
            : `給与計算に失敗しました: ${res.status}`
        );
        return;
      }

      setResult(await res.json());
      setMessage("給与を計算しました。");
    } catch {
      setError("給与計算中に通信エラーが発生しました。");
    } finally {
      setCalculating(false);
    }
  }

  async function finalizePayroll() {
    if (!selected || !result) return;

    const confirmed = window.confirm(
      `${selected.name} の ${yearMonth} の給与を確定しますか？`
    );

    if (!confirmed) return;

    setError("");
    setMessage("");

    try {
      const form = new FormData();
      form.append("employee_id", selected.employee_id);
      form.append("year_month", yearMonth);

      const res = await fetch(`${API_BASE}/payroll/finalize`, {
        method: "POST",
        credentials: "include",
        body: form,
      });

      if (!res.ok) {
        const body = await res.json().catch(() => null);

        const detail =
          typeof body?.detail === "string"
            ? body.detail
            : body?.detail?.message ?? `HTTP ${res.status}`;

        setError(`給与を確定できませんでした: ${detail}`);
        return;
      }

      setResult(await res.json());
      setMessage("給与を確定しました。従業員の給与明細に反映されます。");
    } catch {
      setError("給与確定中に通信エラーが発生しました。");
    }
  }

  function selectEmployee(employee: Employee) {
    setSelected(employee);
    loadPayrollInputs(employee);
    loadExistingPayroll(employee);
  }

  useEffect(() => {
    loadEmployees();
  }, []);

  useEffect(() => {
    if (selected) {
      loadPayrollInputs(selected, yearMonth);
      loadExistingPayroll(selected, yearMonth);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [yearMonth]);

  const filteredEmployees = useMemo(() => {
    const q = search.trim().toLowerCase();

    if (!q) return employees;

    return employees.filter(
      (employee) =>
        employee.employee_id.toLowerCase().includes(q) ||
        employee.name.toLowerCase().includes(q)
    );
  }, [employees, search]);

  return (
    <AuthGuard allow={["admin"]}>
      <main
        style={{
          maxWidth: 1260,
          margin: "0 auto",
          padding: "30px 20px 50px",
        }}
      >
        <header
          style={{
            display: "flex",
            alignItems: "flex-end",
            justifyContent: "space-between",
            gap: 20,
            flexWrap: "wrap",
            marginBottom: 25,
          }}
        >
          <div>
            <div style={eyebrowStyle}>会社側</div>

            <h1 style={{ margin: "7px 0 5px", fontSize: 30 }}>
              給与計算
            </h1>

            <p style={{ margin: 0, color: "#8298ae", fontSize: 12 }}>
              勤怠・従業員情報をもとに月次給与を計算します。
            </p>
          </div>

          <input
            type="month"
            value={yearMonth}
            onChange={(e) => setYearMonth(e.target.value)}
            style={{
              height: 42,
              padding: "0 12px",
            }}
          />
        </header>

        {error && <div style={errorStyle}>{error}</div>}
        {message && <div style={successStyle}>{message}</div>}

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "300px minmax(0, 1fr)",
            gap: 18,
            alignItems: "start",
          }}
        >
          <section style={panelStyle}>
            <h2 style={{ margin: "0 0 13px", fontSize: 15 }}>
              従業員
            </h2>

            <input
              type="search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="社員番号・氏名で検索"
              style={{
                width: "100%",
                padding: 10,
                marginBottom: 10,
              }}
            />

            <div style={{ maxHeight: 600, overflowY: "auto" }}>
              {filteredEmployees.map((employee) => {
                const active =
                  selected?.employee_id === employee.employee_id;

                return (
                  <button
                    key={employee.employee_id}
                    onClick={() => selectEmployee(employee)}
                    style={{
                      width: "100%",
                      display: "flex",
                      alignItems: "center",
                      gap: 10,
                      padding: 10,
                      marginBottom: 6,
                      textAlign: "left",
                      color: "#fff",
                      border: active
                        ? "1px solid rgba(109,124,255,.45)"
                        : "1px solid rgba(148,180,216,.10)",
                      borderRadius: 10,
                      background: active
                        ? "rgba(109,124,255,.15)"
                        : "rgba(8,19,33,.5)",
                      cursor: "pointer",
                    }}
                  >
                    <span
                      style={{
                        width: 34,
                        height: 34,
                        display: "grid",
                        placeItems: "center",
                        flex: "0 0 auto",
                        borderRadius: 9,
                        color: "#dce2ff",
                        background: "rgba(109,124,255,.18)",
                        fontWeight: 800,
                      }}
                    >
                      {employee.name.trim()[0] || "?"}
                    </span>

                    <span>
                      <strong
                        style={{
                          display: "block",
                          fontSize: 12,
                        }}
                      >
                        {employee.name}
                      </strong>

                      <small style={{ color: "#71879d" }}>
                        {employee.employee_id}
                      </small>
                    </span>
                  </button>
                );
              })}
            </div>
          </section>

          {!selected ? (
            <section
              style={{
                ...panelStyle,
                minHeight: 430,
                display: "grid",
                placeItems: "center",
                textAlign: "center",
                color: "#8298ae",
              }}
            >
              <div>
                <div style={{ fontSize: 30, marginBottom: 12 }}>¥</div>
                <strong>従業員を選択してください</strong>
                <p style={{ fontSize: 11 }}>
                  給与を計算する従業員を左から選択します。
                </p>
              </div>
            </section>
          ) : (
            <section>
              <div
                style={{
                  ...panelStyle,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  gap: 15,
                  marginBottom: 13,
                }}
              >
                <div>
                  <strong style={{ fontSize: 17 }}>{selected.name}</strong>
                  <div
                    style={{
                      marginTop: 4,
                      color: "#71879d",
                      fontSize: 10,
                    }}
                  >
                    {selected.employee_id} / {yearMonth}
                  </div>
                </div>

                <button
                  onClick={calculatePayroll}
                  disabled={calculating}
                  style={{
                    padding: "10px 17px",
                    color: "#fff",
                    border: "1px solid rgba(109,124,255,.35)",
                    borderRadius: 10,
                    background:
                      "linear-gradient(135deg, #6d7cff, #5164e8)",
                    cursor: "pointer",
                    fontWeight: 800,
                  }}
                >
                  {calculating ? "計算中..." : "給与を計算"}
                </button>
              </div>

              <div
                style={{
                  ...panelStyle,
                  marginBottom: 13,
                }}
              >
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    gap: 12,
                    marginBottom: 16,
                  }}
                >
                  <div>
                    <strong>月次入力</strong>
                    <div
                      style={{
                        marginTop: 3,
                        color: "#71879d",
                        fontSize: 9,
                      }}
                    >
                      交通費・手当・その他控除
                    </div>
                  </div>

                  <button
                    onClick={savePayrollInputs}
                    disabled={savingInputs}
                    style={{
                      padding: "8px 13px",
                      border:
                        "1px solid rgba(69,224,168,.24)",
                      borderRadius: 9,
                      color: "#65e6b5",
                      background: "rgba(69,224,168,.07)",
                      cursor: "pointer",
                      fontSize: 10,
                      fontWeight: 750,
                    }}
                  >
                    {savingInputs ? "保存中..." : "月次入力を保存"}
                  </button>
                </div>

                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns:
                      "repeat(3, minmax(0, 1fr))",
                    gap: 14,
                  }}
                >
                  <div>
                    <strong style={sectionTitleStyle}>交通費</strong>

                    <label style={fieldLabelStyle}>
                      計算方法
                      <select
                        value={inputs.transport.method}
                        onChange={(e) =>
                          setInputs({
                            ...inputs,
                            transport: {
                              ...inputs.transport,
                              method: e.target.value,
                            },
                          })
                        }
                        style={fieldStyle}
                      >
                        <option value="なし">なし</option>
                        <option value="月額固定">月額固定</option>
                        <option value="日額">日額</option>
                        <option value="実費">実費</option>
                      </select>
                    </label>

                    <label style={fieldLabelStyle}>
                      {inputs.transport.method === "日額"
                        ? "1日あたり（円）"
                        : "金額（円）"}
                      <input
                        value={inputs.transport.unit_amount}
                        onChange={(e) =>
                          setInputs({
                            ...inputs,
                            transport: {
                              ...inputs.transport,
                              unit_amount: e.target.value,
                            },
                          })
                        }
                        inputMode="decimal"
                        style={fieldStyle}
                      />
                    </label>

                    <label
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 7,
                        marginTop: 11,
                        color: "#91a5ba",
                        fontSize: 10,
                      }}
                    >
                      <input
                        type="checkbox"
                        checked={inputs.transport.taxable}
                        onChange={(e) =>
                          setInputs({
                            ...inputs,
                            transport: {
                              ...inputs.transport,
                              taxable: e.target.checked,
                            },
                          })
                        }
                      />
                      課税交通費として扱う
                    </label>
                  </div>

                  <div>
                    <div
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                        marginBottom: 8,
                      }}
                    >
                      <strong style={sectionTitleStyle}>手当</strong>

                      <button
                        onClick={addAllowance}
                        style={smallButtonStyle}
                      >
                        ＋ 追加
                      </button>
                    </div>

                    {inputs.allowances.length === 0 && (
                      <div style={emptyInputStyle}>
                        手当はありません
                      </div>
                    )}

                    {inputs.allowances.map((item, index) => (
                      <div
                        key={index}
                        style={{
                          padding: 9,
                          marginBottom: 7,
                          border:
                            "1px solid rgba(148,180,216,.09)",
                          borderRadius: 9,
                          background: "rgba(5,15,27,.4)",
                        }}
                      >
                        <input
                          value={item.name}
                          placeholder="手当名"
                          onChange={(e) => {
                            const allowances = [...inputs.allowances];
                            allowances[index] = {
                              ...allowances[index],
                              name: e.target.value,
                            };
                            setInputs({ ...inputs, allowances });
                          }}
                          style={{
                            ...fieldStyle,
                            marginTop: 0,
                          }}
                        />

                        <input
                          value={item.amount}
                          placeholder="金額"
                          inputMode="decimal"
                          onChange={(e) => {
                            const allowances = [...inputs.allowances];
                            allowances[index] = {
                              ...allowances[index],
                              amount: e.target.value,
                            };
                            setInputs({ ...inputs, allowances });
                          }}
                          style={fieldStyle}
                        />

                        <div
                          style={{
                            display: "flex",
                            justifyContent: "space-between",
                            alignItems: "center",
                            marginTop: 7,
                          }}
                        >
                          <label
                            style={{
                              color: "#8298ae",
                              fontSize: 9,
                            }}
                          >
                            <input
                              type="checkbox"
                              checked={item.taxable}
                              onChange={(e) => {
                                const allowances = [
                                  ...inputs.allowances,
                                ];
                                allowances[index] = {
                                  ...allowances[index],
                                  taxable: e.target.checked,
                                };
                                setInputs({
                                  ...inputs,
                                  allowances,
                                });
                              }}
                            />{" "}
                            課税
                          </label>

                          <button
                            onClick={() =>
                              setInputs({
                                ...inputs,
                                allowances:
                                  inputs.allowances.filter(
                                    (_, i) => i !== index
                                  ),
                              })
                            }
                            style={deleteButtonStyle}
                          >
                            削除
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>

                  <div>
                    <div
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                        marginBottom: 8,
                      }}
                    >
                      <strong style={sectionTitleStyle}>
                        その他控除
                      </strong>

                      <button
                        onClick={addDeduction}
                        style={smallButtonStyle}
                      >
                        ＋ 追加
                      </button>
                    </div>

                    {inputs.deductions.length === 0 && (
                      <div style={emptyInputStyle}>
                        その他控除はありません
                      </div>
                    )}

                    {inputs.deductions.map((item, index) => (
                      <div
                        key={index}
                        style={{
                          padding: 9,
                          marginBottom: 7,
                          border:
                            "1px solid rgba(148,180,216,.09)",
                          borderRadius: 9,
                          background: "rgba(5,15,27,.4)",
                        }}
                      >
                        <input
                          value={item.name}
                          placeholder="控除名"
                          onChange={(e) => {
                            const deductions = [...inputs.deductions];
                            deductions[index] = {
                              ...deductions[index],
                              name: e.target.value,
                            };
                            setInputs({ ...inputs, deductions });
                          }}
                          style={{
                            ...fieldStyle,
                            marginTop: 0,
                          }}
                        />

                        <input
                          value={item.amount}
                          placeholder="金額"
                          inputMode="decimal"
                          onChange={(e) => {
                            const deductions = [...inputs.deductions];
                            deductions[index] = {
                              ...deductions[index],
                              amount: e.target.value,
                            };
                            setInputs({ ...inputs, deductions });
                          }}
                          style={fieldStyle}
                        />

                        <div
                          style={{
                            textAlign: "right",
                            marginTop: 7,
                          }}
                        >
                          <button
                            onClick={() =>
                              setInputs({
                                ...inputs,
                                deductions:
                                  inputs.deductions.filter(
                                    (_, i) => i !== index
                                  ),
                              })
                            }
                            style={deleteButtonStyle}
                          >
                            削除
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {!result ? (
                <div
                  style={{
                    ...panelStyle,
                    minHeight: 330,
                    display: "grid",
                    placeItems: "center",
                    color: "#8298ae",
                    textAlign: "center",
                  }}
                >
                  <div>
                    <strong>まだ給与計算されていません</strong>
                    <p style={{ fontSize: 11 }}>
                      「給与を計算」を押すと結果が表示されます。
                    </p>
                  </div>
                </div>
              ) : (
                <>
                  <div
                    style={{
                      display: "grid",
                      gridTemplateColumns: "repeat(3, minmax(0, 1fr))",
                      gap: 11,
                      marginBottom: 13,
                    }}
                  >
                    <MoneyCard
                      label="総支給額"
                      value={result.gross_pay}
                      color="#9ba5ff"
                    />

                    <MoneyCard
                      label="控除合計"
                      value={result.total_deductions}
                      color="#ff9aa6"
                    />

                    <MoneyCard
                      label="差引支給額"
                      value={result.net_pay}
                      color="#65e6b5"
                      strong
                    />
                  </div>

                  <div
                    style={{
                      ...panelStyle,
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      gap: 15,
                      marginBottom: 13,
                    }}
                  >
                    <div>
                      <strong>
                        {result.finalized
                          ? "この給与は確定済みです"
                          : "給与計算結果を確認してください"}
                      </strong>

                      <div
                        style={{
                          marginTop: 4,
                          color: "#71879d",
                          fontSize: 9,
                        }}
                      >
                        {result.finalized
                          ? "従業員の給与明細に公開できます。"
                          : result.blocking_issues.length > 0
                            ? "要対応の問題を解消すると確定できます。"
                            : "問題がなければ給与を確定できます。"}
                      </div>
                    </div>

                    {result.finalized ? (
                      <span
                        style={{
                          padding: "8px 12px",
                          color: "#65e6b5",
                          border:
                            "1px solid rgba(69,224,168,.2)",
                          borderRadius: 9,
                          background: "rgba(69,224,168,.07)",
                          fontSize: 10,
                          fontWeight: 800,
                        }}
                      >
                        ✓ 確定済み
                      </span>
                    ) : (
                      <button
                        onClick={finalizePayroll}
                        disabled={result.blocking_issues.length > 0}
                        style={{
                          padding: "9px 14px",
                          border:
                            "1px solid rgba(69,224,168,.26)",
                          borderRadius: 9,
                          color:
                            result.blocking_issues.length > 0
                              ? "#667f98"
                              : "#07151a",
                          background:
                            result.blocking_issues.length > 0
                              ? "rgba(255,255,255,.03)"
                              : "linear-gradient(135deg, #45e0a8, #38d9c4)",
                          cursor:
                            result.blocking_issues.length > 0
                              ? "not-allowed"
                              : "pointer",
                          fontWeight: 800,
                          fontSize: 10,
                        }}
                      >
                        給与を確定
                      </button>
                    )}
                  </div>

                  {(result.blocking_issues.length > 0 ||
                    result.warnings.length > 0) && (
                    <div
                      style={{
                        ...panelStyle,
                        marginBottom: 13,
                        borderColor:
                          result.blocking_issues.length > 0
                            ? "rgba(255,107,122,.25)"
                            : "rgba(246,200,95,.2)",
                      }}
                    >
                      <strong
                        style={{
                          color:
                            result.blocking_issues.length > 0
                              ? "#ff9aa6"
                              : "#f6c85f",
                        }}
                      >
                        要確認
                      </strong>

                      {[
                        ...result.blocking_issues,
                        ...result.warnings,
                      ].map((item, index) => (
                        <div
                          key={index}
                          style={{
                            marginTop: 7,
                            color: "#a5b6c7",
                            fontSize: 10,
                          }}
                        >
                          • {item}
                        </div>
                      ))}
                    </div>
                  )}

                  <div
                    style={{
                      display: "grid",
                      gridTemplateColumns: "1fr 1fr",
                      gap: 13,
                      marginBottom: 13,
                    }}
                  >
                    <Breakdown
                      title="支給"
                      items={result.payments}
                      total={result.gross_pay}
                      color="#65e6b5"
                    />

                    <Breakdown
                      title="控除"
                      items={result.deductions}
                      total={result.total_deductions}
                      color="#ff9aa6"
                    />
                  </div>

                  <div style={panelStyle}>
                    <strong>勤務時間</strong>

                    <div
                      style={{
                        display: "grid",
                        gridTemplateColumns:
                          "repeat(4, minmax(0,1fr))",
                        gap: 12,
                        marginTop: 15,
                      }}
                    >
                      <MiniStat
                        label="通常勤務"
                        value={minutes(
                          result.classification.regular_minutes
                        )}
                      />
                      <MiniStat
                        label="時間外"
                        value={minutes(
                          result.classification.overtime_minutes
                        )}
                      />
                      <MiniStat
                        label="休日"
                        value={minutes(
                          result.classification.holiday_minutes
                        )}
                      />
                      <MiniStat
                        label="深夜"
                        value={minutes(
                          result.classification.night_minutes +
                            result.classification.regular_night_minutes +
                            result.classification.overtime_night_minutes +
                            result.classification.holiday_night_minutes
                        )}
                      />
                    </div>
                  </div>
                </>
              )}
            </section>
          )}
        </div>
      </main>
    </AuthGuard>
  );
}

const sectionTitleStyle = {
  color: "#dce7f4",
  fontSize: 11,
} as const;

const fieldLabelStyle = {
  display: "block",
  marginTop: 10,
  color: "#8298ae",
  fontSize: 9,
} as const;

const fieldStyle = {
  display: "block",
  width: "100%",
  height: 36,
  marginTop: 5,
  padding: "0 9px",
} as const;

const smallButtonStyle = {
  padding: "5px 8px",
  border: "1px solid rgba(109,124,255,.18)",
  borderRadius: 7,
  color: "#aeb7ff",
  background: "rgba(109,124,255,.06)",
  cursor: "pointer",
  fontSize: 9,
} as const;

const deleteButtonStyle = {
  padding: "4px 7px",
  border: "1px solid rgba(255,107,122,.17)",
  borderRadius: 6,
  color: "#ff9aa6",
  background: "rgba(255,107,122,.05)",
  cursor: "pointer",
  fontSize: 8,
} as const;

const emptyInputStyle = {
  padding: 18,
  color: "#667f98",
  textAlign: "center",
  fontSize: 9,
  border: "1px dashed rgba(148,180,216,.10)",
  borderRadius: 9,
} as const;

const panelStyle = {
  padding: 17,
  border: "1px solid rgba(148,180,216,.13)",
  borderRadius: 15,
  background: "rgba(12,25,43,.66)",
} as const;

const eyebrowStyle = {
  color: "#8390ff",
  fontSize: 11,
  fontWeight: 800,
  letterSpacing: ".12em",
} as const;

const errorStyle = {
  padding: 12,
  marginBottom: 14,
  color: "#ff9aa6",
  border: "1px solid rgba(255,107,122,.2)",
  borderRadius: 10,
  background: "rgba(255,107,122,.06)",
} as const;

const successStyle = {
  padding: 12,
  marginBottom: 14,
  color: "#65e6b5",
  border: "1px solid rgba(69,224,168,.18)",
  borderRadius: 10,
  background: "rgba(69,224,168,.06)",
} as const;

function MoneyCard({
  label,
  value,
  color,
  strong = false,
}: {
  label: string;
  value: string;
  color: string;
  strong?: boolean;
}) {
  return (
    <div style={panelStyle}>
      <span style={{ color: "#8298ae", fontSize: 10 }}>{label}</span>
      <strong
        style={{
          display: "block",
          marginTop: 8,
          color,
          fontSize: strong ? 25 : 21,
        }}
      >
        {money(value)}
      </strong>
    </div>
  );
}

function Breakdown({
  title,
  items,
  total,
  color,
}: {
  title: string;
  items: Record<string, string>;
  total: string;
  color: string;
}) {
  return (
    <div style={panelStyle}>
      <strong>{title}内訳</strong>

      <div style={{ marginTop: 12 }}>
        {Object.entries(items).map(([name, value]) => (
          <div
            key={name}
            style={{
              display: "flex",
              justifyContent: "space-between",
              gap: 12,
              padding: "8px 0",
              borderBottom: "1px solid rgba(148,180,216,.07)",
              fontSize: 11,
            }}
          >
            <span style={{ color: "#91a5ba" }}>{name}</span>
            <strong>{money(value)}</strong>
          </div>
        ))}
      </div>

      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          marginTop: 12,
          color,
        }}
      >
        <strong>合計</strong>
        <strong>{money(total)}</strong>
      </div>
    </div>
  );
}

function MiniStat({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <div>
      <span style={{ color: "#71879d", fontSize: 9 }}>{label}</span>
      <strong
        style={{
          display: "block",
          marginTop: 5,
          fontSize: 13,
        }}
      >
        {value}
      </strong>
    </div>
  );
}
