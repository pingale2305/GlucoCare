/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        brand: { 50: '#f0fdfa', 100: '#ccfbf1', 200: '#99f6e4', 300: '#5eead4', 400: '#2dd4bf', 500: '#14b8a6', 600: '#0d9488', 700: '#0f766e', 800: '#115e59', 900: '#134e4a' },
        navy: { 700: '#1c2f52', 800: '#12294d', 900: '#0b1f3f', 950: '#071530' },
      },
      fontFamily: { sans: ['"Plus Jakarta Sans"', 'ui-sans-serif', 'system-ui', 'Segoe UI', 'sans-serif'] },
      boxShadow: { card: '0 1px 2px rgba(15,23,42,.04), 0 4px 16px rgba(15,23,42,.05)' },
      keyframes: { fadeUp: { '0%': { opacity: 0, transform: 'translateY(6px)' }, '100%': { opacity: 1, transform: 'none' } } },
      animation: { fadeUp: 'fadeUp .25s ease-out' },
    },
  },
  plugins: [],
}
