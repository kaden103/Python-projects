import csv
import locale
locale.setlocale(locale.LC_ALL, '')
# Introuduce the file and open to begin unpacking the data inside
FILENAME = 'walmart_inventory.csv'
#Opening the CSV file to store inside the fidleHdl variable
fileHdl = open(FILENAME, 'r', encoding='utf-8-sig')
# Use the CSV function to read the CSV FILE type into the dictRdr variable
dictRdr = csv.DictReader(fileHdl)
# Create inventoryCost dictionary to store obtained data
inventoryCost = dict()

def main(): # Main function which ties functions together, and creates the apps headings "Primary" and "Values"
    CostCollector()
    print(f"{'Primary Category' : >58}", f"{'Values' : ^52}")
    DisplayInventoryCost()




def CostCollector():
    for row in dictRdr: # Loop through the file for each row inside the Primary category section, and it's corresponding value, then insert it into inventory cost
        if row['primary_category'] in inventoryCost.keys():
            inventoryCost[row['primary_category']] += float(row['price']) * float(row['quantity'])
        else:
            inventoryCost[row['primary_category']] = float(row['price']) * float(row['quantity'])

def DisplayInventoryCost(): # Function responsible for display of key and corresponding value pair
    for key, value in inventoryCost.items():
        print(f"{key : >60}",  f"{locale.currency(value, grouping=True) : >30}")



main()

