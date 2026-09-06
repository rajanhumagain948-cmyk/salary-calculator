"use client";

import type { ReactNode } from "react";
import AuthGuard from "@/components/auth/AuthGuard";

export default function SettingsLayout({
  children,
}: {
  children: ReactNode;
}) {
  return <AuthGuard allow={["admin"]}>{children}</AuthGuard>;
}
