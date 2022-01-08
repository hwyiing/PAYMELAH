import os
import telebot
import logging
from ocr import get_data

from telegram import Update

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
#from ocr import get_data

API_KEY = str(os.getenv('API_KEY'))#"5021687305:AAH82QKFwM3_0mx89bo5v8FbuoFfCSsD-5c"
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
PHOTO, PROCESSING, EDITING, DESCRIPTION, PRICE = range(5)

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
  db[chat_id] = {} # Clear db for this chat

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

  # Initialise the bill
  chat_id = update.message.chat.id
  if chat_id in db.keys(): 
    # if db[chat_id] == {}: # Started the bot but haven't started a new bill
    start_message = "You have already started the bot!"
    # else:
    #   start_message = "You already have an existing bill being processed! If you wish to cancel this process and use a new receipt instead, please use /cancel, then /splitnewbill to split a new bill."
  else:
    db[chat_id] = {} # Comment when DB is preloaded
  bot.send_message(chat_id=chat_id, text=start_message)

  print(db) # DEBUGGING
  
  return
  # Specify the succeeding state to enter
  # return NEWBILL

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
  

####################### MEMBERS ###################

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

######################### CALLBACK QUERY ##############
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
    edit_item(chat_id, original_msg)
    return
  elif data == 'Add item':
    add_item(chat_id)
    return
  elif data.startswith('Exclude user from item:'):
    item_index_str = data.split(":")[1]
    display_users_for_item(chat_id, int(item_index_str), original_msg)
    return
  elif data.startswith('Exclude username:'):
    variables = data.split(":")[1]
    username, item_index_str = variables.split()
    exclude_users_from_item(chat_id, int(item_index_str), username, original_msg)
    return
  elif data == 'Calculate bill':
    calculate(chat_id)
    return
  elif data == 'Go to items list':
    split_bill(chat_id)
    return
  
    
  print(f'{chat_id}: Callback not implemented')

########## FUNCTIONS FOR ADDING ITEMS ###########
def add_item(chat_id):
  logger.info("add_item() called")
  input_name(chat_id)
  return DESCRIPTION

####### STATE 4 : DESCRIPTION ####
def description(chat_id):
  item_name = update.message.text
  context.user_data['item_name'] = item_name
  reply_msg = f'Please enter the price for ${item_name}' 
  update.message.reply_text("Nice! Now, please enter the price for your : ")
  return PRICE

####### STATE 5 : PRICE #####
def price(update:Update, context):
  item_price = update.message.text
  context.user_data['item_price'] = item_price
  item_name = context.user_data['']
  update.message.reply_text("You want to add a new item - ")

  return 

###############################################


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

  # Done button to move on to splitting the bill
  buttons.append([InlineKeyboardButton(
    "Done 👍🏻 All my items are correct!",
    callback_data='Go to items list'
  )]
  )

  bot.send_message(
    chat_id=chat_id,
    text='Here are your items 🍴 \n\nClick on the item to edit its name or price, or on the ➕ Add item button if we missed any item out!',
    reply_markup=InlineKeyboardMarkup(buttons)
  )

def edit_item(chat_id, original_msg):
  # original_msg.edit_reply_markup()
  return


  
  
###################### SPLIT BILL ##########################
def split_bill(chat_id):
  '''
  Allows users to exclude specific users from a particular item
  Displays all items as buttons
  '''

  # To each item in db for this chat, add a key-value pair
  # 'members_paying' : [list of usernames of all members]
  # Assume everyone is paying for everything at first
  all_items = db[chat_id]['item']
  all_members = db[chat_id]['individual_bill'].keys()
  for item in all_items:
    if 'members_paying' not in item.keys():
      item['members_paying'] = list(all_members)
    print(item) # DEBUGGING

  # DEBUGGING
  print("------------------------")
  print('DB: ', db)
  print("------------------------")

  # List out all items as inline buttons
  items = db[chat_id]['item']
  buttons = []
  for item in items:
    row = []
    description = str(item['description'])
    logger.info(items.index(item))
    index = items.index(item)
    price = str(item['price'])
    display_message = f'{description} ${price}' 
    button = InlineKeyboardButton(
      display_message, 
      callback_data='Exclude user from item:' + str(index)
    )
    row.append(button)
    buttons.append(row)

  # Done button to move on to calculating
  buttons.append([InlineKeyboardButton(
    "Done 👍🏻 I'm ready to split my bill!",
    callback_data='Calculate bill'
  )]
  )

  bot.send_message(
    chat_id=chat_id,
    text="Click on each item to specify who ate what! By default, each item is shared between all members.\n\nIf a member did not eat an item, click on the item, then on the member's username to exclude them from that item's cost!",
    reply_markup=InlineKeyboardMarkup(buttons)
  )

  return

def display_users_for_item(chat_id, item_index, original_msg):
  '''
  Displays selected item in text
  Displays all members' usernames as buttons, with users currently paying for the item with a green tick emoji in front
  '''
  # # Get item index
  # item_index = -1
  # all_items = db[chat_id]['item']
  # for item in all_items:
  #   if item['description'] == item_description:
  #     item_index = all_items.index(item)
  # print(item_index) # DEBUGGING

  # Get list of all paying members' usernames for that item
  all_members = db[chat_id]['individual_bill'].keys()
  all_paying_members = db[chat_id]['item'][item_index]['members_paying']
  
  # List out all usernames as inline buttons
  buttons = []
  for username in all_members:
    row = []
    emoji = '❌ '

    if username in all_paying_members:
      emoji = '✅ '

    display_text = emoji + username
    button = InlineKeyboardButton(
      display_text, 
      callback_data=f'Exclude username:{username} {item_index}'
    )
    row.append(button)
    buttons.append(row)

  # Back button to go back to item list
  buttons.append([InlineKeyboardButton(
    "Back to items list",
    callback_data='Go to items list'
  )]
  )
  
  # Update original message's text and inline keyboard buttons
  item_description = db[chat_id]['item'][item_index]['description']
  updated_text = f'Selected Item: {item_description}\n\n❌ : User is not paying for this item\n✅ : User is paying for this item'
  # logger.info(buttons)
  # logger.info(InlineKeyboardMarkup(buttons))
  # logger.info(type(InlineKeyboardMarkup(buttons)))
  # logger.info(original_msg.reply_markup)
  # logger.info(type(original_msg.reply_markup))
  bot.edit_message_text(text=updated_text,reply_markup=InlineKeyboardMarkup(buttons), chat_id=chat_id, message_id=original_msg.message_id)
  # original_msg.edit_text(text=updated_text,reply_markup=InlineKeyboardMarkup(buttons))
  # # original_msg = original_msg.edit_text(text=updated_text,reply_markup=original_msg.reply_markup)
  # original_msg.edit_reply_markup(reply_markup=InlineKeyboardMarkup(buttons))

  return 

def exclude_users_from_item(chat_id, item_index, username, original_msg):
  '''
  Adds or removes username from paying members of the item
  Updates inline keyboard buttons of original message (emoji beside selected username should change)
  '''

  # Get list of all paying members' usernames for that item
  all_paying_members = db[chat_id]['item'][item_index]['members_paying']

  if username in all_paying_members: # To remove user from paying members
    db[chat_id]['item'][item_index]['members_paying'].remove(username)
  else: # To add user to paying members
    db[chat_id]['item'][item_index]['members_paying'].append(username)

  return display_users_for_item(chat_id, item_index, original_msg)

###################### CALCULATE ##########################
def calculate(chat_id):
  '''
  Calculates the amount each person has to pay, using the formula (sum of shares of each item / subtotal) * total
  '''
  all_members = db[chat_id]['individual_bill'].keys()

  # Calculate subtotal = sum of prices of all items
  # Calculate individual bill for each member (excl tax)
  subtotal = 0.0
  items = db[chat_id]['item']
  for item in items:
    subtotal += float(item['price'])

    members_paying = item['members_paying']
    num_members_paying = len(members_paying)

    if num_members_paying == 0:
      bot.send_message(chat_id=chat_id, text=f"No one is paying for {item['description']}! Please ensure each item has at least one person paying for it.")
      return split_bill(chat_id)

    amount_per_pax = float(item['price']) / num_members_paying
    for member in members_paying:
      db[chat_id]['individual_bill'][member] += amount_per_pax

  # DEBUGGING
  print("------------------------BEFORE TAX------------------------")
  print('DB: ', db)
  print("----------------------------------------------------------\n")

  # Calculate individual bill for each member (incl tax)
  for member in all_members:
    percentage = db[chat_id]['individual_bill'][member] / subtotal
    amount = percentage * db[chat_id]['total']
    db[chat_id]['individual_bill'][member] = amount

  # DEBUGGING
  print("------------------------AFTER TAX------------------------")
  print('DB: ', db)
  print("----------------------------------------------------------")

  # Send text messages containing final bill and instructions to split new bill
  text_msg = "Here's the final bill! Please pay your share of the bill 💸\n\n"
  count = 0
  for member in all_members:
    count += 1
    amount = round(db[chat_id]['individual_bill'][member], 2)
    text_msg += f'{count}. {member} - ${amount}\n'
  bot.send_message(chat_id=chat_id, text=text_msg)

  bot.send_message(chat_id=chat_id, text="Thanks for using PayMeLah bot to split your bill! To split another bill, use the /splitnewbill to upload a new receipt. 👋🏻 Have a great day, and remember to pay up!")

  # Clear the db for this chat
  db[chat_id] = {}

  return ConversationHandler.END
  
###################### HELP FUNCTION ##################

def help(update, context):
  commands={
  "/start": "Type this command in chat or select it from the pop out menu to start the bot",
  "/splitnewbill": "Use this after /start or when prompted to prepare the bot to accept a photo of your receipt",
  "/cancel": "Use this command when your bill has been successfully split. This puts me to sleep. Use /start to wake me up again",
  "/help": "Brings this message up for future reference"}
  
  cmd_list="\n"
  for i in commands:
    cmd_list+=f"{i}: {commands[i]}\n"
  
  chat_id = update.message.chat.id
  bot.send_message(
      chat_id=chat_id,
      text="I help you split your bills and receipts with just a snap of a photo!\n"+
      "\nHere's a list of commands I can execute for you:\n"+
      cmd_list+
      "\nDon't worry if you can't remember these now, simply typing / in chat will generate a pop out menu with a list of commands for easy reference!"+
      "\nThanks for using PayMeLah bot and happy splitting!"
  )
  return

###################### MAIN FUNCTION ##################

def main():
  print("Bot started")
  #Create the EventHandler and pass it to your bot's token
  updater = Updater(API_KEY, use_context=True)
  #Get the dispatcher to register handlers
  dp = updater.dispatcher

  # Add conversation handler with the states 
  # The conversation is started with entry_points and proceeded with different states. 
  # Each of these requires a handler
  conv_handler = ConversationHandler(

    entry_points=[CommandHandler('splitnewbill', splitnewbill)],
    states={
      PHOTO: [MessageHandler(Filters.photo, callback=image_handler)],
      PROCESSING: [MessageHandler(Filters.photo, callback=image_error)],
      # EDITING: [MessageHandler(Filters.photo, callback=image_error), MessageHandler(Filters.text), callback=]

      DESCRIPTION: [MessageHandler(Filters.text, callback=description)],
      PRICE: [MessageHandler(Filters.text, callback=price)]    
    },
    fallbacks=[CommandHandler('cancel', cancel)]
  )

 #Attach the conversation handler to the dispatcher
  dp.add_handler(conv_handler)

  dp.add_handler(CallbackQueryHandler(handle_callback))
  dp.add_handler(CommandHandler('start', start))
  dp.add_handler(CommandHandler('help', help))
  # dp.add_handler(CommandHandler('splitnewbill', splitnewbill))
  # dp.add_handler(CommandHandler('cancel', cancel))
  # dp.add_handler(MessageHandler(Filters.photo, image_handler))
  # dp.add_handler(MessageHandler(Filters.caption(update=['Receipt']), image_handler))

  updater.start_polling()
  updater.idle()

if __name__ == '__main__':
  main()
# bot.infinity_polling()
