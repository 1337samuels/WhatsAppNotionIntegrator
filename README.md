# WhatsAppNotionIntegrator

A Python tool to scrape WhatsApp Web chats and export them to CSV format, including group chat participant information.

## Features

- Scrapes all chat titles from WhatsApp Web
- Automatically detects group chats vs. individual chats
- Extracts participant names and phone numbers from group chats
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

## Usage

1. Run the script:
```bash
python scrape_whatsapp_chats.py
```

2. A Chrome browser window will open with WhatsApp Web
3. Scan the QR code with your phone to link your WhatsApp
4. Press Enter in the terminal when ready
5. The script will:
   - Scroll through all chats in the sidebar
   - Click into each chat to determine if it's a group
   - Extract participant information from group chats
   - Save all data to `whatsapp_chats.csv`

## CSV Output Format

The output CSV file contains the following columns:

- `chat_name`: Name of the chat/group
- `chat_type`: Either "group", "individual", or "error"
- `participant_name`: Name of participant (for groups) or "N/A"
- `participant_phone`: Phone number if available or "N/A"

### Example Output

```csv
chat_name,chat_type,participant_name,participant_phone
Family Group,group,John Doe,+1234567890
Family Group,group,Jane Smith,N/A
Work Chat,individual,N/A,N/A
Friends,group,Alice,+9876543210
```

Note: For group chats, there will be one row per participant.

## Configuration

You can modify these constants at the top of the script:

- `MAX_ITERATIONS`: Number of scroll iterations (default: 50)
- `DOWN_COUNTER`: Number of down key presses per iteration (default: 20)
- `OUTPUT_DIRECTORY`: Where to save the CSV file (default: current directory)
- `OUTPUT_NAME`: Name of the output CSV file (default: "whatsapp_chats.csv")
- `WAIT_TIMEOUT`: Timeout for waiting for elements (default: 10 seconds)

## Notes

- The script uses multiple strategies to detect group chats and extract participants
- WhatsApp Web's HTML structure may change, which could affect the script's functionality
- Phone numbers may not always be available depending on WhatsApp privacy settings
- The script will continue even if it encounters errors with specific chats

## Troubleshooting

- **Can't find participants**: WhatsApp Web's structure may have changed. The script uses multiple fallback strategies.
- **Script too slow**: Reduce `MAX_ITERATIONS` or `DOWN_COUNTER` to process fewer chats
- **StaleElementReferenceException**: This is expected and handled by the script. It occurs when the page updates while scrolling. 
