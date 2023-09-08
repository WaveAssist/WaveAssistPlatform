import pytz

ist = pytz.timezone('Asia/Kolkata')
from datetime import datetime

parity_call_price_greater = int(vyapak_input[vyapak_input['name'] == 'parity_call_price_greater']['value'].values[0])
parity_call_first_strike = int(vyapak_input[vyapak_input['name'] == 'parity_call_first_strike']['value'].values[0])

filtered_df = vyapak_merged_calls[(vyapak_merged_calls["Zerodha Strike"] >= parity_call_first_strike) & (
            vyapak_merged_calls["Parity"] >= parity_call_price_greater)]

filtered_df = filtered_df[['Zerodha Strike', 'Parity', 'IB Price', 'Currency Hedge']]
main_content = filtered_df.to_string(index=False)

subject = "WaveAssist Alert: Parity greater than -  " + str(parity_call_price_greater)

to = "1163933846"

##Check if both zerodha & IB are logged in. If not - Send email?
zerodha_updated_str = str(vyapak_bottom_numbers['Zerodha Updated'][0])
ib_updated_str = str(vyapak_bottom_numbers['IB Updated'][0])

# Parse the string representations into datetime objects
zerodha_updated = datetime.strptime(zerodha_updated_str, "%Y-%m-%d %H:%M:%S")
ib_updated = datetime.strptime(ib_updated_str, "%Y-%m-%d %H:%M:%S")

# Calculate the time difference
time_difference = ib_updated - zerodha_updated

# Extract the total time difference in seconds
time_difference_seconds = time_difference.total_seconds()

if time_difference_seconds > 200:
    return

identifier = str(parity_call_price_greater)

recent_messages = telegram.fetch_recent_messages()

messages_in_last_4_hours = 0
exit_messages_in_last_4_hours = 0
exit_identifier = 'exit'
for message_dict in recent_messages:
    timestamp = message_dict['timestamp']
    sent_before = (datetime.now(ist) - timestamp).total_seconds()

    if message_dict['identifier'] == identifier:
        if sent_before <= 14400:
            messages_in_last_4_hours += 1
    elif message_dict['identifier'] == exit_identifier:
        if sent_before <= 7400:
            exit_messages_in_last_4_hours += 1

if messages_in_last_4_hours < 2 and len(filtered_df) > 0:
    telegram.send_message(to, subject + "\n\n" + main_content, identifier)


selected_rows = []
for index, row in vyapak_mytrades.iterrows():
    try:
        zerodha_strike = float(row['zerodhaStrike'])
        ib_strike = float(row['ibStrike'])
        option_type = row['optionType']
        target = row['target']
        notification = row['notiifcation']
        parity = row['Parity']

        if int(notification) == 1:
            if float(parity) <= float(target):
                ##Select this row.
                selected_rows.append(row)
    except Exception as e:
        print(e)

subject = "Exit target crossed - WaveAssist Alert"
body = str(selected_rows)

if exit_messages_in_last_4_hours < 4 and len(selected_rows) > 0:
    telegram.send_message(to, subject + "\n\n" + body, exit_identifier)
