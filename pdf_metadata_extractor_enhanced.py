"""
============================================================
  PDF Metadata Extractor
  Developer: SASHINDO PROJECT
  Website  : sashindo.web.id
============================================================
PDF File Renamer - Rename PDF files based on metadata title
Rename file PDF otomatis berdasarkan judul dari CrossRef API
PERINGATAN: Tidak ada konfirmasi, langsung rename!
"""

import os
import io
import re
import json
import time
from datetime import datetime
from PyPDF2 import PdfReader
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
import gspread
import requests

# Konfigurasi
DEFAULT_FOLDER_ID = '17Gf3Kgi-pWB_Dn6aVAEtjNfpIZo0DrmE'  # ID folder Google Drive dengan file PDF

# OPSI 1: Gunakan Spreadsheet ID (spreadsheet yang sudah ada)
SPREADSHEET_ID = '1MCO2zCnmoG1JaVhmYXP0DpBqPthuAT47r9EXhV3E920'  # Isi dengan ID spreadsheet, atau None

# OPSI 2: Gunakan nama spreadsheet (jika SPREADSHEET_ID = None)
SPREADSHEET_NAME = 'PDF Metadata Extractor - Enhanced'
OUTPUT_FOLDER_ID = None

SHEET_NAME = 'PDF Metadata'  # Nama sheet/tab

# RENAME SETTINGS
ENABLE_RENAME = True  # Set False jika hanya ingin lihat preview tanpa rename
MAX_FILENAME_LENGTH = 100  # Maksimal panjang nama file (karakter)

# Scopes untuk Google API
SCOPES = [
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/spreadsheets'
]


class PDFRenamer:
    """Class untuk rename PDF files berdasarkan metadata"""

    def __init__(self, folder_id, sheet_name, spreadsheet_id=None, spreadsheet_name=None, output_folder_id=None):
        self.folder_id = folder_id
        self.spreadsheet_id = spreadsheet_id
        self.spreadsheet_name = spreadsheet_name
        self.output_folder_id = output_folder_id
        self.sheet_name = sheet_name
        self.drive_service = None
        self.sheets_client = None
        self.worksheet = None

    def authenticate(self):
        """Autentikasi dengan Google APIs"""
        print("🔐 Melakukan autentikasi...")

        creds = None
        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)

            with open('token.json', 'w') as token:
                token.write(creds.to_json())

        self.drive_service = build('drive', 'v3', credentials=creds)
        gc = gspread.authorize(creds)

        # Buka spreadsheet
        if self.spreadsheet_id:
            try:
                spreadsheet = gc.open_by_key(self.spreadsheet_id)
                print(f"✅ Spreadsheet dengan ID '{self.spreadsheet_id}' berhasil dibuka")
            except Exception as e:
                print(f"❌ Error: Tidak dapat membuka spreadsheet dengan ID '{self.spreadsheet_id}'")
                raise e
        else:
            try:
                spreadsheet = gc.open(self.spreadsheet_name)
                print(f"✅ Spreadsheet '{self.spreadsheet_name}' ditemukan")
            except gspread.SpreadsheetNotFound:
                spreadsheet = gc.create(self.spreadsheet_name)
                print(f"✅ Spreadsheet '{self.spreadsheet_name}' dibuat")

        # Buka atau buat worksheet
        try:
            self.worksheet = spreadsheet.worksheet(self.sheet_name)
            print(f"✅ Sheet '{self.sheet_name}' ditemukan")
        except gspread.WorksheetNotFound:
            self.worksheet = spreadsheet.add_worksheet(
                title=self.sheet_name,
                rows=1000,
                cols=25
            )
            print(f"✅ Sheet '{self.sheet_name}' dibuat")

        print("✅ Autentikasi berhasil!\n")

    def get_folder_name(self, folder_id):
        """Mendapatkan nama folder dari ID"""
        try:
            folder = self.drive_service.files().get(
                fileId=folder_id,
                fields='name'
            ).execute()
            return folder.get('name', 'Unknown Folder')
        except:
            return 'Unknown Folder'

    def get_pdf_files(self):
        """Mengambil daftar file PDF dari folder Google Drive"""
        print(f"📁 Mengambil daftar PDF dari folder...")

        query = f"'{self.folder_id}' in parents and mimeType='application/pdf' and trashed=false"

        results = self.drive_service.files().list(
            q=query,
            fields="files(id, name, parents, createdTime, modifiedTime, size, webViewLink)",
            pageSize=1000
        ).execute()

        files = results.get('files', [])
        print(f"✅ Ditemukan {len(files)} file PDF\n")

        return files

    def sanitize_filename(self, filename):
        """Membersihkan nama file dari karakter tidak valid"""
        # Hapus karakter yang tidak diperbolehkan di nama file
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '')

        # Hapus karakter kontrol
        filename = ''.join(char for char in filename if ord(char) >= 32)

        # Trim whitespace
        filename = filename.strip()

        # Ganti multiple spaces dengan single space
        filename = re.sub(r'\s+', ' ', filename)

        # Batasi panjang
        if len(filename) > MAX_FILENAME_LENGTH:
            filename = filename[:MAX_FILENAME_LENGTH].strip()

        return filename

    def extract_doi_from_pdf(self, reader):
        """Ekstrak DOI dari PDF"""
        doi = None

        # Cek metadata
        if reader.metadata:
            title = reader.metadata.get('/Title', '')
            if title and 'doi:' in title.lower():
                doi_match = re.search(r'10\.\d{4,}/[^\s]+', title)
                if doi_match:
                    return self.clean_doi(doi_match.group(0))

        # Cek teks 3 halaman pertama
        try:
            text = ""
            max_pages = min(3, len(reader.pages))

            for i in range(max_pages):
                page_text = reader.pages[i].extract_text()
                if page_text:
                    text += page_text + "\n"

            doi_patterns = [
                r'doi:\s*10\.\d{4,}/[^\s\]\)]+',
                r'DOI:\s*10\.\d{4,}/[^\s\]\)]+',
                r'https?://doi\.org/10\.\d{4,}/[^\s\]\)]+',
                r'10\.\d{4,}/[^\s\]\)]+',
            ]

            for pattern in doi_patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    doi = match.group(0)
                    doi = re.sub(r'^(doi:|DOI:|\s)+', '', doi, flags=re.IGNORECASE)
                    doi = re.sub(r'https?://doi\.org/', '', doi)
                    return self.clean_doi(doi)

        except Exception as e:
            pass

        return doi

    def clean_doi(self, doi):
        """Membersihkan DOI"""
        if not doi:
            return None
        doi = re.sub(r'[.,;:\]\)]+$', '', doi)
        doi = doi.strip()
        return doi if doi else None

    def get_crossref_metadata(self, doi):
        """Mengambil metadata dari CrossRef API"""
        if not doi:
            return None

        try:
            url = f"https://api.crossref.org/works/{doi}"
            headers = {
                'User-Agent': 'PDF-Renamer/1.0 (mailto:your-email@example.com)'
            }

            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'ok':
                    return data.get('message', {})

            time.sleep(0.5)

        except Exception as e:
            pass

        return None

    def parse_crossref_data(self, crossref_data):
        """Parse data dari CrossRef"""
        if not crossref_data:
            return {}

        metadata = {}

        # Title
        titles = crossref_data.get('title', [])
        metadata['title'] = titles[0] if titles else None

        # Authors
        authors = crossref_data.get('author', [])
        author_names = []
        for author in authors:
            given = author.get('given', '')
            family = author.get('family', '')
            if given and family:
                author_names.append(f"{given} {family}")
            elif family:
                author_names.append(family)

        metadata['authors'] = '; '.join(author_names) if author_names else None

        # Journal
        container = crossref_data.get('container-title', [])
        metadata['journal'] = container[0] if container else None

        # Year
        published = crossref_data.get('published-print') or crossref_data.get('published-online')
        if published and 'date-parts' in published:
            year = published['date-parts'][0][0] if published['date-parts'][0] else None
            metadata['year'] = year
        else:
            metadata['year'] = None

        metadata['volume'] = crossref_data.get('volume', None)
        metadata['issue'] = crossref_data.get('issue', None)
        metadata['page'] = crossref_data.get('page', None)
        metadata['publisher'] = crossref_data.get('publisher', None)

        subjects = crossref_data.get('subject', [])
        metadata['subjects'] = '; '.join(subjects) if subjects else None

        return metadata

    def download_pdf(self, file_id):
        """Download PDF dari Drive"""
        request = self.drive_service.files().get_media(fileId=file_id)
        file_stream = io.BytesIO()
        downloader = MediaIoBaseDownload(file_stream, request)

        done = False
        while not done:
            status, done = downloader.next_chunk()

        file_stream.seek(0)
        return file_stream

    def extract_pdf_metadata(self, file_stream):
        """Ekstrak metadata dari PDF"""
        metadata = {
            'title': None,
            'author': None,
            'creator': None,
            'producer': None,
            'creation_date': None,
            'page_count': 0,
            'doi': None,
            'crossref': None
        }

        try:
            reader = PdfReader(file_stream)

            pdf_metadata = reader.metadata
            if pdf_metadata:
                metadata['title'] = pdf_metadata.get('/Title', None)
                metadata['author'] = pdf_metadata.get('/Author', None)
                metadata['creator'] = pdf_metadata.get('/Creator', None)
                metadata['producer'] = pdf_metadata.get('/Producer', None)
                metadata['creation_date'] = pdf_metadata.get('/CreationDate', None)

            metadata['page_count'] = len(reader.pages)

            # Ekstrak DOI
            doi = self.extract_doi_from_pdf(reader)
            metadata['doi'] = doi

            # Ambil metadata CrossRef jika ada DOI
            if doi:
                crossref_data = self.get_crossref_metadata(doi)
                if crossref_data:
                    metadata['crossref'] = self.parse_crossref_data(crossref_data)

        except Exception as e:
            print(f"  ⚠️  Error ekstraksi metadata: {str(e)}")

        return metadata

    def rename_file(self, file_id, old_name, new_name):
        """Rename file di Google Drive"""
        try:
            self.drive_service.files().update(
                fileId=file_id,
                body={'name': new_name}
            ).execute()
            return True
        except Exception as e:
            print(f"  ❌ Error rename: {str(e)}")
            return False

    def clean_metadata_value(self, value):
        """Membersihkan nilai metadata"""
        if value is None:
            return '-'
        value_str = str(value)
        if value_str.startswith('D:'):
            try:
                date_str = value_str[2:16]
                dt = datetime.strptime(date_str, '%Y%m%d%H%M%S')
                return dt.strftime('%Y-%m-%d %H:%M:%S')
            except:
                return value_str
        return value_str.strip() if value_str.strip() else '-'

    def setup_sheet_header(self):
        """Setup header sheet"""
        headers = [
            'No',
            'Timestamp Insert',
            'Nama Folder',
            'Nama File Lama',
            'Nama File Baru',
            'Status Rename',
            'DOI',
            'Judul (CrossRef)',
            'Penulis (CrossRef)',
            'Jurnal',
            'Tahun',
            'Volume',
            'Issue',
            'Halaman',
            'Publisher',
            'Subjek/Keywords',
            'Judul (PDF)',
            'Penulis (PDF)',
            'Creator',
            'Producer',
            'Tanggal Dibuat (PDF)',
            'Ukuran (KB)',
            'Jumlah Halaman',
            'Link File'
        ]

        existing_headers = self.worksheet.row_values(1)

        if not existing_headers or existing_headers[0] != 'No':
            self.worksheet.clear()
            self.worksheet.append_row(headers)

            self.worksheet.format('A1:X1', {
                'backgroundColor': {'red': 0.26, 'green': 0.52, 'blue': 0.96},
                'textFormat': {'bold': True, 'foregroundColor': {'red': 1, 'green': 1, 'blue': 1}},
                'horizontalAlignment': 'CENTER'
            })

            print("✅ Header sheet dibuat\n")
        else:
            print("✅ Header sheet sudah ada\n")

    def process_files(self):
        """Proses dan rename file PDF"""
        files = self.get_pdf_files()

        if not files:
            print("❌ Tidak ada file PDF yang ditemukan")
            return

        self.setup_sheet_header()

        # Get folder name
        folder_name = self.get_folder_name(self.folder_id)

        existing_rows = len(self.worksheet.get_all_values())
        row_number = existing_rows if existing_rows > 1 else 1

        print("🔄 Memulai proses...\n")

        if ENABLE_RENAME:
            print("⚠️  MODE: RENAME AKTIF - File akan di-rename otomatis!")
        else:
            print("ℹ️  MODE: PREVIEW - Hanya menampilkan, tidak rename")
        print()

        success_count = 0
        rename_count = 0
        skip_count = 0
        error_count = 0

        for idx, file in enumerate(files, 1):
            old_name = file['name']
            file_id = file['id']

            print(f"[{idx}/{len(files)}] {old_name}")

            try:
                # Download dan ekstrak metadata
                file_stream = self.download_pdf(file_id)
                metadata = self.extract_pdf_metadata(file_stream)

                crossref = metadata.get('crossref', {})

                # Tentukan nama baru
                new_name = None
                rename_status = "Tidak di-rename"

                # Priority: CrossRef title > PDF title > Old name
                if crossref and crossref.get('title'):
                    title = crossref.get('title')
                    new_name = self.sanitize_filename(title) + '.pdf'
                    rename_status = "Rename dari CrossRef"
                    print(f"  📝 Judul CrossRef: {title}")
                elif metadata.get('title'):
                    title = metadata.get('title')
                    if title and title != old_name.replace('.pdf', ''):
                        new_name = self.sanitize_filename(title) + '.pdf'
                        rename_status = "Rename dari PDF metadata"
                        print(f"  📝 Judul PDF: {title}")

                # Lakukan rename jika ada nama baru dan berbeda
                if new_name and new_name != old_name:
                    if ENABLE_RENAME:
                        if self.rename_file(file_id, old_name, new_name):
                            print(f"  ✅ Renamed: {new_name}")
                            rename_count += 1
                            file['name'] = new_name  # Update untuk link
                        else:
                            rename_status = "Error saat rename"
                            new_name = old_name
                            error_count += 1
                    else:
                        print(f"  👁️  Preview: Akan di-rename jadi → {new_name}")
                        rename_status = "Preview mode"
                else:
                    print(f"  ⏭️  Skip: Tidak ada judul atau sama dengan nama file")
                    skip_count += 1
                    new_name = old_name

                # Timestamp
                current_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                # Siapkan data untuk sheet
                row_data = [
                    row_number,
                    current_timestamp,
                    folder_name,
                    old_name,
                    new_name if new_name else old_name,
                    rename_status,
                    metadata.get('doi', '-'),
                    # CrossRef data
                    self.clean_metadata_value(crossref.get('title')) if crossref else '-',
                    self.clean_metadata_value(crossref.get('authors')) if crossref else '-',
                    self.clean_metadata_value(crossref.get('journal')) if crossref else '-',
                    self.clean_metadata_value(crossref.get('year')) if crossref else '-',
                    self.clean_metadata_value(crossref.get('volume')) if crossref else '-',
                    self.clean_metadata_value(crossref.get('issue')) if crossref else '-',
                    self.clean_metadata_value(crossref.get('page')) if crossref else '-',
                    self.clean_metadata_value(crossref.get('publisher')) if crossref else '-',
                    self.clean_metadata_value(crossref.get('subjects')) if crossref else '-',
                    # PDF metadata
                    self.clean_metadata_value(metadata['title']) if metadata['title'] else old_name.replace('.pdf', ''),
                    self.clean_metadata_value(metadata['author']),
                    self.clean_metadata_value(metadata['creator']),
                    self.clean_metadata_value(metadata['producer']),
                    self.clean_metadata_value(metadata['creation_date']),
                    f"{int(file.get('size', 0)) / 1024:.2f}",
                    metadata['page_count'],
                    file.get('webViewLink', '-')
                ]

                self.worksheet.append_row(row_data)
                success_count += 1
                row_number += 1

            except Exception as e:
                print(f"  ❌ Error: {str(e)}")
                error_count += 1

            print()

        # Summary
        print("=" * 60)
        print("📊 HASIL PROSES")
        print("=" * 60)
        print(f"✅ Berhasil diproses: {success_count} file")
        if ENABLE_RENAME:
            print(f"🔄 Berhasil di-rename: {rename_count} file")
        print(f"⏭️  Di-skip: {skip_count} file")
        print(f"❌ Error: {error_count} file")
        print(f"📄 Total: {len(files)} file")
        print("=" * 60)
        print(f"\n🔗 Buka spreadsheet: https://docs.google.com/spreadsheets/d/{self.worksheet.spreadsheet.id}")

    def run(self):
        """Jalankan proses"""
        print("\n" + "=" * 60)
        print("📄 PDF FILE RENAMER - BASED ON METADATA TITLE")
        print("=" * 60 + "\n")

        try:
            self.authenticate()
            self.process_files()

            print("\n✅ Proses selesai!")

        except Exception as e:
            print(f"\n❌ Error: {str(e)}")
            import traceback
            traceback.print_exc()


def main():
    """Main function"""
    print(f"ID Folder default: {DEFAULT_FOLDER_ID}")
    folder_id_input = input("Masukkan ID Folder Google Drive (atau tekan Enter untuk menggunakan default): ").strip()
    
    if not folder_id_input:
        folder_id_input = DEFAULT_FOLDER_ID

    renamer = PDFRenamer(
        folder_id=folder_id_input,
        sheet_name=SHEET_NAME,
        spreadsheet_id=SPREADSHEET_ID,
        spreadsheet_name=SPREADSHEET_NAME,
        output_folder_id=OUTPUT_FOLDER_ID
    )

    renamer.run()


if __name__ == '__main__':
    main()