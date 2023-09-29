import pandas as pd



should_refresh = int(fintrek_input[fintrek_input['name'] == 'should_refresh_trades']['value'].values[0])

if should_refresh == 0:
    return None, None, None


# Convert 'trade_date' column to datetime if it's not already
fintrek_tradebook['trade_date'] = pd.to_datetime(fintrek_tradebook['trade_date'])
fintrek_tradebook['weighted_price'] = fintrek_tradebook['price'] * fintrek_tradebook['quantity']


##Buy df
buy_df = fintrek_tradebook[fintrek_tradebook['trade_type'] == 'buy']

grouped_buy_df = (
    buy_df.groupby(['isin', 'trade_date'])
    .agg(
        symbol=('symbol', 'first'),
        exchange=('exchange', 'first'),
        total_quantity=('quantity', 'sum'),
        total_weighted_price=('weighted_price', 'sum')
    )
    .reset_index()
)

# Compute the weighted average price using the aggregated data
grouped_buy_df['weighted_avg_price'] = grouped_buy_df['total_weighted_price'] / grouped_buy_df['total_quantity']

# Drop the intermediate column if you no longer need it
grouped_buy_df.drop(columns=['total_weighted_price'], inplace=True)



##Sell df
sell_df = fintrek_tradebook[fintrek_tradebook['trade_type'] == 'sell']
grouped_sell_df = (
    sell_df.groupby(['isin', 'trade_date'])
    .agg(
        symbol=('symbol', 'first'),
        exchange=('exchange', 'first'),
        total_quantity=('quantity', 'sum'),
        total_weighted_price=('weighted_price', 'sum')
    )
    .reset_index()
)

grouped_sell_df['weighted_avg_price'] = grouped_sell_df['total_weighted_price'] / grouped_sell_df['total_quantity']
grouped_sell_df.drop(columns=['total_weighted_price'], inplace=True)


# Sort both DataFrames by trade_date
grouped_buy_df = grouped_buy_df.sort_values(by='trade_date')
grouped_sell_df = grouped_sell_df.sort_values(by='trade_date')

# List to store P&L data
pnl_list = []

# Loop through unique ISINs in buy dataframe
for isin_val in grouped_buy_df['isin'].unique():

    specific_isin_buy_df = grouped_buy_df[grouped_buy_df['isin'] == isin_val]
    specific_isin_sell_df = grouped_sell_df[grouped_sell_df['isin'] == isin_val]



    for buy_index, buy_row in specific_isin_buy_df.iterrows():
        remaining_buy_qty = buy_row['total_quantity']

        while remaining_buy_qty > 0 and not specific_isin_sell_df.empty:
            sell_row = specific_isin_sell_df.iloc[0]
            matched_qty = min(remaining_buy_qty, sell_row['total_quantity'])

            # Compute P&L
            profit_or_loss = (sell_row['weighted_avg_price'] - buy_row['weighted_avg_price']) * matched_qty
            pnl_list.append({
                'isin': buy_row['isin'],
                  'symbol': buy_row['symbol'],
                  'exchange': buy_row['exchange'],
                  'buy_date': buy_row['trade_date'],
                  'sell_date': sell_row['trade_date'],
                  'matched_qty': matched_qty,
                  'buy_price': buy_row['weighted_avg_price'],
                  'sell_price': sell_row['weighted_avg_price'],
                  'pnl': profit_or_loss
            })


            # Update quantities
            remaining_buy_qty -= matched_qty
            grouped_buy_df.at[buy_index, 'total_quantity'] -= matched_qty
            if matched_qty == sell_row['total_quantity']:
                specific_isin_sell_df.drop(sell_row.name, inplace=True, errors='ignore')
                grouped_sell_df.drop(sell_row.name, inplace=True, errors='ignore')
            else:
                specific_isin_sell_df.at[sell_row.name, 'total_quantity'] -= matched_qty
                grouped_sell_df.at[sell_row.name, 'total_quantity'] -= matched_qty

pnl_df = pd.DataFrame(pnl_list)

print("P&L df: " + str(pnl_df))


# Remaining buys after matching
remaining_buys = []
for _, buy_row in grouped_buy_df.iterrows():
    remaining_buy_qty = int(buy_row['total_quantity'])
    if remaining_buy_qty > 0:
        remaining_buys.append({
            'isin_check': buy_row['isin'],
            'symbol': buy_row['symbol'],
            'exchange': buy_row['exchange'],
            'buy_date': buy_row['trade_date'],
            'remaining_qty': remaining_buy_qty,
            'weighted_avg_price': buy_row['weighted_avg_price']
        })


remaining_buys_df = pd.DataFrame(remaining_buys)

# In case you want to check if any sells were not processed (though it's unlikely based on the scenario described):
remaining_sells = []
for _, sell_row in grouped_sell_df.iterrows():
    remaining_sell_qty = sell_row['total_quantity']
    if remaining_sell_qty > 0:
        remaining_sells.append({
            'symbol': sell_row['symbol'],
            'Date': sell_row['trade_date'].strftime('%d-%m-%Y'),
            'Quantity': int(remaining_sell_qty),
            'Price': int(sell_row['weighted_avg_price']),
            'Amount': int(remaining_sell_qty * float(sell_row['weighted_avg_price']))
        })


remaining_sells_df = pd.DataFrame(remaining_sells)
remaining_buys_df.fillna(0, inplace=True)
remaining_sells_df.fillna(0, inplace=True)

pnl_df.fillna(0, inplace=True)

return remaining_buys_df , remaining_sells_df, pnl_df





