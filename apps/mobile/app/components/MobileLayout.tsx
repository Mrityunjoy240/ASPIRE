"use client";

import React, { useEffect } from "react";
import { BottomNavigation } from "@/components/BottomNavigation";

interface MobileLayoutProps {
  children: React.ReactNode;
}

export function MobileLayout({ children }: MobileLayoutProps) {
  useEffect(() => {
    // Prevent body scroll when modals/sheets are open
    return () => {
      document.body.style.overflow = "";
    };
  }, []);

  return (
    <div className="min-h-screen bg-[var(--color-bg-canvas)] pb-16">
      <main className="pb-20 animate-fade-in">
        {children}
      </main>
      <BottomNavigation />
    </div>
  );
}