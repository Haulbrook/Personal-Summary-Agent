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
