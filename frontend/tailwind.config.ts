import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        terminal: {
          bg: '#0d1117',
          panel: '#1a1a2e',
          border: '#2d333b',
          text: '#e6edf3',
          muted: '#8b949e',
        },
        accent: {
          yellow: '#ecad0a',
          blue: '#209dd7',
          purple: '#753991',
        },
        market: {
          up: '#3fb950',
          down: '#f85149',
        },
      },
      animation: {
        'flash-up': 'flashUp 500ms ease-out',
        'flash-down': 'flashDown 500ms ease-out',
        'pulse-dot': 'pulseDot 2s infinite',
      },
      keyframes: {
        flashUp: {
          '0%': { backgroundColor: 'rgba(63, 185, 80, 0.4)' },
          '100%': { backgroundColor: 'transparent' },
        },
        flashDown: {
          '0%': { backgroundColor: 'rgba(248, 81, 73, 0.4)' },
          '100%': { backgroundColor: 'transparent' },
        },
        pulseDot: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.4' },
        },
      },
    },
  },
  plugins: [],
};
export default config;
