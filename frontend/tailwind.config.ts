import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Serious, neutral scientific palette. No purple SaaS gradients.
        ink: {
          DEFAULT: "#111827",
          muted: "#4b5563",
          faint: "#9ca3af",
        },
        line: "#e5e7eb",
        surface: "#ffffff",
        panel: "#f9fafb",
        accent: "#1f6feb", // restrained blue for links/interaction only
      },
      fontFamily: {
        sans: ["ui-sans-serif", "system-ui", "-apple-system", "Segoe UI", "Roboto", "Arial", "sans-serif"],
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "Consolas", "monospace"],
      },
      fontSize: {
        xs: ["0.75rem", { lineHeight: "1rem" }],
      },
    },
  },
  plugins: [],
};

export default config;
