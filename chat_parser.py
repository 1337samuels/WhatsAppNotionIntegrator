from notion_client import Client

TEMP_DB_ID = "29a37812620f80f2a963daf81ebe558f"

class Intros:
    def __init__(self, csv_path):
        with open(csv_path, "rb") as csvfile:
            self.chats = csvfile.readlines()
        self.intros = []
        self.intro_dict = {}
        self.notion = Client(auth=NOTION_SECRET)

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
        for row in self.chats:
            row_decoded = row.decode("utf-8")
            if "//" in row_decoded:
                delimiter = "//"
            elif "/" in row_decoded:
                delimiter = "/"
            elif "<>" in row_decoded:
                delimiter = "<>"
            elif "x" in row_decoded:
                delimiter = "x"
            else:
                continue
            sides = row_decoded.split(delimiter)
            self.intros.append((self._parse_inner_side(sides[0]), self._parse_inner_side(sides[1])))
            if len(sides) != 2:
                print(f"Found {len(sides)} sides for {row_decoded}")

    def insert_to_notion_test(self):
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
    intros = Intros(r"C:\Users\gilad\OneDrive\Desktop\Netz\Whatsapp exporter\Lia Results\whatsapp_chats.csv")
    intros.parse_csv()
    print(len(intros.intros))
    print(intros.intros)
    intros.insert_to_notion_test()

main()