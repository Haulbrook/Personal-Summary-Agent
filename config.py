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
