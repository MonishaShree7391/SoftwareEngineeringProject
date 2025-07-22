# shared/scanner.py

import pandas as pd
import re
import json
import os
from ReadImage import processImageText
import logging
from rewe import format_receipt_text
logger = logging.getLogger(__name__)

class ImageScanner:

    def __init__(self,imagepath,filename,extractedtext,month,year):
        self.month = month
        self.year = year
        self.bill_name=filename
        if extractedtext:
            text_1 = 'REWE ' + extractedtext
            self.text = format_receipt_text(text_1)
            print(self.text)
        else:
            self.text = processImageText(imagepath)
        #print(self.text)

    def get_text(self):
        return self.text

    def get_shop_name(self):
        # Look for the line that contains "Kaufland"
        for line in self.text.split('\n'):
            if "Kaufland" in line:
                return line.strip()
            elif "REWE" in line:
                return line.strip()
        return None

    def get_Total_amount(self):
        # amount_pattern = r'((Total\snone\s\d+(,\d+)?)|(Total\s\d+(,\d+)?)|(Summe\s(\d+,\d+)))'
        amount_pattern = r'Summe\s(\d+,\d+)'
        amount_match = re.search(amount_pattern, self.text)
        price_pattern = r"Summe (\d+) (\d{2})"
        price_match = re.search(price_pattern, self.text)
        summe_pattern = r"Summe (\d{1,5})\s(\d{2})"
        summe_match = re.search(summe_pattern, self.text)
        # Regex pattern to capture the price from "Kartenzahlung" (with a comma)
        kartenzahlung_pattern = r"Kartenzahlung (\d{1,5}),(\d{2})"
        kartenzahlung_match = re.search(kartenzahlung_pattern, self.text)

        rewe_pattern = r"SUMME\s+EUR\s+([\d,.]+)"
        rewe_total_match = re.search(rewe_pattern, self.text)

        amount_text = None
        summe_price = None
        kartenzahlung_price = None
        if amount_match:
            amount_match = re.search(amount_pattern, self.text)
            amount_text = amount_match.group(1) if amount_match else "None"
            print('Amount_Total_Sum: ', amount_text)
        elif price_match:
            amount_text = f"{price_match.group(1)},{price_match.group(2)}"
            print("Formatted Price:", amount_text)  # Output: 100,85
        elif summe_match:
            amount_text = summe_price = f"{summe_match.group(1)},{summe_match.group(2)}"
            print("Extracted Summe Price:", amount_text)
        elif kartenzahlung_match:
            amount_text = kartenzahlung_price = f"{kartenzahlung_match.group(1)},{kartenzahlung_match.group(2)}"
            print("Extracted Kartenzahlung Price:", amount_text)
            # Compare values and return correct one
            if summe_price and kartenzahlung_price:
                if summe_price == kartenzahlung_price:
                    print("Prices match. Returning:", summe_price)
                    return summe_price
                else:
                    print("Prices do not match. Returning value from Kartenzahlung:", kartenzahlung_price)
                    return kartenzahlung_price
            elif kartenzahlung_price:
                print("Only Kartenzahlung price found. Returning:", kartenzahlung_price)
                amount_text = kartenzahlung_price
            elif summe_price:
                print("Only Summe price found. Returning:", summe_price)
                amount_text = summe_price
        elif rewe_total_match:
            amount_text = rewe_total_match.group(1) if rewe_total_match else "Not Found"
            print("Rewe total Price:", amount_text)

        if 'none' in amount_text:
            total_amount = amount_text.replace('Total none', '')
        else:
            total_amount = amount_text.replace('Total', '')
        try:
            total_amount = total_amount.replace(',', '.')
            total_amount = float(total_amount)
        except ValueError:
            total_amount = 0.0
        return total_amount

    def get_invoice(self):
        invoice_number_pattern = r"([D][E][0-9]{9})"
        invoice_number_match = re.search(invoice_number_pattern, self.text)
        rewe_invoice_number_pattern = r"Beleg-Nr\.\s+(\d+)"
        rewe_invoice_number_match = re.search(rewe_invoice_number_pattern, self.text)

        if rewe_invoice_number_match:
            invoice_number = rewe_invoice_number_match.group(1) if rewe_invoice_number_match else "Not Found"
        elif invoice_number_match:
            invoice_number = invoice_number_match.group(1) if invoice_number_match else "Not found"

        return invoice_number

    def get_TelephoneNumber(self):
        #Telefone number not present in digital receipt
        telephone_number_pattern = r"(Tel\.\s+\d+/\d*)|(Tel\.\s+[\+\d]+[\s\(\)\d]+\s+\d*)"
        telephone_number_match = re.search(telephone_number_pattern, self.text)
        telephone_number = telephone_number_match.group(0) if telephone_number_match else "Not found"
        return telephone_number

    def get_Address(self):
        # Shop names that we want to extract addresses for
        shop_names = ['Kaufland', 'REWE']

        # Identify which shop is in the receipt
        start_index = -1
        shop_name = None

        for shop in shop_names:
            if shop in self.text:
                start_index = self.text.find(shop) + len(shop)
                shop_name = shop
                break

        if start_index == -1:
            return "Shop name not found"

        # Locate the end of the address (usually before another section like Tel, UID, etc.)
        end_keywords = ["Tel", "UID"]
        end_index = len(self.text)  # Default to end of text if no keyword is found

        for keyword in end_keywords:
            found_index = self.text.find(keyword, start_index)
            if found_index != -1:
                end_index = found_index
                break

        # Extract the raw address text
        # Extract address text
        address_text = self.text[start_index:end_index].strip()

        # Split into lines and clean up spaces
        lines = [line.strip() for line in address_text.splitlines() if line.strip()]

        # Regex pattern to detect city names
        city_pattern = re.compile(
            r'\b(?:Berlin|Adlershof|Ingolstadt|Spandau|Munich|Hamburg|Cologne|Frankfurt|Stuttgart|Dusseldorf|Dresden|Leipzig|Hannover)\b',
            re.IGNORECASE
        )

        # Initialize address extraction logic
        address_lines = []
        for line in lines:
            address_lines.append(line)  # Collect all address lines
            if city_pattern.search(line):
                break  # Stop once a city name is found

        return ', '.join(address_lines)

    def get_items(self):
        Address = self.get_Address()
        start_index = self.text.find('EUR') + len('EUR') + 1  # Skip "REWE" and newline
        end_index = self.text.rfind("Total")  # Find last occurrence of "Berlin"
        # Extract the address substring
        items = self.text[start_index:end_index]
        pattern= re.compile((r'(\b[\w.-]+(\s+[\w.-]+)*\s*\d+,\d+\b)'))
        # Find all matches in the text
        matches = pattern.findall(items)
        # Create a dictionary from the matches
        result_dict = {match[0]: match[1].strip() for match in matches}

    def get_date(self):
        # date_pattern = r"Date:\s+(\d{2}.\d{2}.\d{2})"
        # date_pattern = r"Datum:\s*(\d{2}\s*\.\s*\d{2}\s*\.\s*\d{2})"
        date_pattern = r"Datum:?\s*(\d{2}\s*\.\s*\d{2}\s*\.\s*\d{2})|Datum:?\s*(\d{2}\.\d{2}\.\d{2})"
        date_pattern_1 = r"Datum (\d{2}) (\d{2})\.(\d{2})"
        rewe_date_pattern = r"(\d{2}\.\d{2}\.\d{4})"
        date_match = re.search(date_pattern, self.text)
        date_match_1 = re.search(date_pattern_1, self.text)
        rewe_date_match = re.search(rewe_date_pattern, self.text)

        if rewe_date_match:
            date = rewe_date_match.group(1) if rewe_date_match else "Not Found"
            return date
        elif date_match_1:
            # Replace the matched format with "07.10.24"
            formatted_date = f"{date_match_1.group(1)}.{date_match_1.group(2)}.{date_match_1.group(3)}"
            print("Extracted Date:", formatted_date)
            try:
                normalized_date = re.sub(r'\.\s+', '.', formatted_date)
                print("Normalized Date:", normalized_date)
                return normalized_date
            except Exception as e:
                print("Error processing date:", e)
        elif date_match:
            print(' Date object: ', date_match)
            try:
                # Normalize the date based on the matched group
                if date_match.group(1):  # If the first group matches
                    normalized_date = re.sub(r'\.\s+', '.', date_match.group(1))
                    print("Normalized Date (group 1):", normalized_date)
                    return normalized_date
                elif date_match.group(2):  # If the second group matches
                    normalized_date = date_match.group(2)
                    print("Normalized Date (group 2):", normalized_date)
                    return normalized_date
            except Exception as e:
                print("Error processing date:", e)

        else:
            print('No date match found')
            return None

    def get_groceries_bill(self):
        IsNoneItemMatch = False
        Address = self.get_Address()
        start_index = self.text.find('EUR') + len('EUR') + 1  # Skip "REWE" and newline
        # end_index = self.text.rfind("Total")  # Find last occurrence of "Berlin"

        match = re.search(r'Summe|SUMME', self.text, re.IGNORECASE)  # Case-insensitive search
        if match:
            end_index = match.start()  # Get position of the match
        else:
            end_index = -1
        # Extract the address substring
        items = self.text[start_index:end_index]
        lines = items.splitlines()

        result_list = []

        # Second Approach
        for line in lines:
            # First pattern to match
            pattern1 = re.compile(r'^(.+?)\s*(?:(\d+)\s*\*\s*\d+,\d+|\d+,\d+)\s*(\d+,\d+)\s+([A-B])$')
            pattern3 = re.compile(r'^(.+?)\s*(?:x?(\d+))?\s*(\d\s\d{2})\s+([A-B])$')
            pattern_k_card_rabatt = re.compile(
                r'^( K Card Rabatt)\s+(-?\d+,\d+)$')  # New pattern for K Card Rabatt check
            # pattern_rewe  = re.findall(r'([A-ZÄÖÜa-zäöüß\s.-]+)\s+([\d,.]+)\s+[AB]', self.text)
            # pattern_rewe = re.findall(r'([A-ZÄÖÜa-zäöüß\s.-]+)\s+([\d,.]+)\s+[AB]', self.text)
            item_pattern_match1 = re.search(pattern1, line)
            item_pattern_match3 = re.search(pattern3, line)
            k_card_match = re.search(pattern_k_card_rabatt, line)

            if k_card_match:
                item = k_card_match.group(1).strip()
                quantity = 1
                price = float(k_card_match.group(2).replace(',', '.'))
                if price > 0:
                    price = price * -1
                result_dict = {
                    "item": item,
                    "quantity": quantity,
                    "price": price
                }
                result_list.append(result_dict)

            if item_pattern_match1:
                item = item_pattern_match1.group(1).strip()
                quantity = int(item_pattern_match1.group(2)) if item_pattern_match1.group(2) else 1
                price = float(item_pattern_match1.group(3).replace(',', '.'))

                result_dict = {
                    "item": item,
                    "quantity": quantity,
                    "price": price
                }
                result_list.append(result_dict)

            elif item_pattern_match3:
                item = item_pattern_match3.group(1).strip()
                quantity = int(item_pattern_match3.group(2)) if item_pattern_match3.group(2) else 1

                # Capture the price and replace any spaces with commas
                price_text = item_pattern_match3.group(3).replace(" ", ".")
                price = float(price_text)
                result_dict = {
                    "item": item,
                    "quantity": quantity,
                    "price": price
                }
                result_list.append(result_dict)


            else:
                # If first pattern doesn't match, check the second pattern
                pattern2 = re.compile(r'^(.+?)\s*(?:x(\d+))?\s*(\d+.\d+)\s+([A-D])$')
                item_pattern_match2 = re.search(pattern2, line)
                weightpatternRewe = re.compile(
                    r'^(.+?)\s*(?:x(\d+))?\s*(\d+.\d+)\s+([A-D])\s*([A-ZÄÖÜa-zäöüß\s.-]+)\s*\s*([\d,.]+)\s*kg x\s*([\d,.]+)\s*EUR/kg')
                weightpatternRewe_match = re.search(weightpatternRewe, line)
                stuckpatternRewe = re.compile(r'^(.+?)\s*(?:x(\d+))?\s*(\d+.\d+)\s+([A-D])\s*((\d*) Stk x (\d+,\d+))')
                stuckpatternRewe_match = re.search(stuckpatternRewe, line)

                if item_pattern_match2:
                    item = item_pattern_match2.group(1).strip()
                    quantity = int(item_pattern_match2.group(2)) if item_pattern_match2.group(2) else 1
                    price = float(item_pattern_match2.group(3).replace(',', '.'))

                    result_dict = {
                        "item": item,
                        "quantity": quantity,
                        "price": price
                    }
                    result_list.append(result_dict)
                elif weightpatternRewe_match:
                    item = weightpatternRewe_match.group(1).strip()
                    quantity = float(
                        weightpatternRewe_match.group(6).replace(',', '.')) if weightpatternRewe_match.group(6) else 1
                    price = float(weightpatternRewe_match.group(3).replace(',', '.'))
                    unit_price = float(weightpatternRewe_match.group(7).replace(',', '.'))
                    result_dict = {
                        "item": item,
                        "quantity": quantity,
                        "unit_price": unit_price,
                        "price": price
                    }
                    result_list.append(result_dict)

                elif stuckpatternRewe_match:
                    item = stuckpatternRewe_match.group(1).strip()
                    quantity = float(stuckpatternRewe_match.group(6).replace(',', '.')) if stuckpatternRewe_match.group(
                        6) else 1
                    price = float(stuckpatternRewe_match.group(3).replace(',', '.'))
                    unit_price = float(stuckpatternRewe_match.group(7).replace(',', '.'))
                    result_dict = {
                        "item": item,
                        "quantity": quantity,
                        "unit_price": unit_price,
                        "price": price
                    }
                    result_list.append(result_dict)
        result_json = json.dumps(result_list, indent=2)
        return result_list
        # Convert the list of dictionaries to JSON
        #result_json = json.dumps(result_list, indent=2)



    def create_CSV(self):
            df = pd.read_json(r'static\json\{}.json'.format(self.bill_name))
            df['index'] = df.index
            df['index'] += 1
            df.set_index('index', inplace=True)
            print('+++++++Create_CSV_METHOD+++++',df)
            return df
            #df.to_csv(r'Bills_CSV\{}.csv'.format(self.bill_name), encoding='utf-8', index=False)

    def create_data_frame(self):
        # Extracting data
        shop_name = self.get_shop_name()
        address = self.get_Address()
        invoice_number = self.get_invoice()
        total_sum = self.get_Total_amount()
        items = self.get_groceries_bill()
        date = self.get_date()
        bill_id = self.bill_name
        month = self.month
        year = self.year
        # Construct JSON object
        result_dict = {
            "shopName": shop_name,
            "address": address,
            "invoiceNumber": invoice_number,
            "totalSum": total_sum,
            "items": items,
            "date":date,
            "billId":bill_id,
            "month":month,
            "year":year
        }

        result_json = json.dumps(result_dict, indent=2)
        base_directory = "static/json/"
        json_folder = os.path.join(base_directory, self.year,self.month)
        if not os.path.exists(json_folder):
            os.makedirs(json_folder)
        # Save JSON to file
        json_filename = f"{self.bill_name}.json"
        json_path = os.path.join(json_folder, json_filename)  # Specify your folder path here
        with open(json_path, "w") as json_file:
            json_file.write(result_json)
        # Construct DataFrame
        df = pd.DataFrame(items, columns=['item', 'quantity', 'price'])
        df['shopName'] = shop_name
        df['address'] = address
        df['invoiceNumber'] = invoice_number
        df['totalSum'] = total_sum
        df['date'] = date
        df['month'] = month
        df['year'] = year
        df['billId'] = bill_id
        print('**** create_data_frame ****',df)
        logger.info(df)
        return df