from __future__ import annotations
from models.leave_request import LeaveRequest
from models.user import User
from services.auth_service import hash_password, verify_password
import csv
import shutil
from datetime import date
from decimal import Decimal
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
try:
    from tkcalendar import DateEntry
except ImportError:
    DateEntry = ttk.Entry  # type: ignore[misc,assignment]
from models.allowance import Allowance
from models.deduction import OtherDeduction
from models.employee import Employee
from models.employment import EmploymentTerms
from models.transportation import Transportation
from models.work_record import WorkRecord
from models.break_record import BreakRecord
from models.company import Company
from services.payslip_service import export_pdf, render_text
from services.payroll_service import calculate_payroll
from services.storage_service import PayrollRepository
from services.time_service import parse_date, parse_time
from services.export_service import export_payroll_ledger, export_payslip_zip

BASE = Path(__file__).resolve().parent

class LoginWindow(ttk.Frame):
    def __init__(self, root: tk.Tk) -> None:
        super().__init__(root, padding=30)
        self.root = root
        self.repo = PayrollRepository(BASE / "data" / "payroll.sqlite3")

        root.title("給与計算 - ログイン")
        root.geometry("420x280")
        root.resizable(False, False)

        self.username = tk.StringVar()
        self.password = tk.StringVar()

        self.pack(fill="both", expand=True)

        ttk.Label(
            self,
            text="給与計算システム",
            font=("Helvetica", 20, "bold"),
        ).pack(pady=(15, 25))

        form = ttk.Frame(self)
        form.pack()

        ttk.Label(form, text="ユーザー名").grid(
            row=0, column=0, sticky="w", pady=8
        )
        username_entry = ttk.Entry(
            form,
            textvariable=self.username,
            width=25,
        )
        username_entry.grid(row=0, column=1, padx=10, pady=8)

        ttk.Label(form, text="パスワード").grid(
            row=1, column=0, sticky="w", pady=8
        )
        password_entry = ttk.Entry(
            form,
            textvariable=self.password,
            show="*",
            width=25,
        )
        password_entry.grid(row=1, column=1, padx=10, pady=8)

        ttk.Button(
            self,
            text="ログイン",
            command=self.login,
        ).pack(pady=20)

        username_entry.focus()
        password_entry.bind("<Return>", lambda _: self.login())

    def login(self) -> None:
        username = self.username.get().strip()
        password = self.password.get()

        user = self.repo.user(username)

        if (
            user is None
            or not user.active
            or not verify_password(password, user.password_hash)
        ):
            messagebox.showerror(
                "ログインエラー",
                "ユーザー名またはパスワードが正しくありません。",
            )
            return

        self.destroy()

        self.root.geometry("")
        self.root.resizable(True, True)

        SalaryApp(self.root, user)

class SalaryApp(ttk.Frame):
    def __init__(self, root: tk.Tk, current_user: User) -> None:
        super().__init__(root, padding=12)
        self.current_user = current_user
        self.root, self.repo = root, PayrollRepository(BASE / "data" / "payroll.sqlite3")
        self.records: list[WorkRecord] = []
        self.editing_record_id: int | None = None
        self.allowance_items: list[Allowance] = []
        self.deduction_items: list[OtherDeduction] = []
        self.result = None
        self.employee: Employee | None = None
        root.title("給与計算")
        root.minsize(920, 680)
        self._setup_style()
        self.pack(fill="both", expand=True)
        self._build()
        self.company = self.repo.company()
        self.company_name.set(self.company.name); self.company_address.set(self.company.address); self.company_representative.set(self.company.representative)
        self.refresh_employees()

        if (
            self.current_user.role == "employee"
            and self.current_user.employee_id
        ):
            employee = next(
                (
                    item
                    for item in self.repo.employees()
                    if item.employee_id == self.current_user.employee_id
                ),
                None,
            )

            if employee:
                self.employee = employee
                self.records = self.repo.work_records(
                    employee.employee_id,
                    self.year_month.get(),
                )
                self.load_terms()
                self.load_monthly_inputs()
                self.refresh_records()
                self.status_badge.set(
                    f"ログイン中：{employee.name}（{employee.employee_id}）"
                )
                self.refresh_leave_requests()

    def _setup_style(self) -> None:
        style = ttk.Style(self.root)
        try: style.theme_use("clam")
        except tk.TclError: pass
        style.configure("Brand.TLabel", font=("Helvetica", 18, "bold"), foreground="#2563eb")
        style.configure("SubBrand.TLabel", font=("Helvetica", 10), foreground="#64748b")
        style.configure("Accent.TButton", font=("Helvetica", 11, "bold"))

    def _build(self) -> None:
        brand = ttk.Frame(self, padding=(8, 4)); brand.pack(fill="x")
        ttk.Label(brand, text="給与計算", style="Brand.TLabel").pack(side="left")
        ttk.Label(brand, text="月次給与を、正確に・迷わず処理", style="SubBrand.TLabel").pack(side="left", padx=14)
        self.status_badge = tk.StringVar(value="従業員を選択してください")
        ttk.Label(brand, textvariable=self.status_badge, style="SubBrand.TLabel").pack(side="right")
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True)
        self.employee_tab = ttk.Frame(notebook, padding=10)
        self.attendance_tab = ttk.Frame(notebook, padding=10)
        self.payroll_tab = ttk.Frame(notebook, padding=10)
        self.payslip_tab = ttk.Frame(notebook, padding=10)
        self.leave_tab = ttk.Frame(notebook, padding=10)
        self.analysis_tab = ttk.Frame(notebook, padding=10)
        if self.current_user.role == "admin":
            notebook.add(self.employee_tab, text="👤 従業員管理")
            notebook.add(self.attendance_tab, text="📅 勤怠管理")
            notebook.add(self.payroll_tab, text="💰 給与計算")
            notebook.add(self.payslip_tab, text="📄 給与明細")
            notebook.add(self.analysis_tab, text="⚙️ 会社設定・月次管理")
        else:
            notebook.add(self.attendance_tab, text="📅 マイ勤怠")
            notebook.add(self.payslip_tab, text="📄 マイ給与明細")
            notebook.add(self.leave_tab, text="🏖 有給申請")
        self._employee_ui(); self._attendance_ui(); self._payroll_ui(); self._payslip_ui(); self._leave_ui(); self._analysis_ui()

    def _employee_ui(self) -> None:
        form = ttk.LabelFrame(self.employee_tab, text="従業員情報", padding=10); form.pack(fill="x")
        self.emp_vars = {key: tk.StringVar() for key in ("id", "name", "hire", "hourly", "monthly", "hours", "days", "size", "dependents", "resident", "standard")}
        fields = [("社員番号", "id"), ("氏名", "name"), ("入社日", "hire"), ("時給", "hourly"), ("月給", "monthly"), ("週所定時間", "hours"), ("週日数", "days"), ("勤務先規模", "size"), ("扶養人数", "dependents"), ("住民税（月額）", "resident"), ("標準報酬月額", "standard")]
        for index, (label, key) in enumerate(fields):
            ttk.Label(form, text=label).grid(row=index // 4 * 2, column=(index % 4) * 2, sticky="w", padx=4, pady=2)
            if key == "hire" and DateEntry is not ttk.Entry:
                widget = DateEntry(form, textvariable=self.emp_vars[key], date_pattern="yyyy/mm/dd", width=12)
            else:
                widget = ttk.Entry(form, textvariable=self.emp_vars[key], width=14)
            widget.grid(row=index // 4 * 2 + 1, column=(index % 4) * 2, padx=4, pady=2)
        self.emp_type = tk.StringVar(value="パート"); self.pay_type = tk.StringVar(value="時給"); self.tax_type = tk.StringVar(value="甲"); self.resident_method = tk.StringVar(value="特別徴収")
        for col, (label, var, values) in enumerate((("雇用形態", self.emp_type, ["正社員", "契約社員", "パート", "アルバイト"]), ("賃金形態", self.pay_type, ["時給", "月給"]), ("税区分", self.tax_type, ["甲", "乙"]), ("住民税", self.resident_method, ["特別徴収", "普通徴収"]))):
            ttk.Label(form, text=label).grid(row=6, column=col * 2, sticky="w", padx=4)
            ttk.Combobox(form, textvariable=var, values=values, state="readonly", width=12).grid(row=7, column=col * 2, padx=4)
        ttk.Button(form, text="保存", command=self.save_employee).grid(row=8, column=0, pady=8, sticky="w")
        self.employee_tree = ttk.Treeview(self.employee_tab, columns=("id", "name", "type", "pay"), show="headings", height=8)
        for key, label in zip(("id", "name", "type", "pay"), ("社員番号", "氏名", "雇用形態", "賃金形態")): self.employee_tree.heading(key, text=label)
        self.employee_tree.pack(fill="x", pady=8); self.employee_tree.bind("<<TreeviewSelect>>", lambda _: self.select_employee())

    def _attendance_ui(self) -> None:
        box = ttk.LabelFrame(self.attendance_tab, text="勤務入力（時・分は選択または HH:MM 入力）", padding=10); box.pack(fill="x")
        self.work_date, self.break_mode = tk.StringVar(value=date.today().strftime("%Y/%m/%d")), tk.StringVar(value="合計時間")
        self.start_h, self.start_m, self.end_h, self.end_m = (tk.StringVar(value=v) for v in ("09", "00", "18", "00"))
        self.break_total, self.break_ranges, self.holiday = tk.StringVar(value="60"), tk.StringVar(), tk.BooleanVar()
        ttk.Label(box, text="日付").grid(row=0, column=0); (DateEntry(box, textvariable=self.work_date, date_pattern="yyyy/mm/dd", width=12) if DateEntry is not ttk.Entry else ttk.Entry(box, textvariable=self.work_date, width=12)).grid(row=0, column=1)
        for col, (label, h, m) in enumerate((("開始", self.start_h, self.start_m), ("終了", self.end_h, self.end_m))):
            ttk.Label(box, text=label).grid(row=0, column=2 + col * 3); ttk.Combobox(box, textvariable=h, values=[f"{i:02}" for i in range(24)], width=3).grid(row=0, column=3 + col * 3); ttk.Combobox(box, textvariable=m, values=[f"{i:02}" for i in range(60)], width=3).grid(row=0, column=4 + col * 3)
        ttk.Radiobutton(box, text="合計時間", variable=self.break_mode, value="合計時間").grid(row=1, column=0)
        ttk.Entry(box, textvariable=self.break_total, width=7).grid(row=1, column=1)
        ttk.Radiobutton(box, text="時間帯", variable=self.break_mode, value="時間帯").grid(row=1, column=2)
        ttk.Entry(box, textvariable=self.break_ranges, width=28).grid(row=1, column=3, columnspan=2)
        ttk.Label(box, text="例 12:00-13:00,18:00-18:30").grid(row=2, column=0, columnspan=3, sticky="w")
        ttk.Checkbutton(box, text="法定休日勤務", variable=self.holiday).grid(row=2, column=3)
        ttk.Button(box, text="勤務を追加・更新", command=self.add_record).grid(row=2, column=4); ttk.Button(box, text="選択を削除", command=self.delete_record).grid(row=2, column=5); ttk.Button(box, text="CSV入力", command=self.import_csv).grid(row=2, column=6); ttk.Button(box, text="CSV出力", command=self.export_csv).grid(row=2, column=7)
        self.record_tree = ttk.Treeview(self.attendance_tab, columns=("date", "start", "end", "break", "holiday"), show="headings", height=13)
        for key, label in zip(("date", "start", "end", "break", "holiday"), ("日付", "開始", "終了", "休憩", "休日")): self.record_tree.heading(key, text=label)
        self.record_tree.pack(fill="both", expand=True, pady=8); self.record_tree.bind("<<TreeviewSelect>>", lambda _: self.edit_record())

    def _payroll_ui(self) -> None:
        top = ttk.Frame(self.payroll_tab); top.pack(fill="x")
        self.year_month, self.overtime_method, self.fixed_amount, self.fixed_hours, self.monthly_divisor = tk.StringVar(value=date.today().strftime("%Y-%m")), tk.StringVar(value="実残業時間方式"), tk.StringVar(value="0"), tk.StringVar(value="0"), tk.StringVar(value="0")
        for col, (label, var) in enumerate((("対象年月", self.year_month), ("残業方式", self.overtime_method), ("固定残業代", self.fixed_amount), ("固定残業時間", self.fixed_hours))):
            ttk.Label(top, text=label).grid(row=0, column=col * 2, padx=4)
            if label == "残業方式":
                ttk.Combobox(top, textvariable=var, values=["実残業時間方式", "固定残業代方式"], state="readonly", width=14).grid(row=0, column=col * 2 + 1, padx=4)
            else:
                ttk.Entry(top, textvariable=var, width=16).grid(row=0, column=col * 2 + 1, padx=4)
        self.allowance_name, self.allowance_amount, self.allowance_taxable, self.transport_method, self.transport_amount = tk.StringVar(value="住宅手当"), tk.StringVar(value="0"), tk.BooleanVar(value=True), tk.StringVar(value="なし"), tk.StringVar(value="0")
        ttk.Combobox(top, textvariable=self.allowance_name, values=["住宅手当", "資格手当", "スキル手当", "役職手当", "家族手当", "食事手当", "皆勤手当", "精勤手当", "その他"], width=12).grid(row=1, column=0)
        ttk.Entry(top, textvariable=self.allowance_amount, width=10).grid(row=1, column=1)
        ttk.Button(top, text="手当を追加", command=self.add_allowance).grid(row=1, column=2)
        ttk.Checkbutton(top, text="課税", variable=self.allowance_taxable).grid(row=1, column=3)
        ttk.Combobox(top, textvariable=self.transport_method, values=["なし", "月額固定", "日額", "実費"], width=10).grid(row=1, column=4)
        ttk.Entry(top, textvariable=self.transport_amount, width=10).grid(row=1, column=5)
        ttk.Label(top, text="交通費（単価）").grid(row=1, column=6, columnspan=2)
        ttk.Button(top, text="✦ 計算", command=self.calculate, style="Accent.TButton").grid(row=0, column=8, padx=8)
        ttk.Button(top, text="計算詳細", command=self.show_detail).grid(row=0, column=9)
        ttk.Button(top, text="給与を確定", command=self.finalize).grid(row=0, column=10)
        ttk.Button(top, text="全社員を月次計算", command=self.calculate_all).grid(row=0, column=11)
        ttk.Label(top, text="月平均所定時間").grid(row=2, column=0); ttk.Entry(top, textvariable=self.monthly_divisor, width=12).grid(row=2, column=1)
        ttk.Label(top, text="※固定残業代・時間・月平均所定時間は選択した従業員ごとに保存されます。").grid(row=2, column=2, columnspan=7, sticky="w")
        self.check_message = tk.StringVar(value="入力内容を確認してから計算してください。")
        check = ttk.LabelFrame(self.payroll_tab, text="計算前チェック", padding=8); check.pack(fill="x", pady=(8, 0))
        ttk.Label(check, textvariable=self.check_message, foreground="#b45309").pack(anchor="w")
        self.summary = tk.Text(self.payroll_tab, height=25, wrap="word"); self.summary.pack(fill="both", expand=True, pady=10)
        lists = ttk.Frame(self.payroll_tab); lists.pack(fill="x")
        left = ttk.LabelFrame(lists, text="追加した手当（件数制限なし）", padding=4); left.pack(side="left", fill="both", expand=True, padx=(0, 4))
        self.allowance_tree = ttk.Treeview(left, columns=("name", "amount", "tax"), show="headings", height=5)
        for key, label in (("name", "名称"), ("amount", "金額"), ("tax", "課税")): self.allowance_tree.heading(key, text=label)
        self.allowance_tree.pack(fill="x"); ttk.Button(left, text="選択を削除", command=self.delete_allowance).pack(anchor="e")
        right = ttk.LabelFrame(lists, text="その他控除", padding=4); right.pack(side="left", fill="both", expand=True)
        self.deduction_name, self.deduction_amount = tk.StringVar(value="組合費"), tk.StringVar(value="0")
        ttk.Combobox(right, textvariable=self.deduction_name, values=["社宅本人負担", "組合費", "食事代", "その他"], width=12).pack(side="left")
        ttk.Entry(right, textvariable=self.deduction_amount, width=10).pack(side="left")
        ttk.Button(right, text="控除を追加", command=self.add_deduction).pack(side="left")
        self.deduction_tree = ttk.Treeview(right, columns=("name", "amount"), show="headings", height=5)
        for key, label in (("name", "名称"), ("amount", "金額")): self.deduction_tree.heading(key, text=label)
        self.deduction_tree.pack(fill="x", side="bottom")
        ttk.Button(right, text="選択を削除", command=self.delete_deduction).pack(anchor="e", side="bottom")

    def _payslip_ui(self) -> None:
        ttk.Button(self.payslip_tab, text="PDF出力", command=self.pdf).pack(anchor="w")
        self.payslip = tk.Text(self.payslip_tab, height=31, wrap="word"); self.payslip.pack(fill="both", expand=True, pady=8)

    def _leave_ui(self) -> None:
        form = ttk.LabelFrame(
            self.leave_tab,
            text="有給休暇申請",
            padding=12,
        )
        form.pack(fill="x")

        self.leave_date = tk.StringVar(
            value=date.today().strftime("%Y/%m/%d")
        )
        self.leave_reason = tk.StringVar()

        ttk.Label(
            form,
            text="取得希望日",
        ).grid(row=0, column=0, padx=5, pady=5)

        if DateEntry is not ttk.Entry:
            DateEntry(
                form,
                textvariable=self.leave_date,
                date_pattern="yyyy/mm/dd",
                width=12,
            ).grid(row=0, column=1, padx=5, pady=5)
        else:
            ttk.Entry(
                form,
                textvariable=self.leave_date,
                width=14,
            ).grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(
            form,
            text="理由・備考",
        ).grid(row=0, column=2, padx=5, pady=5)

        ttk.Entry(
            form,
            textvariable=self.leave_reason,
            width=35,
        ).grid(row=0, column=3, padx=5, pady=5)

        ttk.Button(
            form,
            text="有給を申請",
            command=self.submit_leave_request,
        ).grid(row=0, column=4, padx=10, pady=5)

        history = ttk.LabelFrame(
            self.leave_tab,
            text="申請履歴",
            padding=8,
        )
        history.pack(
            fill="both",
            expand=True,
            pady=(10, 0),
        )

        self.leave_tree = ttk.Treeview(
            history,
            columns=("date", "reason", "status"),
            show="headings",
        )

        self.leave_tree.heading("date", text="取得希望日")
        self.leave_tree.heading("reason", text="理由・備考")
        self.leave_tree.heading("status", text="状態")

        self.leave_tree.column("date", width=130)
        self.leave_tree.column("reason", width=400)
        self.leave_tree.column("status", width=100)

        self.leave_tree.pack(
            fill="both",
            expand=True,
        )

    def submit_leave_request(self) -> None:
        if (
            self.current_user.role != "employee"
            or not self.current_user.employee_id
        ):
            return messagebox.showwarning(
                "有給申請",
                "社員アカウントでログインしてください。",
            )

        try:
            request = LeaveRequest(
                employee_id=self.current_user.employee_id,
                leave_date=parse_date(self.leave_date.get()),
                reason=self.leave_reason.get().strip(),
            )

            self.repo.save_leave_request(request)

            self.leave_reason.set("")
            self.refresh_leave_requests()

            messagebox.showinfo(
                "有給申請",
                "有給休暇を申請しました。",
            )

        except Exception as error:
            messagebox.showerror(
                "有給申請エラー",
                str(error),
            )

    def refresh_leave_requests(self) -> None:
        for item in self.leave_tree.get_children():
            self.leave_tree.delete(item)

        if (
            self.current_user.role != "employee"
            or not self.current_user.employee_id
        ):
            return

        requests = self.repo.leave_requests(
            self.current_user.employee_id
        )

        for request in requests:
            self.leave_tree.insert(
                "",
                "end",
                iid=str(request.request_id),
                values=(
                    request.leave_date.strftime("%Y/%m/%d"),
                    request.reason,
                    request.status,
                ),
            )

    def _analysis_ui(self) -> None:
        settings = ttk.LabelFrame(self.analysis_tab, text="会社情報（給与明細に表示）", padding=10); settings.pack(fill="x")
        self.company_name, self.company_address, self.company_representative = tk.StringVar(), tk.StringVar(), tk.StringVar()
        for col, (label, value) in enumerate((("会社名", self.company_name), ("所在地", self.company_address), ("代表者", self.company_representative))):
            ttk.Label(settings, text=label).grid(row=0, column=col * 2, padx=4); ttk.Entry(settings, textvariable=value, width=25).grid(row=0, column=col * 2 + 1, padx=4)
        ttk.Button(settings, text="会社情報を保存", command=self.save_company).grid(row=1, column=0, pady=8)
        dashboard = ttk.LabelFrame(self.analysis_tab, text="今月のダッシュボード", padding=12); dashboard.pack(fill="x", pady=12)
        self.dashboard_vars = {name: tk.StringVar(value="—") for name in ("employees", "gross", "net", "finalized")}
        for col, (label, name) in enumerate((("対象社員", "employees"), ("総支給", "gross"), ("差引支給", "net"), ("確定済", "finalized"))):
            card = ttk.Frame(dashboard, padding=8); card.grid(row=0, column=col, sticky="ew", padx=5); ttk.Label(card, text=label).pack(); ttk.Label(card, textvariable=self.dashboard_vars[name], font=("Helvetica", 20, "bold")).pack()
            dashboard.columnconfigure(col, weight=1)
        controls = ttk.Frame(self.analysis_tab); controls.pack(fill="x")
        ttk.Button(controls, text="ダッシュボード更新", command=self.refresh_dashboard).pack(side="left", padx=3)
        ttk.Button(controls, text="給与台帳CSV出力", command=self.export_ledger).pack(side="left", padx=3)
        ttk.Button(controls, text="全社員明細PDF（ZIP）", command=self.export_all_pdfs).pack(side="left", padx=3)
        ttk.Button(controls, text="データをバックアップ", command=self.backup_database).pack(side="left", padx=3)
        ttk.Button(controls, text="国税庁税額表CSVを登録", command=self.import_tax_table).pack(side="left", padx=3)
        audit = ttk.LabelFrame(self.analysis_tab, text="操作履歴", padding=6); audit.pack(fill="both", expand=True, pady=10)
        self.audit_tree = ttk.Treeview(audit, columns=("time", "action", "subject", "detail"), show="headings", height=9)
        for key, label, width in (("time", "日時", 150), ("action", "操作", 110), ("subject", "対象", 120), ("detail", "詳細", 320)):
            self.audit_tree.heading(key, text=label); self.audit_tree.column(key, width=width)
        self.audit_tree.pack(fill="both", expand=True)

    def save_employee(self) -> None:
        try:
            v = self.emp_vars
            employee = Employee(v["id"].get(), v["name"].get(), self.emp_type.get(), parse_date(v["hire"].get()), self.pay_type.get(), Decimal(v["hourly"].get() or "0"), Decimal(v["monthly"].get() or "0"), Decimal(v["hours"].get() or "0"), int(v["days"].get() or 0), workplace_size=int(v["size"].get() or 0), dependents=int(v["dependents"].get() or 0), tax_category=self.tax_type.get(), resident_tax_monthly=Decimal(v["resident"].get() or "0"), resident_tax_method=self.resident_method.get(), standard_monthly_remuneration=Decimal(v["standard"].get() or "0"))
            if not employee.employee_id or not employee.name: raise ValueError("社員番号と氏名は必須です。")
            self.repo.save_employee(employee); self.employee = employee; self.refresh_employees(); messagebox.showinfo("保存", "従業員を保存しました。")
        except Exception as error: messagebox.showerror("入力エラー", str(error))

    def refresh_employees(self) -> None:
        self.employee_tree.delete(*self.employee_tree.get_children())
        for employee in self.repo.employees(): self.employee_tree.insert("", "end", iid=employee.employee_id, values=(employee.employee_id, employee.name, employee.employment_type, employee.pay_type))

    def select_employee(self) -> None:
        selected = self.employee_tree.selection()
        if not selected:
            return

        self.employee = next(
            e for e in self.repo.employees()
            if e.employee_id == selected[0]
        )

        # 選択した従業員の情報をフォームへ表示
        self.emp_vars["id"].set(self.employee.employee_id)
        self.emp_vars["name"].set(self.employee.name)
        self.emp_vars["hire"].set(self.employee.hire_date.strftime("%Y/%m/%d"))
        self.emp_vars["hourly"].set(str(self.employee.hourly_rate))
        self.emp_vars["monthly"].set(str(self.employee.monthly_salary))
        self.emp_vars["hours"].set(str(self.employee.weekly_hours))
        self.emp_vars["days"].set(str(self.employee.weekly_days))
        self.emp_vars["size"].set(str(self.employee.workplace_size))
        self.emp_vars["dependents"].set(str(self.employee.dependents))
        self.emp_vars["resident"].set(str(self.employee.resident_tax_monthly))
        self.emp_vars["standard"].set(
            str(self.employee.standard_monthly_remuneration)
        )

        self.emp_type.set(self.employee.employment_type)
        self.pay_type.set(self.employee.pay_type)
        self.tax_type.set(self.employee.tax_category)
        self.resident_method.set(self.employee.resident_tax_method)

        self.records = self.repo.work_records(
            self.employee.employee_id,
            self.year_month.get()
        )

        self.load_terms()
        self.load_monthly_inputs()
        self.refresh_records()

        self.status_badge.set(
            f"選択中：{self.employee.name}（{self.employee.employee_id}）"
        )

    def load_terms(self) -> None:
        if not self.employee: return
        terms = self.repo.terms(self.employee.employee_id)
        self.overtime_method.set(terms.overtime_method); self.fixed_amount.set(str(terms.fixed_overtime_amount)); self.fixed_hours.set(str(Decimal(terms.fixed_overtime_minutes) / 60)); self.monthly_divisor.set(str(terms.monthly_hourly_divisor))

    def load_monthly_inputs(self) -> None:
        if not self.employee: return
        self.allowance_items, self.deduction_items, transport = self.repo.monthly_inputs(self.employee.employee_id, self.year_month.get())
        self.transport_method.set(transport.method); self.transport_amount.set(str(transport.unit_amount)); self.refresh_components()

    def add_record(self) -> None:
        if not self.employee: return messagebox.showwarning("従業員", "従業員を選択してください。")
        try:
            breaks = []
            if self.break_mode.get() == "時間帯":
                for item in filter(None, self.break_ranges.get().replace("～", "-").split(",")):
                    start, end = item.strip().split("-")
                    breaks.append(BreakRecord(parse_time(start), parse_time(end)))
            record = WorkRecord(self.employee.employee_id, parse_date(self.work_date.get()), int(self.start_h.get()) * 60 + int(self.start_m.get()), int(self.end_h.get()) * 60 + int(self.end_m.get()), self.holiday.get(), int(self.break_total.get() or 0) if not breaks else 0, breaks, self.editing_record_id)
            self.repo.save_work_record(record)
            self.records = [record if item.record_id == record.record_id else item for item in self.records]
            if not any(item.record_id == record.record_id for item in self.records): self.records.append(record)
            self.editing_record_id = None; self.refresh_records()
        except Exception as error: messagebox.showerror("入力エラー", str(error))

    def refresh_records(self) -> None:
        self.record_tree.delete(*self.record_tree.get_children())
        for r in self.records: self.record_tree.insert("", "end", iid=str(r.record_id), values=(r.work_date, f"{r.start_minute//60:02}:{r.start_minute%60:02}", f"{r.end_minute//60:02}:{r.end_minute%60:02}", r.actual_break_minutes, "○" if r.is_holiday else ""))

    def edit_record(self) -> None:
        selected = self.record_tree.selection()
        if not selected: return
        self.editing_record_id = int(selected[0]); record = next(r for r in self.records if r.record_id == self.editing_record_id)
        self.work_date.set(record.work_date.strftime("%Y/%m/%d")); self.start_h.set(f"{record.start_minute//60:02}"); self.start_m.set(f"{record.start_minute%60:02}"); self.end_h.set(f"{record.end_minute//60:02}"); self.end_m.set(f"{record.end_minute%60:02}"); self.holiday.set(record.is_holiday)
        self.break_mode.set("合計時間"); self.break_total.set(str(record.actual_break_minutes))

    def delete_record(self) -> None:
        selected = self.record_tree.selection()
        if not selected or not self.employee: return
        record_id = int(selected[0]); self.repo.delete_work_record(self.employee.employee_id, record_id); self.records = [r for r in self.records if r.record_id != record_id]; self.editing_record_id = None; self.refresh_records()

    def add_allowance(self) -> None:
        try:
            amount = Decimal(self.allowance_amount.get())
            if amount < 0: raise ValueError("手当は0円以上です。")
            self.allowance_items.append(Allowance(self.allowance_name.get(), amount, self.allowance_taxable.get())); self.refresh_components()
        except Exception as error: messagebox.showerror("手当", str(error))

    def delete_allowance(self) -> None:
        selected = self.allowance_tree.selection()
        if selected: self.allowance_items.pop(int(selected[0])); self.refresh_components()

    def add_deduction(self) -> None:
        try:
            amount = Decimal(self.deduction_amount.get())
            if amount < 0: raise ValueError("控除は0円以上です。")
            self.deduction_items.append(OtherDeduction(self.deduction_name.get(), amount)); self.refresh_components()
        except Exception as error: messagebox.showerror("控除", str(error))

    def delete_deduction(self) -> None:
        selected = self.deduction_tree.selection()
        if selected: self.deduction_items.pop(int(selected[0])); self.refresh_components()

    def refresh_components(self) -> None:
        self.allowance_tree.delete(*self.allowance_tree.get_children()); self.deduction_tree.delete(*self.deduction_tree.get_children())
        for i, item in enumerate(self.allowance_items): self.allowance_tree.insert("", "end", iid=str(i), values=(item.name, f"{item.amount:,.0f}", "課税" if item.taxable else "非課税"))
        for i, item in enumerate(self.deduction_items): self.deduction_tree.insert("", "end", iid=str(i), values=(item.name, f"{item.amount:,.0f}"))

    def calculate(self) -> None:
        if not self.employee: return messagebox.showwarning("従業員", "従業員を選択してください。")
        try:
            terms = EmploymentTerms(self.employee.employee_id, overtime_method=self.overtime_method.get(), fixed_overtime_amount=Decimal(self.fixed_amount.get() or "0"), fixed_overtime_minutes=int(Decimal(self.fixed_hours.get() or "0") * 60), monthly_hourly_divisor=Decimal(self.monthly_divisor.get() or "0"))
            self.repo.save_terms(terms)
            allowances = list(self.allowance_items)
            transport = Transportation(self.transport_method.get(), Decimal(self.transport_amount.get() or "0"), len(self.records))
            self.repo.save_monthly_inputs(self.employee.employee_id, self.year_month.get(), allowances, self.deduction_items, transport)
            self.result = calculate_payroll(self.employee, terms, self.records, allowances, transport, self.deduction_items, self.year_month.get())
            self.result.company_name = self.repo.company().name
            self.repo.save_payroll_result(self.result)
            issues = self.result.blocking_issues + self.result.warnings
            self.check_message.set("要対応：" + " / ".join(issues) if issues else "✓ 計算結果に問題はありません。給与を確定できます。")
            text = render_text(self.employee, self.result); self.summary.delete("1.0", "end"); self.summary.insert("1.0", text + "\n\n【確認事項】\n" + "\n".join(issues or ["ありません"])); self.payslip.delete("1.0", "end"); self.payslip.insert("1.0", text)
        except Exception as error: messagebox.showerror("計算エラー", str(error))

    def show_detail(self) -> None:
        if not self.result: return
        c = self.result.classification; messagebox.showinfo("計算詳細", f"通常勤務: {c.regular_minutes}分\n時間外: {c.overtime_minutes}分\n深夜: {c.night_minutes+c.overtime_night_minutes+c.holiday_night_minutes}分\n休日: {c.holiday_minutes}分\n総支給: {self.result.gross_pay:,.0f}円\n控除: {self.result.total_deductions:,.0f}円")

    def finalize(self) -> None:
        if not self.result: return messagebox.showwarning("給与確定", "先に計算してください。")
        if self.result.blocking_issues: return messagebox.showerror("給与確定不可", "\n".join(self.result.blocking_issues))
        self.result.finalized = True; self.repo.save_payroll_result(self.result); messagebox.showinfo("給与確定", "給与計算結果を確定・保存しました。")

    def calculate_all(self) -> None:
        year_month = self.year_month.get(); summaries: list[str] = []
        for employee in self.repo.employees():
            terms = self.repo.terms(employee.employee_id)
            records = self.repo.work_records(employee.employee_id, year_month)
            allowances, deductions, transport = self.repo.monthly_inputs(employee.employee_id, year_month)
            transport.attendance_days = len(records)
            result = calculate_payroll(employee, terms, records, allowances, transport, deductions, year_month)
            result.company_name = self.repo.company().name
            self.repo.save_payroll_result(result)
            state = "要確認" if result.blocking_issues else "計算済"
            summaries.append(f"{employee.employee_id} {employee.name}: {result.net_pay:,.0f}円（{state}）")
        self.summary.delete("1.0", "end"); self.summary.insert("1.0", "月次一括計算結果\n\n" + "\n".join(summaries))
        self.refresh_dashboard()

    def save_company(self) -> None:
        self.company = Company(self.company_name.get(), self.company_address.get(), self.company_representative.get())
        self.repo.save_company(self.company); messagebox.showinfo("会社情報", "会社情報を保存しました。")

    def _month_items(self) -> list[tuple[Employee, object]]:
        employees = {employee.employee_id: employee for employee in self.repo.employees()}
        return [(employees[result.employee_id], result) for result in self.repo.payroll_results(self.year_month.get()) if result.employee_id in employees]

    def refresh_dashboard(self) -> None:
        items = self._month_items()
        self.dashboard_vars["employees"].set(str(len(items)))
        self.dashboard_vars["gross"].set(f"¥{sum((result.gross_pay for _, result in items), Decimal('0')):,.0f}")
        self.dashboard_vars["net"].set(f"¥{sum((result.net_pay for _, result in items), Decimal('0')):,.0f}")
        self.dashboard_vars["finalized"].set(f"{sum(1 for _, result in items if result.finalized)} / {len(items)}")
        self.audit_tree.delete(*self.audit_tree.get_children())
        for row in self.repo.recent_audit(): self.audit_tree.insert("", "end", values=row)

    def export_ledger(self) -> None:
        items = self._month_items()
        if not items: return messagebox.showwarning("給与台帳", "対象月の計算結果がありません。")
        path = filedialog.asksaveasfilename(defaultextension=".csv", initialdir=BASE / "exports", filetypes=[("CSV", "*.csv")])
        if path: export_payroll_ledger(items, Path(path)); messagebox.showinfo("給与台帳", "CSVを出力しました。")

    def export_all_pdfs(self) -> None:
        items = self._month_items()
        if not items: return messagebox.showwarning("給与明細", "対象月の計算結果がありません。")
        if any(not result.finalized for _, result in items): return messagebox.showwarning("給与明細", "全社員分を確定してから出力してください。")
        path = filedialog.asksaveasfilename(defaultextension=".zip", initialdir=BASE / "exports", filetypes=[("ZIP", "*.zip")])
        if path: export_payslip_zip(items, Path(path)); messagebox.showinfo("給与明細", "全社員分PDFをZIPに出力しました。")

    def backup_database(self) -> None:
        path = filedialog.asksaveasfilename(defaultextension=".sqlite3", initialdir=BASE / "exports", filetypes=[("SQLite", "*.sqlite3")])
        if path: self.repo.backup_to(Path(path)); messagebox.showinfo("バックアップ", "データベースをバックアップしました。")

    def import_tax_table(self) -> None:
        """Register a reviewed NTA monthly tax table without embedding tax rates in code."""
        source = filedialog.askopenfilename(filetypes=[("CSV", "*.csv")])
        if not source: return
        try:
            with open(source, encoding="utf-8-sig", newline="") as file:
                headers = set((csv.DictReader(file).fieldnames or []))
            required = {"lower", "upper", "category", "dependents", "tax"}
            if not required <= headers:
                raise ValueError("CSV列は lower, upper, category, dependents, tax が必要です。")
            year = self.year_month.get().split("-")[0]
            target = BASE / "rules" / year / "monthly_tax_table.csv"
            target.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(source, target)
            messagebox.showinfo("税額表", f"{year}年の月額表を登録しました。再計算してください。")
        except Exception as error: messagebox.showerror("税額表", str(error))

    def pdf(self) -> None:
        if not self.employee:
            return messagebox.showwarning(
                "給与明細",
                "従業員情報を取得できません。",
            )

        # 社員側では会社が保存した給与結果をDBから取得する
        if self.current_user.role == "employee":
            self.result = self.repo.payroll_result(
                self.employee.employee_id,
                self.year_month.get(),
            )

        if not self.result:
            return messagebox.showwarning(
                "給与明細",
                "この月の給与明細はまだありません。",
            )

        if not self.result.finalized:
            return messagebox.showwarning(
                "給与明細",
                "会社側で給与がまだ確定されていません。",
            )

        path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            initialdir=BASE / "exports",
            filetypes=[("PDF", "*.pdf")],
        )

        if path:
            export_pdf(
                self.employee,
                self.result,
                Path(path),
            )
            messagebox.showinfo(
                "PDF",
                "給与明細を出力しました。",
            )

    def export_csv(self) -> None:
        path = filedialog.asksaveasfilename(defaultextension=".csv", initialdir=BASE / "exports", filetypes=[("CSV", "*.csv")])
        if path:
            with open(path, "w", encoding="utf-8-sig", newline="") as file:
                writer = csv.writer(file); writer.writerow(["employee_id", "work_date", "start", "end", "break_minutes", "holiday"])
                writer.writerows([[r.employee_id, r.work_date, r.start_minute, r.end_minute, r.actual_break_minutes, r.is_holiday] for r in self.records])

    def import_csv(self) -> None:
        if not self.employee: return messagebox.showwarning("従業員", "従業員を選択してください。")
        path = filedialog.askopenfilename(filetypes=[("CSV", "*.csv")])
        if not path: return
        try:
            with open(path, encoding="utf-8-sig", newline="") as file:
                for row in csv.DictReader(file):
                    record = WorkRecord(self.employee.employee_id, parse_date(row["work_date"]), int(row["start"]), int(row["end"]), row.get("holiday", "False").lower() in ("true", "1", "○"), int(row.get("break_minutes", "0")))
                    self.repo.save_work_record(record); self.records.append(record)
            self.refresh_records()
        except Exception as error: messagebox.showerror("CSVエラー", str(error))

if __name__ == "__main__":
    root = tk.Tk()
    LoginWindow(root)
    root.mainloop()
