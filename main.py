from dotenv import load_dotenv
import os
from typing import Final
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import sys
import traceback
import pdb
from merchants import FrequentMerchants
from external_requests import get_products

load_dotenv()

TOKEN: Final = os.getenv("TOKEN")
BOT_USERNAME: Final = os.getenv("BOT_USERNAME")
USER_ID: Final = os.getenv("USER_ID")
selected_merchant = ''
products = []
order_dictionary = {}

# COMMANDS
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
  await update.message.reply_text(f"Hello are you ready to order?")

async def delete_list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
  user = update.message.from_user

  if str(user.id) == USER_ID:
    generate_product_order()
    await update.message.reply_text(f"Order list deleted")
  else:
    await update.message.reply_text(f"Only admin Reymond can delete order list")

async def merchants_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
  merchant_list_message = ''
  for merchant in FrequentMerchants:
    merchant_list_message += merchant['name'] + '\n'

  await update.message.reply_text(f"{merchant_list_message}")

async def select_merchant_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
  merchant = " ".join(context.args)
  user = update.message.from_user

  if str(user.id) == USER_ID:
    for m in FrequentMerchants:
      if m['name'].lower() == merchant.lower():
        id = m['id']

    if isinstance(id, int):
      global selected_merchant
      global products
      products = get_products(id)
      product_list = generate_product_order() 
      selected_merchant = merchant.title()

      await update.message.reply_text(product_list)
    else:
      await update.message.reply_text('Unable to find merchant')
  else:
    await update.message.reply_text('Only admin Reymond can set merchant')

async def add_order_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
  order = " ".join(context.args)
  global order_dictionary

  product_names = [product['name'] for product in products]
  p = get_best_match(product_names, order)
  if p == -1:
    await update.message.reply_text(f"Make order more specific")
  else:
    name = update.message.from_user.first_name
    order_dictionary[p]["customers"].append(name)
    new_order_list = show_order_list()
    await update.message.reply_text(new_order_list)

async def show_order_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
  await update.message.reply_text(show_order_list())

async def cancel_order_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
  global order_dictionary
  order = " ".join(context.args)
  name = update.message.from_user.first_name
  product_names = [product['name'] for product in products]
  pname = get_best_match(product_names, order)

  if len(order) == 0:
    for product, details in order_dictionary.items():
      if not details['customers']:
        continue
      details['customers'].remove(name)
  else: # remove specific order
    for product, details in order_dictionary.items():
      if product == pname:
        details['customers'].remove(name)

  await update.message.reply_text(show_order_list())

# RESPONSES
def handle_response(text: str) -> str:
  if 'hello' in text.lower():
    return 'hello'
  
  return 'return valid command'


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
  message_type: str = update.message.chat.type
  text: str = update.message.text

  print(f'User ({update.message.chat.id}) in {message_type}: "{text}"')

  if message_type == 'supergroup':
    if BOT_USERNAME in text:
      new_text: str = text.replace(BOT_USERNAME, '').strip()
      response: str = handle_response(new_text)
    else:
      return
  else:
    response: str = handle_response(text)

  print('Bot:', response)
  await update.message.reply_text(response)

# displays errors
async def error(update: Update, context: ContextTypes.DEFAULT_TYPE):
  _, _, tb = sys.exc_info()
  line_number = traceback.extract_tb(tb)[-1][1]
  exc_type, exc_value, exc_traceback = sys.exc_info()
  error_traceback = traceback.format_exception(exc_type, exc_value, exc_traceback)
  print(f"Update {update} caused error {context.error}:\n{''.join(error_traceback)}")

# match the best order to the list of products
def get_best_match(product_list, product_ordered):
  order_words = product_ordered.lower().split()

  def count_matches(string):
      return sum(1 for word in order_words if word in string.lower())

  # Count matches for each string
  match_counts = {string: count_matches(string) for string in product_list}

  # Find the string with the maximum matches
  best_match = max(match_counts, key=match_counts.get)
  best_match_count = match_counts[best_match]

  # Find if there are ties
  tied = [key for key, value in match_counts.items() if value == best_match_count]
  
  if len(tied) > 1:
      return -1
  else:
      return best_match

def generate_product_order():
  global order_dictionary
  order_dictionary = {}
  product_list = ''

  for p in products:
    order_dictionary[p['name']] = {
      "retail_price": p['retail_price'],
      "customers": []
    }
    product_list += f"{p['name']} {p['retail_price']}\n"

  return product_list

def show_order_list():
  message = f"{selected_merchant}\n\n"
  for product, details in order_dictionary.items():
    if not details["customers"]:
        continue
    retail_price = details["retail_price"]
    customers = "\n".join(f"- {customer}" for customer in details["customers"])
    message += f"{product}({retail_price})\n{customers}\n\n"
  
  if message:
    return message
  else:
    return 'Set merchant to start ordering'

if __name__ == '__main__':
  print('Bot starting')
  app = Application.builder().token(TOKEN).build()

  # Command handler
  app.add_handler(CommandHandler('start', start_command))
  app.add_handler(CommandHandler('delete_list', delete_list_command))
  app.add_handler(CommandHandler('merchants', merchants_command))
  app.add_handler(CommandHandler('set_merchant', select_merchant_command))
  app.add_handler(CommandHandler('add_order', add_order_command))
  app.add_handler(CommandHandler('show_order', show_order_command))
  app.add_handler(CommandHandler('cancel_order', cancel_order_command))


  # Message Handler
  app.add_handler(MessageHandler(filters.TEXT, handle_message))

  app.add_error_handler(error)

  print('Polling...')
  app.run_polling(poll_interval=3)