import pandas as pd
from datetime import datetime
from datetime import timedelta
# fintrek_current - Symbol	Buy Price	Current Price	Quantity	Buy Date	Days	Returns(%)	Expected Returns(%)	Amount	Allocation(%)	Portfolio Returns(%)	P&L
# fintrek_exited -  Symbol	Buy Price	Sell Price	Quantity	Buy Date	Sell Date	Days	Returns(%)	Expected Returns(%)	P&L

def format_indian_currency(amount):
    """Format number to Indian style with ₹ symbol"""
    amount = int(amount)
    amount_str = format(amount, ",")  # Add commas
    return f'₹ {amount_str}'


def calculate_invested_amount(df_input, start_date, end_date):
    # Convert the date columns and input dates to datetime format
    df = df_input.copy(deep=True)
    df['Buy Date'] = pd.to_datetime(df['Buy Date'])

    if 'Sell Date' in df.columns:
        df['Sell Date'] = pd.to_datetime(df['Sell Date'])
    else:
        df['Sell Date'] = pd.to_datetime(datetime.now().date())  # Set Sell Date as today for all rows


    start_date = pd.to_datetime(start_date)
    end_date = pd.to_datetime(end_date)

    total_days = (end_date - start_date).days   # +1 to make it inclusive of both start and end dates

    # Calculate days invested for each stock within the given date range
    df['invested_days'] = (
        df.apply(lambda row:
            min(row['Sell Date'], end_date) - max(row['Buy Date'], start_date) ,
            axis=1
        ).dt.days.clip(lower=0)  # Make sure we don't have negative days
    )

    # Calculate the amount invested for the duration the stock was held within the date range
    df['invested_amount'] = (
        df['Buy Price'] *
        df['Quantity'] *
        df['invested_days'] / total_days
    )

    # Calculate the adjusted returns based on the invested days during the date range
    df['adjusted_profits'] = (
        df['P&L'] * df['invested_days'] / df['Days']
    )

    df['adjusted_returns(%)'] = (
        df['adjusted_profits']  / df['invested_amount'] * 100
    )

    # Calculate the total returns based on the invested amount and adjusted returns for each stock
    df['individual_contribution'] = df['invested_amount'] * (
                df['adjusted_returns(%)'] / 100)


    total_invested_amount = df['invested_amount'].sum()
    if total_invested_amount == 0:
        total_returns = 0
    else:
        total_returns = df['individual_contribution'].sum() / total_invested_amount * 100

    return df, total_invested_amount, total_returns



should_refresh_returns = int(fintrek_input[fintrek_input['name'] == 'should_refresh_returns']['value'].values[0])
if should_refresh_returns == 0:
    return None, None, None, None

returns_for_days = int(fintrek_input[fintrek_input['name'] == 'returns_for_days']['value'].values[0])

offsets = [7, 30, 60, 90, 180, 270, 365, returns_for_days]
# Current date
end_date = datetime.now().date()
returns_array = []

select_dict = {}
select_current_df = None
select_exited_df = None


for offset in offsets:
    start_date = end_date - timedelta(days=offset)
    current_df, current_invested_amount, current_returns = calculate_invested_amount(fintrek_current, start_date, end_date)
    exited_df, exited_invested_amount, exited_returns = calculate_invested_amount(fintrek_exited, start_date, end_date)
    total_invested_amount = current_invested_amount + exited_invested_amount
    total_returns = (current_invested_amount * current_returns + exited_invested_amount * exited_returns) / total_invested_amount
    returns_dict = {
        'offset': offset,
        'start_date': start_date.strftime('%d-%m-%Y'),
        'end_date': end_date.strftime('%d-%m-%Y'),
        'current_invested_amount': current_invested_amount,
        'current_returns': current_returns,
        'exited_invested_amount': exited_invested_amount,
        'exited_returns': exited_returns,
        'total_invested_amount': total_invested_amount,
        'total_returns': total_returns
    }
    returns_array.append(returns_dict)
    if offset == returns_for_days:
        select_dict = returns_dict
        select_current_df = current_df.copy(deep=True)
        select_exited_df = exited_df.copy(deep=True)


returns_df = pd.DataFrame(returns_array)

##These are optional and maybe removed as this makes it a string.
returns_df['current_invested_amount'] = returns_df['current_invested_amount'].apply(format_indian_currency)
returns_df['exited_invested_amount'] = returns_df['exited_invested_amount'].apply(format_indian_currency)
returns_df['total_invested_amount'] = returns_df['total_invested_amount'].apply(format_indian_currency)
returns_df['current_returns'] = returns_df['current_returns'].apply(lambda x: f'{x:.2f}%')
returns_df['exited_returns'] = returns_df['exited_returns'].apply(lambda x: f'{x:.2f}%')
returns_df['total_returns'] = returns_df['total_returns'].apply(lambda x: f'{x:.2f}%')

##Rename all columns
returns_df = returns_df.rename(columns={
    'offset': 'Days',
    'start_date': 'Start Date',
    'end_date': 'End Date',
    'current_invested_amount': 'Current Invested Amount',
    'current_returns': 'Current Returns',
    'exited_invested_amount': 'Exited Invested Amount',
    'exited_returns': 'Exited Returns',
    'total_invested_amount': 'Total Invested Amount',
    'total_returns': 'Total Returns'
})



## process select_dict, select_current_df, select_exited_df
## Remove start_date,  end_date  from select_dict
select_dict.pop('start_date')
select_dict.pop('end_date')

## Format the keys in select_dict with proper caps and spaces
select_dict = {k.replace('_', ' ').title(): v for k, v in select_dict.items()}
select_dict['Total Returns'] = f'{select_dict["Total Returns"]:.2f}%'
select_dict['Current Returns'] = f'{select_dict["Current Returns"]:.2f}%'
select_dict['Exited Returns'] = f'{select_dict["Exited Returns"]:.2f}%'
select_dict['Current Invested Amount'] = format_indian_currency(select_dict['Current Invested Amount'])
select_dict['Exited Invested Amount'] = format_indian_currency(select_dict['Exited Invested Amount'])
select_dict['Total Invested Amount'] = format_indian_currency(select_dict['Total Invested Amount'])


##Rename Current Invested Amount to Invested Amount in select_dict
select_dict['Current Amount'] = select_dict.pop('Current Invested Amount')
select_dict['Exited Amount'] = select_dict.pop('Exited Invested Amount')

##Make select_dict into a dataframe
select_numbers_df = pd.DataFrame([select_dict])


##Remove rows from select_exited_df where individual_contribution is 0
select_exited_df = select_exited_df[select_exited_df['individual_contribution'] != 0]
select_current_df = select_current_df[select_current_df['individual_contribution'] != 0]

return returns_df, select_current_df, select_exited_df, select_numbers_df


