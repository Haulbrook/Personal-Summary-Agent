# Personal Journal System - Complete Build Specification

## Overview

Build a personal journal system that:
1. Collects text from 3 sources (Moleskine notebook exports, Bee voice transcriptions, Apple Notes)
2. All sources export as text files to Google Drive folders
3. Processes content with AI (OpenAI) to generate summaries, extract tasks, provide insights
4. Stores everything in Google Sheets as a database
5. Runs via Python command line

## User's Setup

- **Moleskine Smart Notebook**: Exports as text files (preferred) or PDF
- **Bee Voice Recorder**: Already transcribed text files
- **Apple Notes**: Will export via iOS Shortcut to text files
- **All files go to Google Drive folders**

## Tech Stack

- Python 3.10+
- Google Drive API (read files)
- Google Sheets API (database)
- OpenAI API (GPT-4o for AI processing)
- No OCR needed (text exports)
- No audio transcription needed (Bee pre-transcribes)

---

# SETUP INSTRUCTIONS

## Step 1: Create Project Structure

Create this folder structure:

```
journal-system/
├── config.py
├── main.py
├── requirements.txt
├── credentials.json          (will be added manually)
├── .env                      (will be added manually)
├── processors/
│   ├── __init__.py
│   └── text_processor.py
├── ai/
│   ├── __init__.py
│   └── processor.py
└── storage/
    ├── __init__.py
    └── google_sheets.py
```

## Step 2: Google Cloud Setup (Manual Steps for User)

### 2.1 Create Google Cloud Project

1. Go to https://console.cloud.google.com/
2. Click "Select a project" → "New Project"
3. Name it "journal-system" → Create
4. Wait for project to be created, then select it

### 2.2 Enable APIs

1. Go to "APIs & Services" → "Library"
2. Search for and enable:
   - "Google Drive API" → Enable
   - "Google Sheets API" → Enable

### 2.3 Create Service Account

1. Go to "APIs & Services" → "Credentials"
2. Click "Create Credentials" → "Service Account"
3. Name: "journal-processor"
4. Click "Create and Continue"
5. Role: Select "Editor" → Continue → Done
6. Click on the created service account email
7. Go to "Keys" tab → "Add Key" → "Create new key"
8. Choose JSON → Create
9. Save the downloaded file as `credentials.json` in project folder

### 2.4 Create Google Sheet

1. Go to https://sheets.google.com
2. Create new spreadsheet named "Journal Database"
3. Copy the spreadsheet ID from the URL:
   `https://docs.google.com/spreadsheets/d/[THIS-IS-THE-ID]/edit`
4. Share the spreadsheet with your service account email (found in credentials.json as "client_email")
   - Click Share → paste service account email → Editor access

### 2.5 Create Google Drive Folders

1. In Google Drive, create folder: "Journal"
2. Inside "Journal", create 4 subfolders:
   - "Moleskine"
   - "Bee"
   - "Notes"
   - "Processed"
3. For each folder, get the ID from the URL:
   `https://drive.google.com/drive/folders/[THIS-IS-THE-FOLDER-ID]`
4. Share ALL folders with your service account email (Editor access)

### 2.6 Get OpenAI API Key

1. Go to https://platform.openai.com/api-keys
2. Create new secret key
3. Copy and save it securely

---

# CODE FILES

## File: requirements.txt

```
openai>=1.0.0
google-api-python-client>=2.0.0
google-auth-httplib2>=0.1.0
google-auth-oauthlib>=1.0.0
gspread>=5.0.0
python-dateutil>=2.8.0
pytz>=2023.0
PyPDF2>=3.0.0
python-dotenv>=1.0.0
```

## File: .env

```
OPENAI_API_KEY=sk-your-openai-key-here
GOOGLE_SPREADSHEET_ID=your-spreadsheet-id-here
DRIVE_FOLDER_MOLESKINE=your-moleskine-folder-id
DRIVE_FOLDER_BEE=your-bee-folder-id
DRIVE_FOLDER_NOTES=your-notes-folder-id
DRIVE_FOLDER_PROCESSED=your-processed-folder-id
TIMEZONE=America/New_York
```

## File: config.py

```python
"""
Journal System Configuration
Loads settings from environment variables
"""
import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Google Settings
GOOGLE_CREDENTIALS_FILE = "credentials.json"
SPREADSHEET_ID = os.getenv("GOOGLE_SPREADSHEET_ID")

# Google Drive Folders
DRIVE_FOLDERS = {
    "moleskine": os.getenv("DRIVE_FOLDER_MOLESKINE"),
    "bee": os.getenv("DRIVE_FOLDER_BEE"),
    "notes": os.getenv("DRIVE_FOLDER_NOTES"),
    "processed": os.getenv("DRIVE_FOLDER_PROCESSED")
}

# Processing Settings
DATE_FORMAT = "%Y-%m-%d"
TIMEZONE = os.getenv("TIMEZONE", "America/New_York")

# AI Settings
AI_MODEL = "gpt-4o"
TEMPERATURE = 0.7

# Supported file types
SUPPORTED_EXTENSIONS = {
    "moleskine": [".txt", ".pdf"],
    "bee": [".txt", ".md"],
    "notes": [".txt", ".md"]
}
```

## File: processors/__init__.py

```python
from .text_processor import TextProcessor, ContentMerger
```

## File: processors/text_processor.py

```python
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
```

## File: ai/__init__.py

```python
from .processor import AIProcessor
```

## File: ai/processor.py

```python
"""
AI Processor - Generate summaries, extract tasks, provide insights
"""
import json
from openai import OpenAI
from config import OPENAI_API_KEY, AI_MODEL, TEMPERATURE


class AIProcessor:
    """Handles all AI-powered analysis"""

    def __init__(self):
        self.client = OpenAI(api_key=OPENAI_API_KEY)
        self.model = AI_MODEL

    def _call(self, system: str, user: str, json_mode: bool = False, temperature: float = None) -> str:
        """Make API call to OpenAI"""
        kwargs = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ],
            "temperature": temperature or TEMPERATURE
        }

        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        response = self.client.chat.completions.create(**kwargs)
        return response.choices[0].message.content

    def generate_daily_summary(self, content: str) -> str:
        """Generate a concise daily summary"""
        system = """You are a personal journal assistant creating a daily summary.

Your summary should:
- Be 3-5 sentences
- Capture the essence of the day
- Mention key activities, accomplishments, or events
- Note the overall tone/mood if apparent
- Be written in second person ("You...")
- Be warm and insightful, not generic

Focus on what matters. Skip the fluff."""

        return self._call(system, f"Today's journal entries:\n\n{content}")

    def extract_tasks(self, content: str) -> dict:
        """Extract tasks mentioned in the content"""
        system = """You are a task extraction assistant.

Analyze the journal content and identify all tasks/to-dos mentioned.

Categorize them:
- completed: Tasks that were finished, done, completed
- pending: Tasks still needing to be done
- ideas: Things mentioned as "maybe" or "should consider"

Rules:
- Be specific - convert vague mentions into actionable items
- Include deadlines if mentioned
- Don't invent tasks not mentioned

Return JSON:
{
    "completed": [
        {"task": "description", "context": "brief context if relevant"}
    ],
    "pending": [
        {"task": "description", "priority": "high/medium/low", "deadline": "if mentioned or null"}
    ],
    "ideas": [
        {"task": "description", "notes": "any relevant notes"}
    ]
}"""

        result = self._call(system, content, json_mode=True)

        try:
            return json.loads(result)
        except json.JSONDecodeError:
            return {"completed": [], "pending": [], "ideas": []}

    def extract_insights(self, content: str) -> dict:
        """Extract mood, energy, themes, and patterns"""
        system = """Analyze this journal entry and extract insights.

Return JSON:
{
    "mood": {
        "primary": "one word (happy, stressed, calm, anxious, excited, tired, motivated, etc.)",
        "secondary": "optional secondary mood or null",
        "confidence": "high/medium/low"
    },
    "energy_level": "1-10 scale based on content",
    "themes": ["theme1", "theme2", "theme3"],
    "wins": ["positive things, accomplishments, good moments"],
    "challenges": ["difficulties, frustrations, obstacles"],
    "people_mentioned": ["names of people mentioned"],
    "notable_quotes": ["any memorable phrases or thoughts worth saving"]
}

Base this ONLY on what's actually written. Don't assume or invent."""

        result = self._call(system, content, json_mode=True)

        try:
            return json.loads(result)
        except json.JSONDecodeError:
            return {
                "mood": {"primary": "unknown", "confidence": "low"},
                "energy_level": 5,
                "themes": [],
                "wins": [],
                "challenges": [],
                "people_mentioned": [],
                "notable_quotes": []
            }

    def suggest_tasks(self, today_content: str, pending_tasks: list, recent_history: list = None) -> list:
        """Generate intelligent task suggestions for tomorrow"""
        pending_str = ""
        if pending_tasks:
            pending_str = "\n\nCURRENT PENDING TASKS:\n"
            pending_str += "\n".join([f"- {t}" for t in pending_tasks])

        history_str = ""
        if recent_history:
            history_str = "\n\nRECENT PATTERNS (last 7 days):\n"
            for entry in recent_history[-7:]:
                history_str += f"- {entry.get('date')}: {entry.get('summary', '')[:100]}...\n"

        system = """You are a proactive personal assistant helping plan tomorrow.

Based on:
1. Today's journal content
2. Pending tasks
3. Recent patterns

Suggest 3-5 actionable tasks for tomorrow.

Your suggestions should:
- Be specific and achievable
- Help complete important pending items
- Consider patterns and recurring needs
- Include a mix of urgent and important
- Be realistic for one day

Return JSON:
{
    "suggestions": [
        {
            "task": "Specific, actionable task description",
            "priority": "high/medium/low",
            "reason": "Why this is suggested (1 sentence)",
            "estimated_time": "rough time estimate",
            "category": "work/personal/health/admin/creative/social"
        }
    ]
}"""

        user = f"""TODAY'S JOURNAL:
{today_content}
{pending_str}
{history_str}"""

        result = self._call(system, user, json_mode=True)

        try:
            parsed = json.loads(result)
            return parsed.get("suggestions", [])
        except json.JSONDecodeError:
            return []

    def generate_weekly_review(self, entries: list) -> dict:
        """Generate comprehensive weekly review"""
        entries_text = ""
        for entry in entries:
            entries_text += f"""
--- {entry.get('date', 'Unknown')} ---
Summary: {entry.get('summary', 'N/A')}
Mood: {entry.get('mood', 'N/A')}
Energy: {entry.get('energy', 'N/A')}
Themes: {entry.get('themes', 'N/A')}
"""

        system = """You are creating a thoughtful weekly review for someone's personal journal.

Create a comprehensive review that includes:
1. Week Overview (2-3 sentences capturing the week)
2. Key Accomplishments (bullet points)
3. Patterns Noticed (mood trends, energy patterns, recurring themes)
4. Challenges Faced
5. Insights & Reflections
6. Suggestions for Next Week

Write in second person ("You..."). Be insightful, supportive, and specific.

Return JSON:
{
    "overview": "2-3 sentence overview",
    "accomplishments": ["accomplishment1", "accomplishment2"],
    "patterns": {
        "mood_trend": "description of mood pattern",
        "energy_trend": "description of energy pattern",
        "recurring_themes": ["theme1", "theme2"]
    },
    "challenges": ["challenge1", "challenge2"],
    "insights": ["insight1", "insight2"],
    "next_week_suggestions": [
        {"suggestion": "what to do", "why": "reason"}
    ],
    "highlight_of_week": "single best moment or achievement",
    "word_of_week": "one word that captures the week"
}"""

        result = self._call(system, entries_text, json_mode=True, temperature=0.8)

        try:
            return json.loads(result)
        except json.JSONDecodeError:
            return {"overview": "Could not generate weekly review"}
```

## File: storage/__init__.py

```python
from .google_sheets import SheetsDatabase
```

## File: storage/google_sheets.py

```python
"""
Google Sheets Database - Store and retrieve journal data
"""
import json
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timedelta
from config import GOOGLE_CREDENTIALS_FILE, SPREADSHEET_ID


class SheetsDatabase:
    """Google Sheets as database for journal data"""

    def __init__(self):
        scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        creds = Credentials.from_service_account_file(
            GOOGLE_CREDENTIALS_FILE,
            scopes=scopes
        )
        self.client = gspread.authorize(creds)
        self.spreadsheet = self.client.open_by_key(SPREADSHEET_ID)
        self._init_sheets()

    def _init_sheets(self):
        """Create sheets with headers if they don't exist"""
        existing = [ws.title for ws in self.spreadsheet.worksheets()]

        sheets_config = {
            "Daily Entries": [
                "date", "raw_content", "summary", "mood", "mood_confidence",
                "energy", "themes", "wins", "challenges", "sources",
                "word_count", "created_at", "updated_at"
            ],
            "Tasks": [
                "id", "date", "task", "status", "priority", "category",
                "deadline", "reason", "source", "completed_at",
                "created_at", "updated_at"
            ],
            "Weekly Reviews": [
                "week_start", "week_end", "overview", "accomplishments",
                "patterns", "challenges", "insights", "suggestions",
                "highlight", "word_of_week", "created_at"
            ],
            "Insights": [
                "date", "mood", "energy", "themes", "people_mentioned",
                "notable_quotes", "created_at"
            ]
        }

        for sheet_name, headers in sheets_config.items():
            if sheet_name not in existing:
                ws = self.spreadsheet.add_worksheet(sheet_name, 5000, len(headers))
                ws.append_row(headers)
                print(f"  ✓ Created sheet: {sheet_name}")

    def save_daily_entry(self, entry: dict) -> bool:
        """Save or update a daily entry"""
        ws = self.spreadsheet.worksheet("Daily Entries")

        now = datetime.now().isoformat()
        date_str = entry.get('date', '')

        row_data = [
            date_str,
            entry.get('raw_content', '')[:50000],
            entry.get('summary', ''),
            entry.get('mood', ''),
            entry.get('mood_confidence', ''),
            str(entry.get('energy', '')),
            entry.get('themes', ''),
            entry.get('wins', ''),
            entry.get('challenges', ''),
            entry.get('sources', ''),
            str(entry.get('word_count', 0)),
            now,
            now
        ]

        try:
            cell = ws.find(date_str, in_column=1)
            row_num = cell.row
            ws.update(f'A{row_num}:M{row_num}', [row_data])
        except gspread.exceptions.CellNotFound:
            ws.append_row(row_data)

        return True

    def get_recent_entries(self, days: int = 7) -> list:
        """Get entries from the last N days"""
        ws = self.spreadsheet.worksheet("Daily Entries")
        all_entries = ws.get_all_records()

        cutoff = (datetime.now() - timedelta(days=days)).date()

        recent = []
        for entry in all_entries:
            try:
                entry_date = datetime.strptime(entry['date'], '%Y-%m-%d').date()
                if entry_date >= cutoff:
                    recent.append(entry)
            except (ValueError, KeyError):
                continue

        return sorted(recent, key=lambda x: x.get('date', ''))

    def get_entries_for_week(self, week_start) -> list:
        """Get all entries for a specific week"""
        ws = self.spreadsheet.worksheet("Daily Entries")
        all_entries = ws.get_all_records()

        week_end = week_start + timedelta(days=6)

        week_entries = []
        for entry in all_entries:
            try:
                entry_date = datetime.strptime(entry['date'], '%Y-%m-%d').date()
                if week_start <= entry_date <= week_end:
                    week_entries.append(entry)
            except (ValueError, KeyError):
                continue

        return sorted(week_entries, key=lambda x: x.get('date', ''))

    def add_task(self, task: dict) -> str:
        """Add a new task"""
        ws = self.spreadsheet.worksheet("Tasks")

        all_values = ws.get_all_values()
        task_id = f"T{len(all_values):05d}"

        now = datetime.now().isoformat()

        row_data = [
            task_id,
            task.get('date', ''),
            task.get('task', ''),
            task.get('status', 'pending'),
            task.get('priority', 'medium'),
            task.get('category', ''),
            task.get('deadline', ''),
            task.get('reason', ''),
            task.get('source', 'manual'),
            '',
            now,
            now
        ]

        ws.append_row(row_data)
        return task_id

    def add_tasks_batch(self, tasks: list) -> list:
        """Add multiple tasks at once"""
        ws = self.spreadsheet.worksheet("Tasks")

        all_values = ws.get_all_values()
        start_id = len(all_values)

        now = datetime.now().isoformat()
        rows = []
        ids = []

        for i, task in enumerate(tasks):
            task_id = f"T{start_id + i:05d}"
            ids.append(task_id)

            rows.append([
                task_id,
                task.get('date', ''),
                task.get('task', ''),
                task.get('status', 'pending'),
                task.get('priority', 'medium'),
                task.get('category', ''),
                task.get('deadline', ''),
                task.get('reason', ''),
                task.get('source', 'extracted'),
                '',
                now,
                now
            ])

        if rows:
            ws.append_rows(rows)

        return ids

    def get_pending_tasks(self) -> list:
        """Get all pending tasks"""
        ws = self.spreadsheet.worksheet("Tasks")
        all_tasks = ws.get_all_records()
        return [t for t in all_tasks if t.get('status') == 'pending']

    def complete_task(self, task_id: str) -> bool:
        """Mark a task as completed"""
        ws = self.spreadsheet.worksheet("Tasks")

        try:
            cell = ws.find(task_id, in_column=1)
            row = cell.row

            now = datetime.now().isoformat()
            ws.update(f'D{row}', [['completed']])
            ws.update(f'J{row}', [[now]])
            ws.update(f'L{row}', [[now]])

            return True
        except gspread.exceptions.CellNotFound:
            return False

    def save_weekly_review(self, review: dict) -> bool:
        """Save a weekly review"""
        ws = self.spreadsheet.worksheet("Weekly Reviews")

        row_data = [
            review.get('week_start', ''),
            review.get('week_end', ''),
            review.get('overview', ''),
            json.dumps(review.get('accomplishments', [])),
            json.dumps(review.get('patterns', {})),
            json.dumps(review.get('challenges', [])),
            json.dumps(review.get('insights', [])),
            json.dumps(review.get('suggestions', [])),
            review.get('highlight_of_week', ''),
            review.get('word_of_week', ''),
            datetime.now().isoformat()
        ]

        ws.append_row(row_data)
        return True

    def save_insights(self, date_str: str, insights: dict) -> bool:
        """Save daily insights"""
        ws = self.spreadsheet.worksheet("Insights")

        row_data = [
            date_str,
            insights.get('mood', {}).get('primary', ''),
            str(insights.get('energy_level', '')),
            ', '.join(insights.get('themes', [])),
            ', '.join(insights.get('people_mentioned', [])),
            json.dumps(insights.get('notable_quotes', [])),
            datetime.now().isoformat()
        ]

        ws.append_row(row_data)
        return True
```

## File: main.py

```python
"""
Journal System - Main Entry Point
"""
import argparse
from datetime import datetime, timedelta
import pytz
from processors import TextProcessor, ContentMerger
from ai import AIProcessor
from storage import SheetsDatabase
from config import TIMEZONE, DATE_FORMAT


def process_day(target_date=None):
    """Process a single day's journal entries"""
    tz = pytz.timezone(TIMEZONE)
    if target_date is None:
        target_date = datetime.now(tz).date()

    date_str = target_date.strftime(DATE_FORMAT)

    print(f"\n{'='*60}")
    print(f"📔 JOURNAL PROCESSOR - {date_str}")
    print(f"{'='*60}")

    processor = TextProcessor()
    ai = AIProcessor()
    db = SheetsDatabase()

    # Step 1: Collect content
    print("\n📥 COLLECTING CONTENT...")
    sources = processor.process_all_sources(target_date)

    if not sources:
        print("\n⚠️  No content found for this date.")
        return None

    merged = ContentMerger.merge(sources)
    stats = ContentMerger.get_stats(sources)
    print(f"\n📊 Total: {stats['total_words']:,} words from {len(stats['sources_used'])} sources")

    # Step 2: AI Processing
    print("\n🤖 AI PROCESSING...")

    print("   Generating summary...")
    summary = ai.generate_daily_summary(merged)

    print("   Extracting tasks...")
    tasks = ai.extract_tasks(merged)

    print("   Analyzing insights...")
    insights = ai.extract_insights(merged)

    print("   Creating suggestions...")
    pending = [t['task'] for t in db.get_pending_tasks()]
    history = db.get_recent_entries(days=7)
    suggestions = ai.suggest_tasks(merged, pending, history)

    # Step 3: Save to Database
    print("\n💾 SAVING TO DATABASE...")

    entry = {
        "date": date_str,
        "raw_content": merged,
        "summary": summary,
        "mood": insights.get('mood', {}).get('primary', ''),
        "mood_confidence": insights.get('mood', {}).get('confidence', ''),
        "energy": insights.get('energy_level', ''),
        "themes": ', '.join(insights.get('themes', [])),
        "wins": ', '.join(insights.get('wins', [])),
        "challenges": ', '.join(insights.get('challenges', [])),
        "sources": ', '.join(stats['sources_used']),
        "word_count": stats['total_words']
    }
    db.save_daily_entry(entry)
    print("   ✓ Daily entry saved")

    # Save tasks
    task_records = []

    for t in tasks.get('completed', []):
        task_records.append({
            "date": date_str,
            "task": t.get('task', t) if isinstance(t, dict) else t,
            "status": "completed",
            "source": "extracted"
        })

    for t in tasks.get('pending', []):
        task_records.append({
            "date": date_str,
            "task": t.get('task', t) if isinstance(t, dict) else t,
            "status": "pending",
            "priority": t.get('priority', 'medium') if isinstance(t, dict) else 'medium',
            "source": "extracted"
        })

    for s in suggestions:
        task_records.append({
            "date": date_str,
            "task": s.get('task', ''),
            "status": "suggested",
            "priority": s.get('priority', 'medium'),
            "category": s.get('category', ''),
            "reason": s.get('reason', ''),
            "source": "ai_suggested"
        })

    if task_records:
        db.add_tasks_batch(task_records)
        print(f"   ✓ {len(task_records)} tasks saved")

    db.save_insights(date_str, insights)
    print("   ✓ Insights saved")

    # Step 4: Display Results
    print_results(date_str, summary, tasks, suggestions, insights)

    return {"date": date_str, "summary": summary, "tasks": tasks, "suggestions": suggestions, "insights": insights}


def process_week(week_start=None):
    """Generate a weekly review"""
    tz = pytz.timezone(TIMEZONE)

    if week_start is None:
        today = datetime.now(tz).date()
        week_start = today - timedelta(days=today.weekday() + 7)

    week_end = week_start + timedelta(days=6)

    print(f"\n{'='*60}")
    print(f"📅 WEEKLY REVIEW: {week_start} to {week_end}")
    print(f"{'='*60}")

    ai = AIProcessor()
    db = SheetsDatabase()

    entries = db.get_entries_for_week(week_start)

    if not entries:
        print("\n⚠️  No entries found for this week.")
        return None

    print(f"\n📊 Found {len(entries)} daily entries")
    print("\n🤖 Generating weekly review...")

    review = ai.generate_weekly_review(entries)

    review['week_start'] = str(week_start)
    review['week_end'] = str(week_end)
    db.save_weekly_review(review)
    print("   ✓ Weekly review saved")

    print_weekly_results(review)
    return review


def print_results(date_str, summary, tasks, suggestions, insights):
    """Display formatted results"""
    print(f"\n{'='*60}")
    print(f"📋 DAILY SUMMARY - {date_str}")
    print(f"{'='*60}")

    print(f"\n{summary}")

    mood = insights.get('mood', {})
    print(f"\n🎭 Mood: {mood.get('primary', 'Unknown')} | ⚡ Energy: {insights.get('energy_level', '?')}/10")

    themes = insights.get('themes', [])
    if themes:
        print(f"🏷️  Themes: {', '.join(themes)}")

    completed = tasks.get('completed', [])
    if completed:
        print(f"\n✅ COMPLETED ({len(completed)}):")
        for t in completed:
            task_text = t.get('task', t) if isinstance(t, dict) else t
            print(f"   ✓ {task_text}")

    pending = tasks.get('pending', [])
    if pending:
        print(f"\n📌 PENDING ({len(pending)}):")
        for t in pending:
            task_text = t.get('task', t) if isinstance(t, dict) else t
            priority = t.get('priority', '') if isinstance(t, dict) else ''
            icon = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}.get(priority, '⚪')
            print(f"   {icon} {task_text}")

    if suggestions:
        print(f"\n💡 SUGGESTED FOR TOMORROW ({len(suggestions)}):")
        for s in suggestions:
            icon = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}.get(s.get('priority', ''), '⚪')
            print(f"   {icon} {s.get('task', '')}")
            if s.get('reason'):
                print(f"      └─ {s.get('reason')}")

    wins = insights.get('wins', [])
    if wins:
        print(f"\n🏆 WINS:")
        for w in wins:
            print(f"   ⭐ {w}")

    challenges = insights.get('challenges', [])
    if challenges:
        print(f"\n🎯 CHALLENGES:")
        for c in challenges:
            print(f"   • {c}")

    print(f"\n{'='*60}\n")


def print_weekly_results(review):
    """Display formatted weekly review"""
    print(f"\n📝 OVERVIEW:")
    print(f"   {review.get('overview', '')}")

    print(f"\n🏆 ACCOMPLISHMENTS:")
    for a in review.get('accomplishments', []):
        print(f"   ⭐ {a}")

    patterns = review.get('patterns', {})
    if patterns:
        print(f"\n📊 PATTERNS:")
        print(f"   Mood: {patterns.get('mood_trend', 'N/A')}")
        print(f"   Energy: {patterns.get('energy_trend', 'N/A')}")

    print(f"\n💡 NEXT WEEK:")
    for s in review.get('next_week_suggestions', []):
        sug = s.get('suggestion', s) if isinstance(s, dict) else s
        print(f"   → {sug}")

    print(f"\n⭐ HIGHLIGHT: {review.get('highlight_of_week', 'N/A')}")
    print(f"📌 WORD OF WEEK: {review.get('word_of_week', 'N/A')}")
    print(f"\n{'='*60}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Journal Processing System")
    parser.add_argument("--date", help="Process specific date (YYYY-MM-DD)")
    parser.add_argument("--week", action="store_true", help="Generate weekly review")
    parser.add_argument("--week-start", help="Week start date (YYYY-MM-DD)")

    args = parser.parse_args()

    if args.week or args.week_start:
        week_start = None
        if args.week_start:
            week_start = datetime.strptime(args.week_start, "%Y-%m-%d").date()
        process_week(week_start)
    else:
        target_date = None
        if args.date:
            target_date = datetime.strptime(args.date, "%Y-%m-%d").date()
        process_day(target_date)
```

---

# TESTING

## Test 1: Verify Setup

After creating all files and completing Google setup, run:

```bash
python -c "from config import *; print('Config OK'); print(f'Spreadsheet: {SPREADSHEET_ID[:20]}...')"
```

## Test 2: Test Google Connection

```bash
python -c "from storage import SheetsDatabase; db = SheetsDatabase(); print('Google Sheets connected!')"
```

## Test 3: Test with Sample File

1. Create a test file: `2024-01-15-test.txt` with content:
```
Today I worked on the journal project. Finished setting up the API connections.
Need to test the full pipeline tomorrow.
Feeling productive and motivated!
```

2. Upload to the "Notes" folder in Google Drive
3. Run: `python main.py --date 2024-01-15`

---

# APPLE NOTES SHORTCUT

Create an iOS/macOS Shortcut with these actions:

1. Find All Notes where Modification Date is Today
2. Repeat with Each note
3. Get text from Repeat Item
4. Append to variable "AllNotes" with text plus separator "---"
5. End Repeat
6. Get current date formatted as "yyyy-MM-dd"
7. Save File to Google Drive path /Journal/Notes/[Date]-notes.txt with content from AllNotes variable
8. Show Notification "Notes exported!"

Run this shortcut before running the journal processor each day.

---

# USAGE

## Daily Processing

```bash
# Process today
python main.py

# Process specific date
python main.py --date 2024-01-15
```

## Weekly Review

```bash
# Generate review for last week
python main.py --week

# Generate review for specific week
python main.py --week-start 2024-01-08
```

---

# TROUBLESHOOTING

## "Could not find credentials.json"

- Make sure credentials.json is in the project root folder
- Check the file was downloaded correctly from Google Cloud

## "Permission denied" on Google Sheets

- Share the spreadsheet with the service account email
- The email looks like: name@project-id.iam.gserviceaccount.com

## "No content found for this date"

- Check files are in the correct Google Drive folders
- Verify folders are shared with service account
- Check file dates match the target date

## OpenAI API errors

- Verify API key is correct in .env
- Check you have credits/billing set up on OpenAI

---

# HOW TO USE THIS FILE

1. **Save this file** as `JOURNAL_SYSTEM_BUILD.md` in your project directory

2. **Open Claude Code** (or your terminal with Claude)

3. **Tell Claude Code:**
   > "Read JOURNAL_SYSTEM_BUILD.md and create the complete project. Start by creating the folder structure and all the Python files."

4. **Claude Code will:**
   - Create all folders
   - Create all Python files
   - Guide you through the Google setup
   - Help you test

5. **You'll need to manually:**
   - Do the Google Cloud Console setup (steps 2.1-2.6)
   - Add your API keys to `.env`
   - Add `credentials.json` to the project
