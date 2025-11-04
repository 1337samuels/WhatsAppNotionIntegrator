# WhatsAppNotionIntegrator

A Python tool to scrape WhatsApp "introduction groups" and export participant information to CSV format. Supports both **WhatsApp Desktop** (recommended) and **WhatsApp Web**.

## Features

- **🆕 WhatsApp Desktop Support**: Connect to WhatsApp Desktop app for better contact data retention
- **WhatsApp Web Support**: Original method using Chrome browser
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

## Why WhatsApp Desktop vs Web?

**WhatsApp Desktop may display better contact information** for group participants. If you've found that WhatsApp Desktop shows participant names while WhatsApp Web shows only phone numbers, this tool provides a "Desktop mode" that:

1. Verifies you have WhatsApp Desktop installed
2. Uses a dedicated WhatsApp Web session
3. Prompts you to log in with the **same account** as your WhatsApp Desktop
4. Ensures both are synced to the same data

**Important**: Since WhatsApp Desktop doesn't support reliable browser automation, both modes ultimately use WhatsApp Web with Selenium. The "Desktop mode" ensures you're using the same account/data as your Desktop installation.

**Recommendation**: Start with **'web' mode** (default) - it's simpler and works reliably. Only use 'desktop' mode if you specifically need to verify account sync with WhatsApp Desktop.

## Requirements

- Python 3.x
- Selenium
- Chrome browser (for Web mode) OR WhatsApp Desktop app (for Desktop mode)
- ChromeDriver (compatible with your Chrome version)

## Installation

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
# MODE SELECTION: Choose 'desktop' or 'web'
WHATSAPP_MODE = 'web'  # Recommended: Use 'web' mode (works reliably)
```

- **'web'** (Recommended) - Standard WhatsApp Web automation in Chrome - works reliably
- **'desktop'** - Verifies Desktop installation and uses dedicated profile to ensure same account sync

**Note**: Both modes use WhatsApp Web with Selenium for automation. The difference is that 'desktop' mode checks for WhatsApp Desktop installation and uses a separate Chrome profile to ensure you're logged into the same account.

### Running the Scraper

1. Run the script:
```bash
python scrape_whatsapp_chats.py
```

2. The script will:
   - **Web Mode**: Open Chrome using your default profile (auto-login to WhatsApp Web)
   - **Desktop Mode**: Verify Desktop is installed, then open dedicated Chrome profile (you'll need to login)
   - Wait for you to confirm WhatsApp is loaded and logged in
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

- **`WHATSAPP_MODE`**: Choose between 'web' or 'desktop' (default: 'web')
  - **'web'** (Recommended) - WhatsApp Web automation using default Chrome profile
  - **'desktop'** - Verifies Desktop installation and uses dedicated Chrome profile for account sync
- `MAX_ITERATIONS`: Maximum number of scroll iterations as a safety limit (default: 500)
  - The script will auto-stop when it detects no new chats, usually well before this limit
- `OUTPUT_DIRECTORY`: Where to save output files (default: current directory)
- `OUTPUT_NAME`: Base name for CSV files - timestamp is added automatically (default: "whatsapp_chats")
- `LOG_NAME`: Base name for log files - timestamp is added automatically (default: "whatsapp_scraper")
- `WAIT_TIMEOUT`: Timeout for waiting for elements (default: 10 seconds)
- `INTRO_DELIMITERS`: Delimiters that identify introduction groups (default: `["//", "/", "<>", "x"]`)

## How It Works

### WhatsApp Web Mode (Recommended)

The script opens Chrome with your default user profile:

1. Opens Chrome with your saved profile (auto-login to WhatsApp Web)
2. Uses Selenium for browser automation
3. **Benefit**: Simple, reliable, auto-login if you're already signed in

### WhatsApp Desktop Mode

Since WhatsApp Desktop doesn't support reliable remote debugging automation:

1. Verifies WhatsApp Desktop is installed on your system
2. Opens WhatsApp Web in a **dedicated Chrome profile** (separate from your default)
3. You'll need to scan QR code to login (only once - session is saved)
4. **Important**: Login with the SAME phone number/account as your WhatsApp Desktop
5. **Benefit**: Ensures account sync between Desktop and Web for consistent contact data

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

- **WhatsApp Desktop not found**:
  - Make sure WhatsApp Desktop is installed
  - Check the installation paths in the script match your system
  - The script will automatically fall back to Web mode if Desktop isn't found
- **Need to login every time**:
  - Desktop mode uses a separate Chrome profile to avoid conflicts
  - You only need to login once - the session is saved for future runs
  - Make sure to login with the SAME account as your WhatsApp Desktop
- **Contact data still not showing**:
  - Ensure both WhatsApp Desktop and WhatsApp Web are logged into the same account
  - Keep WhatsApp Desktop open and synced before running the scraper
  - WhatsApp Web will sync the same contact data from your account

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

### About Contact Data and WhatsApp Desktop

If you're seeing better contact information in WhatsApp Desktop compared to WhatsApp Web:

1. **Ensure Same Account**: Both Desktop and Web must be logged into the same WhatsApp account
2. **Wait for Sync**: Keep WhatsApp Desktop running for a while to ensure full contact sync from your phone
3. **Check Web**: After Desktop has synced, WhatsApp Web (logged into the same account) should also have the updated contact information
4. **Reality Check**: WhatsApp Desktop and Web both pull data from the same WhatsApp servers. Any differences are usually due to sync delays or being logged into different accounts 
