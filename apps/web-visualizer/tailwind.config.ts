import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        cyber: {
          bg: "#09090b",       // zinc-950
          card: "#18181b",     // zinc-900
          border: "#27272a",   // zinc-800
          primary: "#06b6d4",  // electric cyan-500
          success: "#10b981",  // emerald-500
          warning: "#f59e0b",  // amber-500
          danger: "#ef4444",   // red-500
          text: "#f4f4f5",     // zinc-100
          muted: "#a1a1aa",    // zinc-400
        }
      },
      fontFamily: {
        sans: ['var(--font-inter)', 'sans-serif'],
        mono: ['var(--font-fira-code)', 'monospace'],
      },
      boxShadow: {
        glow: '0 0 15px rgba(6, 182, 212, 0.15)',
        'glow-success': '0 0 15px rgba(16, 185, 129, 0.2)',
        'glow-warning': '0 0 15px rgba(245, 158, 11, 0.2)',
      }
    },
  },
  plugins: [],
}
export default config
