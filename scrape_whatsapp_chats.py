from time import sleep
import csv
from os.path import join
from selenium import webdriver
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


def get_chat_names(driver):
    """Get list of chat names from the sidebar"""
    chat_names = []
    pane_side = driver.find_element(by=By.CLASS_NAME, value=PANE_SIDE_DIV)
    for _ in range(MAX_ITERATIONS):
        chat_elements = driver.find_elements(by=By.CLASS_NAME, value=CHAT_DIV)
        for chat_element in chat_elements:
            try:
                if chat_element.text not in chat_names:
                    chat_names.append(chat_element.text)
                    print(f"Adding chat {chat_element.text}")
            except StaleElementReferenceException:
                print("Encountered StaleElementReferenceException, continuing")
        for _ in range(DOWN_COUNTER):
            pane_side.send_keys(Keys.DOWN)
    return chat_names


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


def get_chat_details(driver, chat_names):
    """Get detailed information for each chat including participants for groups"""
    chat_details = []

    print(f"\nProcessing {len(chat_names)} chats to extract details...")

    for idx, chat_name in enumerate(chat_names, 1):
        print(f"\n[{idx}/{len(chat_names)}] Processing chat: {chat_name}")

        try:
            # Find and click on the chat
            found = False
            chat_elements = driver.find_elements(by=By.CLASS_NAME, value=CHAT_DIV)

            for chat_element in chat_elements:
                try:
                    if chat_name in chat_element.text:
                        chat_element.click()
                        sleep(2)
                        found = True
                        break
                except StaleElementReferenceException:
                    continue

            if not found:
                print(f"  Could not find chat element for: {chat_name}")
                continue

            # Check if it's a group
            if is_group_chat(driver):
                print(f"  Detected as GROUP chat")
                participants = get_group_participants(driver)

                if participants:
                    for participant in participants:
                        chat_details.append({
                            "chat_name": chat_name,
                            "chat_type": "group",
                            "participant_name": participant["name"],
                            "participant_phone": participant["phone"]
                        })
                else:
                    # Group but no participants found
                    print(f"  Warning: Group detected but no participants extracted")
                    chat_details.append({
                        "chat_name": chat_name,
                        "chat_type": "group",
                        "participant_name": "N/A",
                        "participant_phone": "N/A"
                    })
            else:
                # Individual chat
                print(f"  Detected as INDIVIDUAL chat")
                chat_details.append({
                    "chat_name": chat_name,
                    "chat_type": "individual",
                    "participant_name": "N/A",
                    "participant_phone": "N/A"
                })

        except Exception as e:
            print(f"  Error processing chat {chat_name}: {e}")
            # Add entry anyway to track that we attempted this chat
            chat_details.append({
                "chat_name": chat_name,
                "chat_type": "error",
                "participant_name": "N/A",
                "participant_phone": "N/A"
            })
            continue

    return chat_details

def open_whatsapp():
    driver = webdriver.Chrome()
    driver.get(WHATSAPP_URL)
    sleep(2)
    input("Connect to WhatsappWeb by linking device. Press Enter when done.")
    return driver

def dump_to_csv(chat_details, output_path):
    """Write chat details to CSV file with headers"""
    with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['chat_name', 'chat_type', 'participant_name', 'participant_phone']
        csv_writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        csv_writer.writeheader()
        for detail in chat_details:
            csv_writer.writerow(detail)

def main():
    driver = open_whatsapp()

    # Step 1: Get all chat names
    print("Step 1: Collecting chat names from sidebar...")
    chat_names = get_chat_names(driver)
    print(f"Found {len(chat_names)} chats")

    # Step 2: Get detailed information for each chat
    print("\nStep 2: Extracting detailed information from each chat...")
    chat_details = get_chat_details(driver, chat_names)

    # Step 3: Save to CSV
    output_path = join(OUTPUT_DIRECTORY, OUTPUT_NAME)
    print(f"\nStep 3: Saving {len(chat_details)} records to CSV at {output_path}")
    dump_to_csv(chat_details, output_path)

    print(f"\n✓ Done! Data saved to {output_path}")
    print(f"  Total chats processed: {len(chat_names)}")
    print(f"  Total records: {len(chat_details)}")

    driver.quit()

if __name__ == "__main__":
    main()