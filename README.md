# Automisasi SKP Harian - Ekita

Sistem otomatisasi untuk input SKP Harian ke sistem Ekita BKD HST, menggantikan input manual satu per satu via Postman.

## Fitur

- Login otomatis dengan session management (`ci_session`)
- Auto-detect dan auto-insert target bulanan jika belum ada (step 04-12)
- Resume otomatis jika target bulanan tidak lengkap (fallback logic)
- Parse file template target bulanan `data/target_bulanan.json` (skema uraian SKP 1 & 2)
- Parse file template harian `data/skp_harian.jsonl` (format JSONL, 34 entry)
- Generate tanggal otomatis dari (minggu, hari) dengan auto-adjust weekend
- Grouping sub-sekuens `X.Y`: entry non-terakhir dikirim dengan `proses: "on"`, entry terakhir membawa `kuantitas`
- Kirim SKP Harian secara batch (34 entry) dengan ID yang sudah di-map otomatis

## Setup

### 1. Install Dependencies

```bash
cd automisasi-skp-ekita
pip install -r requirements.txt
```

### 2. Konfigurasi .env

Copy `.env.example` ke `.env`:

```bash
cp .env.example .env
```

Edit `.env`:

```env
EKITA_BASE_URL=https://ekita.bkdhst.kalselprov.go.id
EKITA_USERNAME=198901132020121005
EKITA_PASSWORD=password_anda
```

## Penggunaan

### Preview Data (Dry Run)

Preview tanggal yang akan dipakai tanpa login & tanpa kirim data:

```bash
python skp_automation.py --bulan 8 --tahun 2026 --dry-run
```

### Kirim SKP Harian

```bash
# Input SKP Harian untuk bulan Agustus 2026
python skp_automation.py --bulan 8 --tahun 2026
```

| Parameter   | Wajib | Keterangan                        |
|-------------|-------|-----------------------------------|
| `--bulan`   | Ya    | Bulan target (1-12)               |
| `--tahun`   | Ya    | Tahun target, contoh `2026`       |
| `--dry-run` | Tidak | Preview tanggal tanpa login/kirim |

## Format File Template

### Template Harian (`skp_harian.jsonl`)


File template `data/skp_harian.jsonl` menggunakan format JSON per baris (JSONL), 34 entry:

```json
{"kode":"1.a","minggu":1,"hari":"Rabu","seq":1,"kegiatan_harian_skp":"Kegiatan 1.a - 1","kuantitas":"1"}
{"kode":"1.b","minggu":1,"hari":"Rabu","seq":1,"kegiatan_harian_skp":"Kegiatan 1.b - 1.1","kuantitas":"1"}
```

### Field yang Diperlukan

| Field                 | Keterangan                                                        |
|-----------------------|-------------------------------------------------------------------|
| `kode`                | Kode kegiatan: `1.a`, `1.b`, `1.c`, `2.a`, `2.b`                  |
| `minggu`              | Minggu ke-N dalam bulan (1-5)                                     |
| `hari`                | Nama hari Indonesia: Senin-Jumat                                  |
| `seq`                 | Urutan entry pada tanggal yang sama (default: 1)                  |
| `kuantitas`           | Jumlah (default: "1"); untuk `1.b` berlaku hanya pada entry terakhir per grup |

### Template Target Bulanan (`target_bulanan.json`)

Menyimpan deskripsi/uraian untuk kegiatan SKP bulanan (SKP 1 dan SKP 2). File ini diubah setiap bulannya jika diperlukan uraian baru, dengan mempertahankan struktur JSON aslinya.

### Logika Sub-Sekuens `X.Y`

Kegiatan `1.b` memiliki sub-sekuens (`1.1`, `1.2`, `1.3`, `1.4`). Dalam satu grup (kode + nomor grup sama), hanya entry **terakhir** yang membawa field `kuantitas`; entry sebelumnya dikirim dengan field `proses: "on"` (tanpa `kuantitas`).

Contoh grup `1.b-1`:

| Entry             | Payload dikirim                                                  |
|-------------------|------------------------------------------------------------------|
| `Kegiatan 1.b - 1.1` | `proses: "on"` (tanpa field `kuantitas`)                      |
| `Kegiatan 1.b - 1.2` | `proses: "on"` (tanpa field `kuantitas`)                      |
| `Kegiatan 1.b - 1.3` | `proses: "on"` (tanpa field `kuantitas`)                      |
| `Kegiatan 1.b - 1.4` | `kuantitas: "1"` (tanpa field `proses`)                       |

## Alur Kerja

Script menjalankan 16 langkah otomatis:

```
01. LOGIN                    → POST /c_main/validasi → ci_session
02. GET ID SKP TAHUNAN       → POST /c_tahunan_skp/ajax_list
03. GET ID TARGET SKP        → POST /c_tahunan_skp/ajax_list_target
04. CEK TARGET BULANAN       → POST /c_bulanan_skp/ajax_list
    ├─ BELUM ADA → step 05-12 (INSERT target bulanan + turunan)
    └─ SUDAH ADA → cek kelengkapan, resume jika kosong
05. INSERT BULANAN HEADER
06. RE-QUERY id_bulanan
07-12. INSERT target + turunan (1.a,1.b,1.c,2.a,2.b)
13. GET TARGET BULAN         → mapping kode → id_harian
14. BUILD PAYLOAD            → grouping X.Y (proses/kuantitas)
15. INSERT SKP HARIAN        → POST /c_user/aksi_harian_skp × 34
16. READ LIST                → tampilkan tabel hasil
```

## Mapping Kegiatan

Script otomatis memetakan `kode` ke target bulanan via `get_target_bulan`:

| Kode  | Kegiatan Harian      | Keyword Mapping    | Target   |
|-------|----------------------|--------------------|----------|
| `1.a` | Kegiatan 1.a - N     | "buku besar"       | Target_1 |
| `1.b` | Kegiatan 1.b - x.y   | "rekapitulasi"     | Target_1 |
| `1.c` | Kegiatan 1.c - N     | "pertanggungjawaban"| Target_1 |
| `2.a` | Kegiatan 2.a - N     | "monitoring"       | Target_2 |
| `2.b` | Kegiatan 2.b - N     | "sosialisasi"      | Target_2 |

ID aktual didapat dari response `get_target_bulan` — selalu fresh setiap bulan.

## Aturan Tanggal

- **Minggu 1** = minggu yang mengandung tanggal 1.
- Tanggal dihitung: `Senin minggu ke-1 bulan` + `(minggu-1)×7` + `offset hari kerja`.
- Hari yang jatuh pada **Sabtu** → geser mundur (-1) → Jumat.
- Hari yang jatuh pada **Minggu** → geser maju (+1) → Senin.
- Tanggal tidak boleh keluar dari bulan target.

## Troubleshooting

### Login Gagal

- Periksa `EKITA_USERNAME` / `EKITA_PASSWORD` di `.env`
- Pastikan `EKITA_BASE_URL` benar

### Mapping Tidak Ditemukan

- Pastikan target bulanan sudah dibuat di sistem Ekita (script auto-insert jika belum)
- Jalankan dengan `--dry-run` untuk preview
- Jika target bulanan ada tapi kosong, script otomatis resume (fallback logic)

### Session Expired

- `ci_session` valid ±2 jam
- Jalankan ulang script untuk mendapatkan session baru

## Catatan Penting

- Script auto-detect dan auto-insert target bulanan jika belum ada
- Jika target bulanan ada tapi turunannya kosong, script otomatis melengkapi (resume)
- Backup data sebelum menjalankan automasi
- JANGAN commit `.env` ke git (sudah di-ignore)
