"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

type Me = {
  username: string;
  role: "admin" | "employee";
  employee_id: string | null;
};

export default function LoginPage() {
  const router = useRouter();

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loggingIn, setLoggingIn] = useState(false);
  const [checking, setChecking] = useState(true);

  function redirectUser(me: Me) {
    if (me.role === "admin") {
      router.replace("/dashboard");
    } else {
      router.replace("/my");
    }
  }

  useEffect(() => {
    async function checkSession() {
      try {
        const res = await fetch(`${API_BASE}/me`, {
          credentials: "include",
        });

        if (res.ok) {
          redirectUser(await res.json());
          return;
        }
      } catch {
        // 未ログイン画面をそのまま表示する
      } finally {
        setChecking(false);
      }
    }

    checkSession();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault();

    setError("");
    setLoggingIn(true);

    try {
      const res = await fetch(`${API_BASE}/login`, {
        method: "POST",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
        },
        body: new URLSearchParams({
          username: username.trim(),
          password,
        }).toString(),
        credentials: "include",
      });

      if (!res.ok) {
        setError("ユーザー名またはパスワードが正しくありません。");
        return;
      }

      const meRes = await fetch(`${API_BASE}/me`, {
        credentials: "include",
      });

      if (!meRes.ok) {
        setError("ログイン情報を確認できませんでした。");
        return;
      }

      const me: Me = await meRes.json();
      redirectUser(me);
    } catch {
      setError("サーバーに接続できませんでした。");
    } finally {
      setLoggingIn(false);
    }
  }

  return (
    <main className="login-page">
      <div className="login-glow login-glow-one" />
      <div className="login-glow login-glow-two" />

      <section className="login-hero">
        <div className="login-brand">
          <div className="login-brand-mark">給</div>
          <div>
            <strong>給与管理システム</strong>
            <span>給与・勤怠・人事をひとつに</span>
          </div>
        </div>

        <div className="login-copy">
          <div className="login-badge">
            <span>✦</span>
            スマートな労務管理へ
          </div>

          <h1>
            会社と働く人を、
            <br />
            <span>もっとスマートに。</span>
          </h1>

          <p>
            従業員、勤怠、シフト、給与、有給をひとつの場所で管理。
            これからAIアシスタントや予測機能にも対応していきます。
          </p>

          <div className="login-features">
            <div>
              <span>◉</span>
              <strong>従業員管理</strong>
              <small>人事情報を一元管理</small>
            </div>

            <div>
              <span>◷</span>
              <strong>勤怠・給与</strong>
              <small>毎月の業務を効率化</small>
            </div>

            <div>
              <span>✦</span>
              <strong>AIサポート</strong>
              <small>データ活用をもっと身近に</small>
            </div>
          </div>
        </div>

        <div className="login-hero-footer">
          <span className="status-dot" />
          システム稼働中
        </div>
      </section>

      <section className="login-panel">
        <div className="login-card">
          <div className="login-card-header">
            <div className="login-lock">⌁</div>

            <div>
              <h2>ログイン</h2>
              <p>アカウント情報を入力してください。</p>
            </div>
          </div>

          {checking ? (
            <div className="login-checking">
              ログイン状態を確認しています...
            </div>
          ) : (
            <form onSubmit={handleLogin} className="login-form">
              <label>
                ユーザー名
                <input
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  autoComplete="username"
                  placeholder="ユーザー名"
                  required
                  autoFocus
                />
              </label>

              <label>
                パスワード
                <input
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  type="password"
                  autoComplete="current-password"
                  placeholder="パスワード"
                  required
                />
              </label>

              {error && (
                <div className="login-error">
                  <span>!</span>
                  {error}
                </div>
              )}

              <button
                type="submit"
                className="login-submit"
                disabled={loggingIn}
              >
                {loggingIn ? (
                  "ログインしています..."
                ) : (
                  <>
                    ログイン
                    <span>→</span>
                  </>
                )}
              </button>
            </form>
          )}

          <div className="login-security">
            <span>●</span>
            管理者と従業員で利用できる機能が自動的に切り替わります
          </div>
        </div>

        <p className="login-copyright">
          給与管理システム
        </p>
      </section>
    </main>
  );
}
