# KlausulaAI 🚀

Monorepo untuk pengembangan **KlausulaAI**. Proyek ini mengintegrasikan Backend berbasis FastAPI dengan Frontend berbasis Next.js untuk solusi otomasi analisis dokumen hukum/bisnis.

## 📂 Struktur Folder
- `/backend`: API server menggunakan **FastAPI** dan dimanage oleh **uv**.
- `/frontend`: Interface aplikasi menggunakan **Next.js**.

---

## 🛠️ Setup Awal (Untuk Tim)

Pastikan kalian sudah diundang sebagai kolaborator di GitHub sebelum melakukan langkah di bawah ini.

### 1. Clone Repository
Buka terminal (PowerShell/CMD), lalu jalankan:
```powershell
git clone [https://github.com/ahmdrezaa/KlausulaAI.git](https://github.com/ahmdrezaa/KlausulaAI.git)
cd KlausulaAI
```

### 2. Setup Backend (Nopal & Dzaky)
Wajib menggunakan uv untuk manajemen paket.
```powershell
# Install semua library & buat virtual environment otomatis
uv sync

# Menjalankan server backend
uv run uvicorn backend.main:app --reload
```
> **PENTING:** Hubungi **Ahmad** untuk meminta isi file `.env` dan letakkan di dalam folder `/backend`.

### 3. Setup Frontend (Taraka)
Pastikan Node.js sudah terinstal di laptop.
```powershell
# Masuk ke folder frontend
cd frontend

# Install dependencies
npm install

# Menjalankan server frontend
npm run dev
```

---

## 📝 Kontribusi & Git Flow
1. **Pull First:** Selalu lakukan `git pull origin main` sebelum mulai koding.
2. **Branching:** Jangan langsung koding di `main`. Buat branch baru: `git checkout -b feat-nama-fitur`.
3. **Commit:** Gunakan pesan commit yang jelas (misal: `feat: add login page`).
4. **Security:** Jangan pernah push file `.env` ke GitHub!

---
**Lead Developer & Architect:** Ahmad Reza Fadlan (@ahmdrezaa)