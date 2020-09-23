# Copyright (C) 2020 BY - GitHub.com/code-rgb [TG - @deleteduser420]
# All rights reserved.

"""Module that handles Inline Help"""

from userge import userge, Message, Config
from pyrogram.types import (  
     InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery)
from pyrogram import filters


HELP_BUTTONS = None
PRIV_USERS = list(Config.SUDO_USERS)
PRIV_USERS.append(Config.OWNER_ID)


COMMANDS = {
            "secret" : { 'help_txt' : '**Send a secret message to a user**\n (only the entered user and you can view  the message)\n\n`secret @username [text]`', 'i_q' : 'secret @DeletedUser420 This is a secret message'},
            "alive" : { 'help_txt' : '**Alive Command for USERGE-X**\n\nThis You can view Uptime, Setting and Versions of your bot and when you change settings they are updayted in Real-time UwU', 'i_q' : 'alive'},
            "opinion" : { 'help_txt' : '**Ask for opinion via inline**\n\nYou can now send multple opinion messages at once\n**Note: **All button data is cleared as soon as you restart or update bot\n`op [Question or Statement]`', 'i_q' : 'op Are Cats Cute ?'},
            "repo" : { 'help_txt' : '**Your USERGE-X Github repo**\n\nwith direct deploy button', 'i_q' : 'repo'},
            "gapps" : { 'help_txt' : '**Lastest arm64 Gapps for <u>Android 10 Only !</u>**\n\n`Choose from Niksgapps, Opengapps and Flamegapps`', 'i_q' : 'gapps'},
            "ofox" : { 'help_txt' : '**Lastest Ofox Recovery for supported device, Powered By offcial Ofox API v2**\n\n`ofox <device codename>`', 'i_q' : 'ofox whyred'},
            "rick" : { 'help_txt' : '**Useless Rick Roll**\n\nBasically a wierd looking button with rickroll link xD\n`rick`', 'i_q' : 'rick'},
            "help" : { 'help_txt' : '**Help For All Userbot plugins**\n\n**Note:** `You can load and unload a plugin`', 'i_q' : ''},
            "stylish" : { 'help_txt' : '**Write it in Style**\n\nplugin to decorate text with unicode fonts.\n`stylish [text]`', 'i_q' : 'stylish USERGE-X'}
            }


if Config.BOT_TOKEN and Config.OWNER_ID:
    if Config.HU_STRING_SESSION:
        ubot = userge.bot
    else:
        ubot = userge


    def help_btn_generator():
        btn = []
        b = []
        for cmd in list(COMMANDS.keys()):
            name = cmd.capitalize()
            call_back = f"ihelp_{cmd}"
            b.append(
               InlineKeyboardButton(name, callback_data=call_back)
            )
            if len(b) == 3:   # no. of columns
                btn.append(b)
                b = []
        if len(b) != 0: 
            btn.append(b)     # buttons in the last row
        return btn
   

    if not HELP_BUTTONS:
        HELP_BUTTONS = help_btn_generator()

    BACK_BTN = InlineKeyboardButton(" ◀️  Back ", callback_data="backbtn_ihelp")

    inline_help_txt =" <u><b>INLINE COMMANDS</b></u>\n\nHere is a list of all available inline commands.\nChoose a command and for usage see: [ **📕  EXAMPLE** ]"
            

    @ubot.on_message(filters.user(PRIV_USERS) & filters.private & (filters.command("inline") | filters.regex(pattern=r"^/start inline$")))
    async def inline_help(_, message: Message):
        await ubot.send_message(
            chat_id=message.chat.id,
            text=inline_help_txt,
            reply_markup=InlineKeyboardMarkup(HELP_BUTTONS)
        )


    @ubot.on_callback_query(filters.user(PRIV_USERS) & filters.regex(pattern=r"^backbtn_ihelp$"))
    async def back_btn(_, c_q: CallbackQuery): 
        await c_q.edit_message_text(
            text=inline_help_txt,
            reply_markup=InlineKeyboardMarkup(HELP_BUTTONS)
        )


    @ubot.on_callback_query(filters.user(PRIV_USERS) & filters.regex(pattern=r"^ihelp_([a-zA-Z]+)$"))
    async def help_query(_, c_q: CallbackQuery): 
        command_name = c_q.matches[0].group(1)
        msg = COMMANDS[command_name]['help_txt']
        switch_i_q = COMMANDS[command_name]['i_q']
        buttons = [[BACK_BTN, InlineKeyboardButton(" 📕  EXAMPLE ", switch_inline_query_current_chat=switch_i_q)]]
        await c_q.edit_message_text(
                msg,
                reply_markup=InlineKeyboardMarkup(buttons)
        )
