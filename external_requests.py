from dotenv import load_dotenv
import os
import requests
from typing import Dict
import pdb

load_dotenv()

def get_guest_token() -> str:
  province_code = os.getenv("PROVINCE_CODE")
  city_code = os.getenv("CITY_CODE")
  data: Dict = {
    'province_code': province_code,
    'city_code': city_code
  }
  guest_url = os.getenv("GUEST_URL")

  response = requests.post(guest_url, data=data, verify=False)
  token: str = response.json()['token']
  return token

def get_products(account_id: int):
  headers: Dict = {
    'X-TAPIDEE-TOKEN': get_guest_token()
  }
  data: Dict = {
    'account_id': account_id,
    'sellable': 'true',
    'status': 'active',
  }

  products_url = os.getenv("PRODUCTS_URL")

  response = requests.get(products_url, headers=headers, data=data, verify=False)
  products = permit(response.json()['products'], "name", "retail_price")
  return products

# method to exlcude unneeded columns from the response
def permit(params, *allowed_keys):
    if isinstance(params, list):
        return [{key: value for key, value in item.items() if key in allowed_keys} for item in params]
    return {key: value for key, value in params.items() if key in allowed_keys}
