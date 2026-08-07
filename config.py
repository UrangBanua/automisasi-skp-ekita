"""
Konfigurasi Automasi SKP Harian - Ekita BKD HST
"""
import os
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://ekita.hstkab.go.id"

# Credentials
USERNAME = os.getenv("EKITA_USERNAME", "")
PASSWORD = os.getenv("EKITA_PASSWORD", "")

# Endpoints
ENDPOINTS = {
    "login":              "/c_main/validasi",
    "tahunan_ajax":       "/c_tahunan_skp/ajax_list",
    "tahunan_target_ajax":"/c_tahunan_skp/ajax_list_target",
    "bulanan_ajax":       "/c_bulanan_skp/ajax_list",
    "aksi_bulanan":       "/c_user/aksi_bulanan_skp",
    "aksi_target_bulanan":"/c_user/aksi_target_bulanan_skp",
    "target_bulanan_page":"/c_user/target_bulanan_skp",       # GET /<id>
    "aksi_turunan":       "/c_user/aksi_turunan_skp",
    "get_target_bulan":   "/c_user/get_target_bulan",
    "aksi_harian":        "/c_user/aksi_harian_skp",
    "harian_ajax":        "/c_harian_skp/ajax",
}

# DataTable default params (URL-encoded)
DATATABLE_PARAMS = (
    "draw=1"
    "&columns%5B0%5D%5Bdata%5D=0&columns%5B0%5D%5Bname%5D=&columns%5B0%5D%5Bsearchable%5D=true&columns%5B0%5D%5Borderable%5D=false&columns%5B0%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B0%5D%5Bsearch%5D%5Bregex%5D=false"
    "&columns%5B1%5D%5Bdata%5D=1&columns%5B1%5D%5Bname%5D=&columns%5B1%5D%5Bsearchable%5D=true&columns%5B1%5D%5Borderable%5D=true&columns%5B1%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B1%5D%5Bsearch%5D%5Bregex%5D=false"
    "&columns%5B2%5D%5Bdata%5D=2&columns%5B2%5D%5Bname%5D=&columns%5B2%5D%5Bsearchable%5D=true&columns%5B2%5D%5Borderable%5D=false&columns%5B2%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B2%5D%5Bsearch%5D%5Bregex%5D=false"
    "&columns%5B3%5D%5Bdata%5D=3&columns%5B3%5D%5Bname%5D=&columns%5B3%5D%5Bsearchable%5D=true&columns%5B3%5D%5Borderable%5D=false&columns%5B3%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B3%5D%5Bsearch%5D%5Bregex%5D=false"
    "&columns%5B4%5D%5Bdata%5D=4&columns%5B4%5D%5Bname%5D=&columns%5B4%5D%5Bsearchable%5D=true&columns%5B4%5D%5Borderable%5D=false&columns%5B4%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B4%5D%5Bsearch%5D%5Bregex%5D=false"
    "&columns%5B5%5D%5Bdata%5D=5&columns%5B5%5D%5Bname%5D=&columns%5B5%5D%5Bsearchable%5D=true&columns%5B5%5D%5Borderable%5D=false&columns%5B5%5D%5Bsearch%5D%5Bvalue%5D=&columns%5B5%5D%5Bsearch%5D%5Bregex%5D=false"
    "&start=0&length=12&search%5Bvalue%5D=&search%5Bregex%5D=false"
)


# Nama bulan (untuk matching di ajax_list)
BULAN_NAMA = {
    1: "JANUARI", 2: "FEBRUARI", 3: "MARET", 4: "APRIL",
    5: "MEI", 6: "JUNI", 7: "JULI", 8: "AGUSTUS",
    9: "SEPTEMBER", 10: "OKTOBER", 11: "NOVEMBER", 12: "DESEMBER",
}

# Hari kerja mapping
HARI_KERJA = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat"]
