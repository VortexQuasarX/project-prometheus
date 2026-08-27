import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        border: "hsl(214 32% 91%)",
        background: "hsl(0 0% 100%)",
        foreground: "hsl(222 47% 11%)",
        muted: { DEFAULT: "hsl(210 40% 96%)", foreground: "hsl(215 16% 47%)" },
        card: { DEFAULT: "hsl(0 0% 100%)", foreground: "hsl(222 47% 11%)" },
        primary: { DEFAULT: "hsl(222 47% 11%)", foreground: "hsl(210 40% 98%)" },
        accent: { DEFAULT: "hsl(221 83% 53%)", foreground: "hsl(210 40% 98%)" },
        destructive: { DEFAULT: "hsl(0 72% 51%)", foreground: "hsl(210 40% 98%)" },
      },
      borderRadius: { lg: "0.5rem" },
    },
  },
  plugins: [require("tailwindcss-animate")],
};

export default config;
