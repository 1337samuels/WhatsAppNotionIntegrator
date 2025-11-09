# CRM Contact Matching Setup Guide

## Prerequisites

### 1. Install the Official Notion Client

Make sure you have the **official** `notion-client` library installed:

```bash
pip install notion-client
```

**Important:** Do NOT install `notion-py` or other unofficial libraries. Use the official `notion-client`.

### 2. Get Your Notion API Key

1. Go to https://www.notion.so/my-integrations
2. Click "+ New integration"
3. Give it a name (e.g., "WhatsApp CRM Integrator")
4. Select the workspace
5. Copy the "Internal Integration Token"

### 3. Share Databases with Your Integration

You need to share BOTH databases with your integration:

1. **Intros Database** (TEMP_DB_ID)
   - Open the database in Notion
   - Click "..." menu → "Add connections"
   - Select your integration

2. **CRM Database** (CRM_DB_ID)
   - Open the database in Notion
   - Click "..." menu → "Add connections"
   - Select your integration

### 4. Get Database IDs

**To get a database ID:**
1. Open the database as a full page in Notion
2. Look at the URL: `https://www.notion.so/{workspace}/{DATABASE_ID}?v=...`
3. The DATABASE_ID is the 32-character string (with or without dashes)

Example:
- URL: `https://www.notion.so/myworkspace/29a37812620f80f2a963daf81ebe558f?v=...`
- Database ID: `29a37812620f80f2a963daf81ebe558f`

### 5. Set Up Your CRM Database

Make sure your CRM database has:
- A **title property** named "Contact" containing the full name of each contact

### 6. Set Up Your Intros Database

Make sure your Intros database has these 3 properties:
- **Connection** (Title property) - Contains the connection name (e.g., "John & Beth")
- **First Side Contact** (Relation property → linked to your CRM database)
- **Second Side Contact** (Relation property → linked to your CRM database)

### 7. Configure chat_parser.py

Edit the top of `chat_parser.py`:

```python
NOTION_SECRET = "secret_xxxxxxxxxxxxxxxxxxxxxxxxxxxx"  # Your integration token
TEMP_DB_ID = "29a37812620f80f2a963daf81ebe558f"  # Your Intros database ID
CRM_DB_ID = "your_crm_database_id_here"  # Your CRM database ID
```

Also update the CSV file path in the `main()` function:

```python
csv_path = "whatsapp_chats.csv"  # Path to your CSV file
```

## How It Works

The script uses the new Notion API pattern:

1. **Retrieve Database**: Gets the database info to extract the data_source ID
   ```python
   db_info = notion.databases.retrieve(database_id=CRM_DB_ID)
   crm_data_source_id = db_info['data_sources'][0]['id']
   ```

2. **Query Data Source**: Uses the data_source ID to search for contacts
   ```python
   response = notion.data_sources.query(
       crm_data_source_id,
       filter={
           "property": "Contact",
           "title": {"contains": search_name}
       }
   )
   ```

## Troubleshooting

### Error: "Could not find database" or "object is not subscriptable"

Make sure you've shared the database with your integration (step 3 above).

### Error: "'data_sources'" or "object has no attribute 'data_sources'"

Your notion-client library might be outdated. Update it:

```bash
pip install --upgrade notion-client
```

### Error: "object has no attribute 'databases'"

Your integration token might be wrong or you need to reinstall the library:

```bash
pip uninstall notion-py notion
pip install notion-client
```

## Usage

Once configured, run:

```bash
python chat_parser.py
```

The script will:
1. Parse connections from the CSV
2. Search your CRM for matching contacts
3. Prompt you to select when multiple matches exist
4. Automatically link contacts to the Intros database
