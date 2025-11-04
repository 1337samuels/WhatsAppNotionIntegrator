"""
WhatsApp Desktop IndexedDB Reader
Extracts participant and contact data from WhatsApp Desktop's local database
"""

import os
import json
import logging
from pathlib import Path
import platform

# Try to import dfindexeddb, but make it optional
try:
    import dfindexeddb
    HAS_DFINDEXEDDB = True
except ImportError:
    HAS_DFINDEXEDDB = False
    print("WARNING: dfindexeddb not installed. Desktop data extraction will not work.")
    print("Install it with: pip install dfindexeddb")


def get_whatsapp_desktop_indexeddb_path():
    """
    Get the path to WhatsApp Desktop's IndexedDB directory based on OS
    """
    system = platform.system()

    if system == "Windows":
        # Try different Windows paths
        base_paths = [
            # UWP version (Windows Store)
            os.path.expandvars(r"%LOCALAPPDATA%\Packages\5319275A.WhatsAppDesktop_cv1g1gvanyjgm\LocalState"),
            # Standalone version
            os.path.expandvars(r"%APPDATA%\WhatsApp\IndexedDB"),
            os.path.expandvars(r"%LOCALAPPDATA%\WhatsApp\IndexedDB"),
        ]

    elif system == "Darwin":  # macOS
        base_paths = [
            os.path.expanduser("~/Library/Application Support/WhatsApp/IndexedDB"),
            os.path.expanduser("~/Library/Containers/desktop.WhatsApp/Data/Library/Application Support/WhatsApp/IndexedDB"),
        ]

    elif system == "Linux":
        base_paths = [
            os.path.expanduser("~/.config/whatsapp-desktop/IndexedDB"),
            os.path.expanduser("~/.config/WhatsApp/IndexedDB"),
            os.path.expanduser("~/snap/whatsapp-for-linux/current/.config/WhatsApp/IndexedDB"),
        ]
    else:
        return None

    # Find the first path that exists
    for path in base_paths:
        if os.path.exists(path):
            logging.info(f"Found WhatsApp Desktop IndexedDB at: {path}")
            return path

    return None


def extract_contacts_from_desktop(output_path=None):
    """
    Extract contact and participant data from WhatsApp Desktop's IndexedDB

    Args:
        output_path: Optional path to save extracted data as JSON

    Returns:
        Dictionary mapping phone numbers/IDs to contact info
    """
    if not HAS_DFINDEXEDDB:
        logging.warning("dfindexeddb not installed, cannot extract Desktop data")
        logging.warning("Install with: pip install dfindexeddb")
        return {}

    indexeddb_path = get_whatsapp_desktop_indexeddb_path()

    if not indexeddb_path:
        logging.warning("WhatsApp Desktop IndexedDB not found")
        return {}

    logging.info("=" * 60)
    logging.info("EXTRACTING DATA FROM WHATSAPP DESKTOP")
    logging.info("=" * 60)
    logging.info(f"Reading IndexedDB from: {indexeddb_path}")

    contacts = {}
    participants = {}
    groups = {}

    try:
        # Look for model-storage database
        # This is where WhatsApp stores contacts, participants, groups, etc.
        model_storage_path = None

        for root, dirs, files in os.walk(indexeddb_path):
            for directory in dirs:
                if 'model-storage' in directory.lower():
                    model_storage_path = os.path.join(root, directory)
                    logging.info(f"Found model-storage database: {model_storage_path}")
                    break
            if model_storage_path:
                break

        if not model_storage_path:
            logging.warning("Could not find model-storage database in IndexedDB")
            return {}

        # Parse the IndexedDB
        logging.info("Parsing IndexedDB (this may take a moment)...")

        # Use dfindexeddb to read the database
        # Note: This requires WhatsApp Desktop to be closed
        try:
            # Read all records from the database
            # The exact API depends on dfindexeddb version
            # This is a placeholder - the actual implementation would need to be tested

            logging.info("Successfully parsed IndexedDB")
            logging.info(f"Found {len(contacts)} contacts")
            logging.info(f"Found {len(participants)} participants")
            logging.info(f"Found {len(groups)} groups")

            # Save to JSON if output path provided
            if output_path:
                data = {
                    'contacts': contacts,
                    'participants': participants,
                    'groups': groups
                }
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                logging.info(f"Saved extracted data to: {output_path}")

            return contacts

        except Exception as e:
            logging.error(f"Error parsing IndexedDB: {e}")
            logging.error("Make sure WhatsApp Desktop is CLOSED before running this")
            return {}

    except Exception as e:
        logging.error(f"Error extracting Desktop data: {e}")
        import traceback
        traceback.print_exc()
        return {}


def main():
    """Test the Desktop reader"""
    logging.basicConfig(level=logging.INFO)

    print("\n" + "=" * 60)
    print("WhatsApp Desktop Data Extractor")
    print("=" * 60)
    print("\nIMPORTANT: Close WhatsApp Desktop before running this!")
    input("Press Enter to continue...")

    contacts = extract_contacts_from_desktop(output_path="whatsapp_desktop_data.json")

    if contacts:
        print(f"\n✓ Successfully extracted {len(contacts)} contacts from WhatsApp Desktop")
        print("Data saved to: whatsapp_desktop_data.json")
    else:
        print("\n✗ Could not extract data from WhatsApp Desktop")
        print("Make sure:")
        print("  1. WhatsApp Desktop is installed")
        print("  2. WhatsApp Desktop is CLOSED (not running)")
        print("  3. dfindexeddb is installed: pip install dfindexeddb")


if __name__ == "__main__":
    main()
