"use client";

import React from "react";
import { Sidebar } from "@/components/layout/Sidebar";

interface WebLayoutProps {
  children: React.ReactNode;
}

export function WebLayout({ children }: WebLayoutProps) {
  return (
    <div className="min-h-screen bg-[var(--color-bg-canvas)]">
      <Sidebar />
      <main className="ml-64 min-h-screen transition-all duration-300" style={{ marginLeft: "16rem" }}>
        <div className="p-6 lg:p-8">
          {children}
        </div>
      </main>
    </div>
  );
}