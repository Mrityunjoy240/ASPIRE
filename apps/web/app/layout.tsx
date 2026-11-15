import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ASPIRE Mentor Dashboard",
  description: "ASPIRE Mentor/Admin/Faculty Workspace",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="h-full">
      <head>
        <meta name="theme-color" content="#070A10" />
      </head>
      <body className="h-full min-h-screen bg-[var(--color-bg-canvas)] text-white antialiased">
        {children}
      </body>
    </html>
  );
}