try:
    from notion_client import Client
except ImportError:
    print("ERROR: notion-client library not found!")
    print("Please install it with: pip install notion-client")
    print("\nNote: Make sure to install 'notion-client', NOT 'notion-py' or 'notion'")
    exit(1)

import re
import csv
import os

# Read configuration from notion_secret.txt
def load_config():
    """Load Notion API credentials from notion_secret.txt"""
    config_file = "notion_secret.txt"

    if not os.path.exists(config_file):
        print(f"ERROR: Configuration file '{config_file}' not found!")
        print(f"\nPlease create a file named '{config_file}' with the following format:")
        print("NOTION_SECRET = \"your_notion_secret_here\"")
        print("CRM_DB_ID = \"your_crm_database_id_here\"")
        print("TEMP_DB_ID = \"your_intros_database_id_here\"")
        exit(1)

    config = {}
    try:
        with open(config_file, 'r') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#'):
                    continue

                # Parse line in format: KEY = "value"
                if '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    config[key] = value

        # Validate required keys
        required_keys = ['NOTION_SECRET', 'CRM_DB_ID', 'TEMP_DB_ID', 'TRANSLATIONS_DB_ID']
        missing_keys = [key for key in required_keys if key not in config]

        if missing_keys:
            print(f"ERROR: Missing required configuration keys: {', '.join(missing_keys)}")
            print(f"\nPlease ensure '{config_file}' contains all required keys:")
            for key in required_keys:
                print(f"  {key} = \"your_value_here\"")
            exit(1)

        return config

    except Exception as e:
        print(f"ERROR: Failed to parse configuration file '{config_file}': {e}")
        exit(1)

# Load configuration
config = load_config()
NOTION_SECRET = config['NOTION_SECRET']
CRM_DB_ID = config['CRM_DB_ID']
TEMP_DB_ID = config['TEMP_DB_ID']
TRANSLATIONS_DB_ID = config['TRANSLATIONS_DB_ID']

print(f"✓ Loaded configuration from notion_secret.txt")
print(f"  - NOTION_SECRET: {NOTION_SECRET[:20]}..." if len(NOTION_SECRET) > 20 else f"  - NOTION_SECRET: {NOTION_SECRET}")
print(f"  - CRM_DB_ID: {CRM_DB_ID}")
print(f"  - TEMP_DB_ID: {TEMP_DB_ID}")
print(f"  - TRANSLATIONS_DB_ID: {TRANSLATIONS_DB_ID}")

class Intros:
    def __init__(self, csv_path):
        self.csv_path = csv_path
        self.intros = []
        self.intro_dict = {}
        self.notion = Client(auth=NOTION_SECRET)
        self.crm_cache = {}  # Cache for CRM search results
        self.translations_cache = {}  # Cache for Hebrew translations

        # Get the data_source ID from the CRM database
        # In the new Notion API, we need to query data_sources, not databases
        print("Retrieving CRM data source ID...")
        try:
            db_info = self.notion.databases.retrieve(database_id=CRM_DB_ID)
            self.crm_data_source_id = db_info['data_sources'][0]['id']
            print(f"✓ CRM data source ID: {self.crm_data_source_id}")
        except Exception as e:
            print(f"✗ Error retrieving CRM database info: {e}")
            print("\nMake sure:")
            print("  1. CRM_DB_ID is set correctly")
            print("  2. Your integration has access to the CRM database")
            print("  3. NOTION_SECRET is valid")
            raise

        # Get the data_source ID from the Translations database
        print("Retrieving Translations data source ID...")
        try:
            db_info = self.notion.databases.retrieve(database_id=TRANSLATIONS_DB_ID)
            self.translations_data_source_id = db_info['data_sources'][0]['id']
            print(f"✓ Translations data source ID: {self.translations_data_source_id}")
        except Exception as e:
            print(f"✗ Error retrieving Translations database info: {e}")
            print("\nMake sure:")
            print("  1. TRANSLATIONS_DB_ID is set correctly")
            print("  2. Your integration has access to the Translations database")
            raise

        # Get the data_source ID from the Intros database for duplicate checking
        print("Retrieving Intros data source ID...")
        try:
            db_info = self.notion.databases.retrieve(database_id=TEMP_DB_ID)
            self.intros_data_source_id = db_info['data_sources'][0]['id']
            print(f"✓ Intros data source ID: {self.intros_data_source_id}")
        except Exception as e:
            print(f"✗ Error retrieving Intros database info: {e}")
            print("\nMake sure:")
            print("  1. TEMP_DB_ID is set correctly")
            print("  2. Your integration has access to the Intros database")
            raise

    def _search_crm_contacts(self, search_name):
        """
        Search the CRM database for contacts containing the given name.
        Returns a list of matching contacts with their IDs and full names.
        """
        # Check cache first
        if search_name in self.crm_cache:
            return self.crm_cache[search_name]

        try:
            # Query the CRM data source using the new Notion API
            # In the new API, we use data_sources.query instead of databases.query
            response = self.notion.data_sources.query(
                self.crm_data_source_id,
                filter={
                    "property": "Contact",
                    "title": {
                        "contains": search_name
                    }
                }
            )

            # Extract contact information from results
            contacts = []
            for page in response.get("results", []):
                page_id = page["id"]
                # Get the Contact title property
                title_prop = page["properties"].get("Contact", {})
                if title_prop.get("title"):
                    full_name = "".join([text["plain_text"] for text in title_prop["title"]])
                    contacts.append({
                        "id": page_id,
                        "name": full_name
                    })

            # Cache the results
            self.crm_cache[search_name] = contacts
            return contacts

        except Exception as e:
            print(f"Error searching CRM for '{search_name}': {e}")
            import traceback
            traceback.print_exc()
            return []

    def _create_crm_contact(self, name):
        """
        Create a new contact in the CRM database.
        Prompts user for the full name and creates the contact.
        If user declines, offers to create a spelling variant mapping.
        Returns the contact ID or None if creation fails.
        """
        print(f"\n{'='*60}")
        print(f"Contact '{name}' not found in CRM")
        print(f"{'='*60}")

        while True:
            add_contact = input("Do you want to add this contact to the CRM? (y/n): ").strip().lower()
            if add_contact in ['y', 'yes', 'n', 'no']:
                break
            print("Please enter 'y' or 'n'")

        if add_contact in ['n', 'no']:
            print("Skipping CRM contact creation")

            # Offer to add a spelling variant mapping
            print("\nThe contact might exist with a different spelling.")
            while True:
                add_variant = input("Do you want to add a spelling variant mapping? (y/n): ").strip().lower()
                if add_variant in ['y', 'yes', 'n', 'no']:
                    break
                print("Please enter 'y' or 'n'")

            if add_variant in ['y', 'yes']:
                return self._create_spelling_variant_and_retry(name)

            return None

        # Prompt for full name
        print(f"\nEnter the full name for this contact (or press Enter to use '{name}'):")
        full_name = input("> ").strip()
        if not full_name:
            full_name = name

        print(f"\nCreating CRM contact: {full_name}")

        try:
            # Create the page in CRM database
            response = self.notion.pages.create(
                parent={"database_id": CRM_DB_ID},
                properties={
                    "Contact": {
                        "title": [
                            {
                                "text": {
                                    "content": full_name
                                }
                            }
                        ]
                    }
                }
            )

            contact_id = response["id"]
            print(f"✓ Created CRM contact: {full_name}")

            # Add to cache
            if name not in self.crm_cache:
                self.crm_cache[name] = []
            self.crm_cache[name].append({
                "id": contact_id,
                "name": full_name
            })

            return contact_id

        except Exception as e:
            print(f"✗ Error creating CRM contact: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _create_spelling_variant_and_retry(self, misspelled_name):
        """
        Create a spelling variant mapping in Translations DB and retry CRM search.
        Used for English names with different spellings (e.g., "Nahman" → "Nachman").
        Returns contact ID if found after mapping, None otherwise.
        """
        print(f"\n{'='*60}")
        print(f"Creating spelling variant for '{misspelled_name}'")
        print(f"{'='*60}")
        print("\nEnter the correct spelling(s) as they appear in the CRM,")
        print("separated by commas (e.g., 'Nachman,Nakhman'):")

        while True:
            user_input = input("> ").strip()
            if user_input:
                break
            print("Please enter at least one correct spelling.")

        # Parse the input
        correct_spellings = [name.strip() for name in user_input.split(',') if name.strip()]

        if not correct_spellings:
            print("No valid spellings provided. Skipping variant creation.")
            return None

        print(f"\nCreating spelling variant: {misspelled_name} → {', '.join(correct_spellings)}")

        try:
            # Create the page in Translations database
            # Using "Hebrew Name" field for the misspelling (even though it's English)
            self.notion.pages.create(
                parent={"database_id": TRANSLATIONS_DB_ID},
                properties={
                    "Hebrew Name": {
                        "title": [
                            {
                                "text": {
                                    "content": misspelled_name
                                }
                            }
                        ]
                    },
                    "English Names": {
                        "rich_text": [
                            {
                                "text": {
                                    "content": ", ".join(correct_spellings)
                                }
                            }
                        ]
                    }
                }
            )

            print(f"✓ Created spelling variant entry")

            # Cache it
            self.translations_cache[misspelled_name] = correct_spellings

            # Now search CRM with the correct spellings
            print(f"\nSearching CRM with correct spelling(s)...")
            all_matches = []
            for correct_name in correct_spellings:
                print(f"  Searching CRM for '{correct_name}'...")
                matches = self._search_crm_contacts(correct_name)
                if matches:
                    # Filter for standalone word matches
                    standalone = self._filter_standalone_matches(matches, correct_name)
                    if standalone:
                        # Add to all_matches, avoiding duplicates by ID
                        for contact in standalone:
                            if not any(c['id'] == contact['id'] for c in all_matches):
                                all_matches.append(contact)

            if not all_matches:
                print(f"No contacts found in CRM for any correct spelling")
                return None

            # If only one match, use it automatically
            if len(all_matches) == 1:
                contact = all_matches[0]
                print(f"Only one contact found: {contact['name']}")
                return contact['id']

            # Multiple matches - prompt user to select
            print(f"\nFound {len(all_matches)} contact(s):")
            selected_contact = self._prompt_user_selection(misspelled_name, all_matches)
            if selected_contact == 'CREATE_NEW':
                # User still wants to create a new contact
                return self._create_crm_contact(misspelled_name)
            elif selected_contact:
                return selected_contact['id']
            else:
                return None

        except Exception as e:
            print(f"✗ Error creating spelling variant entry: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _is_hebrew(self, text):
        """
        Check if text contains Hebrew characters.
        Hebrew Unicode range: \u0590-\u05FF
        """
        return bool(re.search(r'[\u0590-\u05FF]', text))

    def _lookup_hebrew_translation(self, hebrew_name):
        """
        Look up Hebrew name in Translations database.
        Returns list of English spellings, or None if not found.
        """
        # Check cache first
        if hebrew_name in self.translations_cache:
            return self.translations_cache[hebrew_name]

        try:
            # Query the Translations database for this Hebrew name
            response = self.notion.data_sources.query(
                self.translations_data_source_id,
                filter={
                    "property": "Hebrew Name",
                    "title": {
                        "equals": hebrew_name
                    }
                }
            )

            results = response.get("results", [])
            if not results:
                return None

            # Get the first matching page
            page = results[0]
            english_names_prop = page["properties"].get("English Names", {})

            # Extract English names from rich_text property
            if english_names_prop.get("rich_text"):
                english_names_text = "".join([text["plain_text"] for text in english_names_prop["rich_text"]])
                # Split by comma and strip whitespace
                english_names = [name.strip() for name in english_names_text.split(',') if name.strip()]

                # Cache the result
                self.translations_cache[hebrew_name] = english_names
                return english_names

            return None

        except Exception as e:
            print(f"Error looking up Hebrew translation for '{hebrew_name}': {e}")
            import traceback
            traceback.print_exc()
            return None

    def _create_hebrew_translation(self, hebrew_name):
        """
        Create a new translation entry for a Hebrew name.
        Prompts user for English spellings and creates the page in Translations DB.
        Returns list of English spellings.
        """
        print(f"\n{'='*60}")
        print(f"Hebrew name '{hebrew_name}' not found in Translations database")
        print(f"{'='*60}")
        print("\nPlease enter all possible English spellings for this name,")
        print("separated by commas (e.g., 'Ittai,Itay,Itai'):")

        while True:
            user_input = input("> ").strip()
            if user_input:
                break
            print("Please enter at least one English spelling.")

        # Parse the input
        english_names = [name.strip() for name in user_input.split(',') if name.strip()]

        if not english_names:
            print("No valid English names provided. Skipping translation creation.")
            return []

        print(f"\nCreating translation: {hebrew_name} → {', '.join(english_names)}")

        try:
            # Create the page in Translations database
            self.notion.pages.create(
                parent={"database_id": TRANSLATIONS_DB_ID},
                properties={
                    "Hebrew Name": {
                        "title": [
                            {
                                "text": {
                                    "content": hebrew_name
                                }
                            }
                        ]
                    },
                    "English Names": {
                        "rich_text": [
                            {
                                "text": {
                                    "content": ", ".join(english_names)
                                }
                            }
                        ]
                    }
                }
            )

            print(f"✓ Created translation entry")

            # Cache it
            self.translations_cache[hebrew_name] = english_names
            return english_names

        except Exception as e:
            print(f"✗ Error creating translation entry: {e}")
            import traceback
            traceback.print_exc()
            return []

    def _filter_standalone_matches(self, contacts, search_name):
        """
        Filter contacts to only include those where the search name appears as a standalone word.
        For example, 'John' matches 'John Smith' and 'Danny John' but not 'Johnson'.
        """
        filtered = []
        # Create a regex pattern that matches the search name as a standalone word
        # \b is word boundary - ensures the name is not part of another word
        pattern = r'\b' + re.escape(search_name) + r'\b'

        for contact in contacts:
            # Case-insensitive search
            if re.search(pattern, contact["name"], re.IGNORECASE):
                filtered.append(contact)

        return filtered

    def _prompt_user_selection(self, search_name, contacts):
        """
        Prompt the user to select from multiple contact matches.
        Returns the selected contact or None if user skips.
        Returns 'CREATE_NEW' string if user wants to create a new contact.
        """
        print(f"\nMultiple contacts found for '{search_name}':")
        for i, contact in enumerate(contacts, 1):
            print(f"  {i}. {contact['name']}")
        print(f"  0. Skip (don't link to any contact)")
        print(f"  n. Create new contact")

        while True:
            try:
                choice = input(f"Select which contact to use (0-{len(contacts)}, or 'n' for new): ").strip().lower()

                # Check if user wants to create new contact
                if choice in ['n', 'new', 'c', 'create']:
                    return 'CREATE_NEW'

                choice_num = int(choice)

                if choice_num == 0:
                    print(f"  Skipping contact for '{search_name}'")
                    return None
                elif 1 <= choice_num <= len(contacts):
                    selected = contacts[choice_num - 1]
                    print(f"  Selected: {selected['name']}")
                    return selected
                else:
                    print(f"  Invalid choice. Please enter a number between 0 and {len(contacts)}, or 'n' for new")
            except ValueError:
                # Not a number, check if it's a create command
                if choice in ['n', 'new', 'c', 'create']:
                    return 'CREATE_NEW'
                print(f"  Invalid input. Please enter a number between 0 and {len(contacts)}, or 'n' for new")
            except KeyboardInterrupt:
                print("\n  Skipping contact selection")
                return None

    def _resolve_name_to_contact(self, name):
        """
        Resolve a single name to a CRM contact.
        Handles both English and Hebrew names.
        For Hebrew names, looks up translations and searches CRM with English spellings.
        Returns the contact ID or None if no match or user skips.
        """
        # Check if name is in Hebrew
        if self._is_hebrew(name):
            print(f"\nDetected Hebrew name: {name}")

            # Look up translation
            english_spellings = self._lookup_hebrew_translation(name)

            # If not found, create new translation
            if english_spellings is None:
                english_spellings = self._create_hebrew_translation(name)

            if not english_spellings:
                print(f"No English spellings provided for '{name}'. Cannot search CRM.")
                return None

            print(f"English spellings for '{name}': {', '.join(english_spellings)}")

            # Search CRM for all English spellings and collect all matches
            all_matches = []
            for english_name in english_spellings:
                print(f"  Searching CRM for '{english_name}'...")
                matches = self._search_crm_contacts(english_name)
                if matches:
                    # Filter for standalone word matches
                    standalone = self._filter_standalone_matches(matches, english_name)
                    if standalone:
                        # Add to all_matches, avoiding duplicates by ID
                        for contact in standalone:
                            if not any(c['id'] == contact['id'] for c in all_matches):
                                all_matches.append(contact)

            if not all_matches:
                print(f"No contacts found in CRM for any English spelling of '{name}'")
                # Offer to create new contact
                return self._create_crm_contact(name)

            # If only one match, use it automatically
            if len(all_matches) == 1:
                contact = all_matches[0]
                print(f"Only one contact found for '{name}': {contact['name']}")
                return contact['id']

            # Multiple matches - prompt user to select
            print(f"\nFound {len(all_matches)} contact(s) for Hebrew name '{name}':")
            selected_contact = self._prompt_user_selection(name, all_matches)
            if selected_contact == 'CREATE_NEW':
                # User wants to create a new contact
                return self._create_crm_contact(name)
            elif selected_contact:
                return selected_contact['id']
            else:
                return None

        else:
            # English name - check if there's a spelling variant in Translations DB
            # This handles cases like "Nahman" → "Nachman"
            spelling_variants = self._lookup_hebrew_translation(name)

            if spelling_variants:
                # Found a spelling variant mapping
                print(f"\nFound spelling variant(s) for '{name}': {', '.join(spelling_variants)}")

                # Search CRM for all spelling variants
                all_matches = []
                for variant_name in spelling_variants:
                    print(f"  Searching CRM for '{variant_name}'...")
                    matches = self._search_crm_contacts(variant_name)
                    if matches:
                        # Filter for standalone word matches
                        standalone = self._filter_standalone_matches(matches, variant_name)
                        if standalone:
                            # Add to all_matches, avoiding duplicates by ID
                            for contact in standalone:
                                if not any(c['id'] == contact['id'] for c in all_matches):
                                    all_matches.append(contact)

                if not all_matches:
                    print(f"No contacts found in CRM for any spelling variant of '{name}'")
                    # Offer to create new contact
                    return self._create_crm_contact(name)

                # If only one match, use it automatically
                if len(all_matches) == 1:
                    contact = all_matches[0]
                    print(f"Only one contact found for '{name}': {contact['name']}")
                    return contact['id']

                # Multiple matches - prompt user to select
                print(f"\nFound {len(all_matches)} contact(s) for '{name}':")
                selected_contact = self._prompt_user_selection(name, all_matches)
                if selected_contact == 'CREATE_NEW':
                    # User wants to create a new contact
                    return self._create_crm_contact(name)
                elif selected_contact:
                    return selected_contact['id']
                else:
                    return None

            # No spelling variants - search CRM directly
            # Search CRM for contacts containing this name
            all_matches = self._search_crm_contacts(name)

            if not all_matches:
                print(f"No contacts found in CRM for '{name}'")
                # Offer to create new contact
                return self._create_crm_contact(name)

            # Filter for standalone word matches
            standalone_matches = self._filter_standalone_matches(all_matches, name)

            if not standalone_matches:
                print(f"No standalone word matches found for '{name}' (found {len(all_matches)} partial matches)")
                # Offer to create new contact
                return self._create_crm_contact(name)

            # If only one match, use it automatically
            if len(standalone_matches) == 1:
                contact = standalone_matches[0]
                print(f"Only one contact found for '{name}': {contact['name']}")
                return contact['id']

            # Multiple matches - prompt user to select
            selected_contact = self._prompt_user_selection(name, standalone_matches)
            if selected_contact == 'CREATE_NEW':
                # User wants to create a new contact
                return self._create_crm_contact(name)
            elif selected_contact:
                return selected_contact['id']
            else:
                return None

    def _connection_exists(self, connection_name):
        """
        Check if a connection already exists in the Intros database.
        Returns True if it exists, False otherwise.
        """
        try:
            # Query the Intros database for this connection name
            response = self.notion.data_sources.query(
                self.intros_data_source_id,
                filter={
                    "property": "Connection",
                    "title": {
                        "equals": connection_name
                    }
                }
            )

            results = response.get("results", [])
            return len(results) > 0

        except Exception as e:
            print(f"Error checking for duplicate connection '{connection_name}': {e}")
            import traceback
            traceback.print_exc()
            # If there's an error, assume it doesn't exist to avoid blocking
            return False

    def _resolve_side_to_contacts(self, side):
        """
        Resolve one side of a connection to CRM contact IDs.
        Handles both single names and multiple names (e.g., "John&Mary").
        Returns a list of contact IDs.
        """
        contact_ids = []

        # If side is a string, it's a single name
        if isinstance(side, str):
            contact_id = self._resolve_name_to_contact(side.strip())
            if contact_id:
                contact_ids.append(contact_id)
        # If side is a list/tuple, it has multiple names
        elif isinstance(side, (list, tuple)):
            for name in side:
                contact_id = self._resolve_name_to_contact(name.strip())
                if contact_id:
                    contact_ids.append(contact_id)

        return contact_ids

    def _parse_inner_side(self, side):
        if "," in side:
            delimiter = ","
        elif "+" in side:
            delimiter = "+"
        elif "&" in side:
            delimiter = "&"
        elif "וינר ו" in side:
            delimiter = "וינר ו"
        elif " ו" in side and "וינר" not in side:
            delimiter = " ו"
        else:
            return side.strip()
        new_parties = side.split(delimiter)
        if len(new_parties) != 2:
            print(f"Found {len(new_parties)} parties for {side}")
        return [new_party.strip() for new_party in new_parties]

    def parse_csv(self):
        """
        Parse the CSV file generated by scrape_whatsapp_chats.py.
        Extracts unique chat names (connections) from the chat_name column.
        """
        seen_chats = set()

        with open(self.csv_path, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)

            for row in reader:
                chat_name = row.get('chat_name', '').strip()

                # Skip if empty or already processed
                if not chat_name or chat_name in seen_chats:
                    continue

                seen_chats.add(chat_name)

                # Parse the chat name to extract sides
                delimiter = None
                if "//" in chat_name:
                    delimiter = "//"
                elif "/" in chat_name:
                    delimiter = "/"
                elif "<>" in chat_name:
                    delimiter = "<>"
                elif "x" in chat_name:
                    delimiter = "x"
                else:
                    print(f"Warning: No delimiter found in chat name: {chat_name}")
                    continue

                sides = chat_name.split(delimiter)
                if len(sides) != 2:
                    print(f"Warning: Found {len(sides)} sides for {chat_name}")
                    continue

                # Parse each side for multiple names
                first_side = self._parse_inner_side(sides[0])
                second_side = self._parse_inner_side(sides[1])

                self.intros.append((first_side, second_side))

        print(f"\nParsed {len(self.intros)} unique connections from CSV")

    def insert_to_notion_with_crm_links(self):
        """
        Insert connections to Notion with CRM contact relations.
        Searches CRM for each name and creates relation links.
        """
        for i in range(len(self.intros)):
            print(f"\n{'='*60}")
            print(f"Processing connection {i+1}/{len(self.intros)}")
            print(f"{'='*60}")

            first_side = self.intros[i][0]
            second_side = self.intros[i][1]

            # Format names for display
            first_side_display = first_side
            second_side_display = second_side
            if isinstance(first_side, (list, tuple)):
                first_side_display = f"({first_side[0]}&{first_side[1]})"
            if isinstance(second_side, (list, tuple)):
                second_side_display = f"({second_side[0]}&{second_side[1]})"

            connection_name = f"{first_side_display} & {second_side_display}"
            print(f"\nConnection: {connection_name}")

            # Check if this connection already exists
            if self._connection_exists(connection_name):
                print(f"⊗ Connection already exists in database. Skipping...")
                continue

            # Resolve both sides to CRM contact IDs
            print(f"\n--- Resolving First Side: {first_side_display} ---")
            first_side_contact_ids = self._resolve_side_to_contacts(first_side)

            print(f"\n--- Resolving Second Side: {second_side_display} ---")
            second_side_contact_ids = self._resolve_side_to_contacts(second_side)

            # Build properties for the Notion page - only 3 fields
            properties = {
                "Connection": {
                    "title": [
                        {
                            "text": {
                                "content": connection_name
                            }
                        }
                    ]
                }
            }

            # Add relation properties if we found contacts
            if first_side_contact_ids:
                properties["First Side Contact"] = {
                    "relation": [{"id": contact_id} for contact_id in first_side_contact_ids]
                }
                print(f"\n✓ Linked {len(first_side_contact_ids)} contact(s) for first side")
            else:
                print(f"\n⚠ No CRM contacts linked for first side")

            if second_side_contact_ids:
                properties["Second Side Contact"] = {
                    "relation": [{"id": contact_id} for contact_id in second_side_contact_ids]
                }
                print(f"✓ Linked {len(second_side_contact_ids)} contact(s) for second side")
            else:
                print(f"⚠ No CRM contacts linked for second side")

            # Create the page in Notion
            try:
                self.notion.pages.create(
                    parent={"database_id": TEMP_DB_ID},
                    properties=properties
                )
                print(f"\n✓ Created Notion page for: {connection_name}")
            except Exception as e:
                print(f"\n✗ Error creating Notion page: {e}")

    def insert_to_notion_test(self):
        """Legacy function - kept for backwards compatibility"""
        for i in range(len(self.intros)):
            first_side_to_add = self.intros[i][0]
            second_side_to_add = self.intros[i][1]
            if isinstance(first_side_to_add, list) or isinstance(second_side_to_add, tuple):
                first_side_to_add = f"({first_side_to_add[0]}&{first_side_to_add[1]})"
            if isinstance(second_side_to_add, list) or isinstance(second_side_to_add, tuple):
                second_side_to_add = f"({second_side_to_add[0]}&{second_side_to_add[1]})"

            self.notion.pages.create(parent={"database_id": TEMP_DB_ID},
                                     properties={"Connection":
                                         { "title":
                                             [
                                                 {"text":
                                                      {"content":f"{first_side_to_add} & {second_side_to_add}"},
                                                  }
                                             ]
                                         },
                                         "First Side": {"rich_text": [
                    {
                        "text": {
                            "content": first_side_to_add
                        }
                    }
                ]},
                                         "Second Side": {"rich_text": [
                                             {
                                                 "text": {
                                                     "content": second_side_to_add
                                                 }
                                             }
                                         ]}

                                     }
                                     )




def main():
    # Update this path to your CSV file
    csv_path = "whatsapp_chats.csv"  # TODO: Update with your CSV file path

    print("WhatsApp to Notion CRM Integrator")
    print("="*60)
    print(f"CSV file: {csv_path}")
    print("="*60)

    intros = Intros(csv_path)
    intros.parse_csv()

    print(f"\nFound {len(intros.intros)} connections:")
    for i, intro in enumerate(intros.intros, 1):
        print(f"  {i}. {intro[0]} <> {intro[1]}")

    print("\n" + "="*60)
    print("Starting CRM matching and Notion insertion...")
    print("="*60)

    intros.insert_to_notion_with_crm_links()

    print("\n" + "="*60)
    print("✓ Complete!")
    print("="*60)

if __name__ == "__main__":
    main()