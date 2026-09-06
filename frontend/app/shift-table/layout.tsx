"use client";

import type { ReactNode } from "react";
import AuthGuard from "@/components/auth/AuthGuard";

export default function ShiftTableLayout({
  children,
}: {
  children: ReactNode;
}) {
  return <AuthGuard allow={["admin"]}>{children}</AuthGuard>;
}
