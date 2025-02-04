from dotenv import load_dotenv
import os
from typing import Final
from telegram import Update, ReplyKeyboardRemove
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, PollAnswerHandler
import sys
import traceback
import pdb
from merchants import FrequentMerchants
from external_requests import AuthToken, Customer, get_products

load_dotenv()

TOKEN: Final = os.getenv("TOKEN")
BOT_USERNAME: Final = os.getenv("BOT_USERNAME")
message = ''
products = []

# COMMANDS
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
  await update.message.reply_text(f"Hello customer {Customer['first_name']}")

async def add_order_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
  order = " ".join(context.args)
  global message 
  message += update.message.from_user.first_name + ' ordered ' + order + '\n'
  await update.message.reply_text(f"{message}")

async def delete_list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
  global message 
  message = ""
  await update.message.reply_text(f"Order list deleted")

# List Frequently ordered restos
async def merchants_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
  merchant_list_message = ''
  for merchant in FrequentMerchants:
    merchant_list_message += merchant['name'] + '\n'

  await update.message.reply_text(f"{merchant_list_message}")

async def select_merchant_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
  merchant = " ".join(context.args)
  for m in FrequentMerchants:
    if m['name'].lower() == merchant.lower():
      id = m['id']
  
  global products
  products = get_products(id)
  product_list = ''

  for p in products:
    product_list += f"{p['name']} {p['retail_price']}\n"

  await update.message.reply_text(product_list)


### POLL FOR ORDERS ###
# MODIFY THIS SINCE THIS IS COPIED STRAIGHT FROM THE DOCUMENTATION
async def poll(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a predefined poll"""
    questions = ["Good", "Really good", "Fantastic", "Great"]
    message = await context.bot.send_poll(
        update.effective_chat.id,
        "How are you?",
        questions,
        is_anonymous=False,
        allows_multiple_answers=True,
    )
    # Save some info about the poll the bot_data for later use in receive_poll_answer
    payload = {
        message.poll.id: {
            "questions": questions,
            "message_id": message.message_id,
            "chat_id": update.effective_chat.id,
            "answers": 0,
        }
    }
    context.bot_data.update(payload)

async def receive_poll_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Summarize a users poll vote"""
    answer = update.poll_answer
    answered_poll = context.bot_data[answer.poll_id]
    try:
        questions = answered_poll["questions"]
    # this means this poll answer update is from an old poll, we can't do our answering then
    except KeyError:
        return
    selected_options = answer.option_ids
    answer_string = ""
    for question_id in selected_options:
        if question_id != selected_options[-1]:
            answer_string += questions[question_id] + " and "
        else:
            answer_string += questions[question_id]

    # message to reply and s
    # await context.bot.send_message(
    #     answered_poll["chat_id"],
    #     f"{update.effective_user.mention_html()} feels {answer_string}!", 
    #     parse_mode=ParseMode.HTML,
    # )
    answered_poll["answers"] += 1
    # Close poll after three participants voted
    if answered_poll["answers"] == 3:
        await context.bot.stop_poll(answered_poll["chat_id"], answered_poll["message_id"])

async def receive_poll(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """On receiving polls, reply to it by a closed poll copying the received poll"""
    actual_poll = update.effective_message.poll
    # Only need to set the question and options, since all other parameters don't matter for
    # a closed poll
    await update.effective_message.reply_poll(
        question=actual_poll.question,
        options=[o.text for o in actual_poll.options],
        # with is_closed true, the poll/quiz is immediately closed
        is_closed=True,
        reply_markup=ReplyKeyboardRemove(),
    )

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


if __name__ == '__main__':
  print('Bot starting')
  app = Application.builder().token(TOKEN).build()

  # Command handler
  app.add_handler(CommandHandler('start', start_command))
  app.add_handler(CommandHandler('add_order', add_order_command))
  app.add_handler(CommandHandler('delete_list', delete_list_command))
  app.add_handler(CommandHandler('merchants', merchants_command))
  app.add_handler(CommandHandler('set_merchant', select_merchant_command))
  # RUN POLL
  app.add_handler(CommandHandler("poll", poll))
  app.add_handler(MessageHandler(filters.POLL, receive_poll))
  app.add_handler(PollAnswerHandler(receive_poll_answer))



  # Message Handler
  app.add_handler(MessageHandler(filters.TEXT, handle_message))

  app.add_error_handler(error)

  print('Polling...')
  app.run_polling(poll_interval=3)