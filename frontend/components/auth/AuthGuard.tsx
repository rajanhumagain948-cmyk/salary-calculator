"use client";

import { useEffect, useState, type ReactNode } from "react";
import { useRouter } from "next/navigation";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

type Role = "admin" | "employee";

type Me = {
  username: string;
  role: Role;
  employee_id: string | null;
};

type AuthGuardProps = {
  children: ReactNode;
  allow: Role[];
};

export default function AuthGuard({
  children,
  allow,
}: AuthGuardProps) {
  const router = useRouter();
  const [allowed, setAllowed] = useState(false);
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    let active = true;

    async function checkAuth() {
      try {
        const res = await fetch(`${API_BASE}/me`, {
          credentials: "include",
          cache: "no-store",
        });

        if (!res.ok) {
          if (active) router.replace("/");
          return;
        }

        const me: Me = await res.json();

        if (!allow.includes(me.role)) {
          if (active) {
            router.replace(
              me.role === "admin" ? "/dashboard" : "/my"
            );
          }
          return;
        }

        if (active) {
          setAllowed(true);
        }
      } catch {
        if (active) {
          router.replace("/");
        }
      } finally {
        if (active) {
          setChecking(false);
        }
      }
    }

    checkAuth();

    return () => {
      active = false;
    };
  }, [allow, router]);

  if (checking || !allowed) {
    return (
      <div
        style={{
          minHeight: "60vh",
          display: "grid",
          placeItems: "center",
          color: "#8fa6bf",
        }}
      >
        <div style={{ textAlign: "center" }}>
          <div
            style={{
              width: 34,
              height: 34,
              margin: "0 auto 12px",
              border: "3px solid rgba(109,124,255,.18)",
              borderTopColor: "#6d7cff",
              borderRadius: "50%",
              animation: "auth-spin .8s linear infinite",
            }}
          />
          ログイン情報を確認しています...
        </div>

        <style jsx>{`
          @keyframes auth-spin {
            to {
              transform: rotate(360deg);
            }
          }
        `}</style>
      </div>
    );
  }

  return <>{children}</>;
}
