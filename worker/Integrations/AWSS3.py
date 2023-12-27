import boto3

class AWSS3(object):
    def __init__(self):
        self.s3 = None
        self.access_key = None
        self.secret = None

    def get_s3(self):
        return self.s3

    def set_keys(self, access_key, secret):
        if access_key != self.access_key or secret != self.secret:
            self.access_key = access_key
            self.secret = secret
            self.s3 = boto3.client('s3', aws_access_key_id=self.access_key, aws_secret_access_key=self.secret)
        return self.s3

    def get_s3_based_on_integrations(self, integrations_df):
        try:
            access_key = str(integrations_df[integrations_df['name'] == 'AWSS3_ACCESS_KEY']['value'].values[0])
            secret = str(integrations_df[integrations_df['name'] == 'AWSS3_SECRET']['value'].values[0])
            return self.set_keys(access_key,secret)
        except:
            return self.s3


# Integration code:
# from Integrations.AWSS3 import AWSS3
# awsS3 = AWSS3()


##Function code:
# s3 = awsS3.get_s3_based_on_integrations(integrations_df)