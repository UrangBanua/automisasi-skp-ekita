# Automisasi SKP - Ekita Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Membuat sistem otomatisasi untuk input SKP (Sasaran Kinerja Pegawai) ke sistem Ekita, menggantikan input manual via Postman.

**Architecture:** Python script dengan requests library untuk HTTP calls, menggunakan session management untuk mempertahankan ci_session cookie. Modular design dengan file terpisah untuk config, API client, dan main logic.

**Tech Stack:** Python 3.x, requests, python-dotenv

---

## Context & Assumptions

- User saat ini input data SKP manual via Postman
- Sistem Ekita menggunakan CodeIgniter dengan session-based authentication (ci_session cookie)
- Endpoint-endpoint yang diperlukan sudah diketahui
- Data SKP memiliki struktur hierarki: Bulanan → Harian dengan sub-kategori [1, 1.a, 1.b, 1.c, 2, 2.a, 2.b]

---

## Endpoint Flow

```
1. Login → dapatkan ci_session cookie
2. Cek List SKP Bulanan → apakah sudah ada?
3. Jika belum → Tambah SKP Bulanan
4. Input List SKP [1, 1.a, 1.b, 1.c, 2, 2.a, 2.b]
5. Get id Target Bulanan dari list di atas
6. Input SKP Harian berdasarkan id yang didapat
```

---

## Files to Create

```
workspace/projects/automisasi-skp-ekita/
├── .env                    # Credentials (username, password)
├── .env.example            # Template .env (tanpa nilai sensitif)
├── .gitignore              # Ignore .env dan file sensitif
├── requirements.txt        # Dependencies
├── config.py               # Konfigurasi dari .env
├── api_client.py           # Class untuk semua API calls
├── skp_manager.py          # Business logic untuk SKP operations
├── main.py                 # Entry point / CLI
└── README.md               # Dokumentasi penggunaan
```

---

## Task List

### Task 1: Setup Project Structure

**Objective:** Membuat struktur folder dan file dasar project

**Files:**
- Create: `workspace/projects/automisasi-skp-ekita/.gitignore`
- Create: `workspace/projects/automisasi-skp-ekita/requirements.txt`
- Create: `workspace/projects/automisasi-skp-ekita/.env.example`

**Step 1: Buat .gitignore**

```gitignore
# Environment
.env
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
ENV/

# IDE
.vscode/
.idea/

# Logs
*.log
```

**Step 2: Buat requirements.txt**

```txt
requests>=2.31.0
python-dotenv>=1.0.0
```

**Step 3: Buat .env.example**

```env
# Ekita Credentials
EKITA_USERNAME=your_username_here
EKITA_PASSWORD=your_password_here

# Ekita Base URL (sesuaikan dengan server Anda)
EKITA_BASE_URL=https://ekita.hstkab.go.id
```

**Step 4: Buat .env dengan placeholder**

```env
# Ekita Credentials
EKITA_USERNAME=
EKITA_PASSWORD=

# Ekita Base URL
EKITA_BASE_URL=
```

---

### Task 2: Create Config Module

**Objective:** Module untuk membaca konfigurasi dari .env

**Files:**
- Create: `workspace/projects/automisasi-skp-ekita/config.py`

**Step 1: Buat config.py**

```python
"""
Configuration module untuk Automisasi SKP - Ekita
Membaca konfigurasi dari environment variables / .env file
"""
import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()


class Config:
    """Konfigurasi aplikasi dari environment variables"""
    
    # Credentials
    USERNAME: str = os.getenv("EKITA_USERNAME", "")
    PASSWORD: str = os.getenv("EKITA_PASSWORD", "")
    
    # Server
    BASE_URL: str = os.getenv("EKITA_BASE_URL", "")
    
    # Endpoints (akan disesuaikan dengan endpoint sebenarnya)
    ENDPOINTS = {
        "login": "/auth/login",
        "list_skp_bulanan": "/skp/bulanan/list",
        "tambah_skp_bulanan": "/skp/bulanan/tambah",
        "input_list_skp": "/skp/input-list",
        "get_id_target": "/skp/target/id",
        "input_skp_harian": "/skp/harian/input",
    }
    
    @classmethod
    def validate(cls) -> bool:
        """Validasi konfigurasi wajib"""
        required = ["USERNAME", "PASSWORD", "BASE_URL"]
        missing = [f for f in required if not getattr(cls, f)]
        
        if missing:
            raise ValueError(f"Missing required config: {', '.join(missing)}")
        return True
    
    @classmethod
    def get_url(cls, endpoint_name: str) -> str:
        """Get full URL untuk endpoint tertentu"""
        if endpoint_name not in cls.ENDPOINTS:
            raise ValueError(f"Unknown endpoint: {endpoint_name}")
        return f"{cls.BASE_URL.rstrip('/')}{cls.ENDPOINTS[endpoint_name]}"
```

---

### Task 3: Create API Client Module

**Objective:** Class untuk menangani semua HTTP requests ke API Ekita

**Files:**
- Create: `workspace/projects/automisasi-skp-ekita/api_client.py`

**Step 1: Buat api_client.py**

```python
"""
API Client untuk Ekita
Menangani semua HTTP requests dengan session management
"""
import requests
from typing import Optional, Dict, Any
from config import Config


class EkitaClient:
    """
    Client untuk berinteraksi dengan API Ekita
    Menggunakan requests.Session untuk mempertahankan cookies
    """
    
    def __init__(self):
        self.session: requests.Session = requests.Session()
        self.ci_session: Optional[str] = None
        self.is_logged_in: bool = False
        
    def login(self) -> Dict[str, Any]:
        """
        Login ke sistem Ekita dan mendapatkan ci_session
        
        Returns:
            Response dari login endpoint
        """
        url = Config.get_url("login")
        payload = {
            "username": Config.USERNAME,
            "password": Config.PASSWORD,
        }
        
        response = self.session.post(url, data=payload)
        response.raise_for_status()
        
        # Extract ci_session dari cookies
        self.ci_session = self.session.cookies.get("ci_session", "")
        
        if self.ci_session:
            self.is_logged_in = True
            
        return response.json() if response.text else {"status": "success"}
    
    def get_list_skp_bulanan(self) -> Dict[str, Any]:
        """
        Cek list SKP Bulanan yang sudah ada
        
        Returns:
            List SKP Bulanan
        """
        if not self.is_logged_in:
            raise RuntimeError("Not logged in. Call login() first.")
            
        url = Config.get_url("list_skp_bulanan")
        response = self.session.get(url)
        response.raise_for_status()
        
        return response.json()
    
    def tambah_skp_bulanan(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Tambah SKP Bulanan baru
        
        Args:
            data: Data SKP Bulanan yang akan ditambahkan
            
        Returns:
            Response dari endpoint
        """
        if not self.is_logged_in:
            raise RuntimeError("Not logged in. Call login() first.")
            
        url = Config.get_url("tambah_skp_bulanan")
        response = self.session.post(url, json=data)
        response.raise_for_status()
        
        return response.json() if response.text else {"status": "success"}
    
    def input_list_skp(self, skp_list: list) -> Dict[str, Any]:
        """
        Input List SKP [1, 1.a, 1.b, 1.c, 2, 2.a, 2.b]
        
        Args:
            skp_list: List data SKP yang akan diinput
            
        Returns:
            Response dari endpoint
        """
        if not self.is_logged_in:
            raise RuntimeError("Not logged in. Call login() first.")
            
        url = Config.get_url("input_list_skp")
        response = self.session.post(url, json={"skp_list": skp_list})
        response.raise_for_status()
        
        return response.json() if response.text else {"status": "success"}
    
    def get_id_target_bulanan(self, skp_items: list) -> Dict[str, Any]:
        """
        Get id Target Bulanan dari list SKP
        
        Args:
            skp_items: List item SKP [1, 1.a, 1.b, 1.c, 2, 2.a, 2.b]
            
        Returns:
            Response berisi id target
        """
        if not self.is_logged_in:
            raise RuntimeError("Not logged in. Call login() first.")
            
        url = Config.get_url("get_id_target")
        response = self.session.post(url, json={"items": skp_items})
        response.raise_for_status()
        
        return response.json()
    
    def input_skp_harian(self, target_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Input SKP Harian berdasarkan id target
        
        Args:
            target_id: ID target bulanan
            data: Data SKP Harian
            
        Returns:
            Response dari endpoint
        """
        if not self.is_logged_in:
            raise RuntimeError("Not logged in. Call login() first.")
            
        url = Config.get_url("input_skp_harian")
        payload = {"target_id": target_id, **data}
        response = self.session.post(url, json=payload)
        response.raise_for_status()
        
        return response.json() if response.text else {"status": "success"}
    
    def close(self):
        """Tutup session"""
        self.session.close()
        self.is_logged_in = False
        
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
```

---

### Task 4: Create SKP Manager Module

**Objective:** Business logic untuk operasi SKP

**Files:**
- Create: `workspace/projects/automisasi-skp-ekita/skp_manager.py`

**Step 1: Buat skp_manager.py**

```python
"""
SKP Manager - Business Logic untuk operasi SKP
"""
from typing import Dict, Any, List, Optional
from api_client import EkitaClient


class SKPManager:
    """
    Manager untuk mengelola operasi SKP
    Menggunakan EkitaClient untuk komunikasi API
    """
    
    # Definisi struktur SKP
    SKP_STRUCTURE = [
        "1", "1.a", "1.b", "1.c",
        "2", "2.a", "2.b"
    ]
    
    def __init__(self):
        self.client: Optional[EkitaClient] = None
        
    def connect(self) -> bool:
        """
        Login ke sistem Ekita
        
        Returns:
            True jika berhasil login
        """
        self.client = EkitaClient()
        try:
            result = self.client.login()
            print(f"[OK] Login berhasil, ci_session: {self.client.ci_session[:20]}...")
            return True
        except Exception as e:
            print(f"[ERROR] Login gagal: {e}")
            return False
    
    def disconnect(self):
        """Logout dan tutup koneksi"""
        if self.client:
            self.client.close()
            self.client = None
    
    def cek_skp_bulanan(self) -> Dict[str, Any]:
        """
        Cek apakah SKP Bulanan sudah ada
        
        Returns:
            Data SKP Bulanan yang ada
        """
        if not self.client:
            raise RuntimeError("Not connected. Call connect() first.")
            
        result = self.client.get_list_skp_bulanan()
        print(f"[OK] SKP Bulanan ditemukan: {len(result.get('data', []))} item")
        return result
    
    def buat_skp_bulanan(self, bulan: int, tahun: int) -> Dict[str, Any]:
        """
        Buat SKP Bulanan baru jika belum ada
        
        Args:
            bulan: Bulan (1-12)
            tahun: Tahun
            
        Returns:
            Response dari endpoint
        """
        if not self.client:
            raise RuntimeError("Not connected. Call connect() first.")
            
        data = {
            "bulan": bulan,
            "tahun": tahun,
        }
        result = self.client.tambah_skp_bulanan(data)
        print(f"[OK] SKP Bulanan dibuat untuk {bulan}/{tahun}")
        return result
    
    def input_semua_skp(self, skp_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Input semua SKP [1, 1.a, 1.b, 1.c, 2, 2.a, 2.b]
        
        Args:
            skp_data: Data untuk setiap item SKP
            
        Returns:
            Response dari endpoint
        """
        if not self.client:
            raise RuntimeError("Not connected. Call connect() first.")
            
        skp_list = []
        for item in self.SKP_STRUCTURE:
            if item in skp_data:
                skp_list.append({
                    "kode": item,
                    "data": skp_data[item]
                })
                
        result = self.client.input_list_skp(skp_list)
        print(f"[OK] {len(skp_list)} item SKP berhasil diinput")
        return result
    
    def get_target_ids(self) -> Dict[str, str]:
        """
        Get ID target untuk semua item SKP
        
        Returns:
            Dict mapping kode SKP ke target ID
        """
        if not self.client:
            raise RuntimeError("Not connected. Call connect() first.")
            
        result = self.client.get_id_target_bulanan(self.SKP_STRUCTURE)
        
        # Parse hasil jadi mapping
        target_ids = {}
        for item in result.get("data", []):
            target_ids[item.get("kode")] = item.get("id")
            
        print(f"[OK] Dapatkan {len(target_ids)} target ID")
        return target_ids
    
    def input_skp_harian(self, target_id: str, tanggal: str, aktivitas: str, kuantitas: int = 1) -> Dict[str, Any]:
        """
        Input SKP Harian
        
        Args:
            target_id: ID target bulanan
            tanggal: Tanggal (format: YYYY-MM-DD)
            aktivitas: Deskripsi aktivitas
            kuantitas: Jumlah
            
        Returns:
            Response dari endpoint
        """
        if not self.client:
            raise RuntimeError("Not connected. Call connect() first.")
            
        data = {
            "tanggal": tanggal,
            "aktivitas": aktivitas,
            "kuantitas": kuantitas,
        }
        result = self.client.input_skp_harian(target_id, data)
        print(f"[OK] SKP Harian diinput untuk tanggal {tanggal}")
        return result
    
    def run_full_automation(self, bulan: int, tahun: int, skp_data: Dict[str, Any], harian_data: List[Dict[str, Any]]):
        """
        Jalankan automasi lengkap
        
        Args:
            bulan: Bulan (1-12)
            tahun: Tahun
            skp_data: Data SKP bulanan
            harian_data: List data SKP harian
        """
        print("\n=== Memulai Automisasi SKP - Ekita ===\n")
        
        # Step 1: Login
        print("[1/6] Login ke sistem...")
        if not self.connect():
            print("[ABORT] Gagal login")
            return
        
        # Step 2: Cek SKP Bulanan
        print("\n[2/6] Cek SKP Bulanan...")
        existing = self.cek_skp_bulanan()
        
        # Step 3: Buat SKP Bulanan jika belum ada
        print("\n[3/6] Buat SKP Bulanan jika belum ada...")
        if not existing.get("data"):
            self.buat_skp_bulanan(bulan, tahun)
        else:
            print("[SKIP] SKP Bulanan sudah ada")
        
        # Step 4: Input List SKP
        print("\n[4/6] Input List SKP...")
        self.input_semua_skp(skp_data)
        
        # Step 5: Get Target IDs
        print("\n[5/6] Get Target IDs...")
        target_ids = self.get_target_ids()
        
        # Step 6: Input SKP Harian
        print("\n[6/6] Input SKP Harian...")
        for harian in harian_data:
            kode = harian.get("kode")
            if kode in target_ids:
                self.input_skp_harian(
                    target_id=target_ids[kode],
                    tanggal=harian.get("tanggal"),
                    aktivitas=harian.get("aktivitas"),
                    kuantitas=harian.get("kuantitas", 1)
                )
        
        # Cleanup
        self.disconnect()
        print("\n=== Automisasi Selesai ===\n")
    
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
```

---

### Task 5: Create Main Entry Point

**Objective:** Entry point untuk menjalankan automasi

**Files:**
- Create: `workspace/projects/automisasi-skp-ekita/main.py`

**Step 1: Buat main.py**

```python
#!/usr/bin/env python3
"""
Main Entry Point untuk Automisasi SKP - Ekita

Usage:
    python main.py [--bulan BULAN] [--tahun TAHUN]
    
Example:
    python main.py --bulan 8 --tahun 2026
"""
import argparse
from datetime import datetime
from config import Config
from skp_manager import SKPManager


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Automisasi SKP - Ekita"
    )
    parser.add_argument(
        "--bulan",
        type=int,
        default=datetime.now().month,
        help="Bulan (1-12), default: bulan sekarang"
    )
    parser.add_argument(
        "--tahun",
        type=int,
        default=datetime.now().year,
        help="Tahun, default: tahun sekarang"
    )
    return parser.parse_args()


def main():
    """Main function"""
    args = parse_args()
    
    # Validasi konfigurasi
    try:
        Config.validate()
    except ValueError as e:
        print(f"[ERROR] Konfigurasi tidak valid: {e}")
        print("\nPastikan file .env sudah diisi dengan benar:")
        print("  - EKITA_USERNAME")
        print("  - EKITA_PASSWORD")
        print("  - EKITA_BASE_URL")
        return 1
    
    print(f"Automisasi SKP - Ekita")
    print(f"Bulan: {args.bulan}, Tahun: {args.tahun}")
    print(f"Base URL: {Config.BASE_URL}")
    
    # Contoh data SKP (sesuaikan dengan kebutuhan)
    skp_data = {
        "1": {"nama": "Sasaran Kinerja 1", "target": 100},
        "1.a": {"nama": "Sub Sasaran 1.a", "target": 25},
        "1.b": {"nama": "Sub Sasaran 1.b", "target": 25},
        "1.c": {"nama": "Sub Sasaran 1.c", "target": 50},
        "2": {"nama": "Sasaran Kinerja 2", "target": 100},
        "2.a": {"nama": "Sub Sasaran 2.a", "target": 50},
        "2.b": {"nama": "Sub Sasaran 2.b", "target": 50},
    }
    
    # Contoh data SKP Harian (sesuaikan dengan kebutuhan)
    harian_data = [
        {"kode": "1.a", "tanggal": "2026-08-01", "aktivitas": "Aktivitas 1.a", "kuantitas": 1},
        {"kode": "1.b", "tanggal": "2026-08-02", "aktivitas": "Aktivitas 1.b", "kuantitas": 1},
        # Tambahkan data lainnya...
    ]
    
    # Jalankan automasi
    with SKPManager() as manager:
        manager.run_full_automation(
            bulan=args.bulan,
            tahun=args.tahun,
            skp_data=skp_data,
            harian_data=harian_data
        )
    
    return 0


if __name__ == "__main__":
    exit(main())
```

---

### Task 6: Create README Documentation

**Objective:** Dokumentasi penggunaan project

**Files:**
- Create: `workspace/projects/automisasi-skp-ekita/README.md`

**Step 1: Buat README.md**

```markdown
# Automisasi SKP - Ekita

Sistem otomatisasi untuk input SKP (Sasaran Kinerja Pegawai) ke sistem Ekita.

## Fitur

- Login otomatis dengan session management (ci_session)
- Cek dan buat SKP Bulanan
- Input list SKP [1, 1.a, 1.b, 1.c, 2, 2.a, 2.b]
- Get Target ID untuk SKP Harian
- Input SKP Harian secara otomatis

## Setup

### 1. Clone / Copy Project

```bash
cd workspace/projects/automisasi-skp-ekita
```

### 2. Buat Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# atau
venv\Scripts\activate  # Windows
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Konfigurasi .env

Copy `.env.example` ke `.env` dan isi credentials:

```bash
cp .env.example .env
```

Edit `.env`:

```env
EKITA_USERNAME=username_anda
EKITA_PASSWORD=password_anda
EKITA_BASE_URL=https://ekita.example.com
```

## Penggunaan

### Jalankan Automasi

```bash
python main.py
```

### Dengan Parameter Bulan/Tahun

```bash
python main.py --bulan 8 --tahun 2026
```

## Struktur Project

```
automisasi-skp-ekita/
├── .env                # Credentials (JANGAN COMMIT)
├── .env.example        # Template .env
├── .gitignore          # Ignore file
├── requirements.txt    # Dependencies
├── config.py           # Konfigurasi
├── api_client.py       # API Client
├── skp_manager.py      # Business Logic
├── main.py             # Entry Point
└── README.md           # Dokumentasi
```

## Customisasi Data SKP

Edit `main.py` untuk menyesuaikan data SKP:

```python
skp_data = {
    "1": {"nama": "Sasaran Anda", "target": 100},
    # ...
}

harian_data = [
    {"kode": "1.a", "tanggal": "2026-08-01", "aktivitas": "Aktivitas", "kuantitas": 1},
    # ...
]
```

## Endpoint Reference

| No | Endpoint | Fungsi |
|----|----------|--------|
| 1 | `/auth/login` | Login dan dapat ci_session |
| 2 | `/skp/bulanan/list` | Cek SKP Bulanan |
| 3 | `/skp/bulanan/tambah` | Tambah SKP Bulanan |
| 4 | `/skp/input-list` | Input List SKP |
| 5 | `/skp/target/id` | Get Target ID |
| 6 | `/skp/harian/input` | Input SKP Harian |

**Note:** Sesuaikan endpoint di `config.py` dengan endpoint sebenarnya.

## Troubleshooting

### Login Gagal

- Periksa username/password di `.env`
- Pastikan `EKITA_BASE_URL` benar

### Session Expired

- Jalankan ulang script untuk mendapatkan session baru

### Data Tidak Masuk

- Periksa response dari API
- Sesuaikan format data dengan yang dibutuhkan API
```

---

## Testing Strategy

### Manual Testing Steps

1. **Test Login**
   ```bash
   python -c "from api_client import EkitaClient; c = EkitaClient(); c.login(); print(c.ci_session)"
   ```

2. **Test Cek SKP Bulanan**
   ```bash
   python -c "from api_client import EkitaClient; c = EkitaClient(); c.login(); print(c.get_list_skp_bulanan())"
   ```

3. **Test Full Automation**
   ```bash
   python main.py --bulan 8 --tahun 2026
   ```

### Unit Tests (Optional - Task 7)

Jika diperlukan, buat unit tests di `tests/` folder menggunakan `pytest`.

---

## Risks & Considerations

1. **Endpoint URL**: Endpoint di `config.py` adalah placeholder. Perlu disesuaikan dengan endpoint sebenarnya dari Postman collection.

2. **Request Payload**: Struktur data request perlu disesuaikan dengan format yang dibutuhkan API Ekita.

3. **Session Expiry**: ci_session mungkin expire setelah beberapa waktu. Perlu handling untuk re-login.

4. **Rate Limiting**: API mungkin memiliki rate limiting. Tambahkan delay jika diperlukan.

5. **Error Handling**: Perlu enhancement untuk handling berbagai error case.

---

## Open Questions

1. Apakah ada endpoint untuk logout?
2. Berapa lama ci_session valid?
3. Format response dari setiap endpoint?
4. Apakah ada validasi khusus untuk data SKP?
5. Bagaimana cara mendapatkan data SKP yang akan diinput (apakah dari file CSV/Excel, atau hardcoded)?

---

## Next Steps After Plan

1. **Gather Endpoint Details**: Dapatkan detail endpoint dari Postman collection
2. **Test Login**: Test login endpoint terlebih dahulu
3. **Iterate on Payloads**: Sesuaikan payload berdasarkan response API
4. **Add Error Handling**: Tambahkan error handling yang lebih robust
5. **Add Data Source**: Jika data dari CSV/Excel, buat parser untuk membaca file
