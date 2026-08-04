"""
API Client untuk Ekita BKD HST
"""
import re
import json
import requests
from config import BASE_URL, ENDPOINTS, DATATABLE_PARAMS

HEADERS = {
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "en-GB,en;q=0.9",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "Origin": BASE_URL,
    "Referer": f"{BASE_URL}/",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36",
    "X-Requested-With": "XMLHttpRequest",
}


class EkitaClient:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.ci_session = None

    # ── helpers ──────────────────────────────────────────────

    def _url(self, key):
        return f"{BASE_URL}{ENDPOINTS[key]}"

    def _post(self, key, data=None, raw=None):
        """POST with form-encoded or raw JSON body."""
        url = self._url(key)
        if raw is not None:
            resp = self.session.post(url, data=raw, headers={"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"})
        elif data is not None:
            resp = self.session.post(url, json=data)
        else:
            resp = self.session.post(url)
        return resp

    def _get(self, key, path=""):
        url = f"{self._url(key)}{path}"
        return self.session.get(url)

    def _update_cookie(self, resp):
        for cookie in resp.cookies:
            if cookie.name == "ci_session":
                self.ci_session = cookie.value
                self.session.cookies.set("ci_session", cookie.value, domain="ekita.hstkab.go.id", path="/")

    # ── 01. Login ────────────────────────────────────────────

    def login(self, username, password):
        # Dapatkan initial session cookie dulu (GET /)
        self.session.get(BASE_URL)
        resp = self.session.post(
            self._url("login"),
            data={"username": username, "password": password},
        )
        self._update_cookie(resp)
        return self.ci_session is not None

    # ── 02. Get id_tahunan ───────────────────────────────────

    def get_id_tahunan(self, tahun):
        """GET /c_tahunan_skp/ajax_list → extract id_tahunan."""
        resp = self._post("tahunan_ajax", raw=f"{DATATABLE_PARAMS}&status={tahun}")
        try:
            data = resp.json()
            rows = data.get("data", [])
            if rows:
                # Gabungkan seluruh kolom HTML — hindari salah index kolom
                row_html = "".join(str(col) for col in rows[0])
                match = re.search(r"target_tahunan_skp\((\d+)\)", row_html)
                if match:
                    return match.group(1)
        except (json.JSONDecodeError, KeyError, IndexError):
            pass
        return None

    # ── 03. Get id_opmt_target_skp ───────────────────────────

    def get_target_skp_ids(self, tahun, id_tahunan):
        """GET /c_tahunan_skp/ajax_list_target → extract [id1, id2]."""
        resp = self._post("tahunan_target_ajax",
                          raw=f"{DATATABLE_PARAMS}&status={tahun}&id={id_tahunan}")
        try:
            data = resp.json()
            rows = data.get("data", [])
            ids = []
            for row in rows:
                # Gabungkan seluruh kolom — hindari salah index
                row_html = "".join(str(col) for col in row)
                match = re.search(r"ubah_target_tahunan_skp\((\d+)\)", row_html)
                if match:
                    ids.append(match.group(1))
            return ids  # [238317, 238318]
        except (json.JSONDecodeError, KeyError, IndexError):
            pass
        return []

    # ── 04. Cek list target bulanan ─────────────────────────

    def cek_bulanan(self, tahun, nama_bulan):
        """GET /c_bulanan_skp/ajax_list → cari bulan, return id_opmt_bulanan_skp atau None."""
        resp = self._post("bulanan_ajax", raw=f"{DATATABLE_PARAMS}&status={tahun}")
        try:
            data = resp.json()
            rows = data.get("data", [])
            for row in rows:
                row_html = "".join(str(col) for col in row)
                if nama_bulan.upper() in row_html.upper():
                    match = re.search(r"hapus_bulanan_skp\((\d+)\)", row_html)
                    if match:
                        return match.group(1)
        except (json.JSONDecodeError, KeyError, IndexError):
            pass
        return None

    # ── 05. INSERT bulanan ───────────────────────────────────

    def insert_bulanan(self, tahun, bulan):
        """POST /c_user/aksi_bulanan_skp → create bulanan header."""
        resp = self._post("aksi_bulanan", data={
            "id_opmt_bulanan_skp": "",
            "tahun": str(tahun),
            "bulan": str(bulan),
        })
        return resp.status_code == 200

    # ── 06. INSERT target bulanan ────────────────────────────

    def insert_target_bulanan(self, id_opmt_bulanan_skp, id_opmt_target_skp, target_waktu="30"):
        """POST /c_user/aksi_target_bulanan_skp."""
        resp = self._post("aksi_target_bulanan", data={
            "id_opmt_target_bulanan_skp": "",
            "id_opmt_bulanan_skp": str(id_opmt_bulanan_skp),
            "id_opmt_target_skp": str(id_opmt_target_skp),
            "turunan": "ya",
            "target_waktu": str(target_waktu),
        })
        return resp.status_code == 200

    # ── 07. Get id_opmt_target_bulanan_skp ───────────────────

    def get_target_bulanan_ids(self, id_opmt_bulanan_skp):
        """GET /c_user/target_bulanan_skp/<id> → extract [id1, id2]."""
        resp = self._get("target_bulanan_page", path=f"/{id_opmt_bulanan_skp}")
        # Parse HTML: cari semua onclick="ubah_target_bulanan_skp('ID', ...)"
        ids = re.findall(r"ubah_target_bulanan_skp\('(\d+)'", resp.text)
        return ids  # [1226899, 1226910]

    # ── 08. INSERT turunan ───────────────────────────────────

    def insert_turunan(self, id_opmt_target_bulanan_skp, turunan_def):
        """POST /c_user/aksi_turunan_skp."""
        resp = self._post("aksi_turunan", data={
            "id_opmt_turunan_skp": "",
            "id_opmt_target_bulanan_skp": str(id_opmt_target_bulanan_skp),
            "kegiatan_turunan": turunan_def["kegiatan_turunan"],
            "target_kuantitas": turunan_def["target_kuantitas"],
            "satuan_kuantitas": turunan_def["satuan_kuantitas"],
            "kualitas": turunan_def["kualitas"],
            "target_waktu": turunan_def["target_waktu"],
            "biaya": turunan_def.get("biaya", ""),
        })
        return resp.status_code == 200

    # ── 09. Get target bulan (mapping) ───────────────────────

    def get_target_bulan(self, tanggal):
        """POST /c_user/get_target_bulan → JSON array."""
        resp = self._post("get_target_bulan", raw=f"tanggal={tanggal}")
        try:
            return resp.json()
        except json.JSONDecodeError:
            return []

    # ── 10. INSERT SKP Harian ────────────────────────────────

    def insert_harian(self, entry):
        """POST /c_user/aksi_harian_skp."""
        data = {
            "tanggal": entry["tanggal"],
            "id_opmt_realisasi_harian_skp": "",
            "kegiatan_harian_skp": entry["kegiatan_harian_skp"],
            "satuan_kuantitas": entry.get("satuan_kuantitas", "127"),
            "id_opmt_target_bulanan_skp": entry["id_opmt_target_bulanan_skp"],
            "id_opmt_target_skp": entry["id_opmt_target_skp"],
        }
        if "proses" in entry:
            data["proses"] = entry["proses"]
        else:
            data["kuantitas"] = entry["kuantitas"]
        resp = self._post("aksi_harian", data=data)
        return resp.status_code == 200

    # ── 11. READ list SKP Harian ─────────────────────────────

    def get_list_harian(self, bulan, tahun):
        """POST /c_harian_skp/ajax → HTML table."""
        resp = self._post("harian_ajax", raw=f"tanggal=&bulan={bulan}&tahun={tahun}")
        return resp.text
