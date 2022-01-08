import os
import telebot
import logging
#from ocr import get_data

from telegram import (
  Update, 
  ReplyKeyboardMarkup
)

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
#from ocr import get_data

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
NEWBILL, PHOTO, PROCESSING, MEMBERS, CONFIRMING, ADDING_DESC, ADDING_PRICE, EDITING_DESC, EDITING_PRICE, ADDING_CFM, EDITING_CFM, DELETING = range(12)

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

  chat_id = update.message.chat.id
  # db[chat_id] = {} # Comment when DB is preloaded
  bot.send_message(chat_id=chat_id, text=start_message)

  return NEWBILL

########################### STATE 0 : NEW BILL ############################
def splitnewbill(update: Update, context: CallbackContext):
  chat_id = update.message.chat.id
  request_start(chat_id)
      
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
  user = update.message.from_user
  user_data = context.user_data
  photo_file = update.message.photo[-1].get_file()
  photo_file.download('user_photo.jpg')
  category = 'Photo Provided'
  user_data[category] = 'Yes'
  logger.info("Photo of %s: %s", user.first_name, 'user_photo.jpg')
  update.message.reply_text(
      'Image of receipt received! Parsing information...'
  )
  chat_id = update.message.chat.id
  
  if ocr_processing(chat_id):
    logger.info("OCR success!")
    getAllMembers(chat_id)
    return MEMBERS
  
  logger.info("OCR failed!")
  return PROCESSING 


def ocr_processing(chat_id):
  '''
  Send photo to OCR, retrieve dictionary
  '''
  # ocr_successful = True
  # if ocr_successful:
  #   getAllMembers(chat_id)

  # else:
  #   bot.send_message(
  #     chat_id=chat_id,
  #     text="Receipt could not be processed! Please send another image of the receipt and ensure that the image is clear, and that receipt takes up most of the image.",
    
    # stay in photo state
  
  return True

########################## STATE 2: PROCESSING ####################

def image_error(update: Update, context: CallbackContext):
  '''
  If they send another image in processing states
  '''
  update.message.reply_text(
      'Image of receipt already sent! If you wish to cancel this process and use a new receipt instead, please use /cancel, then /splitnewbill to split a new bill.'
  )

def testing(update: Update, context: CallbackContext):
  '''
  If they send another image in processing states
  '''
  update.message.reply_text(
      'Testing.'
  )

def testing2(update: Update, context: CallbackContext):
  '''
  If they send another image in processing states
  '''
  update.message.reply_text(
      'Testing 2.'
  )
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

######################### CALLBACK QUERY HANDLERS ##############

def membersCallback(update,context):
  
  call = update.callback_query
  original_msg = call.message
  chat_id = call.message.chat.id
  user = call.from_user
  data = call.data
  
  if data == 'Add new member':
    logger.info("Buttons Callback - new member called")
    add_new_member(chat_id, user, original_msg)
    return
  elif data == 'Finish adding members':
    logger.info("Buttons Callback - finished members")
    confirm_items(chat_id)
    return CONFIRMING

def itemsCallback(update, context): 
  call = update.callback_query
  original_msg = call.message
  chat_id = call.message.chat.id
  user = call.from_user
  data = call.data

  if data.startswith('Edit item '):
    item_index = int(data.split(":")[1])
    # logger.info(db[chat_id]['item'][item_index])
    context.user_data['item_index'] = item_index
    edit_item(chat_id, item_index)
    return EDITING_DESC

  elif data == 'Add item':
    bot.send_message(chat_id, 'Sorry we missed an item out! What is this new item called? ')
    return ADDING_DESC
  
  elif data == ('Delete item'): 
    delete_items(chat_id)
    return DELETING

def deleteCallback(update, context):
  call = update.callback_query
  original_msg = call.message
  chat_id = call.message.chat.id
  user = call.from_user
  data = call.data

  if data.startswith('Delete item'):
    item_index = int(data.split(":")[1])
    context.user_data['item_index'] = item_index
    delete_selected(chat_id, item_index)

  return CONFIRMING 

def delete_items(chat_id):
  '''
    Allows users to delete the items detected from receipt image 
  '''
  logger.info("delete_items() called")
  items = db[chat_id]['item']
  buttons = []
  count = 0
  for item in items:
    row = []
    description = str(item['description'])
    price = str(item['price'])
    display_message = f'{description} ${price}' 
    button = InlineKeyboardButton(
      display_message, 
      callback_data='Delete item :' + str(count)
    )
    row.append(button)
    buttons.append(row)
    count+=1
  
  bot_msg= "Here are your items! What would you like to delete?"
  bot.send_message(
    chat_id=chat_id,
    text=bot_msg,
    reply_markup=InlineKeyboardMarkup(buttons)
  )


def delete_selected(chat_id, item_index):
  item = db[chat_id]['item'][item_index]
  item_name = item['description']
  item_price = item['price']
  bot.send_message(
    chat_id,
    f'You are going to delete {item_name} ${item_price}.'
  )
  db[chat_id]['item'].pop(item_index)
  logger.info(db)
  confirm_items(chat_id)
  return CONFIRMING


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
  
  if data.startswith('Exclude user from item:'):
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


###################### ADD NEW ITEM INTO DB ################
def add_description(update: Update, context: CallbackContext):
  """
    Receives user input for new item's description
  """
  logger.info("add_description() called")
  item_name = update.message.text
  context.user_data['item_name'] = item_name
  reply_msg = f'Please enter the price for {item_name} : \nPlease type the number only. Eg. To input $5.00, input 5.00!' 
  update.message.reply_text(reply_msg)
  return ADDING_PRICE


def add_price(update:Update, context):
  """
    Receives user input for new item's price 
  """
  item_price = update.message.text
  context.user_data['item_price'] = item_price
  item_name = context.user_data['item_name']
  item_message = f'The item is {item_name} with a price of ${item_price}. Type Yes to confirm.'
  update.message.reply_text(item_message)

  return ADDING_CFM

def add_item(update:Update, context):
  """
    Receives a confirmation message from user on whether to insert new item
  """
  user_reply = update.message.text
  chat_id = update.message.chat.id
  item_name = context.user_data['item_name']
  if (user_reply=='Yes'):
    item_price = context.user_data['item_price']
    db[chat_id]['item'].append({'quantity': 1, 'description': item_name, 'price': item_price})

 
  else :
    update.message.reply_text(f'Okay! We will not add {item_name} in')
  
  confirm_items(chat_id)
  return CONFIRMING
###############################################

def add_new_member(chat_id, user, member_list_msg):
  '''
  Adds all members' usernames to db and edits original bot message to display 
  '''
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

  #print(db) 
  # DEBUGGING

###################### CONFIRM ITEMS #####################
def confirm_items(chat_id):
  '''
    Allows users to edit the items detected from receipt image 
  '''

  # List out all items as inline buttons
  items = db[chat_id]['item']
  buttons = []
  count = 0
  for item in items:
    row = []
    description = str(item['description'])
    price = str(item['price'])
    display_message = f'{description} ${price}' 
    button = InlineKeyboardButton(
      display_message, 
      callback_data='Edit item :' + str(count)
    )
    row.append(button)
    buttons.append(row)
    count+=1

  # Add item button
  buttons.append([InlineKeyboardButton(
    '➕ Add item',
    callback_data='Add item'
  )]
  )

  # dELETE item button
  buttons.append([InlineKeyboardButton(
    'Delete item',
    callback_data='Delete item'
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

def edit_item(chat_id, item_index):
  logger.info("edit_item() called")
  item_name = db[chat_id]['item'][item_index]['description']
  item_price = db[chat_id]['item'][item_index]['price']
  item_msg = f'Current item is {item_name} with a price of ${item_price}. Type the new name for the item. If you would like to keep it, type skip'
  bot.send_message(chat_id=chat_id, text=item_msg)

def edit_description(update: Update, context: CallbackContext):
  """
    Receives user input to edit the item's description 
  """
  logger.info("edit_description() called")
  chat_id = update.message.chat.id
  item_index = context.user_data['item_index']

  user_input = update.message.text
  if (user_input!='Skip' and user_input!='skip'):
    context.user_data['item_name'] = user_input
    logger.info(db[chat_id]['item'][item_index])
  
  else : 
    context.user_data['item_name'] = db[chat_id]['item'][item_index]['description']

  item_name = context.user_data['item_name']
  reply_msg = f'Please enter the price for {item_name}.\nPlease type the number only. Eg. To input $5.00, input 5.00!If you would like to keep it, type skip\n' 
  update.message.reply_text(reply_msg)
  return EDITING_PRICE

def edit_price(update: Update, context: CallbackContext):
  """
    Receives user input to edit the item's description 
  """
  logger.info("edit_price() called")
  chat_id = update.message.chat.id
  item_index = context.user_data['item_index']

  user_input = update.message.text
  if (user_input!='Skip' and user_input!='skip'):
    context.user_data['item_price'] = float(user_input)
    logger.info(db[chat_id]['item'][item_index])
  
  else : 
    context.user_data['item_price'] = db[chat_id]['item'][item_index]['price']

  item_name = context.user_data['item_name']
  item_price = context.user_data['item_price']

  db[chat_id]['item'][item_index] = {'quantity':1, 
  'description':item_name, 'price':item_price}
  reply_msg = f'The item has been saved as {item_name} with ${item_price}'
  logger.info(db[chat_id]['item'][item_index]) 
  update.message.reply_text(reply_msg)
  confirm_items(chat_id)
  return CONFIRMING


  
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
    emoji = '❌'

    if username in all_paying_members:
      emoji = '✅'

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
  logger.info(buttons)
  logger.info(InlineKeyboardMarkup(buttons))
  logger.info(type(InlineKeyboardMarkup(buttons)))
  logger.info(original_msg.reply_markup)
  logger.info(type(original_msg.reply_markup))
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
      MEMBERS: [CallbackQueryHandler(membersCallback)
        , MessageHandler(Filters.text, callback=testing),
     ],
      CONFIRMING:[CallbackQueryHandler(itemsCallback), MessageHandler(Filters.photo, callback=image_error)], 
      ADDING_DESC: [MessageHandler(Filters.text, callback=add_description),],
      ADDING_PRICE: [MessageHandler(Filters.text, callback=add_price),],
      ADDING_CFM: [MessageHandler(Filters.text, callback=add_item),],
      EDITING_DESC: [MessageHandler(Filters.text, callback=edit_description)],
      EDITING_PRICE: [MessageHandler(Filters.text, callback=edit_price),],
      DELETING: [CallbackQueryHandler(deleteCallback), MessageHandler(Filters.photo, callback=image_error)],
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
