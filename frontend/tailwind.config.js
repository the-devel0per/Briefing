/** Colours are CSS variables so dark/light switch without duplicating classes. */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        bg: 'var(--bg)', surface: 'var(--surface)', surface2: 'var(--surface2)', card: 'var(--card)',
        ink: 'var(--text)', muted: 'var(--muted)', line: 'var(--border)',
      },
      fontFamily: { sans: ['Inter', 'Geist', 'ui-sans-serif', 'system-ui', '-apple-system', 'Segoe UI', 'Roboto', 'sans-serif'] },
      borderRadius: { card: '20px', ctl: '12px' },
      maxWidth: { page: '1200px' },
      keyframes: {
        reveal: { from: { opacity: '0', transform: 'translateY(12px)' }, to: { opacity: '1', transform: 'none' } },
        shimmer: { '100%': { transform: 'translateX(100%)' } },
      },
      animation: { reveal: 'reveal .5s cubic-bezier(.2,.7,.2,1) both' },
    },
  },
}
