import pytz
from datetime import datetime
import pandas as pd
from datetime import timedelta
ist = pytz.timezone('Asia/Kolkata')
PARITY_TYPE = 'parity'
EXIT_TYPE = 'exit'

def fetch_message_count(alerts_df, parity_call_price_greater):
    if len(alerts_df) == 0:
        return 0, 0

    now_timestamp = datetime.now(ist)
    # Filter for parity alerts within the last 4 hours and with the specific alert_value
    four_hours_ago_timestamp = now_timestamp - timedelta(hours=4)
    parity_alerts = alerts_df[
        (pd.to_datetime(alerts_df['timestamp']).dt.tz_localize(ist) > four_hours_ago_timestamp) &
        (alerts_df['alert_type'] == PARITY_TYPE) &
        (alerts_df['alert_value'] == str(parity_call_price_greater))
        ]

    ## Filter for exit alerts
    two_hours_ago_timestamp = now_timestamp - timedelta(hours=2)
    exit_alerts = alerts_df[
        (pd.to_datetime(alerts_df['timestamp']).dt.tz_localize(ist) > two_hours_ago_timestamp) &
        (alerts_df['alert_type'] == EXIT_TYPE)
        ]

    ##Return
    return len(parity_alerts), len(exit_alerts)


def update_alerts(alerts_df, type, parity):
    alert_dict = {
        'alert_type': str(type),
        'alert_name': 'vyapak_alerts',
        'alert_value': str(parity),
        'timestamp': datetime.now(ist).strftime("%Y-%m-%d %H:%M:%S"),
    }
    alerts_df = pd.concat([alerts_df, pd.DataFrame([alert_dict])], ignore_index=True)
    alerts_df = alerts_df.tail(20) ##Capping to only last 20 in storage
    return alerts_df





def is_realtime(vyapak_bottom_numbers):
    zerodha_updated_str = str(vyapak_bottom_numbers['Zerodha Updated'][0])
    ib_updated_str = str(vyapak_bottom_numbers['IB Updated'][0])
    # Parse the string representations into datetime objects
    zerodha_updated = datetime.strptime(zerodha_updated_str, "%Y-%m-%d %H:%M:%S")
    ib_updated = datetime.strptime(ib_updated_str, "%Y-%m-%d %H:%M:%S")

    # Calculate the time difference
    time_difference = ib_updated - zerodha_updated

    # Extract the total time difference in seconds
    time_difference_seconds = abs(time_difference.total_seconds())
    if time_difference_seconds < 200:
        return True
    else:
        return False

##Inputs
parity_call_price_greater = int(vyapak_input[vyapak_input['name'] == 'parity_call_price_greater']['value'].values[0])
parity_call_first_strike = int(vyapak_input[vyapak_input['name'] == 'parity_call_first_strike']['value'].values[0])


##Data required
filtered_df = vyapak_merged_calls[(vyapak_merged_calls["Zerodha Strike"] >= parity_call_first_strike) & (
            vyapak_merged_calls["Parity"] >= parity_call_price_greater)]
filtered_df = filtered_df[['Zerodha Strike', 'Parity', 'IB Price', 'Currency Hedge']]

##Formatting
formatted_rows = []
for index, row in filtered_df.iterrows():
    formatted_row = f"{row['Zerodha Strike']} = {row['Parity']} - ({row['IB Price']}) : {row['Currency Hedge']}"
    formatted_rows.append(formatted_row)
main_content = '\n'.join(formatted_rows)
subject = "WaveAssist Alert: Parity greater than -  " + str(parity_call_price_greater)
to_array = ["1163933846","6250108283","6446747579"]

##Top numbers content
zerodha_spot = str(vyapak_top_numbers['Zerodha Spot'][0])
selected_dollar_rate = str(vyapak_top_numbers['Selected Dollar Rate'][0])
live_dollar_rate = str(vyapak_top_numbers['Live Dollar Rate'][0])
main_content = main_content + '\n\n'+ 'Spot: ' + zerodha_spot + ', $/INR: ' + live_dollar_rate + '\n\n' + 'Set rate: ' + selected_dollar_rate

##Check if realtime
is_live = is_realtime(vyapak_bottom_numbers)
if not is_live:
    return None


##Fetch counts
parity_messages, exit_messages = fetch_message_count(vyapak_alerts, str(parity_call_price_greater))

##Send parity messages
if parity_messages < 8 and len(filtered_df) > 0 and is_live:
    vyapak_alerts = update_alerts(vyapak_alerts, PARITY_TYPE, str(parity_call_price_greater))
    for to in to_array:
        telegram.send_message(to, subject + "\n\n" + main_content)

##Send exit messages
selected_rows = []
for index, row in vyapak_mytrades.iterrows():
    try:
        target = row['target']
        notification = row['notiifcation']
        parity = row['Parity']
        if int(notification) == 1:
            if float(parity) <= float(target):
                selected_rows.append(row)
    except Exception as e:
        print(e)

subject = "Exit target crossed - WaveAssist Alert"
body = str(selected_rows)

if exit_messages < 4 and len(selected_rows) > 0 and is_live:
    vyapak_alerts = update_alerts(vyapak_alerts, EXIT_TYPE, "0")
    for to in to_array:
        telegram.send_message(to, subject + "\n\n" + body)

return vyapak_alerts