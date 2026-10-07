import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ASPIRE — Web",
  description: "ASPIRE mentor/admin/faculty workspace (scaffold).",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="bg-[#F8F8F5] text-[#37352F] antialiased">{children}</body>
    </html>
  );
}
