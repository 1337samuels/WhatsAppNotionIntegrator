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
    """Check if the currently opened chat is a group"""
    try:
        # Multiple strategies to detect if it's a group chat
        # Strategy 1: Look for group-specific elements in header
        header = driver.find_element(By.TAG_NAME, 'header')
        header_text = header.text.lower()

        # Groups typically show participant count or "click here for group info"
        if any(keyword in header_text for keyword in ['participants', 'group info', 'members']):
            return True

        # Strategy 2: Look for group icon or image that indicates multiple people
        try:
            # Try to find group-specific data attributes
            group_indicators = driver.find_elements(By.CSS_SELECTOR, '[data-testid*="group"]')
            if group_indicators:
                return True
        except:
            pass

        # Strategy 3: Check if clicking header reveals group info (we'll check for specific menu items)
        # This is done in get_group_participants function

        return False
    except Exception as e:
        print(f"Error checking if group: {e}")
        return False


def get_group_participants(driver):
    """Extract participant names and phone numbers from group info"""
    participants = []

    try:
        # Click on the header to open group/contact info
        wait = WebDriverWait(driver, WAIT_TIMEOUT)
        header = wait.until(EC.element_to_be_clickable((By.TAG_NAME, 'header')))
        header.click()
        sleep(2)

        # Try multiple selectors to find participant list
        participant_elements = []

        # Try different possible selectors
        selectors = [
            '[data-testid*="participant"]',
            '[data-testid*="contact"]',
            'div[role="listitem"]',
            '.participant',
            '[aria-label*="participant"]'
        ]

        for selector in selectors:
            try:
                participant_elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if participant_elements:
                    print(f"Found {len(participant_elements)} elements with selector: {selector}")
                    break
            except:
                continue

        # If we still don't have participants, try to find them by looking for a section with multiple contact entries
        if not participant_elements:
            # Look for a container that might hold participants
            try:
                # Groups often have a section titled with participant count
                sections = driver.find_elements(By.TAG_NAME, 'section')
                for section in sections:
                    if 'participant' in section.text.lower():
                        # Try to extract names from this section
                        name_elements = section.find_elements(By.CSS_SELECTOR, 'span[dir="auto"]')
                        for elem in name_elements:
                            text = elem.text.strip()
                            if text and len(text) > 0 and text not in ['Participants', 'Group info']:
                                participants.append({"name": text, "phone": "N/A"})
                        break
            except Exception as e:
                print(f"Error in fallback participant extraction: {e}")
        else:
            # Extract info from participant elements
            for participant in participant_elements:
                try:
                    # Try to find name
                    name_elem = participant.find_element(By.CSS_SELECTOR, 'span[dir="auto"]')
                    name = name_elem.text.strip()

                    if not name or len(name) == 0:
                        continue

                    # Try to find phone number
                    phone = "N/A"
                    try:
                        # Look for phone number patterns
                        phone_elem = participant.find_element(By.CSS_SELECTOR, '[data-testid*="phone"]')
                        phone = phone_elem.text
                    except:
                        # Try to extract from subtitle or other elements
                        try:
                            subtitle = participant.find_element(By.CSS_SELECTOR, 'span.subtitle')
                            phone = subtitle.text if subtitle.text else "N/A"
                        except:
                            pass

                    participants.append({"name": name, "phone": phone})
                    print(f"  - Found participant: {name} ({phone})")
                except Exception as e:
                    print(f"Error extracting individual participant: {e}")
                    continue

        # Close the info panel by clicking back or close button
        try:
            # Try multiple selectors for close/back button
            close_selectors = [
                '[data-testid="back"]',
                '[aria-label*="Back"]',
                '[aria-label*="Close"]',
                'button[aria-label*="back"]'
            ]

            for selector in close_selectors:
                try:
                    close_button = driver.find_element(By.CSS_SELECTOR, selector)
                    close_button.click()
                    sleep(1)
                    break
                except:
                    continue
        except Exception as e:
            print(f"Error closing info panel: {e}")
            # Try pressing ESC as fallback
            try:
                from selenium.webdriver.common.action_chains import ActionChains
                ActionChains(driver).send_keys(Keys.ESCAPE).perform()
                sleep(1)
            except:
                pass

    except Exception as e:
        print(f"Error extracting participants: {e}")

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

                # Click on the chat
                chat_element.click()
                sleep(2)

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