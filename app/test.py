import logging
import json
import re
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters, ConversationHandler, CallbackQueryHandler

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

def __is_on_whitelist(whom_to_check:str) -> bool:
    """
        Checks if user is on whitelist.
        
        Add usernames to whitelist to get more privileges
        
        :Return: True of False
    """
    whitelist = ["CHANGE_ME"]
    if whom_to_check in whitelist:
        return True
    else:
        return False
    
def __read_file() -> dict:
    """
        This func reads file.
        
        :Return: dict of beers which in format like
            beer_name: {
                name: str,
                score: str.
                photo: url_str
            }
    """
    with open('beers.json') as my_file:
        try:
            return json.load(my_file)        
        except json.JSONDecodeError:
            return None
        
def __update_file(data_to_write:str) -> None:
    """
        Func to rewrite file with beers. 
    """
    old_data = __read_file()
    
    with open('beers.json', 'w') as my_file:
        if old_data is None:
            my_file.write(json.dumps(__separate_data(data_to_write.encode('utf-8').decode('utf-8'))))
        else:
            old_data.update(__separate_data(data_to_write.encode('utf-8').decode('utf-8')))
            my_file.write(json.dumps(old_data))

def __separate_data(data:str) -> dict:
    """
        This func sliplit string by regular exeption like (num or numNum \ 10) and transform list into dict
                
        :Returns: dictionary like this
            beer_name :{
                name: str, 
                score: str, 
                photo: str
            }
    """
    score_reg = r"\s(\d|\d\d)\/10\s" # space (num or numnum) space
    beer_name, score, beer_photo = re.split(score_reg, data)
    
    res = {
        beer_name.lower():{
            'name': beer_name,
            'score': f'{score}/10',
            'photo': beer_photo
        }
    }
    return res

def __find_beer_by_full_name(what_to_search:str, where) -> dict:
    return where[what_to_search.lower()]

def __find_beer_by_part_of_name(what_to_search:str, where) -> list:
    """
        This function search beer by first part of his name.
        Using regular exeption like ([what_to_search] & [any character that's not a digit]).
        
        :Return: list of keys wich match with regular exeption (beer_name and any amount non digit) 
    """
    reg = what_to_search.lower() + r"\D*"
    keys_list = list(where.keys())
    res = list()    
    
    for key in keys_list:
        mathed = str(re.findall(reg, key))
        if key == mathed[2:-2]:
            res.append(key)
        else:
            pass        
        
    return res
        
def __delete_beer(beer_to_delete: str):
    file_data = __read_file()
    if beer_to_delete.lower() in file_data:
        del file_data[beer_to_delete.lower()]
        with open('beers.json', 'w') as my_file:
            my_file.write(json.dumps(file_data))
        return True
    else:
        return False
        
        
GUEST_STATE, START, ADD_BEER, WRITE_BEER, FIND_BEER, DELETE_BEER = range(6)
DELETE_BUTTON, REDO_BUTTON, CONFIRM_BUTTON = range(3)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "This is BeerBot. \nYou can start conversation by call him like /beerbot. \nOr you can ask for help by /help."
    await context.bot.send_message(update.effective_chat.id, text=text)

async def start_conv(update:Update, context: ContextTypes.DEFAULT_TYPE):
    if __is_on_whitelist(update.message.from_user['username']):
        reply_keyboard = [["Find beer by name","Add beer"],["Quit"]]
    else:
        reply_keyboard =[["Find beer by name"],["Quit"]]
    
    markup = ReplyKeyboardMarkup(keyboard=reply_keyboard, one_time_keyboard=True)
    
    text = "A pleasure to meet you. I am BeerBot, Human-Beer Relations. I am stock information in over six million(it's definitely not) beer types.\nMay i help you?"
    
    await update.message.reply_text(text,reply_markup=markup)    
    if __is_on_whitelist(update.message.from_user['username']):
        return START
    else:
        return GUEST_STATE

async def check_white_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user['username']
    if __is_on_whitelist(user):
        await update.message.reply_text(f"{user} is in white list")
    else:
        await update.message.reply_text(f"YOU ARE INTRUDER")
        
async def find_beer_by_name(update:Update, context:ContextTypes.DEFAULT_TYPE):
    """
        This function search beer by his full or part name using functions which work with local 'beer storage'.
        
        If func find something by full name -> will sent msg with beer info.
        
        Else -> try to find with part of name -> will sent msg if find something, if its not - will sent regret msg
    """
    file_data = __read_file()
    beer_name = update.message.text.lower()
    inline_keyboard = InlineKeyboardMarkup([[InlineKeyboardButton('Delete Beer', callback_data=str(DELETE_BUTTON))]])
    
    try:
        beer = __find_beer_by_full_name(beer_name, file_data)
        context.user_data['finded_beer'] = beer['name'] # remember finded beer if we want to telete it
        msg = f"{beer['name']} {beer['score']}"
        if __is_on_whitelist(update.message.from_user['username']):
            await context.bot.send_photo(chat_id=update.effective_chat.id, photo=beer["photo"], caption=msg, reply_markup=inline_keyboard)
        else:
            await context.bot.send_photo(chat_id=update.effective_chat.id, photo=beer["photo"], caption=msg)
    except KeyError:
        beer_list = list()
        key_list = __find_beer_by_part_of_name(beer_name,file_data)

        for key in key_list:
            beer_list.append(__find_beer_by_full_name(key, file_data))
        try:
            beer = beer_list[0]
            msg = f"{beer['name']} {beer['score']}"
            context.user_data['finded_beer'] = beer['name'] # remember finded beer if we want to telete it
            
            await update.message.reply_text("Find something like you want, but you should be more accurate")
            if __is_on_whitelist(update.message.from_user['username']): # check if user in on white list
                await context.bot.send_photo(chat_id=update.effective_chat.id, photo=beer["photo"], caption=msg, reply_markup=inline_keyboard)
            else:
                await context.bot.send_photo(chat_id=update.effective_chat.id, photo=beer["photo"], caption=msg)
        except IndexError:
            await update.message.reply_text("I can't find this thing. Maybe this beer is not added yet. SRY!!!!\nYou can try again)")
    
    if __is_on_whitelist(update.message.from_user['username']):
        return START
    else:
        return GUEST_STATE
       
async def goto_find_beer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Sooo, what you want????")
    return FIND_BEER

async def add_beer(update:Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Oh you wanna add some beer??? Let me take a look. \nBest option = write complete words \n(med instead medium = not good) \nExample: Heineken 7/10 photo_url")
    return ADD_BEER

async def add_beer_to_db(update: Update, context:ContextTypes.DEFAULT_TYPE):
    """
        This function separate input string to beer_name score beer_photo.
        
        Then send example how it gonna look.
        
        Store beer info into context.user_data['beer']. 
        
        And move conversation to WRITE_BEER state.
    """
    text = update.message.text
    score_reg = r"\s(\d|\d\d)\/10\s" # space (num or numnum) space
    try:
        beer_name, score, beer_photo = re.split(score_reg, text)
       
        if isinstance(int(score), int) and len(beer_name) > 0 and len(beer_photo) > 4:
            keyboard = [[InlineKeyboardButton('Confirm', callback_data=str(CONFIRM_BUTTON)), InlineKeyboardButton('Redo', callback_data=str(REDO_BUTTON))]]
            inline_keyboard = InlineKeyboardMarkup(keyboard)
            context.user_data['beer'] = text.encode('utf-8').decode('utf-8') # store data in to context.user_data['beer']
            
            await update.message.reply_text("beer gonna look like this")
            await context.bot.send_photo(chat_id=update.effective_chat.id, photo=beer_photo, caption=f"{beer_name} {score}/10")
            await update.message.reply_text("You wanna keep this or redo?", reply_markup=inline_keyboard)
            return WRITE_BEER
        else:
            await update.message.reply_text("You should check if anything alright. Press 'Add beer' again.")
            return START
    except:
            await update.message.reply_text("You should check if anything alright. Press 'Add beer' again.")
            return START
        
async def confirmation_add_beer(update:Update, context: ContextTypes.DEFAULT_TYPE):
    """
        Reads beer info from context.user_data['beer'].
        
        Write this info into file = __update_file().
        
        Move conversation into START state.
    """
    query = update.callback_query
    beer = context.user_data['beer']
    __update_file(beer)
    del context.user_data['beer']
    
    await query.answer()
    await query.edit_message_text(text='Beer added')
    return START
    
async def redo_add_beer(update:Update, context: ContextTypes.DEFAULT_TYPE):
    del context.user_data['beer']
    
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(text='Send what you wanna add again')
    return ADD_BEER

async def goto_delete_beer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
        Function track us to DELETE_BEER state in conversation.
        
        If we wanna delete beer 
    """
    query = update.callback_query
    finded_beer = context.user_data['finded_beer']
    inline_keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("yes", callback_data=str(CONFIRM_BUTTON)), InlineKeyboardButton("NO", callback_data=str(REDO_BUTTON))]])
    await query.answer()
    await context.bot.send_message(update.effective_chat.id, text=f"You wanna delete {finded_beer}???", reply_markup=inline_keyboard)
    return DELETE_BEER

async def delete_beer_from_db(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
        Reads data from context.user_data, then use 'local' func __delete_beer to delete beer.
        
        If __delete_beer return True -> beer deleted
        
        Else -> something goes wrong
    """
    query = update.callback_query
    beer_to_delete = context.user_data['finded_beer']
    await query.answer()

    if __delete_beer(beer_to_delete):
        await query.edit_message_text("Beer deleted(((")
    else:
        await query.edit_message_text("Something goes wrong")
    return START

async def not_delete_beer_from_db(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Do not scare me please)")
    return START

async def reply_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_msg = f"Soooo you need some help...\nYou can call BeerBot by /beerbot.\nHe's can find some beer if you press button and type at least 1 character.\nBetter option - search by full name.\nGOOD LUCK!!!"
    await update.message.reply_text(help_msg)

async def end_conv(update:Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("I'm done. I'm quit!!!", reply_markup=ReplyKeyboardRemove())    
    return ConversationHandler.END
    

if __name__ == "__main__":
    application = ApplicationBuilder().token("CHANGE_ME").build()
    
    start_handler = CommandHandler("start", start)
    help_handler = CommandHandler('help', reply_help)

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("beerbot", start_conv)],
        states={
            GUEST_STATE:[
                MessageHandler(filters.Regex("^Find beer by name$"), goto_find_beer),
            ],
            START:[
                MessageHandler(filters.Regex("^Add beer$"),add_beer),
                MessageHandler(filters.Regex("^Find beer by name$"), goto_find_beer),
                CallbackQueryHandler(goto_delete_beer, pattern=f"^{str(DELETE_BUTTON)}$")
            ],
            ADD_BEER:[
                MessageHandler(filters.TEXT & ~(filters.COMMAND | filters.Regex('^quit$')), add_beer_to_db),
            ],
            WRITE_BEER:[
                CallbackQueryHandler(confirmation_add_beer, pattern=f'^{str(CONFIRM_BUTTON)}$'),                
                CallbackQueryHandler(redo_add_beer, pattern=f'^{str(REDO_BUTTON)}$')                
            ],
            DELETE_BEER:[
                CallbackQueryHandler(delete_beer_from_db, pattern=f"^{str(CONFIRM_BUTTON)}$"),
                CallbackQueryHandler(not_delete_beer_from_db, pattern=f"^{str(REDO_BUTTON)}$"),
            ],
            FIND_BEER:[
                MessageHandler(filters.TEXT & ~(filters.COMMAND | filters.Regex('^quit$')), find_beer_by_name)
            ]
            },
        fallbacks=[MessageHandler(filters.Regex("^Quit$"),end_conv)]
    )
    
    application.add_handler(start_handler)
    application.add_handler(conv_handler)
    application.add_handler(help_handler)
    
    
    application.run_polling()