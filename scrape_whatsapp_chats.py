from time import sleep
import csv
import logging
import subprocess
import platform
from os.path import join, exists
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver import Keys
from selenium.webdriver.common.by import By
from selenium.common.exceptions import StaleElementReferenceException, NoSuchElementException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# MODE SELECTION: Choose 'desktop' or 'web'
# 'desktop' = WhatsApp Desktop app (better contact data retention)
# 'web' = WhatsApp Web in browser (original method)
WHATSAPP_MODE = 'desktop'  # Change to 'web' to use WhatsApp Web instead

WHATSAPP_URL = 'https://web.whatsapp.com/'
REMOTE_DEBUGGING_PORT = 9223  # Port for WhatsApp Desktop remote debugging
MAX_ITERATIONS = 500  # Maximum iterations as safety limit
CHAT_DIV = "_ak8q"
PANE_SIDE_DIV = "_ak9y"
#OUTPUT_DIRECTORY = r"C:\Users\gilad\OneDrive\Desktop\Netz\Whatsapp exporter"
OUTPUT_DIRECTORY = "."
OUTPUT_NAME = "whatsapp_chats"  # Timestamp will be added automatically
LOG_NAME = "whatsapp_scraper"  # Timestamp will be added automatically
WAIT_TIMEOUT = 10

# Introduction group delimiters from chat_parser.py
INTRO_DELIMITERS = ["//", "/", "<>", "x"]


def setup_logging(log_path):
    """
    Set up logging to both console and file.
    All messages are logged to file and also printed to console.
    """
    # Create logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Remove any existing handlers
    logger.handlers = []

    # Create formatter
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s',
                                  datefmt='%Y-%m-%d %H:%M:%S')

    # File handler - logs everything to file
    file_handler = logging.FileHandler(log_path, mode='w', encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Console handler - logs to terminal
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger


def log(message):
    """Helper function to log messages (simpler than logging.info)"""
    logging.info(message)


def is_introduction_group(chat_name):
    """Check if chat name matches introduction group format from chat_parser.py"""
    # Check if the chat name contains any of the introduction delimiters
    for delimiter in INTRO_DELIMITERS:
        if delimiter in chat_name:
            log(f"  ✓ Matches introduction format with delimiter: '{delimiter}'")
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
                    log(f"  Found header using panel selector: {selector}")
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
                log(f"  Found {len(headers)} header elements total")
                if len(headers) >= 2:
                    # Use the second header (first is usually sidebar)
                    header = headers[1]
                    log(f"  Using header index 1 (second header)")
                elif len(headers) == 1:
                    header = headers[0]
                    log(f"  Only one header found, using it")
            except:
                pass

        if not header:
            log("  ERROR: Could not find any header element")
            return False

        # Debug: Print all text in header
        header_full_text = header.text
        log(f"  Header full text:\n{header_full_text}")

        # Split by newlines to get separate lines
        lines = [line.strip() for line in header_full_text.split('\n') if line.strip()]
        log(f"  Header lines: {lines}")

        # Usually the structure is:
        # Line 0: Chat name
        # Line 1: Subtitle (participant names for groups, "click here..." for contacts)

        subtitle_text = ""

        if len(lines) >= 2:
            # The second line is typically the subtitle
            subtitle_text = lines[1].lower()
            log(f"  Subtitle text (from lines): '{subtitle_text}'")
        else:
            log(f"  Only found {len(lines)} line(s) in header, trying other methods...")

            # Try to find specific elements
            try:
                # Look for all span elements and get their text
                spans = header.find_elements(By.TAG_NAME, 'span')
                log(f"  Found {len(spans)} span elements in header")

                # Try to find the subtitle by looking for spans that aren't the title
                span_texts = []
                for i, span in enumerate(spans):
                    text = span.text.strip()
                    if text:
                        span_texts.append(text)
                        log(f"    Span {i}: '{text}'")

                # Look for a span that looks like a subtitle (not the chat name)
                # The subtitle is usually shorter and contains specific patterns
                chat_name = lines[0] if lines else ""
                for text in span_texts:
                    if text != chat_name and len(text) > 0:
                        subtitle_text = text.lower()
                        log(f"  Found potential subtitle: '{subtitle_text}'")
                        break

            except Exception as e:
                log(f"  Error getting spans: {e}")

        if not subtitle_text:
            log(f"  Could not find subtitle text")
            # Try one more method - get all divs in header
            try:
                divs = header.find_elements(By.TAG_NAME, 'div')
                log(f"  Trying {len(divs)} div elements...")
                for i, div in enumerate(divs):
                    text = div.text.strip()
                    if text and '\n' not in text and len(text) > 5 and len(text) < 100:
                        # This might be a subtitle
                        if i > 0:  # Not the first div (which is likely the title)
                            subtitle_text = text.lower()
                            log(f"    Found subtitle from div {i}: '{subtitle_text}'")
                            break
            except Exception as e:
                log(f"  Error getting divs: {e}")

        log(f"  Final subtitle text: '{subtitle_text}'")

        # Individual contacts typically say "click here for contact info" or "tap here for contact info"
        contact_keywords = ['click here for contact info', 'tap here for contact info',
                           'click for contact info', 'tap for contact info',
                           'select for contact info']
        group_keywords = ['click here for group info', 'tap here for group info',
                           'click for group info', 'tap for group info',
                           'select for group info', ',']

        if any(keyword in subtitle_text for keyword in contact_keywords):
            log(f"  → Detected as INDIVIDUAL (contact info message)")
            return False

        # Groups show participant names (comma-separated) or participant count
        # If subtitle contains commas, it's likely a list of participants
        if any(keyword in subtitle_text for keyword in group_keywords):
            log(f"  → Detected as GROUP (participant list with commas)")
            return True

        # Groups may also show "you, person1, person2" or similar
        if 'you' in subtitle_text and len(subtitle_text) > 10:
            log(f"  → Detected as GROUP (contains 'you' with other names)")
            return True

        # Check for participant count indicators
        if any(keyword in subtitle_text for keyword in ['participants', 'members', 'participant', 'member']):
            log(f"  → Detected as GROUP (participant/member count)")
            return True

        # If we have a subtitle that's not a contact info message and has some length,
        # it's likely a group showing participant names
        if subtitle_text and len(subtitle_text) > 5 and not any(keyword in subtitle_text for keyword in contact_keywords):
            log(f"  → Detected as GROUP (has subtitle, not contact info)")
            return True

        # Default to not a group if we can't determine
        log(f"  → Could not determine, defaulting to NOT a group")
        return False

    except Exception as e:
        log(f"  Error checking if group: {e}")
        import traceback
        traceback.print_exc()
        return False


def get_group_participants(driver):
    """Extract FULL participant names by clicking into group info"""
    participants = []

    try:
        log("  Opening group info to extract full names...")

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
            log("  ERROR: Could not find header element")
            return participants

        # Click on the header to open group info
        try:
            # Find a clickable element in the header
            clickable_area = header.find_element(By.CSS_SELECTOR, 'div[role="button"]')
            clickable_area.click()
            log("  Clicked header to open group info")
            sleep(3)  # Wait for panel to open
        except Exception as e:
            log(f"  Error clicking header: {e}, trying alternative...")
            try:
                header.click()
                sleep(3)
            except Exception as e2:
                log(f"  Could not open group info: {e2}")
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
                log("  Scrolled group info panel")
        except Exception as e:
            log(f"  Warning: Could not scroll group info: {e}")

        # Extract participants - look for contact cells/listitems
        log("  Extracting participant names from group info...")

        # Strategy 1: Look for list items with contact information
        contact_cells = driver.find_elements(By.CSS_SELECTOR, 'div[role="listitem"]')

        for cell in contact_cells:
            try:
                # Get all spans with dir="auto" (usually contains names)
                name_spans = cell.find_elements(By.CSS_SELECTOR, 'span[dir="auto"]')

                for span in name_spans:
                    name = span.text.strip()

                    # Filter out non-participant text (but keep "You" as it's a valid participant)
                    if (name and len(name) > 1 and
                        name not in ['Admin', 'Group Admin', 'Group admin', 'Participants', 'Members', 'Group info'] and
                        not any(keyword in name.lower() for keyword in ['add participant', 'invite link', 'group settings', 'search', 'uk number', 'number +'])):

                        # Check if we already have this participant
                        if not any(p['name'] == name for p in participants):
                            # Determine if it's a phone number or name
                            if name.startswith('+') or (name.replace('-', '').replace(' ', '').replace('(', '').replace(')', '').isdigit() and len(name) > 8):
                                participants.append({"name": name, "phone": name})
                            else:
                                participants.append({"name": name, "phone": "N/A"})
                            log(f"    - Found: {name}")
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
                log("  Closed group info panel")
                sleep(1)
            else:
                # Press ESC key as fallback
                from selenium.webdriver.common.action_chains import ActionChains
                ActionChains(driver).send_keys(Keys.ESCAPE).perform()
                log("  Closed group info panel (ESC)")
                sleep(1)
        except Exception as e:
            log(f"  Warning: Error closing group info: {e}")

        log(f"  Total participants found: {len(participants)}")

    except Exception as e:
        log(f"  Error in get_group_participants: {e}")
        import traceback
        traceback.print_exc()

    return participants


def append_to_csv(chat_name, participants, output_path):
    """Append chat details to CSV file immediately (for crash recovery)"""
    file_exists = exists(output_path)

    with open(output_path, 'a', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['chat_name', 'chat_type', 'participant_name', 'participant_phone', 'participant_count']
        csv_writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        # Write header only if file doesn't exist
        if not file_exists:
            csv_writer.writeheader()

        # Calculate total participant count
        participant_count = len(participants) if participants else 0

        # Write all participants
        if participants:
            for participant in participants:
                csv_writer.writerow({
                    "chat_name": chat_name,
                    "chat_type": "group",
                    "participant_name": participant["name"],
                    "participant_phone": participant["phone"],
                    "participant_count": participant_count
                })
            log(f"  ✓ Saved {len(participants)} participants to CSV (total: {participant_count})")
        else:
            # Group but no participants found
            csv_writer.writerow({
                "chat_name": chat_name,
                "chat_type": "group",
                "participant_name": "N/A",
                "participant_phone": "N/A",
                "participant_count": 0
            })
            log(f"  ! Warning: No participants found, saved placeholder")


def process_introduction_groups(driver, output_path):
    """Process introduction groups using DFS - check and process immediately"""
    processed_chats = set()
    total_processed = 0
    no_new_chats_count = 0  # Track iterations with no new chats
    max_no_new_iterations = 3  # Stop after this many iterations with no new chats

    log("\nScanning chats for introduction groups (DFS approach)...")
    log("=" * 60)

    pane_side = driver.find_element(by=By.CLASS_NAME, value=PANE_SIDE_DIV)

    iteration = 0
    while iteration < MAX_ITERATIONS:
        iteration += 1
        log(f"\nIteration {iteration}")

        chat_elements = driver.find_elements(by=By.CLASS_NAME, value=CHAT_DIV)

        # Get current visible chat names to detect if scrolling reveals new chats
        current_visible_chats = set()
        for elem in chat_elements:
            try:
                name = elem.text.strip()
                if name:
                    current_visible_chats.add(name)
            except:
                continue

        # Track if we found any new chats in this iteration
        found_new_chats = False

        for chat_element in chat_elements:
            try:
                chat_name = chat_element.text.strip()

                if not chat_name or chat_name in processed_chats:
                    continue

                # Mark that we found a new chat
                found_new_chats = True

                # Skip Archive
                if is_archive_chat(chat_name):
                    log(f"⊗ Skipping Archive: {chat_name}")
                    processed_chats.add(chat_name)
                    continue

                # Check if it's an introduction group
                if not is_introduction_group(chat_name):
                    processed_chats.add(chat_name)
                    continue

                # Found an introduction group - process it immediately!
                log(f"\n{'=' * 60}")
                log(f"★ Found introduction group: {chat_name}")
                processed_chats.add(chat_name)
                total_processed += 1

                # Scroll the chat element into view before clicking
                try:
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", chat_element)
                    sleep(0.5)  # Brief pause after scrolling
                    log(f"  Scrolled chat into view")
                except Exception as e:
                    log(f"  Warning: Could not scroll into view: {e}")

                # Click on the chat
                try:
                    chat_element.click()
                    sleep(2)
                except Exception as e:
                    log(f"  Error clicking chat: {e}")
                    # Try JavaScript click as fallback
                    try:
                        driver.execute_script("arguments[0].click();", chat_element)
                        sleep(2)
                        log(f"  Clicked using JavaScript")
                    except Exception as e2:
                        log(f"  JavaScript click also failed: {e2}")
                        continue

                # Verify it's a group (should be, but double check)
                if is_group_chat(driver):
                    log(f"  ✓ Confirmed as GROUP chat")
                    participants = get_group_participants(driver)

                    # Save immediately to CSV
                    append_to_csv(chat_name, participants, output_path)
                else:
                    log(f"  ! Not a group chat, skipping")

                log(f"{'=' * 60}")

            except StaleElementReferenceException:
                log("  StaleElementReferenceException - continuing")
                continue
            except Exception as e:
                log(f"  Error processing chat: {e}")
                continue

        # Check if we found new chats in this iteration
        if not found_new_chats:
            no_new_chats_count += 1
            log(f"  No new chats found in this iteration ({no_new_chats_count}/{max_no_new_iterations})")

            if no_new_chats_count >= max_no_new_iterations:
                log(f"\n✓ Reached end of chat list (no new chats after {max_no_new_iterations} iterations)")
                break
        else:
            # Reset counter if we found new chats
            no_new_chats_count = 0

        # Scroll down to reveal more chats
        # Use a smaller number of DOWN keys and detect when we've reached the end
        scroll_amount = 5
        for _ in range(scroll_amount):
            pane_side.send_keys(Keys.DOWN)

        sleep(0.5)  # Small delay between iterations

    log(f"\n{'=' * 60}")
    log(f"Scan complete! Processed {total_processed} introduction groups")
    log(f"{'=' * 60}")

    return total_processed

def get_whatsapp_desktop_path():
    """Get the path to WhatsApp Desktop executable based on OS"""
    system = platform.system()

    if system == "Linux":
        # Common Linux paths
        linux_paths = [
            "/opt/WhatsApp/whatsapp",
            "/usr/bin/whatsapp",
            "/usr/local/bin/whatsapp",
            "/snap/bin/whatsapp",
            "/usr/share/whatsapp/WhatsApp"
        ]
        for path in linux_paths:
            if exists(path):
                return path
        # Try using 'which' command
        try:
            result = subprocess.run(['which', 'whatsapp'], capture_output=True, text=True)
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except:
            pass
        return None

    elif system == "Darwin":  # macOS
        return "/Applications/WhatsApp.app/Contents/MacOS/WhatsApp"

    elif system == "Windows":
        import os
        # WhatsApp Desktop on Windows (installed via Microsoft Store or standalone)
        windows_paths = [
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'WhatsApp', 'WhatsApp.exe'),
            os.path.join(os.environ.get('PROGRAMFILES', ''), 'WhatsApp', 'WhatsApp.exe'),
            os.path.join(os.environ.get('PROGRAMFILES(X86)', ''), 'WhatsApp', 'WhatsApp.exe'),
        ]
        for path in windows_paths:
            if exists(path):
                return path
        return None

    return None


def launch_whatsapp_desktop_with_debugging():
    """Launch WhatsApp Desktop with remote debugging enabled"""
    whatsapp_path = get_whatsapp_desktop_path()

    if not whatsapp_path:
        log("ERROR: Could not find WhatsApp Desktop installation.")
        log("Please install WhatsApp Desktop from:")
        log("  - Windows: Microsoft Store or https://www.whatsapp.com/download")
        log("  - macOS: https://www.whatsapp.com/download")
        log("  - Linux: Snap Store or https://www.whatsapp.com/download")
        return False

    log(f"Found WhatsApp Desktop at: {whatsapp_path}")
    log(f"Launching with remote debugging on port {REMOTE_DEBUGGING_PORT}...")

    try:
        # Launch WhatsApp Desktop with remote debugging
        # Note: This works because WhatsApp Desktop is an Electron app (Chromium-based)
        subprocess.Popen([
            whatsapp_path,
            f'--remote-debugging-port={REMOTE_DEBUGGING_PORT}'
        ])

        log("WhatsApp Desktop launched successfully!")
        log(f"Remote debugging enabled on port {REMOTE_DEBUGGING_PORT}")
        sleep(5)  # Give WhatsApp time to start
        return True

    except Exception as e:
        log(f"ERROR launching WhatsApp Desktop: {e}")
        return False


def open_whatsapp_desktop():
    """Connect to WhatsApp Desktop via remote debugging"""
    log("\n" + "=" * 60)
    log("WHATSAPP DESKTOP MODE")
    log("=" * 60)

    # Check if WhatsApp Desktop is already running with debugging
    # If not, launch it
    log("Attempting to connect to WhatsApp Desktop...")

    chrome_options = Options()
    chrome_options.add_experimental_option("debuggerAddress", f"127.0.0.1:{REMOTE_DEBUGGING_PORT}")

    try:
        # Try to connect to existing WhatsApp Desktop instance
        driver = webdriver.Chrome(options=chrome_options)
        log("✓ Connected to WhatsApp Desktop successfully!")

    except Exception as e:
        log(f"Could not connect to existing WhatsApp Desktop: {e}")
        log("\nLaunching WhatsApp Desktop with remote debugging...")

        if not launch_whatsapp_desktop_with_debugging():
            log("\nFailed to launch WhatsApp Desktop.")
            log("Falling back to WhatsApp Web...")
            return open_whatsapp_web()

        # Try to connect again
        try:
            log("Connecting to WhatsApp Desktop...")
            driver = webdriver.Chrome(options=chrome_options)
            log("✓ Connected to WhatsApp Desktop successfully!")
        except Exception as e2:
            log(f"ERROR: Still could not connect: {e2}")
            log("Falling back to WhatsApp Web...")
            return open_whatsapp_web()

    sleep(3)
    log("\nPlease ensure WhatsApp Desktop is logged in.")
    log("If you see a QR code, scan it with your phone.")
    input("Press Enter when WhatsApp Desktop is ready and you can see your chats...")

    return driver


def open_whatsapp_web():
    """Open WhatsApp Web using default Chrome profile (auto-login)"""
    log("\n" + "=" * 60)
    log("WHATSAPP WEB MODE")
    log("=" * 60)

    # Set up Chrome options to use default profile
    chrome_options = Options()

    # Use default user profile to auto-login to WhatsApp Web
    # Note: Update this path if your Chrome profile is in a different location
    # Linux: ~/.config/google-chrome/Default
    # macOS: ~/Library/Application Support/Google/Chrome/Default
    # Windows: %USERPROFILE%\AppData\Local\Google\Chrome\User Data\Default
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
        log(f"Warning: Unknown system {system}, using Chrome without default profile")
        driver = webdriver.Chrome()
        driver.get(WHATSAPP_URL)
        sleep(2)
        input("Connect to WhatsappWeb by linking device. Press Enter when done.")
        return driver

    chrome_options.add_argument(f"user-data-dir={user_data_dir}")
    chrome_options.add_argument("profile-directory=Default")

    log(f"Opening Chrome with profile from: {user_data_dir}")
    log("WhatsApp Web should auto-login if you're already logged in...")

    try:
        driver = webdriver.Chrome(options=chrome_options)
        driver.get(WHATSAPP_URL)
        sleep(5)  # Wait for WhatsApp to load

        # Check if we need to scan QR code
        log("\nIf you see a QR code, scan it with your phone.")
        log("If you're already logged in, you should see your chats.")
        input("Press Enter when WhatsApp Web is ready and you can see your chats...")

        return driver
    except Exception as e:
        log(f"Error opening Chrome with profile: {e}")
        log("Falling back to Chrome without profile...")
        driver = webdriver.Chrome()
        driver.get(WHATSAPP_URL)
        sleep(2)
        input("Connect to WhatsappWeb by linking device. Press Enter when done.")
        return driver


def open_whatsapp():
    """Open WhatsApp based on configured mode (Desktop or Web)"""
    if WHATSAPP_MODE.lower() == 'desktop':
        return open_whatsapp_desktop()
    else:
        return open_whatsapp_web()

def main():
    # Generate timestamped filenames for this run
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Create unique filenames with timestamp
    csv_filename = f"{OUTPUT_NAME}_{timestamp}.csv"
    log_filename = f"{LOG_NAME}_{timestamp}.log"

    output_path = join(OUTPUT_DIRECTORY, csv_filename)
    log_path = join(OUTPUT_DIRECTORY, log_filename)

    # Set up logging to both console and file
    setup_logging(log_path)
    log("=" * 60)
    log("WhatsApp Introduction Group Scraper - Starting")
    log(f"Mode: {WHATSAPP_MODE.upper()}")
    log(f"Timestamp: {timestamp}")
    log(f"Log file: {log_path}")
    log(f"CSV file: {output_path}")
    log("=" * 60)

    driver = open_whatsapp()

    log("\n" + "=" * 60)
    log("INTRODUCTION GROUP SCRAPER")
    log("=" * 60)
    log(f"Mode: WhatsApp {WHATSAPP_MODE.upper()}")
    log(f"Output file: {output_path}")
    log(f"Looking for groups with delimiters: {', '.join(INTRO_DELIMITERS)}")
    log("=" * 60)

    try:
        # Process introduction groups with DFS approach
        total_processed = process_introduction_groups(driver, output_path)

        log("\n" + "=" * 60)
        log("✓ SCRAPING COMPLETE!")
        log("=" * 60)
        log(f"Total introduction groups processed: {total_processed}")
        log(f"Data saved to: {output_path}")
        log("=" * 60)
    except KeyboardInterrupt:
        log("\n\n⚠ Interrupted by user")
        log(f"Partial data saved to: {output_path}")
    except Exception as e:
        log(f"\n\n✗ Error: {e}")
        log(f"Partial data may be saved to: {output_path}")
    finally:
        driver.quit()
        log("\nBrowser closed.")

if __name__ == "__main__":
    main()