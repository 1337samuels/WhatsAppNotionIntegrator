# WhatsApp Desktop Mode Guide

## The Problem

When you leave a WhatsApp group, **WhatsApp Web loses participant information** and only shows phone numbers. However, **WhatsApp Desktop retains this information** in its local cache, continuing to display participant names even after you've left the group.

This is because WhatsApp Desktop stores participant data locally in an IndexedDB database, while WhatsApp Web doesn't maintain this persistent cache.

## The Solution

This scraper's "Desktop Mode" extracts participant data directly from WhatsApp Desktop's local database, giving you access to those cached participant names that Web doesn't have.

## Requirements

### 1. WhatsApp Desktop Installed

Download and install WhatsApp Desktop:
- **Windows**: [Microsoft Store](https://www.microsoft.com/store/apps/whatsapp) or [whatsapp.com/download](https://www.whatsapp.com/download)
- **macOS**: [whatsapp.com/download](https://www.whatsapp.com/download)
- **Linux**: Snap Store (`snap install whatsapp-for-linux`) or [whatsapp.com/download](https://www.whatsapp.com/download)

### 2. Python Packages

```bash
pip install selenium
pip install dfindexeddb
```

**Note**: `dfindexeddb` is a forensic tool for reading IndexedDB/LevelDB databases. It's essential for Desktop mode.

## How to Use Desktop Mode

### Step 1: Configure the Mode

Open `scrape_whatsapp_chats.py` and set:

```python
WHATSAPP_MODE = 'desktop'
```

### Step 2: Ensure Desktop Has the Data

Before running the scraper:

1. **Open WhatsApp Desktop** and let it fully sync
2. **Browse through your groups** - especially the introduction groups you want to scrape
3. Click into each group to load participant information
4. Let Desktop run for a while to ensure all data is cached locally
5. **Close WhatsApp Desktop** (required for database access)

### Step 3: Run the Scraper

```bash
python scrape_whatsapp_chats.py
```

The scraper will:
1. Extract participant/contact data from WhatsApp Desktop's local database
2. Open WhatsApp Web for UI automation
3. Scrape introduction groups
4. Enrich the data with Desktop's cached participant information

## How It Works

### Desktop Mode Process:

```
┌─────────────────────────────────────┐
│  1. Close WhatsApp Desktop          │
│                                     │
│  2. Read IndexedDB database         │
│     - Location: AppData/WhatsApp    │
│     - Database: model-storage       │
│     - Extract: contacts,            │
│                participants,        │
│                groups               │
└─────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────┐
│  3. Open WhatsApp Web               │
│     (for UI automation)             │
│                                     │
│  4. Scrape introduction groups      │
│     - Click each group              │
│     - Extract participant list      │
└─────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────┐
│  5. Merge data                      │
│     - Web UI data (current groups)  │
│     - Desktop cache (all groups)    │
│                                     │
│  6. Output enriched CSV             │
│     with participant names          │
└─────────────────────────────────────┘
```

## Database Locations

WhatsApp Desktop stores its IndexedDB in these locations:

### Windows
- **UWP Version** (Microsoft Store):
  ```
  %LOCALAPPDATA%\Packages\5319275A.WhatsAppDesktop_cv1g1gvanyjgm\LocalState
  ```
- **Standalone Version**:
  ```
  %APPDATA%\WhatsApp\IndexedDB
  %LOCALAPPDATA%\WhatsApp\IndexedDB
  ```

### macOS
```
~/Library/Application Support/WhatsApp/IndexedDB
~/Library/Containers/desktop.WhatsApp/Data/Library/Application Support/WhatsApp/IndexedDB
```

### Linux
```
~/.config/whatsapp-desktop/IndexedDB
~/.config/WhatsApp/IndexedDB
~/snap/whatsapp-for-linux/current/.config/WhatsApp/IndexedDB
```

## Troubleshooting

### "WhatsApp Desktop database not found"

**Solution:**
1. Ensure WhatsApp Desktop is installed
2. Open WhatsApp Desktop at least once and log in
3. Browse some groups to populate the database
4. Check the database path exists for your OS (see locations above)

### "Cannot read database / File locked"

**Solution:**
- **Close WhatsApp Desktop completely** before running the scraper
- The IndexedDB files are locked while the app is running
- Make sure it's not just minimized - it must be completely closed

### "dfindexeddb not installed"

**Solution:**
```bash
pip install dfindexeddb
```

If that doesn't work:
```bash
pip install --upgrade pip
pip install dfindexeddb
```

### "No contacts extracted from Desktop"

**Possible causes:**
1. **First time using Desktop**: The database needs to be populated by using the app
2. **Fresh install**: Browse your groups in Desktop first to cache participant data
3. **Different account**: Make sure Desktop is logged into the account you want to scrape
4. **Database format changed**: WhatsApp may have updated their database structure

**Solution:**
- Use WhatsApp Desktop for a few days first
- Open and browse through your introduction groups
- Let the app fully sync before extracting

### Fallback to Web Mode

If Desktop mode fails for any reason, the scraper automatically falls back to Web mode. You'll still get data, but it won't have Desktop's cached participant information for groups you've left.

## Manual Alternative

If the automated Desktop extraction doesn't work, you can manually export data from WhatsApp Desktop:

1. Open WhatsApp Desktop
2. For each introduction group:
   - Click the group
   - Click the group name at the top
   - Scroll through all participants
   - Take screenshots or manually copy names
3. Use `web` mode for the scraper
4. Manually enrich the CSV file with the participant names you collected

## Why This Matters

**Example scenario:**

You were in an introduction group "Alice / Bob" months ago but left the group.

- **WhatsApp Web shows**: `+1234567890, +9876543210`
- **WhatsApp Desktop shows**: `Alice Smith, Bob Johnson`

Desktop mode extracts Desktop's cache, so your CSV output will have actual names instead of just phone numbers, even for groups you've left!

## Privacy & Security

**Is this safe?**
- Yes, you're reading **your own** WhatsApp data
- The data is stored locally on your computer
- No data is sent anywhere - everything stays on your machine
- The script only reads, never writes or modifies WhatsApp data

**What data is extracted?**
- Contact names and phone numbers
- Group participant lists
- Group metadata (names, member counts)
- **Not extracted**: Message content, media, or any encrypted data

## Limitations

1. **Desktop must be closed**: Can't read database while app is running
2. **Requires dfindexeddb**: Additional dependency needed
3. **Platform-specific**: Database locations vary by OS
4. **Cache dependency**: Only shows data that Desktop has cached
5. **Format changes**: WhatsApp updates may break compatibility

## When to Use Web Mode Instead

Use `WHATSAPP_MODE = 'web'` if:
- You only need current group participants (not left groups)
- You want simpler setup without dfindexeddb
- You're okay with phone numbers instead of names for some participants
- Desktop mode isn't working for your setup

Web mode is simpler and more reliable, but won't have Desktop's participant cache.
