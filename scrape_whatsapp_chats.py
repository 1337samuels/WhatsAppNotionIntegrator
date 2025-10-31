from time import sleep
import csv
from os.path import join
from selenium import webdriver
from selenium.webdriver import Keys
from selenium.webdriver.common.by import By
from selenium.common.exceptions import StaleElementReferenceException

WHATSAPP_URL = 'https://web.whatsapp.com/'
MAX_ITERATIONS = 50
DOWN_COUNTER = 20
CHAT_DIV = "_ak8q"
PANE_SIDE_DIV = "_ak9y"
#OUTPUT_DIRECTORY = r"C:\Users\gilad\OneDrive\Desktop\Netz\Whatsapp exporter"
OUTPUT_DIRECTORY = "."
OUTPUT_NAME = "whatsapp_chats.csv"


def get_chats(driver):
    chats = []
    pane_side = driver.find_element(by=By.CLASS_NAME, value=PANE_SIDE_DIV)
    for _ in range(MAX_ITERATIONS):
        chat_elements = driver.find_elements(by=By.CLASS_NAME, value=CHAT_DIV)
        for chat_element in chat_elements:
            try:
                if chat_element.text not in chats:
                    chats.append(chat_element.text)
                    print(f"Adding chat {chat_element.text}")
            except StaleElementReferenceException:
                print("Encountered StaleElementReferenceException, continuing")
        for _ in range(DOWN_COUNTER):
            pane_side.send_keys(Keys.DOWN)
    return chats

def open_whatsapp():
    driver = webdriver.Chrome()
    driver.get(WHATSAPP_URL)
    sleep(2)
    input("Connect to WhatsappWeb by linking device. Press Enter when done.")
    return driver

def dump_to_csv(chats, output_path):
    with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
        csv_writer = csv.writer(csvfile)
        for chat in chats:
            csv_writer.writerow([chat])

def main():
    driver = open_whatsapp()
    chats = get_chats(driver)
    output_path = join(OUTPUT_DIRECTORY, OUTPUT_NAME)
    print(f"Found {len(chats)} chats, dumping to CSV at {output_path}")
    dump_to_csv(chats, output_path)

main()