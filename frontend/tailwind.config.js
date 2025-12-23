/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Geist', 'sans-serif'],
        mono: ['Geist Mono', 'monospace'],
      },
      colors: {
        // Dark Theme Palette
        zinc: {
          950: '#050505', // Deep black background
        },
        // Accents
        reach: '#ff6b2b',
        target: '#2b7fff',
        safety: '#2bff88',
      },
      backgroundImage: {
        'mesh': 'radial-gradient(at 0% 0%, rgba(255,255,255,0.03) 0px, transparent 50%), radial-gradient(at 100% 100%, rgba(255,255,255,0.03) 0px, transparent 50%)',
      }
    },
  },
  plugins: [
    require('@tailwindcss/typography'),
  ],
}
