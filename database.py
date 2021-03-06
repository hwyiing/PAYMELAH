'''
Stores each chat's current receipt in a dictionary
db {
  chat_id : {
    item : list of items' quantity, description, price, list of members paying,
    subtotal : subtotal of all items,
    tax : optional, any service charge and gst, // for calculation checking purposes
    total : total including any tax,
    individual_bill : dictionary of each member and how much they need to pay 
  }
}
'''
class database:
  def __init__(self,db):
    self.db=db
  def set_db(self,db):
    self.db=db
  def get_db(self):
    return self.db

db = {
  # -786171741 : { # Pegasus on the Fly receipt
  #   'item' : [
  #     { # item 1
  #       'quantity' : 1,
  #       'description' : 'Gyros Pita, Fries',
  #       'price' : 8.99,
  #     },
  #     { # item 2
  #       'quantity' : 1,
  #       'description' : 'Large Soft Drink',
  #       'price' : 2.59,
  #     },
  #     { # item 3
  #       'quantity' : 1,
  #       'description' : 'Greek Cookies 3pcs',
  #       'price' : 2.29,
  #     }
  #   ],
  #   'subtotal' : 13.87,
  #   'tax' : 1.68,
  #   'total' : 15.55,
    # 'individual_bill' : {
    #   'lyntanrambutan' : 0,
    #   'rkambai' : 0,
    #   'clarissajew' : 0,
    #   'cheam99' : 0
    # }
  # }
}

d = database(db)
'''
END RESULT
'individual_bill' : {
  'lyntanrambutan' : 3.38,
  'rkambai' : 3.38,
  'clarissajew' : 5.42,
  'cheam99' : 3.38
}
'''