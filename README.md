PayMELah Telegram Bot
=====================
By Clarissa Jew, Rainer Kam, and Lyn Tan  
Hack&Roll 2022: Hackathon Project

* **[Video Demo](https://youtu.be/WijowPbr0JI)**
* **[Devpost Link](https://devpost.com/software/paymelah-telebot)**

## Inspiration
Have to work out some crazy math after eating out with your friends? With payMElah, you'll never have to stare at your receipt calculating! Simply send a photo of the receipt to our Telegram bot and let it do your work for you. It's that simple. Settle group payments in a blink of an eye with our Telegram bot, payMElah! 

Being from the same social group, we often found it frustrating to keep track of how much each individual should pay after group meals. We came across a TikTok video showing how the accountant in a social group had to perform seemingly insanely complicated calculations whenever he ate out with his friends. All those intimidating numbers and equations prodded us to think, "Is there a way to automate this?". This compelled us to brainstorm of an efficient and accurate system that friend groups in Singapore could potentially use to automate this process of splitting bills. 

## What it does
payMElah is  a user friendly telegram bot that facilitates the process of splitting bills within groups using OCR concept for its backend. All you have to do is upload an image of their receipt and with a click of a few buttons, the payMElah bot will settle everything for you! 

Here are the list of commands payMElah can execute for you:
- */start*: Type this command in chat or select it from the pop out menu to start the bot
- */splitnewbill*: Use this after /start or whenever you want to split a new bill. This prepares the bot to accept a photo of your receipt.
- */cancel*: Use this command if you wish to cancel the splitting of your current bill. Use /splitnewbill after cancelling to start a new splitting process.
- */help*: Brings this message up for future reference

## How we built it
We built payMElah using Python and telegrambot APIs for our bot flow, and our Optical Character Recognition (OCR) with the Pytesseract library.  

## Challenges we ran into
The biggest challenge we ran into was the variety of receipt formats there are. Almost every receipt we found online was of a different format — some showed unit prices and subtotals, some didn't; some . The lack of a standard receipt format made OCR of receipt images extremely challenging. Due to the time constraint, we limited our receipt formats to the most basic format (each item is on one line with its total price shown, no unit price).

Integrating different libraries into our system was challenging as well, as we had to connect our Telegram bot frontend with our OCR processing backend. 

## Accomplishments that we're proud of

## What we learned

## What's next for payMElah telebot
1. Given more time, we could extend our bot to accept images of receipts of a more complicated format. To handle such receipts, we could improve the accuracy of our OCR AI backend by training it on the dataset of labelled receipt images.
2. Bot user experience can be enhanced by refining bot flow or adding extra features:

    * Changing modes between Inclusive and Exclusive
        * Currently, our bot is in Exclusive mode by default, meaning everyone is assumed to pay for every item on the list by default. To specify who exactly ate what, it will be done by tapping usernames of people who didn't eat that item. 
        * The Inclusive mode can be added, such that no one is assumed to pay for every item on the list by default. To specify who exactly ate what, it will be done by tapping usernames of people who did eat that item (and have to pay for it).

    * Allowing users to create a receipt manually
        * If the receipt is too damaged or complicated for OCR processing, users can create a bill manually by keying in items' quantity, description, and price. Then, the same bot flow and logic can be used to split the bill.

3. Integration of payment systems into the bot flow so that users can reimburse their friends conveniently
