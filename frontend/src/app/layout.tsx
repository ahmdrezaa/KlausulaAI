// src/app/layout.tsx
// Root layout — KlausulaAI
// Letakkan di: frontend/src/app/layout.tsx

import type { Metadata } from 'next'
import './globals.css' // Pastikan file CSS global sudah dibuat di src/app/globals.css

export const metadata: Metadata = {
  title: 'KlausulaAI — Asisten Hukum Indonesia',
  description: 'Workspace hukum bertenaga AI untuk mahasiswa dan praktisi hukum Indonesia.',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="id">
      <body>{children}</body>
    </html>
  )
}
