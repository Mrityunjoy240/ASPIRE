import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Status colors (strict semantic)
        critical: {
          DEFAULT: "#F43F5E",
          bg: "rgba(244, 63, 94, 0.12)",
          border: "rgba(244, 63, 94, 0.30)",
        },
        warning: {
          DEFAULT: "#F59E0B",
          bg: "rgba(245, 158, 11, 0.12)",
          border: "rgba(245, 158, 11, 0.30)",
        },
        safe: {
          DEFAULT: "#10B981",
          bg: "rgba(16, 185, 129, 0.12)",
          border: "rgba(16, 185, 129, 0.30)",
        },
        pending: {
          DEFAULT: "#38BDF8",
          bg: "rgba(56, 189, 248, 0.12)",
          border: "rgba(56, 189, 248, 0.30)",
        },
        overdue: {
          DEFAULT: "#FB7185",
          bg: "rgba(251, 113, 133, 0.15)",
          border: "rgba(244, 63, 94, 0.40)",
        },
      },
      fontFamily: {
        display: ["Inter", "Plus Jakarta Sans", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "Geist Mono", "monospace"],
      },
      animation: {
        "pulse-ring": "pulse-ring 2s ease-in-out infinite",
        "slide-up": "slide-up 300ms ease-out forwards",
        "fade-in": "fade-in 200ms ease-out forwards",
      },
      keyframes: {
        "pulse-ring": {
          "0%": { transform: "scale(1)", opacity: "0.5" },
          "50%": { transform: "scale(1.05)", opacity: "1" },
          "100%": { transform: "scale(1)", opacity: "0.5" },
        },
        "slide-up": {
          from: { opacity: "0", transform: "translateY(12px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        "fade-in": {
          from: { opacity: "0" },
          to: { opacity: "1" },
        },
      },
    },
  },
};

export default config;