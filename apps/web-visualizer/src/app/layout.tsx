import type { Metadata } from 'next'
import { Inter, Fira_Code } from 'next/font/google'
import './globals.css'

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-inter',
})

const firaCode = Fira_Code({
  subsets: ['latin'],
  variable: '--font-fira-code',
})

export const metadata: Metadata = {
  title: 'AuraPitch 2026 — Tactical Digital Twin',
  description: 'FIFA World Cup 2026 real-time multi-agent spatial analytics platform and 3D digital twin visualization suite.',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" className={`${inter.variable} ${firaCode.variable} dark`}>
      <body className="font-sans antialiased text-cyber-text bg-cyber-bg min-h-screen">
        {children}
      </body>
    </html>
  )
}
