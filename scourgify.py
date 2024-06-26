import sys
import csv

# Function used to strip data error from the first and last name paring, returns the names as individual data points
def Name_Split(file_worked):
    file_edit = file_worked.split(',')
    return file_edit

# Define the expected file extension
if sys.argv[1].endswith(".csv") and sys.argv[2]:
    try:
        # Testing if the command-line has the correct entries to run app, If not sys.exit(1)
        file_name = sys.argv[1]
        writer_name = sys.argv[2]
    except TypeError:
        sys.exit(1)

# Check if the file name ends with the expected extension
if file_name.endswith(".csv") and len(sys.argv) == 3:
    try:
        # Open said file, after checking to make sure it ends in .csv and is no more than 3 command-lines
        # Also open a file to write the new data into to fix data entry error
        with open(file_name,mode='r') as viewer, open(writer_name,mode='w') as writer:
            # Use the file_name='r' to open the file in read mode for the user to see but not make any changes to
            reader = csv.DictReader(viewer)
            # Create the new field names, first,last,house to seperate the headers correctly
            updated = csv.DictWriter(writer, fieldnames= ["first", "last","house"])
            # Write the new headers into a new file/create the new file with updated headers
            updated.writeheader()

            # Iterate over the row inside the 'reader' file to locate the row['name']
            for row in reader:
                # Once found split the data into 2 with the Name_Split function above
                first_name, last_name = Name_Split(row['name'])
                # Assign the new data to the corresponding pair
                row["first"] = last_name.strip()
                row["last"] = first_name.strip()
                # Delete row['name'] and strip and unwanted white space left behind
                del row['name']
                # Write the new restructed data into the updated file
                updated.writerow(row)
    except FileNotFoundError:
        sys.exit(1)

