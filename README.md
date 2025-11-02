# WhatsAppNotionIntegrator

A Python tool to scrape WhatsApp Web "introduction groups" and export participant information to CSV format.

## Features

- Auto-login to WhatsApp Web using default Chrome profile (no QR scanning needed)
- Intelligently filters for "introduction groups" based on specific naming patterns
- Depth-First Search (DFS) approach - processes groups immediately as found
- Crash-resistant: Saves data immediately after each group is processed
- Extracts participant names and phone numbers from group chats
- **Smart scrolling**: Automatically detects when it has reached the end of your chat list
- **Comprehensive logging**: All operations logged to both console and file for debugging
- Includes participant count for each group
- Ignores Archive and individual chats
- Exports data to CSV format for easy analysis

## Requirements

- Python 3.x
- Selenium
- Chrome browser
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

## Usage

1. Make sure you're logged into WhatsApp Web in your default Chrome browser profile

2. Run the script:
```bash
python scrape_whatsapp_chats.py
```

3. The script will:
   - Open Chrome using your default profile (auto-login to WhatsApp Web)
   - Wait for you to confirm WhatsApp is loaded
   - Scroll through all chats in the sidebar
   - Identify introduction groups by their naming pattern
   - **Immediately** click into each matching group
   - Extract participant information
   - **Save immediately** to CSV (crash-resistant)
   - Continue to the next introduction group

4. The script creates two files in the output directory:
   - `whatsapp_chats.csv` - All participant data (saved incrementally)
   - `whatsapp_scraper.log` - Complete log of all operations (for debugging)

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

- `MAX_ITERATIONS`: Maximum number of scroll iterations as a safety limit (default: 500)
  - The script will auto-stop when it detects no new chats, usually well before this limit
- `OUTPUT_DIRECTORY`: Where to save output files (default: current directory)
- `OUTPUT_NAME`: Name of the output CSV file (default: "whatsapp_chats.csv")
- `LOG_NAME`: Name of the log file (default: "whatsapp_scraper.log")
- `WAIT_TIMEOUT`: Timeout for waiting for elements (default: 10 seconds)
- `INTRO_DELIMITERS`: Delimiters that identify introduction groups (default: `["//", "/", "<>", "x"]`)

## How It Works

### DFS (Depth-First Search) Approach

Unlike a typical scraper that collects all chat names first and then processes them (BFS), this script uses a DFS approach:

1. **Scroll** through chats in the sidebar
2. **Check** each chat name for introduction group patterns
3. **Process immediately** if it matches (click, extract participants, save to CSV)
4. **Continue** to next chat
5. **Auto-detect** when the end of the chat list is reached (stops scrolling when no new chats appear)

### Crash Resistance

The script writes data to the CSV file immediately after processing each group using **append mode**. This means:

- If the script crashes, all previously processed groups are already saved
- No data loss even with interruptions
- Can resume by running the script again (it removes the old CSV and starts fresh)

### Chrome Profile Auto-Login

The script opens Chrome with your default user profile, which means:

- If you're already logged into WhatsApp Web in Chrome, you'll stay logged in
- No need to scan QR codes every time
- Faster startup and more convenient

## Notes

- **Only processes introduction groups**: Individual chats and groups without the special delimiters are ignored
- **Archive is skipped**: The Archive chat (first in sidebar) is automatically ignored
- **Multiple strategies**: Uses multiple fallback methods to detect and extract participant information
- **WhatsApp Web changes**: If WhatsApp updates their HTML structure, the script may need adjustments
- **Privacy settings**: Phone numbers may not always be available depending on contact privacy settings
- **Error handling**: The script continues even if specific groups fail to process

## Troubleshooting

- **Chrome profile error**: If Chrome can't open with your profile (already open), close Chrome and try again, or the script will fallback to a fresh profile
- **Can't find participants**: WhatsApp Web's structure may have changed. The script uses multiple fallback strategies
- **Script stops early**: The script auto-detects when it has reached the end of chats. If you have many chats, it should process them all
- **StaleElementReferenceException**: Expected and handled automatically - occurs when the page updates while scrolling
- **No introduction groups found**: Check that your groups have the correct naming pattern with delimiters: `//`, `/`, `<>`, or `x` 
