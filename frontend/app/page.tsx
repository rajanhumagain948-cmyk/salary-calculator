"use client";

import { useState } from "react";

const API_BASE = "http://localhost:8000";

export default function Home() {
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("test1234");
  const [error, setError] = useState<string>("");
  const [me, setMe] = useState<any>(null);

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setMe(null);

    const res = await fetch(`${API_BASE}/login`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({ username, password }).toString(),
      credentials: "include",
    });

    if (!res.ok) {
      setError("ログインに失敗しました（ユーザー名/パスワード確認）");
      return;
    }

    const meRes = await fetch(`${API_BASE}/me`, {
      credentials: "include",
    });

    if (!meRes.ok) {
      setError("ログイン後のユーザー取得に失敗しました");
      return;
    }

    setMe(await meRes.json());
  }

  async function handleLogout() {
    setError("");
    setMe(null);
    await fetch(`${API_BASE}/logout`, { method: "POST", credentials: "include" });
  }

  return (
    <main style={{ maxWidth: 520, margin: "10vh auto", fontFamily: "system-ui" }}>
      <h1>Salary Calculator Web</h1>

      <form onSubmit={handleLogin} style={{ display: "grid", gap: 10, marginTop: 16 }}>
        <label>
          ユーザー名
          <input
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            style={{ width: "100%", padding: 8 }}
          />
        </label>

        <label>
          パスワード
          <input
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            type="password"
            style={{ width: "100%", padding: 8 }}
          />
        </label>

        <button type="submit" style={{ padding: 10, fontWeight: 700 }}>
          ログイン
        </button>

        <button type="button" onClick={handleLogout} style={{ padding: 10 }}>
          ログアウト
        </button>
      </form>

      {error && <p style={{ color: "crimson", marginTop: 12 }}>{error}</p>}

      {me && (
        <pre style={{ marginTop: 16, background: "#111", color: "#0f0", padding: 12 }}>
          {JSON.stringify(me, null, 2)}
        </pre>
      )}
    </main>
  );
}
