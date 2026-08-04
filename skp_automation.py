#!/usr/bin/env python3
"""
Automisasi SKP Harian - Ekita BKD HST
Run sekali dengan parameter --bulan dan --tahun.
Contoh: ./venv/bin/python skp_automation.py --bulan 8 --tahun 2026
"""
import argparse
import calendar
import json
import re
import sys
from datetime import date, timedelta

from config import USERNAME, PASSWORD, BULAN_NAMA, TURUNAN_SKP
from api_client import EkitaClient

# Mapping nama hari Indonesia → Python weekday (Senin=0 ... Minggu=6)
HARI_INDEX = {
    "Senin": 0, "Selasa": 1, "Rabu": 2, "Kamis": 3,
    "Jumat": 4, "Sabtu": 5, "Minggu": 6,
}

# Keyword mapping kegiatan → kode
KEYWORD_MAP = [
    ("1.a", "buku besar"),
    ("1.b", "rekapitulasi"),
    ("1.c", "pertanggungjawaban"),
    ("2.a", "monitoring"),
    ("2.b", "sosialisasi"),
]


# ──────────────────────────────────────────────────────────────
# Tanggal generation
# ──────────────────────────────────────────────────────────────

def generate_tanggal(tahun, bulan, minggu, hari):
    """Hitung tanggal untuk (minggu, hari) dalam bulan target. Return 'YYYY-MM-DD'.

    Anchor = hari pertama yang jatuh pada target weekday di dalam bulan (>= tanggal 1).
    Week 1 = minggu yang mengandung anchor.
    """
    first = date(tahun, bulan, 1)
    target_wd = HARI_INDEX[hari]
    # Anchor: hari pertama >= tanggal 1 dengan weekday = target
    offset_to_target = (target_wd - first.weekday()) % 7
    anchor = first + timedelta(days=offset_to_target)
    # Minggu N = anchor + (N-1) * 7 hari
    d = anchor + timedelta(weeks=minggu - 1)

    # Weekend adjust
    if d.weekday() == 5:      # Sabtu → -1 (Jumat)
        d = d - timedelta(days=1)
    elif d.weekday() == 6:    # Minggu → +1 (Senin)
        d = d + timedelta(days=1)

    # Boundary: jaga tetap di bulan target
    last_day = calendar.monthrange(tahun, bulan)[1]
    if d < date(tahun, bulan, 1):
        d = date(tahun, bulan, 1)
    elif d > date(tahun, bulan, last_day):
        d = date(tahun, bulan, last_day)

    return d.strftime("%Y-%m-%d")


def load_template(path):
    """Parse file JSONL template → list of dict."""
    entries = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or not line.startswith("{"):
                continue
            entries.append(json.loads(line))
    return entries


# ──────────────────────────────────────────────────────────────
# Mapping kegiatan → id harian
# ──────────────────────────────────────────────────────────────

def build_harian_mapping(targets):
    """
    Dari response get_target_bulan, build mapping:
      kode → {"id_harian": "<id>-turunan", "id_opmt_target_skp": "<...>"}
    """
    mapping = {}
    for row in targets:
        kegiatan = row.get("kegiatan", "")
        kode = None
        for kw_kode, keyword in KEYWORD_MAP:
            if keyword.lower() in kegiatan.lower():
                kode = kw_kode
                break
        if kode is None:
            continue
        mapping[kode] = {
            "id_harian": f"{row.get('id')}-turunan",
            "id_opmt_target_skp": row.get("id_opmt_target_skp", ""),
        }
    return mapping


# ──────────────────────────────────────────────────────────────
# Tabel print
# ──────────────────────────────────────────────────────────────

def cell_values(row_html):
    """Extract text of each <td> in a <tr>."""
    return [re.sub(r"<[^>]+>", "", c).strip()
            for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row_html, re.DOTALL)]


def print_harian(html):
    """Parse HTML dari /c_harian_skp/ajax → print tabel text."""
    tbody = re.search(r"<tbody>(.*?)</tbody>", html, re.DOTALL)
    if not tbody:
        print("  [SKIP] Tidak ada data SKP Harian.")
        return
    rows = re.findall(r"<tr>(.*?)</tr>", tbody.group(1), re.DOTALL)

    print()
    print("=" * 110)
    print("DAFTAR SKP HARIAN BULAN")
    print("=" * 110)
    print(f"{'No':>4} | {'Tanggal':<12} | {'Kegiatan':<22} | {'SKP Bulanan':<50} | {'Kuantitas':<10} | {'Proses'}")
    print("-" * 110)
    count = 0
    for r in rows:
        c = cell_values(r)
        if len(c) >= 5:
            count += 1
            print(f"{c[0]:>4} | {c[1]:<12} | {c[2]:<22} | {c[3][:50]:<50} | {c[4]:<10} | {c[5] if len(c) > 5 else ''}")
    print("-" * 110)
    print(f"Total: {count} baris")


# ──────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────

# ──────────────────────────────────────────────────────────────
# Helper: buat target + turunan bulanan (step 07-12)
# ──────────────────────────────────────────────────────────────

def buat_target_bulanan(client, id_bulanan, target_skp_1, target_skp_2):
    """Buat target bulanan SKP 1 & 2 beserta turunannya. Return True jika berhasil."""
    # 07. Insert target 1
    print("[07] Insert target bulanan SKP 1...")
    client.insert_target_bulanan(id_bulanan, target_skp_1, TURUNAN_SKP["1"]["target_waktu"])
    tb_ids_1 = client.get_target_bulanan_ids(id_bulanan)
    if not tb_ids_1:
        print("[ERROR] Tidak dapat id target bulanan 1")
        return False
    id_target_bulan_1 = tb_ids_1[0]
    print(f"      id_opmt_target_bulanan_skp_1 = {id_target_bulan_1}")

    # 09. Insert turunan 1.a, 1.b, 1.c
    print("[09] Insert turunan 1.a, 1.b, 1.c...")
    for td in TURUNAN_SKP["1"]["turunan"]:
        ok = client.insert_turunan(id_target_bulan_1, td)
        print(f"      {td['kode']}: {'OK' if ok else 'GAGAL'}")

    # 10. Insert target 2
    print("[10] Insert target bulanan SKP 2...")
    client.insert_target_bulanan(id_bulanan, target_skp_2, TURUNAN_SKP["2"]["target_waktu"])
    tb_ids_2 = client.get_target_bulanan_ids(id_bulanan)
    if len(tb_ids_2) < 2:
        print(f"[ERROR] target bulanan 2 tidak ditemukan: {tb_ids_2}")
        return False
    id_target_bulan_2 = tb_ids_2[1]
    print(f"      id_opmt_target_bulanan_skp_2 = {id_target_bulan_2}")

    # 12. Insert turunan 2.a, 2.b
    print("[12] Insert turunan 2.a, 2.b...")
    for td in TURUNAN_SKP["2"]["turunan"]:
        ok = client.insert_turunan(id_target_bulan_2, td)
        print(f"      {td['kode']}: {'OK' if ok else 'GAGAL'}")

    return True


def main():
    parser = argparse.ArgumentParser(description="Automasi SKP Harian - Ekita BKD HST")
    parser.add_argument("--bulan", type=int, required=True, help="Bulan (1-12)")
    parser.add_argument("--tahun", type=int, required=True, help="Tahun, contoh 2026")
    parser.add_argument("--dry-run", action="store_true", help="Preview tanpa kirim & tanpa login")
    args = parser.parse_args()

    if not 1 <= args.bulan <= 12:
        print("[ERROR] --bulan harus 1-12")
        sys.exit(1)

    print("=" * 60)
    print("AUTOMASI SKP HARIAN - EKITA")
    print(f"Bulan: {args.bulan} ({BULAN_NAMA.get(args.bulan, '?')})  Tahun: {args.tahun}")
    print("=" * 60)

    # Load template
    template_path = "data/skp_harian.jsonl"
    template = load_template(template_path)
    if not template:
        print("[ERROR] Template kosong / tidak ditemukan:", template_path)
        sys.exit(1)

    # Preview
    print(f"\n[PREVIEW] {len(template)} entry dari template")
    for e in template[:5]:
        tgl = generate_tanggal(args.tahun, args.bulan, e["minggu"], e["hari"])
        print(f"  {tgl}  {e['kegiatan_harian_skp']:<22} qty={e['kuantitas']}")
    if len(template) > 5:
        print(f"  ... dan {len(template) - 5} entry lainnya")

    if args.dry_run:
        print("\n[DRY RUN] Selesai (tanpa login, tanpa kirim).")
        return

    if not USERNAME or not PASSWORD:
        print("[ERROR] EKITA_USERNAME/EKITA_PASSWORD belum diatur di .env")
        sys.exit(1)

    client = EkitaClient()

    # 01. Login
    print("\n[01] Login...")
    if not client.login(USERNAME, PASSWORD):
        print("[ERROR] Login gagal")
        sys.exit(1)
    print(f"      OK, ci_session: {client.ci_session[:16]}...")

    # 02. id_tahunan
    print("[02] Ambil id SKP Tahunan...")
    id_tahunan = client.get_id_tahunan(args.tahun)
    if not id_tahunan:
        print("[ERROR] Tidak dapat id_tahunan")
        sys.exit(1)
    print(f"      id_tahunan = {id_tahunan}")

    # 03. id_opmt_target_skp
    print("[03] Ambil id_opmt_target_skp (SKP Tahunan Target)...")
    target_skp_ids = client.get_target_skp_ids(args.tahun, id_tahunan)
    if len(target_skp_ids) < 2:
        print(f"[ERROR] target_skp_ids kurang: {target_skp_ids}")
        sys.exit(1)
    target_skp_1, target_skp_2 = target_skp_ids[0], target_skp_ids[1]
    print(f"      target_skp_1 = {target_skp_1}, target_skp_2 = {target_skp_2}")

    print("[04] Cek list target bulanan...")
    id_bulanan = client.cek_bulanan(args.tahun, BULAN_NAMA[args.bulan])
    if id_bulanan:
        print(f"      Bulan {BULAN_NAMA[args.bulan]} SUDAH ADA → id_opmt_bulanan_skp = {id_bulanan}")
    else:
        print(f"      Bulan {BULAN_NAMA[args.bulan]} BELUM ADA → melakukan INSERT target bulanan.")

        # 05. Insert bulanan header
        print("[05] INSERT bulanan header...")
        if not client.insert_bulanan(args.tahun, args.bulan):
            print("[ERROR] insert_bulanan gagal")
            sys.exit(1)
        print("      OK")

        # 06. Re-query id bulanan
        id_bulanan = client.cek_bulanan(args.tahun, BULAN_NAMA[args.bulan])
        if not id_bulanan:
            print("[ERROR] Tidak dapat id_opmt_bulanan_skp setelah insert")
            sys.exit(1)
        print(f"      id_opmt_bulanan_skp = {id_bulanan}")

        # 07-12. Buat target + turunan
        if not buat_target_bulanan(client, id_bulanan, target_skp_1, target_skp_2):
            sys.exit(1)

    # 13. Mapping get_target_bulan
    tanggal_first = f"{args.tahun}-{args.bulan:02d}-01"
    print(f"\n[13] Get target bulan ({tanggal_first}) → mapping...")
    targets = client.get_target_bulan(tanggal_first)

    # Fallback: bulanan header ada tapi target kosong (dari run sebelumnya yg gagal)
    if not targets and id_bulanan:
        print("      Target kosong — membuat target entries...")
        if not buat_target_bulanan(client, id_bulanan, target_skp_1, target_skp_2):
            sys.exit(1)
        targets = client.get_target_bulan(tanggal_first)

    if not targets:
        print("[ERROR] get_target_bulan kosong")
        sys.exit(1)
    harian_map = build_harian_mapping(targets)
    for k in ("1.a", "1.b", "1.c", "2.a", "2.b"):
        info = harian_map.get(k)
        if info:
            print(f"      {k}: id_harian={info['id_harian']}, target_skp={info['id_opmt_target_skp']}")
        else:
            print(f"      {k}: TIDAK ADA — mapping gagal")


    # 14. Build payload harian
    print("\n[14] Generate tanggal & build payload...")
    payloads = []
    for e in template:
        tgl = generate_tanggal(args.tahun, args.bulan, e["minggu"], e["hari"])
        kode = e["kode"]
        info = harian_map.get(kode)
        if not info:
            print(f"      SKIP {e['kegiatan_harian_skp']} (tidak ada mapping)")
            continue
        payloads.append({
            "tanggal": tgl,
            "id_opmt_realisasi_harian_skp": "",
            "kegiatan_harian_skp": e["kegiatan_harian_skp"],
            "kuantitas": e["kuantitas"],
            "satuan_kuantitas": e.get("satuan_kuantitas", "127"),
            "id_opmt_target_bulanan_skp": info["id_harian"],
            "id_opmt_target_skp": info["id_opmt_target_skp"],
        })
    print(f"      Total payload: {len(payloads)}")

    # 15. Insert harian
    print("\n[15] Insert SKP Harian...")
    ok_count = 0
    fail_count = 0
    for i, p in enumerate(payloads, 1):
        if client.insert_harian(p):
            ok_count += 1
        else:
            fail_count += 1
            print(f"      [{i}] GAGAL: {p['tanggal']} {p['kegiatan_harian_skp']}")
    print(f"      Sukses: {ok_count}, Gagal: {fail_count}")

    # 16. READ list
    print("\n[16] READ list SKP Harian...")
    hp = client.get_list_harian(args.bulan, args.tahun)
    print_harian(hp)

    print("\n" + "=" * 60)
    print("SELESAI")
    print("=" * 60)


if __name__ == "__main__":
    main()
