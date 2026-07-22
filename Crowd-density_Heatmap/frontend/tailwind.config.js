/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        base: "#0b0f1a",
        panel: "#141a2a",
        panel2: "#1b2336",
        accent: "#3b82f6",
      },
    },
  },
  plugins: [],
};
