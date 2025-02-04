from dotenv import load_dotenv
import os
import requests
from typing import Dict
import pdb

load_dotenv()

request_url = os.getenv("REQUEST_URL")

def get_guest_token() -> str:
  province_code = os.getenv("PROVINCE_CODE")
  city_code = os.getenv("CITY_CODE")
  data: Dict = {
    'province_code': province_code,
    'city_code': city_code
  }
  guest_url = request_url + 'tokens/guest'

  response = requests.post(guest_url, data=data)
  token: str = response.json()['token']
  return token

def login_customer():
  phone = os.getenv("PHONE")
  password = os.getenv("PASS")

  headers: Dict = {
    'X-TAPIDEE-TOKEN': get_guest_token()
  }
  data: Dict = {
    'mobile_phone': phone,
    'password': password
  }

  user_url = request_url + 'tokens/user'

  response = requests.post(user_url, headers=headers, data=data)
  customer_details: Dict = response.json()
  return customer_details

AuthToken = login_customer()['token']
Customer = login_customer()['customer']

def get_products(account_id: int):
  global AuthToken
  headers: Dict = {
    'X-TAPIDEE-TOKEN': AuthToken
  }
  data: Dict = {
    'account_id': account_id,
    'sellable': 'true',
    'status': 'active',
  }

  products_url = request_url + 'products'

  response = requests.get(products_url, headers=headers, data=data)
  products = permit(response.json()['products'], "name", "retail_price", "account_id")
  return products

# method to exlcude unneeded columns from the response
def permit(params, *allowed_keys):
    if isinstance(params, list):
        return [{key: value for key, value in item.items() if key in allowed_keys} for item in params]
    return {key: value for key, value in params.items() if key in allowed_keys}
