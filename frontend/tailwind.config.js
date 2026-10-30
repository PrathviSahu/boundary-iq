/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        canvas: '#F5F7F5',
        surface: '#FFFFFF',
        ink: {
          primary: '#17201B',
          secondary: '#69746D',
          muted: '#8E9A92',
          border: '#E5EAE6',
          borderDark: '#D3DDD6',
        },
        forest: {
          50: '#F2F7F4',
          100: '#E7EEE9',
          200: '#CDE0D4',
          300: '#9FC3AB',
          400: '#5A9E7A',
          500: '#2E8B5F',
          600: '#237A52', // primary accent
          700: '#1B6342',
          800: '#144C32',
          900: '#0E3624',
        },
        sport: {
          wicket: '#B91C1C',
          wicketBg: '#FEF2F2',
          wicketBorder: '#FECACA',
          milestone: '#B45309',
          milestoneBg: '#FFFBEB',
          milestoneBorder: '#FDE68A',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
        mono: ['JetBrains Mono', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'Monaco', 'Consolas', 'monospace'],
      },
    },
  },
  plugins: [],
};
