try:
    from notion_client import Client
except ImportError:
    print("ERROR: notion-client library not found!")
    print("Please install it with: pip install notion-client")
    print("\nNote: Make sure to install 'notion-client', NOT 'notion-py' or 'notion'")
    exit(1)

import re
import csv

# TODO: Fill in your Notion API key
# Get this from: https://www.notion.so/my-integrations
NOTION_SECRET = "Samuels you need to fill this manually!"  # TODO: Fix

# Database IDs - get these from the database URLs
TEMP_DB_ID = "29a37812620f80f2a963daf81ebe558f"  # Intros database
CRM_DB_ID = "Samuels you need to fill this manually!"  # TODO: Fix - CRM database

class Intros:
    def __init__(self, csv_path):
        self.csv_path = csv_path
        self.intros = []
        self.intro_dict = {}
        self.notion = Client(auth=NOTION_SECRET)
        self.crm_cache = {}  # Cache for CRM search results

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
        """
        print(f"\nMultiple contacts found for '{search_name}':")
        for i, contact in enumerate(contacts, 1):
            print(f"  {i}. {contact['name']}")
        print(f"  0. Skip (don't link to any contact)")

        while True:
            try:
                choice = input(f"Select which contact to use (0-{len(contacts)}): ").strip()
                choice_num = int(choice)

                if choice_num == 0:
                    print(f"  Skipping contact for '{search_name}'")
                    return None
                elif 1 <= choice_num <= len(contacts):
                    selected = contacts[choice_num - 1]
                    print(f"  Selected: {selected['name']}")
                    return selected
                else:
                    print(f"  Invalid choice. Please enter a number between 0 and {len(contacts)}")
            except ValueError:
                print(f"  Invalid input. Please enter a number between 0 and {len(contacts)}")
            except KeyboardInterrupt:
                print("\n  Skipping contact selection")
                return None

    def _resolve_name_to_contact(self, name):
        """
        Resolve a single name to a CRM contact.
        Searches CRM, filters for standalone matches, and prompts user if multiple matches found.
        Returns the contact ID or None if no match or user skips.
        """
        # Search CRM for contacts containing this name
        all_matches = self._search_crm_contacts(name)

        if not all_matches:
            print(f"No contacts found in CRM for '{name}'")
            return None

        # Filter for standalone word matches
        standalone_matches = self._filter_standalone_matches(all_matches, name)

        if not standalone_matches:
            print(f"No standalone word matches found for '{name}' (found {len(all_matches)} partial matches)")
            return None

        # If only one match, use it automatically
        if len(standalone_matches) == 1:
            contact = standalone_matches[0]
            print(f"Only one contact found for '{name}': {contact['name']}")
            return contact['id']

        # Multiple matches - prompt user to select
        selected_contact = self._prompt_user_selection(name, standalone_matches)
        if selected_contact:
            return selected_contact['id']
        else:
            return None

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