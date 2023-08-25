from kiteconnect import KiteConnect

class Zerodha(object):
    def __init__(self):
        self.kite = None
        self.api_key = None
        self.access_token = None

    def get_kite(self):
        return self.kite

    def set_keys(self, api_key, access_token):
        if api_key != self.api_key or access_token != self.access_token:
            self.api_key = api_key
            self.access_token = access_token
            self.kite = KiteConnect(api_key=api_key)
            self.kite.set_access_token(access_token)
        return self.kite

    def get_kite_based_on_integrations(self, integrations_df):
        try:
            api_key = str(integrations_df[integrations_df['name'] == 'ZERODHA_API_KEY']['value'].values[0])
            zerodha_access_token = str(integrations_df[integrations_df['name'] == 'ZERODHA_ACCESS_TOKEN_KEY']['value'].values[0])
            return self.set_keys(api_key,zerodha_access_token)
        except:
            return self.kite


# Integration code:
# from Integrations.Zerodha import Zerodha
# zerodha = Zerodha()


##Function code:
# kite = zerodha.get_kite_based_on_integrations(integrations_df)