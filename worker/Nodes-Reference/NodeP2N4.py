# from kiteconnect import KiteConnect
# import pandas as pd
# from datetime import datetime
# from py_vollib.black_scholes.implied_volatility import implied_volatility
# from py_vollib.black_scholes.greeks.analytical import delta
# from py_vollib.black_scholes import black_scholes
#
#
# ##From DF WAU359P2D6, show name, fut_expiry_0, fut_price_0, last_price, strike_0, option_price_0, iv_0, delta_0
# WAU359P2D6 = WAU359P2D6[['name', 'fut_expiry_0', 'fut_price_0', 'strike_0', 'option_price_0', 'iv_0', 'delta_0']]
#
# ##Rename each column, remove _0
# WAU359P2D6.rename(columns={'name':'Name','fut_expiry_0': 'Expiry', 'fut_price_0': 'Future Price', 'strike_0': 'Strike', 'option_price_0': 'Option Price', 'iv_0': 'IV', 'delta_0': 'Delta'}, inplace=True)
#
# ##Multiply IV & Delta by 100 and round off to 2 decimals
# WAU359P2D6['IV'] = WAU359P2D6['IV'] * 100
# WAU359P2D6['IV'] = WAU359P2D6['IV'].round(1)
# WAU359P2D6['Delta'] = WAU359P2D6['Delta'] * 100
# WAU359P2D6['Delta'] = WAU359P2D6['Delta'].round(0)
#
# return WAU359P2D6
#
#
#
