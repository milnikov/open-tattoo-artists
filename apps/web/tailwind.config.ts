import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ["var(--font-inter)", "ui-sans-serif", "system-ui", "sans-serif"],
        "spectral-italic": ["var(--font-spectral-italic)", "Georgia", "serif"],
        "spectral-italic-logo": ["var(--font-spectral-italic)"], // logo only: no fallback
      },
      colors: {
        background: "var(--background)",
        foreground: "var(--foreground)",
        muted: "var(--muted)",
        "muted-foreground": "var(--muted-foreground)",
        border: "var(--border)",
        secondary: "var(--secondary)",
        "secondary-foreground": "var(--secondary-foreground)",
        card: "var(--card)",
      },
    },
  },
  plugins: [],
};

export default config;
