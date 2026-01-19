# Personal Summary Agent - New Computer Setup

Google Cloud is already configured. Just need to set up local files.

## Step 1: Clone the repo

```bash
git clone https://github.com/Haulbrook/Personal-Summary-Agent
cd Personal-Summary-Agent
```

## Step 2: Install dependencies

```bash
pip install -r requirements.txt
```

## Step 3: Add credentials.json

Download from Google Cloud Console:
1. Go to https://console.cloud.google.com/
2. Select project: **summary-agent**
3. Go to **IAM & Admin** → **Service Accounts**
4. Click on: `journal-processor@summary-agent-484817.iam.gserviceaccount.com`
5. **Keys** tab → **Add Key** → **Create new key** → **JSON**
6. Save the downloaded file as `credentials.json` in the project folder

## Step 4: Create .env file

Create a file named `.env` in the project folder with this content:

```
OPENAI_API_KEY=<your-openai-api-key>
GOOGLE_SPREADSHEET_ID=1UKEfOgrZUXMNfjAKnD0Pv9tG43tPIpDEtevrW5oXrXE
DRIVE_FOLDER_MOLESKINE=1yoJVn40-k2od5i2-3DY6tbX5Ykvx8YVy
DRIVE_FOLDER_BEE=1VsyYSNAqfzuaZwUFAXuryjssISBp4AFY
DRIVE_FOLDER_NOTES=1rE5AvMsBL_iz4cNjkW1RJ-Fsh_hQQEb4
DRIVE_FOLDER_PROCESSED=148Cz1A75DJtuwWH4nkilDvxqxBhfiZi9
TIMEZONE=America/New_York
```

Get your OpenAI API key from: https://platform.openai.com/api-keys

## Step 5: Test

```bash
py -X utf8 main.py
```

Should output "No content found for this date" if folders are empty (that's OK).

---

## Usage

```bash
# Process today
py -X utf8 main.py

# Process specific date
py -X utf8 main.py --date 2026-01-15

# Weekly review
py -X utf8 main.py --week
```

## Adding Content

Upload text files to Google Drive folders:
- **Moleskine/** - notebook exports (.txt, .pdf)
- **Bee/** - voice transcriptions (.txt, .md)
- **Notes/** - Apple Notes exports (.txt, .md)

Files are processed by modified date, then moved to **Processed/** folder.
