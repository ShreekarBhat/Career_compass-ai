import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: { extend: { boxShadow: { card: "0 1px 2px rgba(15,23,42,.04), 0 4px 16px rgba(15,23,42,.04)" } } },
  plugins: [],
};
export default config;
