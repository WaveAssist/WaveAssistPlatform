##Import libraries
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from time import sleep
import pyotp
import pytz
ist = pytz.timezone('Asia/Kolkata')

from datetime import datetime

##Check if time is between 6 & 7 AM with timezone of IST
current_time = datetime.now(ist).strftime("%H:%M:%S")
if current_time < '06:00:00' or current_time > '07:00:00':
    print("Not in time")
    return


api_key = str(Integrations_WAU359P1[Integrations_WAU359P1['name'] == 'ZERODHA_API_KEY']['value'].values[0])
api_secret = str(Integrations_WAU359P1[Integrations_WAU359P1['name'] == 'ZERODHA_API_SECRET']['value'].values[0])
project_key = str(Integrations_WAU359P1[Integrations_WAU359P1['name'] == 'PROJECT_KEY']['value'].values[0])
uid = str(Integrations_WAU359P1[Integrations_WAU359P1['name'] == 'UID']['value'].values[0])
zerodha_username = str(Integrations_WAU359P1[Integrations_WAU359P1['name'] == 'ZERODHA_USERNAME']['value'].values[0])
zerodha_password = str(Integrations_WAU359P1[Integrations_WAU359P1['name'] == 'ZERODHA_PASSWORD']['value'].values[0])
zerodha_TOTP = str(Integrations_WAU359P1[Integrations_WAU359P1['name'] == 'ZERODHA_TOTP']['value'].values[0])

##Replace url parameters with actual api key and project key and uid
url = "https://kite.zerodha.com/connect/login?api_key=" + api_key + "&v=3&redirect_params=project_key%3D" + project_key + "%26uid%3D" + uid



chrome_options = Options()
chrome_options.add_argument('--headless')
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')
chrome_options.add_argument('--incognito')
driver = webdriver.Chrome(options=chrome_options)

print("Starting login")
driver.get(url)
sleep(5)

##Get login elements
username_input = driver.find_element(By.XPATH, '//*[@id="userid"]')
password_input = driver.find_element(By.XPATH, '//*[@id="password"]')
button_element = driver.find_element(By.XPATH, '//*[@id="container"]/div/div/div[2]/form/div[4]/button')

##Login
try:
    username_input.send_keys(zerodha_username)
except:
    pass
password_input.send_keys(zerodha_password)

sleep(2)
button_element.click()

print("Login clicked")
sleep(5)

##Get OTP
auth_key = pyotp.TOTP(zerodha_TOTP)
otp = auth_key.now()

##Get OTP elements
otp_input = driver.find_element(By.XPATH, '//*[@id="container"]/div[2]/div/div[2]/form/div[1]/input')
verify_button = driver.find_element(By.XPATH, '//*[@id="container"]/div[2]/div/div[2]/form/div[2]/button')

##Enter OTP
otp_input.send_keys(otp)

try:
    verify_button.click()
except:
    pass

print("Verify Clicked")
sleep(2)
##Print output
print(str(driver.page_source))

##Get access token
zerodha_access_token = str(Integrations_WAU359P1[Integrations_WAU359P1['name'] == 'ZERODHA_ACCESS_TOKEN_KEY']['value'].values[0])

zerodha.set_keys(api_key,zerodha_access_token)
