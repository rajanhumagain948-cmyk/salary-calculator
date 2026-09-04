"use client";

import { useEffect, useState } from "react";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

type Company = {
  name: string;
  address: string;
  representative: string;
};

export default function SettingsPage() {
  const [company, setCompany] = useState<Company>({
    name: "",
    address: "",
    representative: "",
  });

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  async function loadCompany() {
    setLoading(true);
    setError("");

    try {
      const res = await fetch(`${API_BASE}/company`, {
        credentials: "include",
      });

      if (!res.ok) {
        setError(`会社情報を取得できませんでした: ${res.status}`);
        return;
      }

      setCompany(await res.json());
    } catch {
      setError("会社情報の取得中に通信エラーが発生しました。");
    } finally {
      setLoading(false);
    }
  }

  async function saveCompany() {
    setError("");
    setMessage("");

    if (!company.name.trim()) {
      setError("会社名を入力してください。");
      return;
    }

    setSaving(true);

    try {
      const form = new FormData();
      form.append("name", company.name);
      form.append("address", company.address);
      form.append("representative", company.representative);

      const res = await fetch(`${API_BASE}/company`, {
        method: "PUT",
        credentials: "include",
        body: form,
      });

      if (!res.ok) {
        const body = await res.json().catch(() => null);
        setError(
          body?.detail
            ? `保存できませんでした: ${body.detail}`
            : `保存できませんでした: ${res.status}`
        );
        return;
      }

      const result = await res.json();
      setCompany(result.company);
      setMessage("会社情報を保存しました。");

      // AppShellへ会社名変更を通知
      window.dispatchEvent(
        new CustomEvent("company-updated", {
          detail: result.company,
        })
      );
    } catch {
      setError("会社情報の保存中に通信エラーが発生しました。");
    } finally {
      setSaving(false);
    }
  }

  useEffect(() => {
    loadCompany();
  }, []);

  return (
    <main
      style={{
        maxWidth: 900,
        margin: "0 auto",
        padding: "28px 16px",
      }}
    >
      <div style={{ marginBottom: 24 }}>
        <div
          style={{
            color: "#8390ff",
            fontSize: 12,
            fontWeight: 800,
            letterSpacing: "0.12em",
          }}
        >
          システム設定
        </div>

        <h1 style={{ margin: "6px 0" }}>会社情報</h1>

        <p style={{ color: "#8fa6bf", margin: 0 }}>
          給与管理システムに表示する会社情報を設定します。
        </p>
      </div>

      <section
        style={{
          padding: 24,
          border: "1px solid rgba(148,180,216,0.16)",
          borderRadius: 18,
          background: "rgba(14,27,46,0.72)",
          boxShadow: "0 22px 60px rgba(0,0,0,0.18)",
        }}
      >
        {loading ? (
          <p>会社情報を読み込み中...</p>
        ) : (
          <>
            <div
              style={{
                display: "grid",
                gap: 18,
              }}
            >
              <label>
                会社名 *
                <input
                  value={company.name}
                  onChange={(e) =>
                    setCompany({ ...company, name: e.target.value })
                  }
                  placeholder="株式会社〇〇"
                  style={{
                    display: "block",
                    width: "100%",
                    padding: 12,
                    marginTop: 6,
                  }}
                />
              </label>

              <label>
                代表者
                <input
                  value={company.representative}
                  onChange={(e) =>
                    setCompany({
                      ...company,
                      representative: e.target.value,
                    })
                  }
                  placeholder="代表取締役 山田 太郎"
                  style={{
                    display: "block",
                    width: "100%",
                    padding: 12,
                    marginTop: 6,
                  }}
                />
              </label>

              <label>
                住所
                <textarea
                  value={company.address}
                  onChange={(e) =>
                    setCompany({ ...company, address: e.target.value })
                  }
                  placeholder="東京都..."
                  rows={3}
                  style={{
                    display: "block",
                    width: "100%",
                    padding: 12,
                    marginTop: 6,
                    resize: "vertical",
                  }}
                />
              </label>
            </div>

            {error && (
              <p style={{ color: "#ff6b7a", marginTop: 18 }}>{error}</p>
            )}

            {message && (
              <p style={{ color: "#45e0a8", marginTop: 18 }}>{message}</p>
            )}

            <button
              onClick={saveCompany}
              disabled={saving}
              style={{
                marginTop: 20,
                padding: "11px 20px",
                border: "1px solid rgba(109,124,255,0.35)",
                borderRadius: 11,
                color: "#fff",
                background:
                  "linear-gradient(135deg, #6d7cff, #5164e8)",
                fontWeight: 750,
                cursor: "pointer",
              }}
            >
              {saving ? "保存中..." : "会社情報を保存"}
            </button>
          </>
        )}
      </section>
    </main>
  );
}
