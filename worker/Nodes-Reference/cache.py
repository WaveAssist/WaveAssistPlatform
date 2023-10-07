import pytz
ist = pytz.timezone('Asia/Kolkata')
from datetime import datetime
from datetime import timedelta
import pandas as pd

##fintrek_remaining_buy_trades: isin_check	symbol	exchange	buy_date	remaining_qty	weighted_avg_price

def format_indian_currency(amount):
    """Format number to Indian style with ₹ symbol"""
    amount = int(amount)
    amount_str = format(amount, ",")  # Add commas
    return f'₹ {amount_str}'

def format_percentages(value):
    return f'{value:.2f}%'


def refresh_prices(df):
    df['kite_symbol'] = df['exchange'] + ":" + df['symbol']
    symbols_list = df['kite_symbol'].unique().tolist()
    all_quotes = kite.quote(symbols_list)

    # Moved datetime calculations out of the loop
    today_str = datetime.now(ist).strftime("%Y-%m-%d %H:%M:%S")
    from_str = (datetime.now(ist) - timedelta(days=10)).strftime("%Y-%m-%d %H:%M:%S")


    for key, value in all_quotes.items():
        try:
            price = value['last_price']
            low = value['ohlc']['low']
            high = value['ohlc']['high']
            instrument_token = str(value['instrument_token'])


            ##Get the historical data for each symbol
            historical_data = kite.historical_data(instrument_token, from_str, today_str, 'day', continuous=False, oi=False)
            history_df = pd.DataFrame(historical_data)
            history_df.sort_values(by=['date'], inplace=True, ascending=False)

            ##Remove today's date row if it exists
            today_str_date_only = datetime.now(ist).strftime("%Y-%m-%d")
            history_df = history_df[history_df['date'].dt.strftime("%Y-%m-%d") != today_str_date_only]

            ##Get the close of first row
            yesterday_price = history_df.iloc[0]['close']


            ##Set values
            df.loc[df['kite_symbol'] == key, 'current_price'] = price
            df.loc[df['kite_symbol'] == key, 'low'] = low
            df.loc[df['kite_symbol'] == key, 'high'] = high
            df.loc[df['kite_symbol'] == key, 'yesterday_close'] = yesterday_price
        except Exception as e:
            print("Error with symbol: " + key + " error: " + str(e))
            continue

    return df



def get_message_count_for_today(alerts_df):
    # Localize the timestamp to IST
    if len(alerts_df) == 0:
        return 0

    ist_timezone = pytz.timezone('Asia/Kolkata')
    today = datetime.now(ist_timezone).date()

    # Filter for today's alerts
    alerts_today = alerts_df[pd.to_datetime(alerts_df['timestamp']).dt.date == today]

    # Count the alerts
    count_today = len(alerts_today)
    return count_today


def update_alerts(alerts_df):
    alert_dict = {
        'alert_type': 'email',
        'alert_name': 'finTrek_emails',
        'timestamp': datetime.now(ist).strftime("%Y-%m-%d %H:%M:%S"),
    }
    alerts_df = pd.concat([alerts_df, pd.DataFrame([alert_dict])], ignore_index=True)
    alerts_df = alerts_df.tail(20) ##Capping to only last 20 in storage
    return alerts_df



should_email_summary = False

messages_today = get_message_count_for_today(fintrek_alerts)

##Check if time is between 6 & 7 AM with timezone of IST
current_time = datetime.now(ist).strftime("%H:%M:%S")


if current_time > '10:00:00':
    if messages_today == 0:
        should_email_summary = True

if current_time > '15:30:00':
    if messages_today < 2:
        should_email_summary = True



if should_email_summary:
    df = refresh_prices(fintrek_remaining_buy_trades)

    # Calculate the new columns
    df['quantity'] = df['remaining_qty']
    df['buy_amount'] = df['weighted_avg_price'] * df['quantity']
    df['current_amount'] = df['current_price'] * df['quantity']

    ##Today
    df['today_p&l'] = df['current_price'] - df['yesterday_close']
    df['today_p&l_amount'] = df['today_p&l'] * df['quantity']
    df['today_p&l_percent'] = (df['today_p&l'] / df['yesterday_close']) * 100

    ##Total
    df['total_p&l'] = df['current_price'] - df['weighted_avg_price']
    df['total_p&l_amount'] = df['total_p&l'] * df['quantity']
    df['total_p&l_percent'] = (df['total_p&l_amount'] / df['buy_amount']) * 100


    # Create the result dataframe with the desired columns
    df = df[
        ['symbol', 'buy_amount', 'current_price', 'yesterday_close', 'current_amount', 'high', 'low', 'today_p&l', 'today_p&l_amount', 'today_p&l_percent',
            'total_p&l', 'total_p&l_amount', 'total_p&l_percent','quantity']]


    # Assuming you have 'yesterday_close' column in df
    portfolio_yesterday = (df['yesterday_close'] * df['quantity']).sum()
    portfolio_high = (df['high'] * df['quantity']).sum()
    high_percent = ((portfolio_high - portfolio_yesterday) / portfolio_yesterday) * 100

    portfolio_low = (df['low'] * df['quantity']).sum()
    low_percent = ((portfolio_low - portfolio_yesterday) / portfolio_yesterday) * 100


    total_pnl_amount = df['total_p&l_amount'].sum()
    total_buy_amount = df['buy_amount'].sum()
    total_pnl_percent = (total_pnl_amount / total_buy_amount) * 100



    today_pnl_amount = df['today_p&l_amount'].sum()
    today_pnl_percent = (today_pnl_amount / total_buy_amount) * 100


    # Format the values
    high_percent_str = f'{high_percent:.2f}%'
    low_percent_str = f'{low_percent:.2f}%'
    total_pnl_str = format_indian_currency(total_pnl_amount)
    total_pnl_percent_str = f'{total_pnl_percent:.2f}%'
    today_pnl_str = format_indian_currency(today_pnl_amount)
    today_pnl_percent_str = f'{today_pnl_percent:.2f}%'


    ## Format df
    df['buy_amount'] = df['buy_amount'].apply(format_indian_currency)
    df['current_amount'] = df['current_amount'].apply(format_indian_currency)
    df['today_p&l_amount'] = df['today_p&l_amount'].apply(format_indian_currency)
    df['total_p&l_amount'] = df['total_p&l_amount'].apply(format_indian_currency)


    df['today_p&l_percent'] = df['today_p&l_percent'].apply(format_percentages)
    df['total_p&l_percent'] = df['total_p&l_percent'].apply(format_percentages)


    ##Sort df by symbol
    df = df.sort_values(by=['symbol'])

    header_dict = {
        'Today P&L': today_pnl_str,
        'Today P&L Percent': today_pnl_percent_str,
        'Total P&L': total_pnl_str,
        'Total P&L Percent': total_pnl_percent_str,
        'High Percent': high_percent_str,
        'Low Percent': low_percent_str
    }
    header_df = pd.DataFrame([header_dict])


    # Creating a styled HTML string for the numbers
    numbers_html = header_df.to_html(index=False)

    # Adding the new HTML to your email body
    email_body = "<h3>Current Portfolio</h3>"
    email_body += numbers_html  # Add the numbers above the table

    email_body += "<br><br><hr><br><br>"

    email_body += df.to_html(index=False)

    to = 'kakshil.shah@wavepredict.com'
    mailer.send_email(to, "Daily stock updates from FinTrek", email_body)


    fintrek_alerts = update_alerts(fintrek_alerts)

return fintrek_alerts