import os
import telebot
import logging
from ocr import get_data

from telegram import Update

#test

#print(get_data("user_photo.jpg"))

from telebot.types import(
    BotCommand,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    LabeledPrice,
)
from telegram.ext import(
  Updater,
  CommandHandler,
  MessageHandler,
  ConversationHandler,
  CallbackQueryHandler,
  Filters,
  CallbackContext
)
from database import db

API_KEY = str(os.getenv('API_KEY'))
bot = telebot.TeleBot(API_KEY)



bot.set_my_commands([
    BotCommand('start', 'Starts the bot'),
    BotCommand('splitnewbill', 'Upload a receipt and split a new bill'),
    BotCommand('cancel', 'Cancel processing an existing bill'),
    BotCommand('help', 'Learn how to use this bot')
])


# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)

#states must be int
NEWBILL, PHOTO, PROCESSING, MEMBERS, CONFIRM_ITEMS, SPLIT_BILL, CALCULATE = range(7)

def request_start(chat_id):
  """
  Helper function to request user to execute command /start
  """
  if chat_id not in db:
    bot.send_message(chat_id=chat_id, text='Please start the bot by sending /start')
  return


def image_handler(update: Update, context: CallbackContext):
  """
  Helper function to get image of receipt from user
  """
  print("Function image_handler() called")
  user = update.message.from_user
  photo_file = update.message.photo[-1].get_file()
  photo_file.download('user_photo.jpg')
  logger.info("Photo of %s: %s", user.first_name, 'user_photo.jpg')
  update.message.reply_text(
      'Image of receipt received! Parsing information...'
  )
  return ConversationHandler.END


@bot.message_handler(commands=['start'])
def start(update: Update, context: CallbackContext):
  """
  Welcome message & configure initial setup
  """
  # Send start message
  if update.message.chat.type == 'private':
      chat_user = update.message.chat.first_name
  else:
      chat_user = update.message.chat.title

  start_message = f'''
  Hey there, {chat_user}! This bot will help you split the bill among your friends.\n\nBegin by sending the command /splitnewbill to upload a receipt and let us split the bill for you!\n\nNote: Only receipts with standard format (quantity, item description, price) are allowed.
  '''

  #initialise the bill
  chat_id = update.message.chat.id
  # db[chat_id] = {} # Comment when DB is preloaded
  bot.send_message(chat_id=chat_id, text=start_message)
  
  # Specify the succeeding state to enter
  return NEWBILL

def getAllMembers(chat_id):
  '''
  Displays inline keyboard for users to click on and gets all the members of the party
  If existing member clicks the button, he/she will be removed
  '''

  buttons = [[]]
  display_message = 'Add me as a member! 🙋🏻‍♀️🙋🏻'
  button = InlineKeyboardButton(
    display_message, 
    callback_data='Add new member'
  )
  buttons[0].append(button)

  bot.send_message(
    chat_id=chat_id,
    text="Which users should be included in the bill? Those who are splitting the bill, click the button below!\n\nCurrent Members:",
    reply_markup=InlineKeyboardMarkup(buttons)
  )


# @bot.callback_query_handler(func=lambda call: True)
def handle_callback(update, context):
  """
  Handles the execution of the respective functions upon receipt of the callback query
  """

  print("Function handle_callback() called") # DEBUGGING

  call = update.callback_query
  member_list_msg = call.message
  chat_id = call.message.chat.id
  user = call.from_user
  data = call.data
  
  if data == 'Add new member':
    add_new_member(chat_id, user, member_list_msg)
    return
    
  print(f'{chat_id}: Callback not implemented')

def add_new_member(chat_id, user, member_list_msg):
  '''
  Adds all members' usernames to db and edits original bot message to display 
  '''

  print("Function add_new_member() called") # DEBUGGING  

  username = user.username
  is_user_existing_member = False

  # Initialize dict if no members added yet
  if 'individual_bill' not in db[chat_id].keys(): # empty dict
    db[chat_id]['individual_bill'] = {}
  
  # Get list of all members' usernames
  existing_members = db[chat_id]['individual_bill'].keys()

  # If username already in members, remove username
  if username in existing_members:
    db[chat_id]['individual_bill'].pop(username)
    is_user_existing_member = True
  else: 
    db[chat_id]['individual_bill'][username] = 0
  
  # Update original bot message
  # "Which users should be included in the bill? Those who are splitting the bill, click the button below!\n\nCurrent Members:"
  old_text = member_list_msg.text
  # new_text = old_text.split("\n\n")[1]
  # members = new_text.split(":") # members[0] = 'Current Members'

  if not is_user_existing_member:
    updated_text = old_text + "\n" + username
  else:
    str_to_remove = "\n" + username
    updated_text = old_text.replace(str_to_remove, '')

  member_list_msg.edit_text(text=updated_text, reply_markup=member_list_msg.reply_markup)

  print(db) # DEBUGGING
  

@bot.message_handler(commands=['splitnewbill'])
def splitnewbill(update: Update, context: CallbackContext):
  chat_id = update.message.chat.id
  if chat_id not in db:
      request_start(chat_id)
      return

  # STEP 1 : Uploading receipt image
  bot.send_message(
      chat_id=chat_id,
      text=
      "Start by uploading a clear image of your receipt. Ensure that the receipt takes up most of the image, the whole receipt can be seen, and that the background is clear.\n\nNote: Only receipts with standard format (quantity, item description, price) are allowed."
  )

  # STEP 2 : Get all members of the chat
  getAllMembers(chat_id)
  
  # STEP 3 : List out all items and their quantities

  return PHOTO


#Fallback handler, when user inputs '/cancel'
def cancel(update: Update, context: CallbackContext):
    chat_id = update.message.chat.id
    end_message = 'Bye! I hope I can help you split the bill someday.'
    bot.send_message(chat_id=chat_id, text=end_message)
 
    return ConversationHandler.END

def main():
  print("Bot started")
  #Create the EventHandler and pass it to your bot's token
  updater = Updater(API_KEY, use_context=True)
  #Get the dispatcher to register handlers
  dp = updater.dispatcher

  # Add conversation handler with the states 
  # The conversation is started with entry_points and proceeded with different states. 
  #Each of these requires a handler
  conv_handler = ConversationHandler(

    #We define a CommandHandler called start which is called when user inputs command '/start'
    entry_points=[CommandHandler('start', start)],
    states={
      NEWBILL: [CommandHandler('splitnewbill', callback=splitnewbill)],
      PHOTO: [MessageHandler(Filters.photo, callback=image_handler)],
    },
    fallbacks=[CommandHandler('cancel', cancel)]
  )

 #Attach the conversation handler to the dispatcher
  dp.add_handler(conv_handler)

  dp.add_handler(CallbackQueryHandler(handle_callback))
  # dp.add_handler(CommandHandler('start', start))
  # dp.add_handler(CommandHandler('splitnewbill', splitnewbill))
  # dp.add_handler(CommandHandler('cancel', cancel))
  # dp.add_handler(MessageHandler(Filters.photo, image_handler))
  # dp.add_handler(MessageHandler(Filters.caption(update=['Receipt']), image_handler))

  updater.start_polling()
  updater.idle()


if __name__ == '__main__':
  main()
# bot.infinity_polling()
