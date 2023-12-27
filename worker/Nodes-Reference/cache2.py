import xlwings as xw
import pandas as pd

# Open the workbook and select the sheet
wb = xw.Book('/Users/shreyarao/Desktop/crude_watch.xlsx')
sheet = wb.sheets['Sheet1']

# Read the entire used range of the sheet
data = sheet.range('A1').expand().value

# Convert the data to a Pandas DataFrame
df = pd.DataFrame(data[1:], columns=data[0])

print(df)

# Close the workbook if it's no longer needed
wb.close()
