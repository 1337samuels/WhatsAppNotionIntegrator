from time import sleep
import csv
from os.path import join, exists
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver import Keys
from selenium.webdriver.common.by import By
from selenium.common.exceptions import StaleElementReferenceException, NoSuchElementException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

WHATSAPP_URL = 'https://web.whatsapp.com/'
MAX_ITERATIONS = 50
DOWN_COUNTER = 20
CHAT_DIV = "_ak8q"
PANE_SIDE_DIV = "_ak9y"
#OUTPUT_DIRECTORY = r"C:\Users\gilad\OneDrive\Desktop\Netz\Whatsapp exporter"
OUTPUT_DIRECTORY = "."
OUTPUT_NAME = "whatsapp_chats.csv"
WAIT_TIMEOUT = 10

# Introduction group delimiters from chat_parser.py
INTRO_DELIMITERS = ["//", "/", "<>", "x"]


def is_introduction_group(chat_name):
    """Check if chat name matches introduction group format from chat_parser.py"""
    # Check if the chat name contains any of the introduction delimiters
    for delimiter in INTRO_DELIMITERS:
        if delimiter in chat_name:
            print(f"  ✓ Matches introduction format with delimiter: '{delimiter}'")
            return True
    return False


def is_archive_chat(chat_name):
    """Check if this is the Archive chat"""
    return chat_name.lower().strip() in ['archive', 'archived']


def is_group_chat(driver):
    """Check if the currently opened chat is a group by looking at the subtitle under chat name"""
    try:
        # Find the CORRECT header - the one in the main chat area, not sidebar
        # WhatsApp has multiple headers, we need the one in the conversation panel

        # Try to find the conversation/chat panel first
        header = None

        # Strategy 1: Look for header within the main conversation area
        try:
            # Common selectors for the main chat panel
            chat_panel_selectors = [
                'div[data-testid="conversation-panel-wrapper"]',
                'div[data-testid="conversation-header"]',
                'div#main',
                'div.main',
            ]

            for selector in chat_panel_selectors:
                try:
                    chat_panel = driver.find_element(By.CSS_SELECTOR, selector)
                    header = chat_panel.find_element(By.TAG_NAME, 'header')
                    print(f"  Found header using panel selector: {selector}")
                    break
                except:
                    continue
        except:
            pass

        # Strategy 2: If we didn't find it in a panel, get all headers and use the last one
        # (sidebar headers come first, chat header comes last)
        if not header:
            try:
                headers = driver.find_elements(By.TAG_NAME, 'header')
                print(f"  Found {len(headers)} header elements total")
                if len(headers) >= 2:
                    # Use the second header (first is usually sidebar)
                    header = headers[1]
                    print(f"  Using header index 1 (second header)")
                elif len(headers) == 1:
                    header = headers[0]
                    print(f"  Only one header found, using it")
            except:
                pass

        if not header:
            print("  ERROR: Could not find any header element")
            return False

        # Debug: Print all text in header
        header_full_text = header.text
        print(f"  Header full text:\n{header_full_text}")

        # Split by newlines to get separate lines
        lines = [line.strip() for line in header_full_text.split('\n') if line.strip()]
        print(f"  Header lines: {lines}")

        # Usually the structure is:
        # Line 0: Chat name
        # Line 1: Subtitle (participant names for groups, "click here..." for contacts)

        subtitle_text = ""

        if len(lines) >= 2:
            # The second line is typically the subtitle
            subtitle_text = lines[1].lower()
            print(f"  Subtitle text (from lines): '{subtitle_text}'")
        else:
            print(f"  Only found {len(lines)} line(s) in header, trying other methods...")

            # Try to find specific elements
            try:
                # Look for all span elements and get their text
                spans = header.find_elements(By.TAG_NAME, 'span')
                print(f"  Found {len(spans)} span elements in header")

                # Try to find the subtitle by looking for spans that aren't the title
                span_texts = []
                for i, span in enumerate(spans):
                    text = span.text.strip()
                    if text:
                        span_texts.append(text)
                        print(f"    Span {i}: '{text}'")

                # Look for a span that looks like a subtitle (not the chat name)
                # The subtitle is usually shorter and contains specific patterns
                chat_name = lines[0] if lines else ""
                for text in span_texts:
                    if text != chat_name and len(text) > 0:
                        subtitle_text = text.lower()
                        print(f"  Found potential subtitle: '{subtitle_text}'")
                        break

            except Exception as e:
                print(f"  Error getting spans: {e}")

        if not subtitle_text:
            print(f"  Could not find subtitle text")
            # Try one more method - get all divs in header
            try:
                divs = header.find_elements(By.TAG_NAME, 'div')
                print(f"  Trying {len(divs)} div elements...")
                for i, div in enumerate(divs):
                    text = div.text.strip()
                    if text and '\n' not in text and len(text) > 5 and len(text) < 100:
                        # This might be a subtitle
                        if i > 0:  # Not the first div (which is likely the title)
                            subtitle_text = text.lower()
                            print(f"    Found subtitle from div {i}: '{subtitle_text}'")
                            break
            except Exception as e:
                print(f"  Error getting divs: {e}")

        print(f"  Final subtitle text: '{subtitle_text}'")

        # Individual contacts typically say "click here for contact info" or "tap here for contact info"
        contact_keywords = ['click here for contact info', 'tap here for contact info',
                           'click for contact info', 'tap for contact info',
                           'select for contact info']
        group_keywords = ['click here for group info', 'tap here for group info',
                           'click for group info', 'tap for group info',
                           'select for group info', ',']

        if any(keyword in subtitle_text for keyword in contact_keywords):
            print(f"  → Detected as INDIVIDUAL (contact info message)")
            return False

        # Groups show participant names (comma-separated) or participant count
        # If subtitle contains commas, it's likely a list of participants
        if any(keyword in subtitle_text for keyword in group_keywords):
            print(f"  → Detected as GROUP (participant list with commas)")
            return True

        # Groups may also show "you, person1, person2" or similar
        if 'you' in subtitle_text and len(subtitle_text) > 10:
            print(f"  → Detected as GROUP (contains 'you' with other names)")
            return True

        # Check for participant count indicators
        if any(keyword in subtitle_text for keyword in ['participants', 'members', 'participant', 'member']):
            print(f"  → Detected as GROUP (participant/member count)")
            return True

        # If we have a subtitle that's not a contact info message and has some length,
        # it's likely a group showing participant names
        if subtitle_text and len(subtitle_text) > 5 and not any(keyword in subtitle_text for keyword in contact_keywords):
            print(f"  → Detected as GROUP (has subtitle, not contact info)")
            return True

        # Default to not a group if we can't determine
        print(f"  → Could not determine, defaulting to NOT a group")
        return False

    except Exception as e:
        print(f"  Error checking if group: {e}")
        import traceback
        traceback.print_exc()
        return False


def get_group_participants(driver):
    """Extract FULL participant names by clicking into group info"""
    participants = []

    try:
        print("  Opening group info to extract full names...")

        # Find the CORRECT header - the one in the main chat area
        header = None

        # Strategy 1: Look for header within the main conversation area
        try:
            chat_panel_selectors = [
                'div[data-testid="conversation-panel-wrapper"]',
                'div[data-testid="conversation-header"]',
                'div#main',
                'div.main',
            ]

            for selector in chat_panel_selectors:
                try:
                    chat_panel = driver.find_element(By.CSS_SELECTOR, selector)
                    header = chat_panel.find_element(By.TAG_NAME, 'header')
                    break
                except:
                    continue
        except:
            pass

        # Strategy 2: Get all headers and use the second one (chat header, not sidebar)
        if not header:
            headers = driver.find_elements(By.TAG_NAME, 'header')
            if len(headers) >= 2:
                header = headers[1]
            elif len(headers) == 1:
                header = headers[0]

        if not header:
            print("  ERROR: Could not find header element")
            return participants

        # Click on the header to open group info
        try:
            # Find a clickable element in the header
            clickable_area = header.find_element(By.CSS_SELECTOR, 'div[role="button"]')
            clickable_area.click()
            print("  Clicked header to open group info")
            sleep(3)  # Wait for panel to open
        except Exception as e:
            print(f"  Error clicking header: {e}, trying alternative...")
            try:
                header.click()
                sleep(3)
            except Exception as e2:
                print(f"  Could not open group info: {e2}")
                return participants

        # Now look for the participant list in the group info panel
        # Scroll down in the group info to load all participants
        try:
            # Find the scrollable container in group info
            scrollable_containers = driver.find_elements(By.CSS_SELECTOR, 'div[data-testid="drawer-right"]')
            if not scrollable_containers:
                scrollable_containers = driver.find_elements(By.CSS_SELECTOR, 'div.pane-side')

            if scrollable_containers:
                container = scrollable_containers[0]
                # Scroll down a few times to load all participants
                for _ in range(5):
                    driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", container)
                    sleep(0.3)
                print("  Scrolled group info panel")
        except Exception as e:
            print(f"  Warning: Could not scroll group info: {e}")

        # Extract participants - look for contact cells/listitems
        print("  Extracting participant names from group info...")

        # Strategy 1: Look for list items with contact information
        contact_cells = driver.find_elements(By.CSS_SELECTOR, 'div[role="listitem"]')

        for cell in contact_cells:
            try:
                # Get all spans with dir="auto" (usually contains names)
                name_spans = cell.find_elements(By.CSS_SELECTOR, 'span[dir="auto"]')

                for span in name_spans:
                    name = span.text.strip()

                    # Filter out non-participant text
                    if (name and len(name) > 1 and
                        name not in ['You', 'Admin', 'Group Admin', 'Participants', 'Members', 'Group info'] and
                        not any(keyword in name.lower() for keyword in ['add participant', 'invite link', 'group settings', 'search'])):

                        # Check if we already have this participant
                        if not any(p['name'] == name for p in participants):
                            # Determine if it's a phone number or name
                            if name.startswith('+') or (name.replace('-', '').replace(' ', '').replace('(', '').replace(')', '').isdigit() and len(name) > 8):
                                participants.append({"name": name, "phone": name})
                            else:
                                participants.append({"name": name, "phone": "N/A"})
                            print(f"    - Found: {name}")
                        break  # Only take first valid name from this cell

            except Exception as e:
                continue

        # Close the group info panel
        sleep(1)
        try:
            # Try to find and click back/close button
            close_buttons = driver.find_elements(By.CSS_SELECTOR, '[data-testid="back"], button[aria-label*="Back"], button[aria-label*="Close"]')

            if close_buttons:
                close_buttons[0].click()
                print("  Closed group info panel")
                sleep(1)
            else:
                # Press ESC key as fallback
                from selenium.webdriver.common.action_chains import ActionChains
                ActionChains(driver).send_keys(Keys.ESCAPE).perform()
                print("  Closed group info panel (ESC)")
                sleep(1)
        except Exception as e:
            print(f"  Warning: Error closing group info: {e}")

        print(f"  Total participants found: {len(participants)}")

    except Exception as e:
        print(f"  Error in get_group_participants: {e}")
        import traceback
        traceback.print_exc()

    return participants


def append_to_csv(chat_name, participants, output_path):
    """Append chat details to CSV file immediately (for crash recovery)"""
    file_exists = exists(output_path)

    with open(output_path, 'a', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['chat_name', 'chat_type', 'participant_name', 'participant_phone']
        csv_writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        # Write header only if file doesn't exist
        if not file_exists:
            csv_writer.writeheader()

        # Write all participants
        if participants:
            for participant in participants:
                csv_writer.writerow({
                    "chat_name": chat_name,
                    "chat_type": "group",
                    "participant_name": participant["name"],
                    "participant_phone": participant["phone"]
                })
            print(f"  ✓ Saved {len(participants)} participants to CSV")
        else:
            # Group but no participants found
            csv_writer.writerow({
                "chat_name": chat_name,
                "chat_type": "group",
                "participant_name": "N/A",
                "participant_phone": "N/A"
            })
            print(f"  ! Warning: No participants found, saved placeholder")


def process_introduction_groups(driver, output_path):
    """Process introduction groups using DFS - check and process immediately"""
    processed_chats = set()
    total_processed = 0

    print("\nScanning chats for introduction groups (DFS approach)...")
    print("=" * 60)

    pane_side = driver.find_element(by=By.CLASS_NAME, value=PANE_SIDE_DIV)

    for iteration in range(MAX_ITERATIONS):
        print(f"\nIteration {iteration + 1}/{MAX_ITERATIONS}")

        chat_elements = driver.find_elements(by=By.CLASS_NAME, value=CHAT_DIV)

        for chat_element in chat_elements:
            try:
                chat_name = chat_element.text.strip()

                if not chat_name or chat_name in processed_chats:
                    continue

                # Skip Archive
                if is_archive_chat(chat_name):
                    print(f"⊗ Skipping Archive: {chat_name}")
                    processed_chats.add(chat_name)
                    continue

                # Check if it's an introduction group
                if not is_introduction_group(chat_name):
                    processed_chats.add(chat_name)
                    continue

                # Found an introduction group - process it immediately!
                print(f"\n{'=' * 60}")
                print(f"★ Found introduction group: {chat_name}")
                processed_chats.add(chat_name)
                total_processed += 1

                # Scroll the chat element into view before clicking
                try:
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", chat_element)
                    sleep(0.5)  # Brief pause after scrolling
                    print(f"  Scrolled chat into view")
                except Exception as e:
                    print(f"  Warning: Could not scroll into view: {e}")

                # Click on the chat
                try:
                    chat_element.click()
                    sleep(2)
                except Exception as e:
                    print(f"  Error clicking chat: {e}")
                    # Try JavaScript click as fallback
                    try:
                        driver.execute_script("arguments[0].click();", chat_element)
                        sleep(2)
                        print(f"  Clicked using JavaScript")
                    except Exception as e2:
                        print(f"  JavaScript click also failed: {e2}")
                        continue

                # Verify it's a group (should be, but double check)
                if is_group_chat(driver):
                    print(f"  ✓ Confirmed as GROUP chat")
                    participants = get_group_participants(driver)

                    # Save immediately to CSV
                    append_to_csv(chat_name, participants, output_path)
                else:
                    print(f"  ! Not a group chat, skipping")

                print(f"{'=' * 60}")

            except StaleElementReferenceException:
                print("  StaleElementReferenceException - continuing")
                continue
            except Exception as e:
                print(f"  Error processing chat: {e}")
                continue

        # Scroll down to reveal more chats
        for _ in range(DOWN_COUNTER):
            pane_side.send_keys(Keys.DOWN)

        sleep(0.5)  # Small delay between iterations

    return total_processed

def open_whatsapp():
    """Open WhatsApp Web using default Chrome profile (auto-login)"""
    # Set up Chrome options to use default profile
    chrome_options = Options()

    # Use default user profile to auto-login to WhatsApp Web
    # Note: Update this path if your Chrome profile is in a different location
    # Linux: ~/.config/google-chrome/Default
    # macOS: ~/Library/Application Support/Google/Chrome/Default
    # Windows: %USERPROFILE%\AppData\Local\Google\Chrome\User Data\Default
    import platform
    system = platform.system()

    if system == "Linux":
        user_data_dir = "/home/user/.config/google-chrome"
    elif system == "Darwin":  # macOS
        from os.path import expanduser
        user_data_dir = expanduser("~/Library/Application Support/Google/Chrome")
    elif system == "Windows":
        import os
        user_data_dir = os.path.join(os.environ['USERPROFILE'], 'AppData', 'Local', 'Google', 'Chrome', 'User Data')
    else:
        print(f"Warning: Unknown system {system}, using Chrome without default profile")
        driver = webdriver.Chrome()
        driver.get(WHATSAPP_URL)
        sleep(2)
        input("Connect to WhatsappWeb by linking device. Press Enter when done.")
        return driver

    chrome_options.add_argument(f"user-data-dir={user_data_dir}")
    chrome_options.add_argument("profile-directory=Default")

    print(f"Opening Chrome with profile from: {user_data_dir}")
    print("WhatsApp Web should auto-login if you're already logged in...")

    try:
        driver = webdriver.Chrome(options=chrome_options)
        driver.get(WHATSAPP_URL)
        sleep(5)  # Wait for WhatsApp to load

        # Check if we need to scan QR code
        print("\nIf you see a QR code, scan it with your phone.")
        print("If you're already logged in, you should see your chats.")
        input("Press Enter when WhatsApp Web is ready and you can see your chats...")

        return driver
    except Exception as e:
        print(f"Error opening Chrome with profile: {e}")
        print("Falling back to Chrome without profile...")
        driver = webdriver.Chrome()
        driver.get(WHATSAPP_URL)
        sleep(2)
        input("Connect to WhatsappWeb by linking device. Press Enter when done.")
        return driver

def main():
    output_path = join(OUTPUT_DIRECTORY, OUTPUT_NAME)

    # Delete existing CSV if present (fresh start)
    if exists(output_path):
        print(f"Removing existing CSV file: {output_path}")
        import os
        os.remove(output_path)

    driver = open_whatsapp()

    print("\n" + "=" * 60)
    print("INTRODUCTION GROUP SCRAPER")
    print("=" * 60)
    print(f"Output file: {output_path}")
    print(f"Looking for groups with delimiters: {', '.join(INTRO_DELIMITERS)}")
    print("=" * 60)

    try:
        # Process introduction groups with DFS approach
        total_processed = process_introduction_groups(driver, output_path)

        print("\n" + "=" * 60)
        print("✓ SCRAPING COMPLETE!")
        print("=" * 60)
        print(f"Total introduction groups processed: {total_processed}")
        print(f"Data saved to: {output_path}")
        print("=" * 60)
    except KeyboardInterrupt:
        print("\n\n⚠ Interrupted by user")
        print(f"Partial data saved to: {output_path}")
    except Exception as e:
        print(f"\n\n✗ Error: {e}")
        print(f"Partial data may be saved to: {output_path}")
    finally:
        driver.quit()
        print("\nBrowser closed.")

if __name__ == "__main__":
    main()