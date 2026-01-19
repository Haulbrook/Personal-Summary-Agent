"""
Text Processor - Reads and processes text from all input sources
"""
import io
from datetime import datetime
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from PyPDF2 import PdfReader
from config import GOOGLE_CREDENTIALS_FILE, DRIVE_FOLDERS, SUPPORTED_EXTENSIONS


class TextProcessor:
    """Processes text files from Google Drive folders"""

    def __init__(self):
        scopes = ['https://www.googleapis.com/auth/drive']
        creds = Credentials.from_service_account_file(
            GOOGLE_CREDENTIALS_FILE,
            scopes=scopes
        )
        self.drive = build('drive', 'v3', credentials=creds)

    def process_all_sources(self, target_date) -> dict:
        """Process all input sources for a given date"""
        results = {}

        for source in ["moleskine", "bee", "notes"]:
            folder_id = DRIVE_FOLDERS.get(source)
            if folder_id:
                content = self._process_folder(folder_id, source, target_date)
                if content:
                    results[source] = content
                    print(f"  ✓ {source.capitalize()}: {len(content):,} characters")
                else:
                    print(f"  - {source.capitalize()}: No new files")

        return results

    def _process_folder(self, folder_id: str, source: str, target_date) -> str:
        """Process all files in a folder for the target date"""
        query = f"'{folder_id}' in parents and trashed=false"
        results = self.drive.files().list(
            q=query,
            fields="files(id, name, createdTime, modifiedTime, mimeType)",
            orderBy="createdTime"
        ).execute()

        files = results.get('files', [])
        all_content = []

        for file in files:
            file_date = self._get_file_date(file)
            if file_date != target_date:
                continue

            if not self._is_supported(file['name'], source):
                continue

            print(f"    📄 {file['name']}")
            content = self._extract_text(file)

            if content:
                formatted = f"[{source.upper()}: {file['name']}]\n{content}"
                all_content.append(formatted)
                self._move_to_processed(file['id'])

        return "\n\n---\n\n".join(all_content)

    def _get_file_date(self, file: dict):
        """Extract date from file metadata"""
        time_str = file.get('modifiedTime') or file.get('createdTime')
        if time_str:
            dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
            return dt.date()
        return None

    def _is_supported(self, filename: str, source: str) -> bool:
        """Check if file extension is supported"""
        extensions = SUPPORTED_EXTENSIONS.get(source, [])
        return any(filename.lower().endswith(ext) for ext in extensions)

    def _extract_text(self, file: dict) -> str:
        """Extract text content from file"""
        mime_type = file['mimeType']
        filename = file['name'].lower()

        if mime_type == 'text/plain' or filename.endswith(('.txt', '.md')):
            return self._download_text(file['id'])

        if mime_type == 'application/pdf' or filename.endswith('.pdf'):
            return self._extract_pdf_text(file['id'])

        if mime_type == 'application/vnd.google-apps.document':
            return self._export_google_doc(file['id'])

        return ""

    def _download_text(self, file_id: str) -> str:
        """Download plain text file"""
        request = self.drive.files().get_media(fileId=file_id)
        content = io.BytesIO()
        downloader = MediaIoBaseDownload(content, request)

        done = False
        while not done:
            _, done = downloader.next_chunk()

        return content.getvalue().decode('utf-8', errors='ignore')

    def _extract_pdf_text(self, file_id: str) -> str:
        """Extract text from PDF"""
        request = self.drive.files().get_media(fileId=file_id)
        content = io.BytesIO()
        downloader = MediaIoBaseDownload(content, request)

        done = False
        while not done:
            _, done = downloader.next_chunk()

        content.seek(0)

        try:
            reader = PdfReader(content)
            text_parts = []
            for i, page in enumerate(reader.pages):
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(f"[Page {i+1}]\n{page_text}")
            return "\n\n".join(text_parts)
        except Exception as e:
            print(f"      ⚠️ PDF extraction error: {e}")
            return ""

    def _export_google_doc(self, file_id: str) -> str:
        """Export Google Doc as text"""
        request = self.drive.files().export_media(
            fileId=file_id,
            mimeType='text/plain'
        )
        content = io.BytesIO()
        downloader = MediaIoBaseDownload(content, request)

        done = False
        while not done:
            _, done = downloader.next_chunk()

        return content.getvalue().decode('utf-8', errors='ignore')

    def _move_to_processed(self, file_id: str):
        """Move processed file to the processed folder"""
        processed_folder = DRIVE_FOLDERS.get("processed")
        if not processed_folder:
            return

        try:
            file = self.drive.files().get(
                fileId=file_id,
                fields='parents'
            ).execute()

            previous_parents = ",".join(file.get('parents', []))

            self.drive.files().update(
                fileId=file_id,
                addParents=processed_folder,
                removeParents=previous_parents
            ).execute()
        except Exception as e:
            print(f"      ⚠️ Could not move file: {e}")


class ContentMerger:
    """Merges content from multiple sources"""

    @staticmethod
    def merge(sources: dict) -> str:
        """Merge all source content into one document"""
        sections = []

        order = ["moleskine", "bee", "notes"]
        labels = {
            "moleskine": "📓 NOTEBOOK ENTRIES",
            "bee": "🎤 VOICE NOTES",
            "notes": "📱 DIGITAL NOTES"
        }

        for source in order:
            content = sources.get(source)
            if content:
                section = f"{'='*50}\n{labels[source]}\n{'='*50}\n\n{content}"
                sections.append(section)

        return "\n\n\n".join(sections)

    @staticmethod
    def get_stats(sources: dict) -> dict:
        """Get statistics about the merged content"""
        stats = {
            "total_characters": 0,
            "total_words": 0,
            "sources_used": [],
            "by_source": {}
        }

        for source, content in sources.items():
            if content:
                char_count = len(content)
                word_count = len(content.split())

                stats["sources_used"].append(source)
                stats["total_characters"] += char_count
                stats["total_words"] += word_count
                stats["by_source"][source] = {
                    "characters": char_count,
                    "words": word_count
                }

        return stats
