/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./templates/**/*.html",
    "./apps/**/*.py",
    "./apps/**/*.html",
  ],
  darkMode: "class",
  theme: {
    extend: {
      fontFamily: {
        vazirmatn: ["Vazirmatn", "system-ui", "sans-serif"],
      },
      colors: {
        // iOS-inspired system colors
        "ios-blue": "#007aff",
        "ios-red": "#ff3b30",
        "ios-green": "#34c759",
        "ios-orange": "#ff9500",
        "ios-gray": "#8e8e93",
        "ios-gray2": "#aeaeb2",
        "ios-gray6": "#f2f2f7",
      },
      borderRadius: {
        "2xl": "1rem",
        "3xl": "1.5rem",
        "4xl": "2rem",
      },
    },
  },
  plugins: [],
};
