# Workflow: Automasi SKP Harian - Ekita

Dokumen ini menjelaskan alur kerja lengkap script `skp_automation.py` untuk menginput SKP Harian ke sistem Ekita BKD HST secara otomatis, menggantikan input manual via Postman.

---

## 1. Cara Menjalankan

```bash
cd /opt/data/workspace/projects/automisasi-skp-ekita
./venv/bin/python skp_automation.py --bulan 8 --tahun 2026
```

| Parameter   | Wajib | Keterangan                  |
|-------------|-------|-----------------------------|
| `--bulan`   | Ya    | Bulan target (1–12)         |
| `--tahun`   | Ya    | Tahun target, contoh `2026` |
| `--dry-run` | Tidak | Preview tanggal tanpa login |

```bash
# Preview saja (cara aman)
./venv/bin/python skp_automation.py --bulan 8 --tahun 2026 --dry-run
```

---

## 2. Alur Kerja Lengkap

```
┌───────────────────────────────────────────────────────────────┐
│ 01. LOGIN                                                     │
│     POST /c_main/validasi  → ci_session                       │
└──────────────┬────────────────────────────────────────────────┘
               ▼
┌───────────────────────────────────────────────────────────────┐
│ 02. GET ID SKP TAHUNAN                                        │
│     POST /c_tahunan_skp/ajax_list (status=tahun)              │
│     → parse "target_tahunan_skp(ID)" → id_tahunan             │
└──────────────┬────────────────────────────────────────────────┘
               ▼
┌───────────────────────────────────────────────────────────────┐
│ 03. GET ID TARGET SKP TAHUNAN                                 │
│     POST /c_tahunan_skp/ajax_list_target (status,id)          │
│     → parse "ubah_target_tahunan_skp(ID)"                     │
│     → target_skp_1, target_skp_2 (cth 238317, 238318)         │
└──────────────┬────────────────────────────────────────────────┘
               ▼
┌───────────────────────────────────────────────────────────────┐
│ 04. CEK LIST TARGET BULANAN                                   │
│     POST /c_bulanan_skp/ajax_list                             │
│     Cari bulan sesuai nama (AGUSTUS)                          │
│               │                                               │
│        ┌──────┴──────────────┐                                │
│        ▼                      ▼                               │
│   SUDAH ADA             BELUM ADA                             │
│   id_bulanan diambil    → INSERT target bulanan               │
│        │                      │                               │
│   (langsung ke 13)      ┌─────┴─────────┐                     │
│                         ▼               ▼                     │
│                 05 INSERT bulanan header                      │
│                 06 re-query id_bulanan                        │
│                 07 INSERT target_1 (SKP1)                     │
│                 08 GET target_bulanan_ids → id_target_1       │
│                 09 INSERT turunan 1.a,1.b,1.c                 │
│                 10 INSERT target_2 (SKP2)                     │
│                 11 GET → id_target_2                          │
│                 12 INSERT turunan 2.a,2.b                     │
└──────────────┬────────────────────────────────────────────────┘
               ▼
┌───────────────────────────────────────────────────────────────┐
│ 13. GET TARGET BULAN (mapping)                                │
│     POST /c_user/get_target_bulan (tanggal=tahun-bulan-01)    │
│     → matching kegiatan → id_harian ("<id>-turunan")           │
└──────────────┬────────────────────────────────────────────────┘
               ▼
┌───────────────────────────────────────────────────────────────┐
│ 14. GENERATE TANGGAL & BUILD PAYLOAD                          │
│     Baca template data/skp_harian.jsonl (34 entry)            │
│     Tanggal auto-adjust weekend                               │
│     Grouping X.Y: entry non-terakhir → proses="on"            │
│     entry terakhir per grup → kuantitas dari template         │
               ▼
┌───────────────────────────────────────────────────────────────┐
│ 15. INSERT SKP HARIAN                                         │
│     POST /c_user/aksi_harian_skp × 34                        │
│     → Sukses / Gagal                                          │
└──────────────┬────────────────────────────────────────────────┘
               ▼
┌───────────────────────────────────────────────────────────────┐
│ 16. READ LIST (hasil tabel)                                   │
│     POST /c_harian_skp/ajax → tampilkan tabel                 │
└───────────────────────────────────────────────────────────────┘
```

---

## 3. Token/Parameter Penting

| Field                          | Sumber              | Contoh          |
|--------------------------------|---------------------|-----------------|
| `ci_session`                   | Login               | `kjyiac...`     |
| `id_tahunan`                   | Step 02 (otomatis)  | `29971`         |
| `id_opmt_target_skp`           | Step 03 (otomatis)  | `238317`,`238318` |
| `id_opmt_bulanan_skp`          | Step 04/06 (otomatis)| `167179`        |
| `id_opmt_target_bulanan_skp`   | Step 08/11 (otomatis)| `1226899` dsb  |
| Turunan `target_waktu`         | Config              | `30`            |
| `satuan_kuantitas`             | Config              | `127`           |
| `kualitas`                     | Config              | `100`           |

---

## 4. Mapping Template → Kegiatan
Template `skp_harian.jsonl` berisi 34 entry dengan atribut `kode`, `minggu`, `hari`, `seq`, `kegiatan_harian_skp`, `kuantitas`.

| `kode` | Kegiatan Harian      | Target   |
|--------|----------------------|----------|
| `1.a`  | Kegiatan 1.a - N     | Target_1 |
| `1.b`  | Kegiatan 1.b - x.y   | Target_1 |
| `1.c`  | Kegiatan 1.c - N     | Target_1 |
| `2.a`  | Kegiatan 2.a - N     | Target_2 |
| `2.b`  | Kegiatan 2.b - N     | Target_2 |
`kegiatan_harian_skp` diformat: `{kode} - x.y` (untuk 1.b, sub-sekuens) atau `{kode} - N` (untuk 1.a/1.c/2.x). Dalam grup sub-sekuens `X.Y`, hanya entry terakhir yang membawa `kuantitas`; entry sebelumnya dikirim dengan `proses: "on"` (tanpa field `kuantitas`).

---

## 5. Aturan Tanggal

Template menggunakan **minggu ke-N** dan **hari dalam minggu** (hari kerja Senin–Jumat).

- **Minggu 1** = minggu yang mengandung tanggal 1.
- Tanggal dihitung: `Senin minggu ke-1 bulan` + `(minggu-1)×7 hari` + `offset hari kerja`.
- Hari yang jatuh pada **Sabtu** → geser mundur (-1) → Jumat.
- Hari yang jatuh pada **Minggu** → geser maju (+1) → Senin.
- **Batas bulan dipertahankan** — tanggal tidak boleh keluar dari bulan target (awal = 1, akhir = hari terakhir bulan).

Contoh: bulan Juli 2026 (1 Juli = Rabu, minggu1锚 ke Jul1); bulan Agustus 2026 (1 Agst = Sabtu, minggu1锚 ke Ag5):

| Template      | Hasil Tanggal |
|---------------|---------------|
| Ag: minggu 1, Rabu| 2026-08-05    |
| minggu 1, Kam | 2026-07-02    |
| minggu 2, Sen | 2026-07-06    |
| minggu 3, Rab | 2026-07-15    |

---

## 6. Hasil Output

Tabel akhir ditampilkan dari endpoint `POST /c_harian_skp/ajax`. Kolom:

| No | Tanggal | Kegiatan Harian SKP | Kuantitas | Status Proses |
|----|---------|---------------------|-----------|---------------|

---

## 7. File Project

```
automisasi-skp-ekita/
├── config.py            # Endpoint, turunan SKP, nama bulan
├── api_client.py        # Client HTTP (login, CRUD SKP)
├── skp_automation.py    # Script utama (argumen --bulan --tahun)
│   └── skp_harian.jsonl # Template 34 entry (hari relatif)
├── docs/
│   ├── project_plan.md  # Dokumen rencana
│   └── workflow.md      # Dokumen alur kerja (ini)
├── .env                 # Credentials (jangan di-commit)
└── README.md
```