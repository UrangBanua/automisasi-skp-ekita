# Dokumentasi Perbaikan Automasi SKP Ekita

Dokumen ini mencatat perbaikan bug dan peningkatan stabilitas sistem (berdasarkan uji coba agustus 2026) pada `api_client.py` dan `skp_automation.py`.

## 1. Perbaikan Alur Login (Initial Cookie)
- **Masalah:** Login sering gagal (kredensial ditolak) karena server Ekita mengharuskan client (script) memiliki *cookie* `ci_session` awal sebelum men-_submit_ *password*.
- **Perbaikan (`api_client.py`):** Menambahkan request otomatis `GET /` ke *Base URL* Ekita sebelum melakukan POST data *login*, guna memancing pembentukan sesi pada server.

## 2. Penghapusan Hardcoded Array Index pada DataTable
- **Masalah:** Script gagal menangkap `id_tahunan`, id SKP target, dan `id_bulanan` karena metode lawas menebak lokasi ID pada array spesifik (misal: `row[2]` atau `row[8]`). Pada respon asli (berdasarkan *real run*), urutan kolom ini ternyata bergeser (contoh berada di indeks 4).
- **Perbaikan (`api_client.py`):** Seluruh iterasi tabel sekarang dilakukan dengan menggabungkan semua kolom respon menjadi satu string HTML (`"".join(str(col) for col in row)`), lalu Regex diinstruksikan menyapu seluruh baris secara bebas (terhindar dari error walau tabel berganti kolom).

## 3. Penyesuaian Regex Argumen String (JavaScript)
- **Masalah:** Langkah pencarian ID gagal total membaca HTML `<a onclick="ubah_target_bulanan_skp('1227847', '167342')">`. Regex yang ada mencoba membaca angka murni di dalam tanda kurung kurawal `\((\d+)\)`. 
- **Perbaikan (`api_client.py`):** Regex dirubah menjadi mengakomodir tanda kutip satu secara tepat: `r"ubah_target_bulanan_skp\('(\d+)'"`.

## 4. Penambahan Mekanisme "Resume" (Fallback Logic)
- **Masalah:** Jika script pernah mati mendadak atau *crash* setelah berhasil membuat Header Bulanan (Step 05) namun belum sempat melengkapi Rincian Target (Step 07-12) — maka ketika dijalankan ulang, eksekusi akan membaca "Bulan Telah Ada", men-skip proses pelengkapan turunan, dan langsung mati akibat *mapping* harian yang kosong (Error di Step 13).
- **Perbaikan (`skp_automation.py`):**
  - Membuat *helper function* independen `buat_target_bulanan()` (membungkus logika Step 07-12).
  - Menanamkan fallback: Meskipun script mendeteksi Header Bulan sudah ada, script tetap akan mengecek ketersediaan isian target (`get_target_bulan`). Apabila kosong, maka metode *helper* secara otomatis dipanggil ulang guna meneruskan (meresume) turunan target yang gagal kemarin. 

## 5. Pembaruan Standar Environment
- **Perbaikan:** Menyesuaikan variabel `.env.example` agar merujuk parameter `EKITA_BASE_URL` dan konfigurasi *username* sesuai dengan panggilan utilitas di `config.py`.
