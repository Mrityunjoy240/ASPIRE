import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ASPIRE Student",
  description: "ASPIRE Student Success Intelligence — Mobile PWA",
  appleWebApp: {
    capable: true,
    statusBarStyle: "black-translucent",
    title: "ASPIRE",
  },
  manifest: "/manifest.json",
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="h-full">
      <head>
        <link rel="manifest" href="/manifest.json" />
        <meta name="theme-color" content="#070A10" />
        <meta name="apple-mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent" />
        <meta name="apple-mobile-web-app-title" content="ASPIRE" />
        <link rel="apple-touch-icon" href="/icon-192.png" />
      </head>
      <body className="h-full min-h-screen bg-[var(--color-bg-canvas)] text-white antialiased">
        {children}
      </body>
    </html>
  );
}