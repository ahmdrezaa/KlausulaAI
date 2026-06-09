// src/components/modals/UploadModal.tsx
// Modal Upload File — Mockup halaman upload
// Letakkan di: frontend/src/components/modals/UploadModal.tsx

'use client'
import { useState, useRef, DragEvent } from 'react'

interface Props {
  onClose: () => void
  // TODO: Hubungkan onUpload dengan backend POST /api/v1/knowledge/upload
  onUpload: (files: File[]) => void
}

export default function UploadModal({ onClose, onUpload }: Props) {
  const [dragging, setDragging] = useState(false)
  const fileRef = useRef<HTMLInputElement>(null)

  const handleDrop = (e: DragEvent) => {
    e.preventDefault()
    setDragging(false)
    const files = Array.from(e.dataTransfer.files)
    if (files.length) onUpload(files)
  }

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || [])
    if (files.length) onUpload(files)
  }

  return (
    /* Backdrop */
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ background: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(4px)' }}
      onClick={onClose}
    >
      {/* Modal box */}
      <div
        className="relative w-full max-w-xl rounded-2xl border p-12"
        style={{
          background: 'var(--bg-card)',
          borderColor: 'var(--border)',
        }}
        onClick={e => e.stopPropagation()}
      >
        {/* Close */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 opacity-40 hover:opacity-80 transition-opacity"
        >
          <CloseIcon />
        </button>

        {/* Drop zone */}
        <div
          onDragOver={e => { e.preventDefault(); setDragging(true) }}
          onDragLeave={() => setDragging(false)}
          onDrop={handleDrop}
          className="rounded-xl border-2 border-dashed flex flex-col items-center justify-center py-14 px-6 mb-6 transition-all"
          style={{
            borderColor: dragging ? 'var(--accent)' : 'var(--border-light)',
            background: dragging ? 'rgba(201,139,122,0.06)' : 'transparent',
          }}
        >
          <p className="font-display text-3xl font-semibold mb-2"
            style={{ color: 'var(--text-primary)' }}>
            drop your files
          </p>
          <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
            pdf, images, docs, and more
          </p>
        </div>

        {/* Action buttons */}
        <div className="flex flex-col sm:flex-row gap-3">
          {/* Upload from device */}
          <button
            onClick={() => fileRef.current?.click()}
            className="flex-1 flex items-center justify-center gap-2.5 py-3 px-4 rounded-xl border text-sm font-medium transition-all hover:opacity-80 active:scale-[0.97]"
            style={{ borderColor: 'var(--border-light)', color: 'var(--text-primary)', background: 'transparent' }}
          >
            <UploadIcon />
            Upload Files
          </button>

          {/* Upload from cloud — TODO: Google Drive integration
          <button
            className="flex-1 flex items-center justify-center gap-2.5 py-3 px-4 rounded-xl border text-sm font-medium transition-all hover:opacity-80 active:scale-[0.97]"
            style={{ borderColor: 'var(--border-light)', color: 'var(--text-primary)', background: 'transparent' }}
          >
            <CloudIcon />
            Upload Files
          </button> */}

          {/* Paste text — TODO: Handle pasted text as document */}
          <button
            className="flex-1 flex items-center justify-center gap-2.5 py-3 px-4 rounded-xl border text-sm font-medium transition-all hover:opacity-80 active:scale-[0.97]"
            style={{ borderColor: 'var(--border-light)', color: 'var(--text-primary)', background: 'transparent' }}
          >
            <ClipboardIcon />
            Copied Text
          </button>
        </div>

        {/* Hidden file input */}
        <input
          ref={fileRef}
          type="file"
          multiple
          accept=".pdf,.doc,.docx,.txt,.png,.jpg,.jpeg"
          className="hidden"
          onChange={handleFileInput}
        />
      </div>
    </div>
  )
}

function CloseIcon() {
  return <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
}
function UploadIcon() {
  return <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="16 16 12 12 8 16"/><line x1="12" y1="12" x2="12" y2="21"/><path d="M20.39 18.39A5 5 0 0018 9h-1.26A8 8 0 103 16.3"/></svg>
}
function CloudIcon() {
  return <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="16 16 12 12 8 16"/><line x1="12" y1="12" x2="12" y2="21"/><path d="M20.39 18.39A5 5 0 0018 9h-1.26A8 8 0 103 16.3"/></svg>
}
function ClipboardIcon() {
  return <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M16 4h2a2 2 0 012 2v14a2 2 0 01-2 2H6a2 2 0 01-2-2V6a2 2 0 012-2h2"/><rect x="8" y="2" width="8" height="4" rx="1" ry="1"/></svg>
}
