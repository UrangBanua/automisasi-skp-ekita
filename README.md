# Automisasi SKP Harian - Ekita

Sistem otomatisasi untuk input SKP Harian ke sistem Ekita BKD HST, menggantikan input manual satu per satu via Postman.

## Fitur

- Login otomatis dengan session management (ci_session)
- Get target bulanan untuk mapping ID
- Parse file data SKP Harian (format JSON per baris / JSONL)
- Kirim SKP Harian secara batch dengan ID yang sudah di-map otomatis

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
EKITA_USERNAME=198901132020121005
EKITA_PASSWORD=your_password
```

## Penggunaan

### Preview Data (Dry Run)

```bash
python skp_automation.py --file data/skp_harian_juli_2026.jsonl --dry-run
```

### Kirim SKP Harian

```bash
# Untuk bulan Juli 2026
python skp_automation.py --file data/skp_harian_juli_2026.jsonl --tanggal 2026-07-01

# Untuk bulan ini
python skp_automation.py --file data/skp_harian.jsonl
```

### Test Mode

```bash
python skp_automation.py --test
```

## Format File Data

File data menggunakan format JSON per baris (JSONL):

```json
{"tanggal":"2026-07-01","id_opmt_realisasi_harian_skp":"","kegiatan_harian_skp":"Kegiatan 1.a - 1","kuantitas":"1","satuan_kuantitas":"127"}
{"tanggal":"2026-07-08","id_opmt_realisasi_harian_skp":"","kegiatan_harian_skp":"Kegiatan 1.a - 2","kuantitas":"1","satuan_kuantitas":"127"}
```

### Field yang Diperlukan

| Field | Keterangan |
|-------|------------|
| tanggal | Format YYYY-MM-DD |
| kegiatan_harian_skp | Nama kegiatan (contoh: "Kegiatan 1.a - 1") |
| kuantitas | Jumlah (default: "1") |
| satuan_kuantitas | Satuan (default: "127" = Kegiatan) |
| proses | Optional, "on" untuk kegiatan tertentu |

> **Catatan:** File `.txt` hasil export dari Postman/Excel juga bisa langsung dipakai — script hanya membaca baris yang dimulai dengan `{`. Header section (`=> ...`) diabaikan otomatis.

## Alur Kerja

```
1. Login → ci_session cookie
2. Get Target Bulanan (POST /c_user/get_target_bulan) → mapping kegiatan → info target
3. Parse file data (baris JSON)
4. Untuk setiap entry, isi otomatis id_opmt_target_bulanan_skp + id_opmt_target_skp dari mapping
5. POST ke /c_user/aksi_harian_skp
```

## Mapping Kegiatan

Script otomatis memetakan kegiatan berdasarkan nama kegiatan, dan mengisi **dua field sekaligus**:

| Kegiatan | Keyword Mapping | ID Bulanan (contoh) | id_opmt_target_skp (contoh) |
|----------|----------------|--------------------|----------------------------|
| Kegiatan 1.a | "buku besar" | 83985 | 238317 |
| Kegiatan 1.b | "rekapitulasi" | 83986 | 238317 |
| Kegiatan 1.c | "penjabaran pertanggungjawaban" | 83987 | 238317 |
| Kegiatan 2.a | "monitoring" | 83988 | 238318 |
| Kegiatan 2.b | "sosialisasi" | 83989 | 238318 |

ID aktual didapat dari response `get_target_bulan` — selalu fresh setiap bulan. Script menimpa nilai lama di file data dengan nilai terbaru dari server, sehingga aman dipakai ulang antar bulan.

## Endpoint yang Digunakan

| No | Endpoint | Purpose |
|----|----------|---------|
| 01 | `/c_main/validasi` | Login, dapatkan ci_session |
| 12 | `/c_user/get_target_bulan` | Get ID target bulanan |
| 13 | `/c_user/aksi_harian_skp` | Insert SKP Harian |

## Troubleshooting

### Login Gagal

- Periksa username/password di `.env`
- Pastikan NIP benar (contoh: 198901132020121005)

### Mapping Tidak Ditemukan

- Pastikan target bulanan sudah dibuat di sistem Ekita
- Jalankan dengan `--dry-run` untuk debug
- Periksa output `[OK] Mapping: ...` untuk melihat hasil mapping

### Session Expired

- ci_session valid ±2 jam
- Jalankan ulang script untuk mendapatkan session baru

## Catatan Penting

- Script ini mengasumsikan target bulanan sudah ada di sistem
- Pastikan periode SKP sudah aktif
- Backup data sebelum menjalankan automasi
- JANGAN commit `.env` ke git (sudah di-ignore)
