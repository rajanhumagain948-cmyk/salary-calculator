"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";

type Props = {
  children: ReactNode;
};

const adminNav = [
  { href: "/dashboard", label: "ダッシュボード", icon: "⌂", enabled: true },
  { href: "/employees", label: "従業員", icon: "◉", enabled: true },
  { href: "/attendance", label: "勤怠管理", icon: "◷", enabled: false },
  { href: "/shift-table", label: "シフト管理", icon: "▦", enabled: true },
  { href: "/payroll", label: "給与計算", icon: "¥", enabled: false },
  { href: "/leave", label: "有給管理", icon: "◇", enabled: false },
  { href: "/ai", label: "AIアシスタント", icon: "✦", enabled: false },
  { href: "/settings", label: "設定", icon: "⚙", enabled: true },
];

const employeeNav = [
  { href: "/my", label: "マイページ", icon: "⌂", enabled: true },
  { href: "/my-attendance", label: "自分の勤怠", icon: "◷", enabled: false },
  { href: "/shifts", label: "自分のシフト", icon: "▦", enabled: true },
  { href: "/payslips", label: "給与明細", icon: "¥", enabled: false },
  { href: "/my-leave", label: "有給休暇", icon: "◇", enabled: false },
  { href: "/ai", label: "AIアシスタント", icon: "✦", enabled: false },
];

export default function AppShell({ children }: Props) {
  const pathname = usePathname();
  const router = useRouter();
  const [companyName, setCompanyName] = useState("");
  const [me, setMe] = useState<{
    username: string;
    role: "admin" | "employee";
    employee_id: string | null;
  } | null>(null);

  useEffect(() => {
    const apiBase =
      process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

    async function loadMe() {
      try {
        const res = await fetch(`${apiBase}/me`, {
          credentials: "include",
        });

        if (res.ok) {
          setMe(await res.json());
        }
      } catch {
        // ログイン状態は各ページ側でも保護する
      }
    }

    async function loadCompany() {
      try {

        const res = await fetch(`${apiBase}/company`, {
          credentials: "include",
        });

        if (!res.ok) return;

        const company = await res.json();
        setCompanyName(company.name ?? "");
      } catch {
        // 会社情報を取得できなくても画面自体は利用可能にする
      }
    }

    loadMe();
    loadCompany();

    function handleCompanyUpdated(event: Event) {
      const customEvent = event as CustomEvent<{ name?: string }>;
      setCompanyName(customEvent.detail?.name ?? "");
    }

    window.addEventListener("company-updated", handleCompanyUpdated);

    return () => {
      window.removeEventListener("company-updated", handleCompanyUpdated);
    };
  }, [pathname]);

  async function handleLogout() {
    const apiBase =
      process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

    try {
      await fetch(`${apiBase}/logout`, {
        method: "POST",
        credentials: "include",
      });
    } finally {
      setMe(null);
      router.replace("/");
    }
  }

  if (pathname === "/") {
    return <>{children}</>;
  }

  return (
    <div className="app-shell">
      <aside className="app-sidebar">
        <div className="brand">
          <div className="brand-mark">S</div>

          <div>
            <div className="brand-name">給与管理システム</div>
            <div className="brand-subtitle">給与・人事管理</div>
          </div>
        </div>

        <nav className="app-nav" aria-label="メインナビゲーション">
          {(me
            ? me.role === "employee"
              ? employeeNav
              : adminNav
            : []
          ).map((item) => {
            const active =
              pathname === item.href ||
              (item.href !== "/" && pathname.startsWith(`${item.href}/`));

            if (!item.enabled) {
              return (
                <div
                  key={item.href}
                  className="nav-item nav-disabled"
                  title="近日追加予定"
                >
                  <span className="nav-icon">{item.icon}</span>
                  <span>{item.label}</span>
                  <span className="coming-soon">近日</span>
                </div>
              );
            }

            return (
              <Link
                key={item.href}
                href={item.href}
                className={`nav-item ${active ? "nav-active" : ""}`}
              >
                <span className="nav-icon">{item.icon}</span>
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>

        <div className="sidebar-ai-card">
          <div className="ai-orb">✦</div>
          <strong>AIアシスタント</strong>
          <p>給与・勤怠をAIと一緒に管理。</p>
          <span>近日公開</span>
        </div>

        <div className="sidebar-footer">
          <span className="status-dot" />
          システム正常
        </div>
      </aside>

      <div className="app-main">
        <header className="app-topbar">
          <div>
            <div className="topbar-eyebrow">給与管理システム</div>
            <div className="topbar-title">
              {companyName || "会社名未設定"}
            </div>
          </div>

          <div className="topbar-actions">
            <div className="live-chip">
              <span className="status-dot" />
              稼働中
            </div>

            {me && (
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 10,
                }}
              >
                <div
                  style={{
                    textAlign: "right",
                    lineHeight: 1.25,
                  }}
                >
                  <strong
                    style={{
                      display: "block",
                      fontSize: 11,
                    }}
                  >
                    {me.username}
                  </strong>

                  <span
                    style={{
                      color: "#8fa6bf",
                      fontSize: 9,
                    }}
                  >
                    {me.role === "admin" ? "管理者" : "従業員"}
                  </span>
                </div>

                <div className="avatar">
                  {(me.username[0] || "?").toUpperCase()}
                </div>

                <button
                  onClick={handleLogout}
                  style={{
                    padding: "7px 11px",
                    border: "1px solid rgba(148,180,216,.16)",
                    borderRadius: 9,
                    color: "#b7c7d8",
                    background: "rgba(255,255,255,.03)",
                    cursor: "pointer",
                    fontSize: 10,
                  }}
                >
                  ログアウト
                </button>
              </div>
            )}
          </div>
        </header>

        <div className="app-content">{children}</div>
      </div>
    </div>
  );
}
