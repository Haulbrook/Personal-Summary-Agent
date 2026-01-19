# Personal Journal System

A Python-based personal journal system that collects text from multiple sources, processes content with AI to generate summaries, extract tasks, and provide insights, then stores everything in Google Sheets.

## Features

- **Multi-source collection**: Pulls from Moleskine Smart Notebook exports, Bee voice transcriptions, and Apple Notes
- **AI-powered processing**: Uses OpenAI GPT-4o for intelligent analysis
- **Daily summaries**: Automatically generates concise daily summaries
- **Task extraction**: Identifies completed, pending, and idea tasks from your entries
- **Mood & energy tracking**: Analyzes emotional tone and energy levels
- **Weekly reviews**: Comprehensive weekly analysis with patterns and suggestions
- **Google Sheets database**: All data stored in easily accessible spreadsheets

## Project Structure

```
Personal-Summary-Agent/
├── config.py              # Configuration and environment settings
├── main.py                # CLI entry point
├── requirements.txt       # Python dependencies
├── .env.example           # Environment variable template
├── credentials.json       # Google service account (add manually)
├── processors/
│   ├── __init__.py
│   └── text_processor.py  # Google Drive file processing
├── ai/
│   ├── __init__.py
│   └── processor.py       # OpenAI integration
└── storage/
    ├── __init__.py
    └── google_sheets.py   # Google Sheets database operations
```

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Google Cloud Setup

1. Create a project at https://console.cloud.google.com/
2. Enable Google Drive API and Google Sheets API
3. Create a service account and download the JSON key
4. Save as `credentials.json` in the project root

### 3. Create Google Sheet

1. Create a new spreadsheet named "Journal Database"
2. Share it with your service account email (Editor access)
3. Copy the spreadsheet ID from the URL

### 4. Create Google Drive Folders

Create these folders in Google Drive and share with service account:
- Journal/Moleskine
- Journal/Bee
- Journal/Notes
- Journal/Processed

### 5. Configure Environment

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

Edit `.env` with your API keys and folder IDs.

### 6. Get OpenAI API Key

1. Go to https://platform.openai.com/api-keys
2. Create and copy your secret key
3. Add to `.env`

## Usage

### Daily Processing

```bash
# Process today's entries
python main.py

# Process a specific date
python main.py --date 2024-01-15
```

### Weekly Review

```bash
# Generate review for last week
python main.py --week

# Generate review for specific week
python main.py --week-start 2024-01-08
```

## Input Sources

- **Moleskine**: Export text/PDF files to Journal/Moleskine folder
- **Bee**: Pre-transcribed text files go to Journal/Bee folder
- **Apple Notes**: Use iOS Shortcut to export to Journal/Notes folder

## Testing

```bash
# Verify configuration
python -c "from config import *; print('Config OK')"

# Test Google Sheets connection
python -c "from storage import SheetsDatabase; db = SheetsDatabase(); print('Connected!')"
```

## Documentation

See `JOURNAL_SYSTEM_BUILD.md` for complete build specification and detailed setup instructions.
