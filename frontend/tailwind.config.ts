import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Patient "clinical dawn" palette
        paper: "#F4F1E9",
        "paper-2": "#FBF9F3",
        ink: "#19302B",
        "ink-soft": "#4C5F58",
        pine: "#0E5E52",
        "pine-deep": "#0A463E",
        sage: "#7FA99B",
        apricot: "#DD7E4A",
        "apricot-soft": "#F1C9A8",
        line: "#E2DACB",
        // Verdict
        eligible: "#1C7C50",
        "eligible-bg": "#E3F1E7",
        possible: "#B5781F",
        "possible-bg": "#F8EDD7",
        unlikely: "#5C6B6B",
        "unlikely-bg": "#E9EBEA",
        // Dashboard "mission control"
        "d-bg": "#080C0E",
        "d-bg-2": "#0D1518",
        "d-panel": "#101D21",
        "d-panel-2": "#13242A",
        "d-line": "#1E3036",
        "d-text": "#CADAD7",
        "d-dim": "#6A817B",
        "d-gpu": "#33E6B0",
        "d-cpu": "#5CB4E8",
        "d-runpod": "#9A86FF",
        "d-bright": "#22D3EE",
        "d-amber": "#F4B53F",
        "d-claude": "#C99BF0",
      },
      fontFamily: {
        display: ["var(--font-display)", "Georgia", "serif"],
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
      },
      keyframes: {
        "fade-up": {
          "0%": { opacity: "0", transform: "translateY(12px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        "pulse-soft": {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.55" },
        },
      },
      animation: {
        "fade-up": "fade-up 0.6s cubic-bezier(0.22,1,0.36,1) both",
        "pulse-soft": "pulse-soft 1.6s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};

export default config;
