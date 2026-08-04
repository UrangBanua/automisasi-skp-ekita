# Project Plan: Automasi SKP Harian - Ekita

## Tujuan

Otomatisasi input SKP Harian ke sistem Ekita BKD HST dalam satu command:
```bash
./venv/bin/python skp_automation.py --bulan 8 --tahun 2026
```

## Parameter

| Parameter | Wajib | Default | Contoh |
|-----------|-------|---------|--------|
| `--bulan` | Ya | - | `8` (Agustus) |
| `--tahun` | Ya | - | `2026` |
| `--dry-run` | Tidak | `false` | Preview tanpa kirim |

## Alur Eksekusi (16 Step)

### Fase 1: Login & Cek Target Bulanan

```
01. POST /c_main/validasi
    └─ payload: username, password
    └─ output: ci_session cookie

02. POST /c_tahunan_skp/ajax_list
    └─ payload: DataTable params, status=<tahun>
    └─ output: id_tahunan (dari onclick="target_tahunan_skp(ID)")

03. POST /c_tahunan_skp/ajax_list_target
    └─ payload: DataTable params, status=<tahun>, id=<id_tahunan>
    └─ output: id_opmt_target_skp[] (dari onclick="ubah_target_tahunan_skp(ID)")
       - target_skp_1 = ID pertama (mis. 238317)
       - target_skp_2 = ID kedua (mis. 238318)

04. POST /c_bulanan_skp/ajax_list
    └─ payload: DataTable params, status=<tahun>
    └─ output: list bulanan, cari nama bulan di kolom index 2
       - Jika DITEMUKAN: id_opmt_bulanan_skp dari onclick="hapus_bulanan_skp(ID)"
         → LANJUT ke Step 13
       - Jika TIDAK DITEMUKAN: → lanjut Step 05
```

### Fase 2: Insert Target Bulanan (hanya jika bulan belum ada)

```
05. POST /c_user/aksi_bulanan_skp
    └─ payload: {"id_opmt_bulanan_skp":"", "tahun":"<tahun>", "bulan":"<bulan>"}
    └─ output: OK/gagal

06. POST /c_bulanan_skp/ajax_list (re-query)
    └─ ambil id_opmt_bulanan_skp baru dari onclick="hapus_bulanan_skp(ID)"

07. POST /c_user/aksi_target_bulanan_skp (Target 1)
    └─ payload: {"id_opmt_target_bulanan_skp":"", "id_opmt_bulanan_skp":"<id_baru>",
                  "id_opmt_target_skp":"<target_skp_1>", "turunan":"ya", "target_waktu":"30"}

08. GET /c_user/target_bulanan_skp/<id_opmt_bulanan_skp>
    └─ parse HTML, cari onclick="ubah_target_bulanan_skp(ID)"
    └─ output: id_opmt_target_bulanan_skp_1 (ID pertama)

09. POST /c_user/aksi_turunan_skp × 3 (Turunan 1.a, 1.b, 1.c)
    └─ payload per turunan: {"id_opmt_turunan_skp":"",
         "id_opmt_target_bulanan_skp":"<id_opmt_target_bulanan_skp_1>",
         "kegiatan_turunan":"<nama kegiatan>",
         "target_kuantitas":"<qty>", "satuan_kuantitas":"127",
         "kualitas":"100", "target_waktu":"<waktu>", "biaya":""}

10. POST /c_user/aksi_target_bulanan_skp (Target 2)
    └─ payload: sama dengan step 07, beda id_opmt_target_skp (<target_skp_2>)

11. GET /c_user/target_bulanan_skp/<id_opmt_bulanan_skp>
    └─ output: id_opmt_target_bulanan_skp_2 (ID kedua)

12. POST /c_user/aksi_turunan_skp × 2 (Turunan 2.a, 2.b)
    └─ payload: sama, pakai id_opmt_target_bulanan_skp_2
```

### Fase 3: Mapping & Generate Tanggal

```
13. POST /c_user/get_target_bulan
    └─ payload: tanggal=<tahun>-<bulan>-01
    └─ output: JSON array dengan id, kegiatan, id_opmt_target_bulanan_skp, id_opmt_target_skp
    └─ mapping: kode kegiatan (1.a, 1.b, dst) → {id, id_opmt_target_skp}

14. Generate tanggal dari template skp_harian.jsonl
    └─ Aturan adjust:
       - Sabtu (weekday=5) → tanggal -1 (Jumat)
       - Minggu (weekday=6) → tanggal +1 (Senin)
       - Tanggal awal bulan: jika adjust menyebabkan pindah bulan, tetap di tanggal 1
       - Tanggal akhir bulan: jika adjust menyebabkan pindah bulan, tetap di tanggal terakhir
```

### Fase 4: Insert SKP Harian & Tampilkan Hasil

```
15. POST /c_user/aksi_harian_skp × 34
    └─ payload per entry: {"tanggal":"<adjusted>", "id_opmt_realisasi_harian_skp":"",
         "kegiatan_harian_skp":"<nama>", "kuantitas":"<qty>",
         "satuan_kuantitas":"127",
         "id_opmt_target_bulanan_skp":"<id>-turunan",
         "id_opmt_target_skp":"<target_skp>"}

16. POST /c_harian_skp/ajax
    └─ payload: tanggal=&bulan=<bulan>&tahun=<tahun>
    └─ output: HTML tabel → parse → tampilkan sebagai tabel text
```

## Template Data (skp_harian.jsonl)

Template menggunakan **hari relatif** (minggu ke-X, hari kerja ke-Y dalam minggu):

```jsonl
{"kode":"1.a","minggu":1,"hari_kerja":1,"kegiatan_harian_skp":"Kegiatan 1.a - 1","kuantitas":"1"}
{"kode":"1.a","minggu":2,"hari_kerja":1,"kegiatan_harian_skp":"Kegiatan 1.a - 2","kuantitas":"1"}
{"kode":"1.a","minggu":3,"hari_kerja":1,"kegiatan_harian_skp":"Kegiatan 1.a - 3","kuantitas":"1"}
{"kode":"1.c","minggu":1,"hari_kerja":1,"kegiatan_harian_skp":"Kegiatan 1.c - 1","kuantitas":"1"}
...
```

### Aturan Generate Tanggal

1. Hitung tanggal: minggu ke-X × hari kerja ke-Y (Senin=1, Jumat=5)
2. `minggu=1, hari_kerja=1` = Senin minggu pertama bulan tersebut
3. Setelah dapat tanggal, cek hari:
   - Sabtu → kurangi 1 hari
   - Minggu → tambah 1 hari
4. Boundary check: tidak boleh keluar dari bulan target

### Mapping Kuantitas per Kegiatan

| Kode | Kegiatan | Target Kuantitas | Waktu | Entries |
|------|----------|-----------------|-------|---------|
| 1.a | Buku Besar Pendapatan & Belanja | 3 | 10 | 3 (minggu 1,2,3) |
| 1.b | Rekapitulasi Pendapatan & Belanja | 5 | 20 | 20 (harian senin-jumat, 4 minggu) |
| 1.c | Penyelenggaraan Akuntansi | 3 | 10 | 3 (minggu 1,2,3) |
| 2.a | Monitoring SIPD | 20 | 4 | 4 (minggu 1,2,3,4) |
| 2.b | Sosialisasi SIPD | 4 | 4 | 4 (minggu 1,2,3,4) |

Total: **34 entries** per bulan

## Struktur File

```
/opt/workspace/projects/automisasi-skp-ekita/
├── .env                    # Credentials
├── .env.example
├── .gitignore
├── config.py               # Konfigurasi + endpoint URLs
├── api_client.py           # API client (semua method)
├── skp_automation.py       # Main script (--bulan --tahun)
├── requirements.txt
├── README.md
├── data/
│   └── skp_harian.jsonl    # Template baku (34 entries, hari relatif)
└── docs/
    └── project_plan.md     # Dokumen ini
```

## Endpoint Reference

| # | Endpoint | Method | Purpose |
|---|----------|--------|---------|
| 01 | `/c_main/validasi` | POST | Login |
| 02 | `/c_tahunan_skp/ajax_list` | POST | Get id SKP Tahunan |
| 03 | `/c_tahunan_skp/ajax_list_target` | POST | Get id_opmt_target_skp |
| 04 | `/c_bulanan_skp/ajax_list` | POST | Cek list target bulanan |
| 05 | `/c_user/aksi_bulanan_skp` | POST | INSERT bulanan header |
| 06 | `/c_user/aksi_target_bulanan_skp` | POST | INSERT target bulanan (1 & 2) |
| 07 | `/c_user/target_bulanan_skp/<id>` | GET | Get id_opmt_target_bulanan_skp |
| 08 | `/c_user/aksi_turunan_skp` | POST | INSERT turunan (1.a-1.c, 2.a-2.b) |
| 09 | `/c_user/get_target_bulan` | POST | Get mapping kegiatan → ID |
| 10 | `/c_user/aksi_harian_skp` | POST | INSERT SKP Harian |
| 11 | `/c_harian_skp/ajax` | POST | READ list SKP Harian |
