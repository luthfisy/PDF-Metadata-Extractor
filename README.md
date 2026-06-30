# PDF Metadata Extractor

![PDF Metadata Extractor](https://raw.githubusercontent.com/luthfisy/PDF-Metadata-Extractor/master/pdf-metadata-extractor.png)

**PDF File Renamer — Rename PDF files based on metadata title**  
Rename file PDF otomatis berdasarkan judul dari CrossRef API

> ⚠️ **PERINGATAN:** Tidak ada konfirmasi, file langsung di-rename. Gunakan mode preview dulu sebelum mengaktifkan rename.

Dikembangkan oleh **[SASHINDO PROJECT](https://sashindo.web.id)**

---

## Fitur

- Konek langsung ke **Google Drive** — baca semua PDF dari folder yang ditentukan
- Ekstrak **DOI** dari metadata PDF maupun teks konten (3 halaman pertama)
- Lookup otomatis ke **CrossRef API** untuk judul resmi, penulis, jurnal, tahun, volume, publisher
- **Rename file** di Google Drive berdasarkan judul terbaik yang ditemukan
- Ekspor seluruh hasil ke **Google Sheets** (timestamp, status, metadata lengkap, link file)
- **Mode preview** — lihat hasil tanpa rename apapun
- Sanitasi nama file otomatis: hapus karakter tidak valid, batasi panjang

---

## Prioritas Penamaan

```
1. Judul dari CrossRef API  (paling akurat — dari database resmi)
2. Judul dari metadata PDF internal
3. Nama file lama dipertahankan  (dicatat sebagai skip)
```

---

## Requirements

- Python 3.8+
- Library Python (install via pip):

```bash
pip install PyPDF2 gspread google-auth-oauthlib google-api-python-client requests
```

- File `credentials.json` dari Google Cloud Console  
  *(Drive API + Sheets API harus diaktifkan)*

---

## Setup Google Cloud

1. Buka [Google Cloud Console](https://console.cloud.google.com)
2. Buat project baru
3. Aktifkan **Google Drive API** dan **Google Sheets API**
4. Buat **OAuth 2.0 Client ID** (tipe: Desktop app)
5. Download → simpan sebagai `credentials.json` di folder yang sama dengan script

---

## Konfigurasi

Edit bagian `# Konfigurasi` di awal script:

```python
DEFAULT_FOLDER_ID = 'ID_FOLDER_GOOGLE_DRIVE'   # folder berisi file PDF
SPREADSHEET_ID    = 'ID_SPREADSHEET_OUTPUT'     # atau None untuk buat spreadsheet baru
SPREADSHEET_NAME  = 'PDF Metadata Extractor'
SHEET_NAME        = 'PDF Metadata'

ENABLE_RENAME        = False   # True = rename aktif | False = preview saja
MAX_FILENAME_LENGTH  = 100
```

**Cara ambil Folder ID:**  
Buka folder di Google Drive → lihat URL:  
`drive.google.com/drive/folders/`**`FOLDER_ID_INI`**

---

## Cara Penggunaan

```bash
python pdf_metadata_extractor_enhanced.py
```

Pertama kali dijalankan, browser terbuka otomatis untuk autentikasi Google.  
Setelah izin diberikan, `token.json` dibuat — run berikutnya langsung jalan tanpa login ulang.

### Alur yang Disarankan

```
1. Set ENABLE_RENAME = False  →  jalankan script
2. Cek hasil preview di Google Sheets
3. Kalau sudah yakin, set ENABLE_RENAME = True  →  jalankan ulang
```

---

## Output Terminal

```
[1/47] download (12).pdf
  📝 Judul CrossRef: Deep Learning for Medical Image Analysis
  ✅ Renamed: Deep Learning for Medical Image Analysis.pdf

[2/47] paper_final_v2.pdf
  ⏭️  Skip: Tidak ada judul atau sama dengan nama file
```

---

## Output Google Sheets

| Kolom | Keterangan |
|---|---|
| No, Timestamp | Nomor urut dan waktu proses |
| Nama Folder | Nama folder Google Drive |
| Nama File Lama / Baru | Sebelum dan sesudah rename |
| Status Rename | CrossRef / PDF metadata / Skip / Error |
| DOI | DOI yang ditemukan di PDF |
| Judul, Penulis, Jurnal, Tahun | Data dari CrossRef API |
| Volume, Issue, Halaman, Publisher | Detail bibliografi |
| Judul & Penulis (PDF) | Metadata internal PDF |
| Jumlah Halaman, Ukuran | Info file |
| Link File | Link langsung ke Google Drive |

---

## File yang Diperlukan

```
project/
├── pdf_metadata_extractor_enhanced.py   ← script utama
├── credentials.json                      ← dari Google Cloud (jangan dipush!)
└── token.json                            ← dibuat otomatis setelah login pertama
```

> `credentials.json` dan `token.json` sudah di-exclude via `.gitignore` — tidak akan ikut ke repository.

---

## Lisensi

MIT License — bebas digunakan dan dimodifikasi.

---

*SASHINDO PROJECT — [sashindo.web.id](https://sashindo.web.id)*
