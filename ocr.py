import cv2
import numpy as np
import urllib
import pytesseract
import re


#preprocessing
def process_text(img):

  img = cv2.imread(img,0)
  img=cv2.resize(img,None,fx=2,fy=2,interpolation=cv2.INTER_CUBIC)
  # Thresholding
  img = cv2.threshold(img,0,255,cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
  # Apply dilation and erosion to remove some noise
  kernel = np.ones((1, 1), np.uint8)
  img = cv2.dilate(img, kernel, iterations=1)
  img = cv2.erode(img, kernel, iterations=1)
  # Apply blur to smooth out the edges
  img = cv2.GaussianBlur(img, (5, 5), 0)
  text = pytesseract.image_to_string(img,lang="eng",config="--psm 4")

  return text


def check(s):
  if s.isdigit():
      return 'quantity'
  elif s.isalpha():
      return 'name'
  elif (s[-1]==":")and(s[:-1].isalpha()):
    return 'name'
  else:
    if s[0]=="$":
      try:
        float(s[1:])
        return "cost"
      except:
        return None
    else:
      try:
        float(s)
        return "cost"
      except:
        return None

# get separate lines from text

def get_data(img):
  text=process_text(img)
  if text.isspace():
    return None
  splits = text.splitlines()
  ocr={}

  # find the date
  try:
    date_pattern=r"(0[1-9]|[12][0-9]|3[01])[/](0[1-9]|1[012])[/](19|20)\d\d"
    date=re.search(date_pattern,text).group()
    ocr['date']=date
  except AttributeError:
    date="not found"
  
  # define a regular expression that will match line items that include
  # a price component
  pricePattern = r'([0-9]+\.[0-9]+)'

  # loop over each of the line items in the OCR'd receipt
  prices = []
  for line in splits:
    if re.search(pricePattern, line) is not None:
      prices.append(line)

# get items that have price attached to them
  items = []
  for line in prices:
    if re.search(r'Incl',line):
      continue
    else:
      items.append(line)

# go through items and create the dictionary
  all_items=[]
  tax={}
  totals={}
  for item in items:
    details = item.split()
    name=""
    quantity,cost=None,None
    for elem in details:
      if check(elem)==None:
        continue
      elif (check(elem)=="quantity")and(quantity==None):
        quantity=elem
      elif check(elem)=="name":
        name+=elem
      elif (check(elem)=="cost")and(cost==None):
        cost=elem
    if ("tax" in name)or("Tax" in name):
      tax[name]=cost
    elif ("total" in name)or("Total" in name):
      totals[name]=cost
    else:
      all_items.append({'quantity':quantity, 'description':name,'price':cost})

  # Store the results in the dict
  ocr['item']=all_items
  ocr['totals']=totals
  ocr['tax']=tax

  return ocr

# testing
# normal=r"user_photo.jpg"
# bad=r"bad_photo.jpg"
# good=r"nice_receipt.jpg"
# print(get_data(good))
