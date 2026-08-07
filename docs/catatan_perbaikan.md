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
## 6. Logika Kuantitas & Proses untuk Sub-Sekuens (X.Y)
- **Masalah:** Kegiatan `1.b` memiliki sub-sekuens (`1.1`, `1.2`, `1.3`, `1.4`). Dalam satu grup, hanya entry **terakhir** yang boleh membawa `kuantitas`; entry sebelumnya harus dikirim dengan field `proses: "on"` (tanpa field `kuantitas` sama sekali).
- **Perbaikan (`skp_automation.py`):** Payload builder sekarang mendeteksi pola `X.Y` pada `kegiatan_harian_skp`, mengelompokkan entry berdasarkan `(kode, X)`, lalu:
  - Entry non-terakhir: hapus field `kuantitas`, set `proses: "on"`.
  - Entry terakhir: tetap membawa `kuantitas` dari template (tidak ada field `proses`).
- **Perbaikan (`api_client.py`):** Method `insert_harian` kini mengirim field secara eksklusif — jika `proses` ada, kirim `proses` tanpa `kuantitas`; jika tidak, kirim `kuantitas` tanpa `proses`.
- **Hasil verifikasi:** 34/34 entry sukses pada real-run Agustus 2026; 15 entry `proses` + 19 entry `kuantitas`. Server menampilkan kolom Kuantitas kosong (hanya satuan "Kegiatan") untuk entry `proses: on`.

## 7. Penambahan Fitur Ekstra & Keamanan (Agustus 2026)
- **Session Caching**: Skrip sekarang tidak lagi memanggil *login POST* secara membabi buta. Sesi (`ci_session`) disimpan sementara di dalam `data/session.txt`. Sebelum *login*, skrip akan me-*ping* server untuk menguji apakah sesi tersebut masih hidup; jika masih aktif, *login POST* akan dilewati demi menghemat performa server Ekita dan waktu pengguna.
- **Perubahan Ekstensi JSON**: Format `skp_harian.jsonl` (JSON *per lines*) resmi diubah ke format array murni `skp_harian.json` agar selaras dengan file `target_bulanan.json`. Fungsi `load_template()` telah disederhanakan menggunakan metode standar `json.load()`.
- **Fitur `--cek nilai`**: Ditambahkan argumen `--cek choices=["nilai"]` untuk melihat hasil *real-time* skor bulanan serta status persetujuannya langsung melalui terminal tanpa masuk ke browser.
- **Fitur Penghapusan Aman (`--del harian` & `--del bulanan`)**:
  - **Hapus Selektif**: Diakomodir lewat parameter opsional `--del`.
  - **Mekanisme Pelindung ("Sesuai" / "Disetujui")**: Mengatasi risiko terhapusnya data yang telah diterima oleh admin, skrip akan melakuan verifikasi teks HTML pada kolom *Status Kesesuaian*. Jika baris mengandung status **"Sesuai"** (untuk *harian*) atau **"Disetujui"** (untuk *bulanan*), baris tersebut akan dilewati (*skipped*). Hanya data berstatus kosong atau belum disetujui yang ditembak dengan POST *hapus*.
- **Pembenahan Payload Hapus**: Memperbaiki jenis konten HTTP request di dalam `api_client.py` agar aksi penghapusan mematuhi standar *CodeIgniter* Ekita, yakni *x-www-form-urlencoded* (melalui pengiriman `raw="id=XXXX"`).
- **Antarmuka (CLI) Cerdas**: Penerapan *fallback argument* jika argumen wajib tidak ada. Menjalankan skrip tanpa parameter kini otomatis memunculkan teks `help`. Parameter `--bulan` dinamis berubah menjadi opsional khusus untuk kasus eksekusi `--cek nilai`.
