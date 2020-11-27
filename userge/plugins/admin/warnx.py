from time import time

from bson import ObjectId
from pyrogram import filters

# from pyrogram.errors import PeerIdInvalid
from pyrogram.types import (
    CallbackQuery,
    Chat,
    ChatPermissions,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    User,
)

from userge import Config, Message, get_collection, userge

WARN_DATA = get_collection("WARN_DATA")
WARNS_DB = get_collection("WARNS_DB")
CHANNEL = userge.getCLogger(__name__)

no_input_reply = (
    "I don't know who you're talking about, you're going to need to specify a user...!"
)
userid_not_valid = "can't get the user!"
user_is_admin = "Sorry! I can't warn an Admin"
owner_or_sudo = "I can't Ban My Owner and Sudo Users"
permission_denied = "You Don't have the permission to do it !"
warn_removed = "✅ Warn Removed Successfully"
warn_removed_caption = "✅ Warn removed by {} !"
no_warns_msg = "Well, {} doesn't have any warns."
total_warns_msg = "User {} has {}/{} warnings.\n**Reasons** are:"
purge_warns = "{} reset {} warns of {} in {}!"
banned_text = "Warnings has been exceeded! {} has been {}!"


@userge.on_cmd(
    "warn",
    about={
        "header": "warn a user",
        "description": "Use this command to warn the user! you can mention or reply to the offended user and add reason if needed",
        "usage": "{tr}warn [username | userid] or [reply to user] :reason (optional)",
    },
    allow_private=False,
    allow_bots=False,
    allow_channels=False,
    check_restrict_perm=True,
)
async def warn_func(message: Message):
    warn_user_id, reason = message.extract_user_and_text
    if not warn_user_id:
        return await message.err(no_input_reply, del_in=3)

    warned_user = await message.client.get_users(warn_user_id)

    if await admin_check(message.chat, warned_user.id):
        return await message.err(user_is_admin, del_in=3)
    elif warned_user.id in Config.OWNER_ID or warned_user.id in Config.SUDO_USERS:
        return await message.err(owner_or_sudo, del_in=3)

    found = await WARN_DATA.find_one({"chat_id": message.chat.id})
    if found:
        max_warns = found.get("max_warns", 3)
        rules = found.get("rules", None)
        warn_mode = found.get("warn_mode", "ban")

    else:
        warn_mode = "ban"
        max_warns = 3  # Default
        rules = None

    by_user = message.from_user
    wcount = await WARNS_DB.count_documents(
        {"chat_id": message.chat.id, "user_id": warned_user.id}
    )
    chat_title = message.chat.title

    wcount += 1

    if wcount >= max_warns:

        if warn_mode == "mute":
            warn_mode_text = "muted"
        elif warn_mode == "kick":
            warn_mode_text = "kicked"
        else:
            warn_mode_text = "banned"

        await message.reply(
            banned_text.format(warned_user.mention, warn_mode_text),
            disable_web_page_preview=True,
        )
        await ban_function(message, warned_user, warn_mode)
        await WARNS_DB.delete_many(
            {"user_id": warned_user.id, "chat_id": message.chat.id}
        )
        return

    warn_text = f"""
{by_user.mention} has warned {warned_user.mention} in <b>{chat_title}</b>
Reason: <code>{reason}</code>
Warns: {wcount}/{max_warns}
"""
    warn_id = str(
        (
            await WARNS_DB.insert_one(
                {
                    "user_id": warned_user.id,
                    "chat_id": message.chat.id,
                    "reason": str(reason),
                    "by": by_user.id,
                }
            )
        ).inserted_id
    )

    if message.client.is_bot:
        btn_row = [
            InlineKeyboardButton(
                "⚠️  Remove Warn", callback_data=f"remove_warn_{warn_id}"
            )
        ]
        if rules:
            btn_row.append(InlineKeyboardButton("📝  Rules", url=rules))

        buttons = InlineKeyboardMarkup([btn_row])
        reply_id = message.reply_to_message.message_id if message.reply_to_message else None
        await userge.bot.send_message(
            message.chat.id,
            warn_text,
            disable_web_page_preview=True,
            reply_markup=buttons,
            reply_to_message_id=reply_id
        )
    else:
        await message.edit(
            warn_text,
            disable_web_page_preview=True,
        )


@userge.on_cmd(
    "warnmode",
    about={"header": "warn_mode"},
    allow_private=False,
    allow_bots=False,
    allow_channels=False,
    check_restrict_perm=True,
)
async def warn_mode(message: Message):
    warn_types = ["kick", "ban", "mute"]
    warn_mode = message.input_str
    if not warn_mode and message.client.is_bot:
        buttons = [
            [
                InlineKeyboardButton("⚽️  KICK", callback_data="warnmode_type_kick"),
                InlineKeyboardButton("🤫  MUTE", callback_data="warnmode_type_mute"),
            ],
            [InlineKeyboardButton("⚰️  BAN", callback_data="warnmode_type_ban")],
        ]
        await message.reply(
            f"Choose a warn mode for:\n**Chat: {message.chat.title}**",
            reply_markup=InlineKeyboardMarkup(buttons),
        )
        return
    if not (warn_mode and warn_mode in warn_types):
        return await message.err("Not a valid warm mode", del_in=5)
    out = await update_warnmode(message, warn_mode)
    await message.edit(out)


async def update_warnmode(message: Message, warn_mode: str):
    result = await WARN_DATA.update_one(
        {"chat_id": message.chat.id}, {"$set": {"warn_mode": warn_mode}}, upsert=True
    )
    out = "{} <b>{}</b> to {} for {}\n**ID:** {}"
    if result.upserted_id:
        out = out.format("Warn Mode", "Changed", warn_mode, message.chat.title, message.chat.id)
    else:
        out = out.format("Warn Mode", "Updated", warn_mode, message.chat.title, message.chat.id)
    return out


@userge.on_cmd(
    "maxwarns",
    about={"header": "maxwarns"},
    allow_private=False,
    allow_bots=False,
    allow_channels=False,
    check_restrict_perm=True,
)
async def maxwarns(message: Message):
    maxwarns = message.input_str
    if not (maxwarns.isdigit() and maxwarns in range(2, 1001)):
        return await message.err('Invalid Input! Choose a number between 2 - 1000 \n(min. 2, max. 1000)', del_in=5)
    result = await WARN_DATA.update_one(
        {"chat_id": message.chat.id},
        {"$set": {"max_warns": int(maxwarns)}},
        upsert=True,
    )
    out = "{} <b>{}</b> for {}\n**ID:** {}"
    if result.upserted_id:
        out = out.format("Max Warns", "Changed", message.chat.title, message.chat.id)
    else:
        out = out.format("Max Warns", "Updated", message.chat.title, message.chat.id)
    await message.edit(out)


@userge.on_cmd(
    "chatrules",
    about={"header": "chat rules"},
    allow_private=False,
    allow_bots=False,
    allow_channels=False,
    check_restrict_perm=True,
)
async def chat_rules(message: Message):
    rules = message.input_str
    result = await WARN_DATA.update_one(
        {"chat_id": message.chat.id}, {"$set": {"rules": rules}}, upsert=True
    )
    out = "{} <b>{}</b> for {} \n**ID:** {}"
    if result.upserted_id:
        out = out.format("Rules", "Changed", message.chat.title, message.chat.id)
    else:
        out = out.format("Rules", "Updated", message.chat.title, message.chat.id)
    await message.edit(out)


async def admin_check(chatx: Chat, user_id: int) -> bool:
    check_status = await chatx.get_member(user_id)
    admin_strings = ["creator", "administrator"]
    return check_status.status in admin_strings


async def ban_function(message: Message, warned_user: User, warn_mode: str):
    if warn_mode == "ban":
        await message.chat.kick_member(warned_user.id)
    elif warn_mode == "mute":
        await message.chat.restrict_member(
            user_id=warned_user.id, permissions=ChatPermissions(can_send_messages=False)
        )
    elif warn_mode == "kick":
        await message.chat.kick_member(warned_user.id, until_date=int(time() + 90))


@userge.on_cmd(
    "(?:resetwarns|delwarns)",
    about={
        "header": "reset warns",
        "description": "This command is used to delete all the warns user got so far in the chat",
    },
    name="resetwarns",
    allow_private=False,
    allow_bots=False,
    allow_channels=False,
    check_restrict_perm=True,
)
async def totalwarns(message: Message):
    warn_user_id = (message.extract_user_and_text)[0]
    if not warn_user_id:
        return await message.err(no_input_reply, del_in=5)
    warn_user = await message.client.get_users(warn_user_id)
    
  
    if await WARNS_DB.find_one(
        {"chat_id": message.chat.id, "user_id": warn_user_id}
        ):
        deleted = await WARNS_DB.delete_many(
            {"chat_id": message.chat.id, "user_id": warn_user_id}
        )
        purged = deleted.deleted_count
        await message.reply(
            purge_warns.format(
                message.from_user.mention,
                purged,
                warn_user.mention,
                message.chat.title,
            )
        )
    else:
        await message.edit(no_warns_msg.format(warn_user.mention))


@userge.on_cmd(
    "warns",
    about={"header": "check warns of a user"},
    allow_private=False,
    allow_bots=False,
    allow_channels=False,
    check_restrict_perm=True,
)
async def totalwarns(message: Message):
    warn_user_id = (message.extract_user_and_text)[0]
    if not warn_user_id:
        return await message.err(no_input_reply, del_in=5)
    warn_user = await message.client.get_users(warn_user_id)
    
    count = 0
    found = await WARN_DATA.find_one({"chat_id": message.chat.id})
    max_warns = 3
    if found:
        max_warns = found.get("max_warns", 3)
    warns_ = ""
    async for warn in WARNS_DB.find(
        {"chat_id": message.chat.id, "user_id": warn_user.id}
    ):
        count += 1
        rsn = warn["reason"]
        reason = f"<code>{rsn}</code>"
        if not rsn or rsn == "None":
            reason = "<i>No Reason</i>"
        u_mention = (await userge.get_users(warn["by"])).mention
        warns_ += f"  \n**{count}.** {reason} by {u_mention}"
    if count == 0:
        await message.reply(no_warns_msg.format(warned_user.mention))
        return
    warns_text = total_warns_msg.format(warned_user.mention, count, max_warns)
    warns_text += warns_
    await message.reply(warns_text, disable_web_page_preview=True)


if userge.has_bot:

    @userge.bot.on_callback_query(filters.regex(pattern=r"^remove_warn_(.*)$"))
    async def remove_warn_(_, c_q: CallbackQuery):
        await CHANNEL.log(str(c_q))
        u_id = c_q.from_user.id
        if u_id not in Config.OWNER_ID:
            return await c_q.answer(permission_denied, show_alert=True)
        obj_id = c_q.matches[0].group(1)
        if await WARNS_DB.delete_one({"_id": ObjectId(obj_id)}):
            await c_q.answer(warn_removed, show_alert=False)
            await c_q.edit_message_caption(
                caption=(warn_removed_caption.format(c_q.from_user.mention)),
                reply_markup=None,
            )

    @userge.bot.on_callback_query(filters.regex(pattern=r"^warnmode_type_(.*)$"))
    async def remove_warn_(_, c_q: CallbackQuery):
        u_id = c_q.from_user.id
        if u_id not in Config.OWNER_ID:
            return await c_q.answer(permission_denied, show_alert=True)
        warnmode = c_q.matches[0].group(1)
        await c_q.answer(f"Changing Warn Mode to {warnmode}...", show_alert=False)
        out = await update_warnmode(c_q.message, warnmode)
        await c_q.edit_message_caption(
            caption=out,
            reply_markup=None,
        )
