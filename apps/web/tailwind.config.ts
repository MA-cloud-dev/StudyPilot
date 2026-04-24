import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        canvas: "#ffffff",
        ink: "#111827",
        accent: "#dc2626", // Prototype primary red
        warm: "#fafafa",
      },
    },
  },
  plugins: [],
};

export default config;
