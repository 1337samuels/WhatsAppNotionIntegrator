# WhatsAppNotionIntegrator

A Python tool to scrape WhatsApp "introduction groups" and export participant information to CSV format. Supports both **WhatsApp Desktop** (recommended) and **WhatsApp Web**.

## Features

- **🆕 WhatsApp Desktop Database Extraction**: Read participant data from WhatsApp Desktop's local cache
- **WhatsApp Web Automation**: Reliable browser-based scraping with Selenium
- **Hybrid Approach**: Combines Desktop's cached data with Web's UI automation
- Auto-login with saved sessions (no repeated QR scanning)
- Intelligently filters for "introduction groups" based on specific naming patterns
- Depth-First Search (DFS) approach - processes groups immediately as found
- Crash-resistant: Saves data immediately after each group is processed
- Extracts participant names and phone numbers from group chats
- **Smart scrolling**: Automatically detects when it has reached the end of your chat list
- **Comprehensive logging**: All operations logged to both console and file for debugging
- Includes participant count for each group
- Ignores Archive and individual chats
- Exports data to CSV format for easy analysis

## Why Use Desktop Mode?

**Critical Discovery**: WhatsApp Desktop maintains a **local cache** of participant data that WhatsApp Web doesn't have!

### The Problem

When you **leave a WhatsApp group**:
- ❌ **WhatsApp Web**: Shows only phone numbers (`+1234567890`)
- ✅ **WhatsApp Desktop**: Still shows names (`Alice Smith`) from its local cache

This means WhatsApp Desktop has valuable participant information that WhatsApp Web has completely lost.

### The Solution

This tool's **Desktop Mode** extracts data directly from WhatsApp Desktop's IndexedDB database, giving you access to those cached participant names that Web can't see.

**See [DESKTOP_MODE.md](DESKTOP_MODE.md) for detailed guide on using Desktop mode.**

## Requirements

- Python 3.x
- Selenium
- Chrome browser
- ChromeDriver (compatible with your Chrome version)
- (Optional) WhatsApp Desktop - for Desktop mode participant cache extraction
- (Optional) dfindexeddb - for reading Desktop's database

## Installation

### Basic Installation (Web Mode Only)

```bash
pip install selenium
```

### Full Installation (Desktop Mode Support)

```bash
pip install -r requirements.txt
```

Or manually:
```bash
pip install selenium
pip install dfindexeddb
```

### WhatsApp Desktop (for Desktop Mode)

Only needed if you want to use Desktop mode to extract cached participant data:

- **Windows**: [Microsoft Store](https://www.microsoft.com/store/apps/whatsapp) or [whatsapp.com/download](https://www.whatsapp.com/download)
- **macOS**: [whatsapp.com/download](https://www.whatsapp.com/download)
- **Linux**: Snap Store (`snap install whatsapp-for-linux`)

## Quick Start

```bash
pip install selenium
```

## What are "Introduction Groups"?

Introduction groups are WhatsApp groups with names that follow a specific pattern indicating connections between people. The script recognizes groups with these delimiters in their names:

- `//` (double slash) - e.g., "John & Mary//Bob + Alice"
- `/` (single slash) - e.g., "John/Jane"
- `<>` (angle brackets) - e.g., "Person1<>Person2"
- `x` (letter x) - e.g., "AlicexBob"

These patterns are defined in `chat_parser.py` and indicate groups created for introducing people to each other.

## Installation & Setup

### For WhatsApp Desktop Mode (Recommended)

1. Install WhatsApp Desktop on your system:
   - **Windows**: Download from [Microsoft Store](https://www.microsoft.com/store/apps/whatsapp) or [whatsapp.com/download](https://www.whatsapp.com/download)
   - **macOS**: Download from [whatsapp.com/download](https://www.whatsapp.com/download)
   - **Linux**: Install from Snap Store (`snap install whatsapp-for-linux`) or download from [whatsapp.com/download](https://www.whatsapp.com/download)

2. Log into WhatsApp Desktop and ensure it's working

3. Install Python dependencies:
```bash
pip install selenium
```

### For WhatsApp Web Mode

1. Make sure you're logged into WhatsApp Web in your default Chrome browser profile

2. Install Python dependencies:
```bash
pip install selenium
```

## Usage

### Choosing Your Mode

Open `scrape_whatsapp_chats.py` and set the mode at the top of the file:

```python
# MODE SELECTION
WHATSAPP_MODE = 'desktop'  # For best participant data
# WHATSAPP_MODE = 'web'     # For simpler operation
```

#### Mode Comparison

| Mode | Best For | Requirements | Participant Data |
|------|----------|--------------|------------------|
| **`desktop`** | Groups you've left | WhatsApp Desktop installed<br>dfindexeddb package<br>Desktop must be closed | ✅ Excellent<br>Shows cached names |
| **`web`** | Current groups only | Just Selenium | ⚠️ Limited<br>Shows phone numbers for left groups |

**Recommendation**:
- Use **`desktop`** mode if you need participant names from groups you've left
- Use **`web`** mode if you only care about current groups or want simpler setup

**See [DESKTOP_MODE.md](DESKTOP_MODE.md) for complete Desktop mode guide.**

### Running the Scraper

1. Run the script:
```bash
python scrape_whatsapp_chats.py
```

2. The script will:

   **Desktop Mode**:
   - Extract participant/contact data from WhatsApp Desktop's local IndexedDB cache
   - Open WhatsApp Web in Chrome for UI automation
   - Scrape introduction groups
   - Enrich data with Desktop's cached participant information

   **Web Mode**:
   - Open Chrome using your default profile (auto-login to WhatsApp Web)
   - Scrape introduction groups directly

   **Both modes**:
   - Scroll through all chats in the sidebar
   - Identify introduction groups by their naming pattern
   - **Immediately** click into each matching group
   - Extract participant information
   - **Save immediately** to CSV (crash-resistant)
   - Continue to the next introduction group

3. The script creates two timestamped files in the output directory (each run creates unique files):
   - `whatsapp_chats_YYYYMMDD_HHMMSS.csv` - All participant data (saved incrementally)
   - `whatsapp_scraper_YYYYMMDD_HHMMSS.log` - Complete log of all operations (for debugging)
   - Example: `whatsapp_chats_20251102_143055.csv` and `whatsapp_scraper_20251102_143055.log`

## CSV Output Format

The output CSV file contains the following columns:

- `chat_name`: Name of the introduction group
- `chat_type`: Always "group" (only group chats are processed)
- `participant_name`: Name of participant in the group
- `participant_phone`: Phone number if available or "N/A"
- `participant_count`: Total number of participants in the group

### Example Output

```csv
chat_name,chat_type,participant_name,participant_phone,participant_count
John/Jane,group,John Smith,+1234567890,2
John/Jane,group,Jane Doe,+9876543210,2
Alice<>Bob,group,Alice Williams,N/A,2
Alice<>Bob,group,Bob Johnson,+1122334455,2
Sarah & Mike//Tom + Lisa,group,Sarah Chen,+9998887777,4
Sarah & Mike//Tom + Lisa,group,Mike Brown,N/A,4
Sarah & Mike//Tom + Lisa,group,Tom Davis,+5554443333,4
Sarah & Mike//Tom + Lisa,group,Lisa Wilson,N/A,4
```

Note: Each participant gets their own row with the total participant count for that group. Data is saved immediately after processing each group.

## Configuration

You can modify these constants at the top of the script:

- **`WHATSAPP_MODE`**: Choose between 'desktop' or 'web' (default: 'desktop')
  - **'desktop'** - Extract from WhatsApp Desktop's local cache, then scrape Web (best participant data)
  - **'web'** - Standard WhatsApp Web automation (simpler, but limited participant data for left groups)
- `MAX_ITERATIONS`: Maximum number of scroll iterations as a safety limit (default: 500)
  - The script will auto-stop when it detects no new chats, usually well before this limit
- `OUTPUT_DIRECTORY`: Where to save output files (default: current directory)
- `OUTPUT_NAME`: Base name for CSV files - timestamp is added automatically (default: "whatsapp_chats")
- `LOG_NAME`: Base name for log files - timestamp is added automatically (default: "whatsapp_scraper")
- `WAIT_TIMEOUT`: Timeout for waiting for elements (default: 10 seconds)
- `INTRO_DELIMITERS`: Delimiters that identify introduction groups (default: `["//", "/", "<>", "x"]`)

## How It Works

### Desktop Mode (Best for Participant Data)

**Hybrid approach**: Extracts Desktop's cache + Web automation

1. **Close WhatsApp Desktop** (required to access database)
2. **Read IndexedDB**: Extract participant/contact data from Desktop's local database
   - Contacts with names and phone numbers
   - Group participant lists (including left groups)
   - Cached data that Web doesn't have
3. **Open WhatsApp Web**: Use Selenium for UI automation
4. **Scrape Groups**: Navigate and extract introduction groups
5. **Enrich Data**: Merge Web data with Desktop's cached participant info
6. **Output CSV**: Complete participant data with names (not just phone numbers)

**Why this works**: WhatsApp Desktop stores participant information locally even after you leave groups. By reading this cache, we get names that WhatsApp Web no longer has access to.

**See [DESKTOP_MODE.md](DESKTOP_MODE.md) for detailed explanation.**

### Web Mode (Simpler Operation)

Standard browser automation:

1. Opens Chrome with your saved profile (auto-login to WhatsApp Web)
2. Uses Selenium for browser automation
3. Scrapes introduction groups
4. **Limitation**: Only shows current participant data, may show phone numbers instead of names for left groups

### DFS (Depth-First Search) Approach

Unlike a typical scraper that collects all chat names first and then processes them (BFS), this script uses a DFS approach:

1. **Scroll** through chats in the sidebar
2. **Check** each chat name for introduction group patterns
3. **Process immediately** if it matches (click, extract participants, save to CSV)
4. **Continue** to next chat
5. **Auto-detect** when the end of the chat list is reached (stops scrolling when no new chats appear)

### Crash Resistance

The script writes data to the CSV file immediately after processing each group using **append mode**. This means:

- If the script crashes, all previously processed groups are already saved in that run's CSV file
- No data loss even with interruptions
- Each run creates new timestamped files, so previous runs are never overwritten
- Can safely run multiple times to collect data from different time periods

### Auto-Login

- **Desktop Mode**: Connects to your already-logged-in WhatsApp Desktop
- **Web Mode**: Opens Chrome with your default user profile (stays logged in)
- No need to scan QR codes every time (unless session expires)
- Faster startup and more convenient

## Notes

- **Only processes introduction groups**: Individual chats and groups without the special delimiters are ignored
- **Archive is skipped**: The Archive chat (first in sidebar) is automatically ignored
- **Multiple strategies**: Uses multiple fallback methods to detect and extract participant information
- **WhatsApp Web changes**: If WhatsApp updates their HTML structure, the script may need adjustments
- **Privacy settings**: Phone numbers may not always be available depending on contact privacy settings
- **Error handling**: The script continues even if specific groups fail to process

## Troubleshooting

### Desktop Mode Issues

- **WhatsApp Desktop database not found**:
  - Make sure WhatsApp Desktop is installed and you've used it at least once
  - Browse some groups in Desktop to populate the database
  - Check the installation paths match your system
  - The script will automatically fall back to Web mode if not found

- **"Cannot read database" or "File locked"**:
  - **Close WhatsApp Desktop completely** before running the scraper
  - The database files are locked while the app is running
  - Make sure it's fully closed, not just minimized

- **"dfindexeddb not installed"**:
  - Install with: `pip install dfindexeddb`
  - Or use: `pip install -r requirements.txt`

- **No contacts extracted**:
  - Use WhatsApp Desktop regularly first to build up the cache
  - Open and browse through your introduction groups in Desktop
  - The database only contains data that Desktop has cached

**For detailed Desktop mode troubleshooting**, see [DESKTOP_MODE.md](DESKTOP_MODE.md)

### Web Mode Issues

- **Chrome profile error**: If Chrome can't open with your profile (already open), close Chrome and try again, or the script will fallback to a fresh profile
- **Session expired**: You may need to scan the QR code again if your session has expired

### General Issues

- **Can't find participants**: WhatsApp's structure may have changed. The script uses multiple fallback strategies
- **Script stops early**: The script auto-detects when it has reached the end of chats. If you have many chats, it should process them all
- **StaleElementReferenceException**: Expected and handled automatically - occurs when the page updates while scrolling
- **No introduction groups found**: Check that your groups have the correct naming pattern with delimiters: `//`, `/`, `<>`, or `x`

### Switching Modes

If one mode isn't working well, simply change `WHATSAPP_MODE` in the script:
```python
# Try web mode first (recommended):
WHATSAPP_MODE = 'web'

# Or use desktop mode if you need to ensure account sync:
WHATSAPP_MODE = 'desktop'
```

### Understanding Desktop vs Web Data

**Important**: WhatsApp Desktop and Web do NOT share the same local cache!

- **WhatsApp Desktop**: Stores participant data locally in IndexedDB
  - Keeps names even after you leave groups
  - This cache persists on your computer

- **WhatsApp Web**: Loads data fresh from servers each time
  - Only shows current group participants
  - Loses access to participant info when you leave a group

This is why Desktop mode extracts from Desktop's **local database** rather than just syncing accounts. The local cache is the key difference! 
