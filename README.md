# Student Finance Tracker

Project ini menggunakan **FastAPI + Jinja2**. Kode aplikasi berada di folder `backend/`, sedangkan HTML dan aset UI berada di `frontend/`. Frontend saat ini dirender dan disajikan oleh FastAPI, jadi keduanya sudah terpisah secara struktur, bukan dijalankan sebagai dua server terpisah.

## Struktur

- `backend/app/` — konfigurasi, repository, service, schema, middleware, dan utilitas.
- `backend/routers/` — endpoint dashboard, transaksi, dan budget.
- `backend/tests/` — pengujian backend.
- `frontend/templates/` — template Jinja2.
- `frontend/static/` — CSS dan aset statis.
- `finance.db` — database SQLite lokal di root proyek.

## Database, akun, dan keamanan

Aplikasi mendukung SQLite untuk pengembangan lokal serta PostgreSQL (termasuk Supabase) dan MySQL untuk deployment. Jika `DATABASE_URL` tidak diisi, SQLite digunakan. Untuk Vercel + Supabase, gunakan URL **Transaction pooler** dari Supabase Dashboard → Connect (port 6543), bukan koneksi database langsung. Connection pooler transaction sesuai dengan fungsi serverless Vercel. URL PostgreSQL otomatis menggunakan driver psycopg, TLS, pool satu koneksi per instance, dan menonaktifkan prepared statements.

Isi `SESSION_SECRET_KEY` dengan nilai acak rahasia minimal 32 karakter. Di Vercel nilai itu wajib; set `COOKIE_SECURE=true` karena deployment memakai HTTPS. Jangan commit `.env` atau menaruh kredensial di kode. Supabase Free mempunyai batas kuota/hibernasi sesuai ketentuan paket; periksa dashboard Supabase sebelum penggunaan produksi.

Pengguna dapat membuat akun melalui `/register`. Kata sandi di-hash PBKDF2-HMAC-SHA256, sementara session ditandatangani. Setiap transaksi dan budget memiliki `user_id`; query, grafik, ringkasan, edit, dan hapus dibatasi ke pemilik yang login. Database PostgreSQL dipakai bersama dengan tabel `users`, `transactions`, dan `budgets`, bukan satu database fisik per pengguna.

Halaman akun memungkinkan pengguna memperbarui nama/email, memilih mode terang atau gelap (preferensi disimpan per akun), dan mengunggah foto profil JPEG/PNG/WebP maksimal 2 MB. Foto divalidasi, diubah ukurannya, lalu disimpan sebagai data biner (`BYTEA` pada PostgreSQL); file gambar tidak disimpan di folder publik.

Startup membuat tabel dan menambahkan kolom yang belum ada. Jika ingin memindahkan data dari SQLite lama, buat backup terlebih dahulu, buat akun di Supabase, lalu import dari root proyek dengan `python backend/migrate_sqlite_to_database.py --owner-email alamat@anda.com` setelah `DATABASE_URL` diarahkan ke Supabase. Import menolak akun tujuan yang sudah berisi data serta sumber SQLite yang sudah menyimpan beberapa akun.

## Menjalankan aplikasi

Aktifkan virtual environment, pasang dependency dari `requirements.txt`, lalu jalankan `uvicorn main:app --reload` dari root proyek. Entrypoint `main.py` di root dipertahankan sebagai kompatibilitas agar perintah tersebut tetap sederhana.

## Build CSS

Jalankan `npm run build:css` dari root proyek setelah mengubah template atau `frontend/static/css/input.css`. Mode watch tersedia melalui `npm run watch:css`.

## Menjalankan test

Jalankan `pytest` dari root proyek. Konfigurasi pytest mengarahkan pencarian test ke `backend/tests/`.

## Deploy GitHub → Vercel → Supabase

1. Pastikan repository GitHub baru `student_finance_tracker` sudah menerima branch `main`; jangan push `.env`, file database, atau kredensial.
2. Di Vercel pilih **Add New → Project**, impor repository tersebut, dan gunakan root directory proyek (folder yang berisi `pyproject.toml`, `vercel.json`, dan `main.py`). Konfigurasi `pyproject.toml` menetapkan entrypoint FastAPI `backend/main.py`; build menjalankan `npm run build:css`.
3. Buat project Supabase. Di **Connect**, salin URL **Transaction pooler** dan set di Vercel sebagai `DATABASE_URL`. Set juga `SESSION_SECRET_KEY` ke string acak minimal 32 karakter dan `COOKIE_SECURE=true` untuk Production, Preview, serta Development jika semuanya memakai HTTPS.
4. Deploy dari Vercel. Startup pertama membuat tabel secara otomatis. Verifikasi `/health`, lalu daftar akun baru. Untuk data SQLite lama, jalankan importer dari mesin lokal dengan URL Supabase yang sama setelah membuat akun pemilik.

Deploy otomatis akan berjalan pada push ke GitHub setelah integrasi Vercel dibuat. Jangan menjalankan importer berkali-kali dan jangan pernah menaruh URL database beserta password dalam commit atau log publik.