// src/app/page.tsx
// Root page — redirect ke halaman login
// Letakkan di: frontend/src/app/page.tsx

import { redirect } from 'next/navigation'

export default function Home() {
  redirect('/login')
}
