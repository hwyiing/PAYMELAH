import os
from numpy.core.arrayprint import _guarded_repr_or_str
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
from ocr import get_data

API_KEY = "5021687305:AAH82QKFwM3_0mx89bo5v8FbuoFfCSsD-5c"#str(os.getenv('API_KEY'))
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
NEWBILL, PHOTO, PROCESSING, EDITING = range(4)

######################### FUNCTIONS ##########################

def request_start(chat_id):
  """
  Helper function to request user to execute command /start
  """
  if chat_id not in db:
    bot.send_message(chat_id=chat_id, text='Please start the bot by sending /start')
  return

def cancel(update: Update, context: CallbackContext):
    chat_id = update.message.chat.id
    if chat_id not in db:
      request_start(chat_id)
      return
    end_message = 'Sorry to see you go! I hope I can help you split the bill someday.'
    bot.send_message(chat_id=chat_id, text=end_message)
 
    return ConversationHandler.END
    
############################ START COMMAND #################
@bot.message_handler(commands=['start'])
def start(update: Update, context: CallbackContext):
  """
  Welcome message & configure initial setup
  """
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

########################### STATE 0 : NEW BILL ############################
def splitnewbill(update: Update, context: CallbackContext):
  chat_id = update.message.chat.id
  if chat_id not in db:
      request_start(chat_id)
      return
    
  bot.send_message(
      chat_id=chat_id,
      text=
      "Start by uploading a clear image of your receipt. Ensure that the receipt takes up most of the image, the whole receipt can be seen, and that the background is clear.\n\nNote: Only receipts with standard format (quantity, item description, price) are allowed."
  )
  return PHOTO

########################### STATE 1: PHOTO #################

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
  chat_id = update.message.chat.id
  processing(chat_id)
  return PROCESSING 

########################## STATE 2: PROCESSING ####################

def image_error(update: Update, context: CallbackContext):
  '''
  If they send another image in processing states
  '''
  update.message.reply_text(
      'Image of receipt already sent! If you wish to cancel this process and use a new receipt instead, please use /cancel, then /splitnewbill to split a new bill.'
  )

def processing(chat_id):
  '''
  Send photo to OCR, retrieve dictionary
  '''

  ocr_successful = get_data(r"user_photo.jpg")
  
  if ocr_successful is not None:
    global db
    db = {chat_id:ocr_successful}
    return getAllMembers(chat_id)
    # return PROCESSING
  else:
    bot.send_message(
      chat_id=chat_id,
      text="Receipt could not be processed! Please send another image of the receipt and ensure that the image is clear, and that receipt takes up most of the image.",
    )
    # stay in photo state
    return
  

############################# STATE 3 : MEMBERS ###################

def getAllMembers(chat_id):
  '''
  Displays inline keyboard for users to click on and gets all the members of the party
  If existing member clicks the button, he/she will be removed
  '''

  buttons = [[]]
  row_one = []
  display_message = 'Add me as a member! 🙋🏻‍♀️🙋🏻'
  button = InlineKeyboardButton(
    display_message, 
    callback_data='Add new member'
  )
  row_one.append(button)
  buttons.append(row_one)

  row_two = []
  display_message = 'Done' 
  button = InlineKeyboardButton(
    display_message,
    callback_data='Finish adding members'
  )
  row_two.append(button)
  buttons.append(row_two)

  bot.send_message(
    chat_id=chat_id,
    text="Which users should be included in the bill? Those who are splitting the bill, click the button below!\n\nCurrent Members:",
    reply_markup=InlineKeyboardMarkup(buttons)
  )

  return PROCESSING


# @bot.callback_query_handler(func=lambda call: True)
def handle_callback(update, context):
  """
  Handles the execution of the respective functions upon receipt of the callback query
  """

  print("Function handle_callback() called") # DEBUGGING

  call = update.callback_query
  original_msg = call.message
  chat_id = call.message.chat.id
  user = call.from_user
  data = call.data
  
  if data == 'Add new member':
    add_new_member(chat_id, user, original_msg)
    return
  elif data == 'Finish adding members':
    confirm_items(chat_id)
    return EDITING
  elif data.startswith('Edit item '):
    logger.info("EDIT AN ITEM!")
    return
  elif data == 'Add item':
    logger.info("ADD ITEM!")
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

###################### CONFIRM ITEMS #####################
def confirm_items(chat_id):
  '''
    Allows users to edit the items detected from receipt image 
  '''

  # List out all items as inline buttons
  items = db[chat_id]['item']
  buttons = []
  for item in items:
    row = []
    logger.info(item['description'])
    description = str(item['description'])
    price = str(item['price'])
    display_message = f'{description} ${price}' 
    button = InlineKeyboardButton(
      display_message, 
      callback_data='Edit item ' + description
    )
    row.append(button)
    buttons.append(row)

  # Add item button
  buttons.append([InlineKeyboardButton(
    '➕ Add item',
    callback_data='Add item'
  )]
  )

  bot.send_message(
    chat_id=chat_id,
    text='Here are your items 🍴 \n\nClick on the item to edit its name or price, or on the ➕ Add item button if we missed any item out!',
    reply_markup=InlineKeyboardMarkup(buttons)
  )

def edit_item(chat_id):
  return

def add_item(chat_id):
  return
  

  
  
###################### SPLIT BILL ##########################
def split_bill(chat_id):
  return 

###################### CALCULATE ##########################
def calculate(chat_id):

  return ConversationHandler.END
  

###################### MAIN FUNCTION ##################

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
      PROCESSING: [MessageHandler(Filters.photo, callback=image_error)],
      # EDITING: [MessageHandler(Filters.photo, callback=image_error), MessageHandler(Filters.text), callback=]
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
