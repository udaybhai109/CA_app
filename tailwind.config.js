/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx}",
    "./components/**/*.{js,ts,jsx,tsx}",
    "./context/**/*.{js,ts,jsx,tsx}",
    "./lib/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: "#0B63FF",
        navy: "#0F172A",
        success: "#00B37E",
        warning: "#F59E0B",
        danger: "#E02424",
        muted: "#6B7280",
        bg: "#F7FAFC",
        card: "#FFFFFF",
        borderLight: "#E5E7EB",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "Segoe UI", "sans-serif"],
      },
    },
  },
  plugins: [],
};
