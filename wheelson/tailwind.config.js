/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./core/templates/**/*.html",
    "./core/**/*.py",
    "./static/**/*.js",
  ],
  theme: {
    extend: {},
  },
  plugins: [
    require("daisyui"),
  ],
  daisyui: {
    themes: ["business", "corporate"],
    darkTheme: "business",
    base: true,
    styled: true,
    utils: true,
    prefix: "",
    logs: false,
  },
}
