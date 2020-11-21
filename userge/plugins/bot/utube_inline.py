import datetime
import glob
import os
from pathlib import Path
from time import time

import requests
import youtube_dl
from pyrogram import filters
from pyrogram.errors import MessageIdInvalid
from pyrogram.raw.types import UpdateNewChannelMessage, UpdateNewMessage
from pyrogram.types import CallbackQuery, InlineKeyboardButton, InputMediaVideo
from wget import download
from youtube_dl.utils import DownloadError

from userge import Config, Message, pool, userge
from userge.utils import get_file_id_and_ref

from ..misc.upload import upload

LOGGER = userge.getLogger(__name__)
CHANNEL = userge.getCLogger(__name__)
STORE_DATA = {}


def get_ytthumb(videoid):
    thumb_quality = [
        "maxresdefault.jpg",
        "hqdefault.jpg",
        "sddefault.jpg",
        "mqdefault.jpg",
        "default.jpg",
    ]
    thumb_link = "https://i.imgur.com/4LwPLai.png"
    for qualiy in thumb_quality:
        link = f"https://i.ytimg.com/vi/{videoid}/{qualiy}"
        r = requests.get(link)
        if r.status_code == 200:
            thumb_link = link
            break
    return thumb_link


def ytdl_btn_generator(array, code, i_q_id):
    btn = []
    b = []
    for i in array:
        name = f"{i.get('format_note', None)} ({i.get('ext', None)})"
        call_back = f"ytdl{code}|{i.get('format_id', '')}|{i_q_id}"
        b.append(InlineKeyboardButton(name, callback_data=call_back))
        if len(b) == 3:  # no. of columns
            btn.append(b)
            b = []
    if len(b) != 0:
        btn.append(b)  # buttons in the last row
    return btn


def date_formatter(date_):
    if len(date_) != 8:  # TODO change it according to the input
        return date_
    year, day, month = date_[:4], date_[4:6], date_[6:]
    if int(month) > 12:
        return date_
    x = datetime.datetime(int(year), int(month), int(day))
    return str(x.strftime("%d-%b-%Y"))


@userge.on_cmd("iytdl", about={"header": "Inline youtube go Brr"})
async def iytdl_inline(message: Message):
    input_url = message.input_str
    bot = await userge.bot.get_me()
    x = await userge.get_inline_bot_results(bot.username, f"ytdl {input_url}")
    y = await userge.send_inline_bot_result(
        chat_id=message.chat.id, query_id=x.query_id, result_id=x.results[0].id
    )
    for i in y.updates:
        if isinstance(i, UpdateNewMessage) or isinstance(i, UpdateNewChannelMessage):
            datax = (
                (
                    (i["message"].reply_markup.rows[0].buttons[0].data).decode("utf-8")
                ).split("|")
            )[2]
            break

    STORE_DATA[datax] = {"chat_id": message.chat.id, "msg_id": y.updates[0].id}
    # await CHANNEL.log(str(x))
    # await CHANNEL.log(str(y))
    await message.delete()
    # await asyncio.sleep(90)
    # await userge.delete_messages(message.chat.id, y.updates[0].id)


if userge.has_bot:

    @userge.bot.on_callback_query(filters.regex(pattern=r"^ytdl(\S+)\|(\d+)\|(\d+)$"))
    async def ytdl_callback(_, c_q: CallbackQuery):
        await CHANNEL.log(str(c_q))
        startTime = time()
        inline_mode = True
        u_id = c_q.from_user.id
        if u_id not in Config.OWNER_ID and u_id not in Config.SUDO_USERS:
            return await c_q.answer("𝘿𝙚𝙥𝙡𝙤𝙮 𝙮𝙤𝙪𝙧 𝙤𝙬𝙣 𝙐𝙎𝙀𝙍𝙂𝙀-𝙓", show_alert=True)
        choice_id = c_q.matches[0].group(2)
        i_q_id = c_q.matches[0].group(3)
        callback_continue = "Downloading Video Please Wait..."
        callback_continue += f"\n\nFormat Code : {choice_id}"
        await c_q.answer(callback_continue, show_alert=True)
        upload_msg = await userge.send_message(Config.LOG_CHANNEL_ID, "Uploading...")
        yt_code = c_q.matches[0].group(1)
        yt_url = f"https://www.youtube.com/watch?v={yt_code}"
        try:
            await c_q.edit_message_caption(
                caption=(
                    f"Video is now Downloading, for progress [<b>click here</b>]({upload_msg.link})"
                    f"\n\n🔗  [<b>Link</b>]({yt_url})\n🆔  <b>Format Code</b> : {choice_id}"
                ),
                reply_markup=None,
            )
        except MessageIdInvalid:
            inline_mode = False
            todelete = STORE_DATA.get(i_q_id, None)
            print(todelete)
            if todelete:
                bad_msg = await userge.get_messages(
                    todelete["chat_id"], todelete["msg_id"]
                )
                print(bad_msg)
                await bad_msg.delete()
                upload_msg = await userge.send_message(
                    todelete["chat_id"], "Uploading ..."
                )

        retcode = await _tubeDl(yt_url, startTime, choice_id)
        if retcode == 0:
            _fpath = ""
            for _path in glob.glob(os.path.join(Config.DOWN_PATH, str(startTime), "*")):
                if not _path.lower().endswith((".jpg", ".png", ".webp")):
                    _fpath = _path
            if not _fpath:
                await upload_msg.err("nothing found !")
                return
            uploaded_vid = await upload(upload_msg, Path(_fpath))
        else:
            return await upload_msg.edit(str(retcode))
        if not inline_mode:  # WIP
            return
        refresh_vid = await userge.bot.get_messages(
            Config.LOG_CHANNEL_ID, uploaded_vid.message_id
        )
        f_id, f_ref = get_file_id_and_ref(refresh_vid)
        video_thumb = None
        if refresh_vid.video.thumbs:
            video_thumb = await userge.bot.download_media(
                refresh_vid.video.thumbs[0].file_id
            )
        else:
            video_thumb = download(get_ytthumb(yt_code))

        if inline_mode:
            await c_q.edit_message_media(
                media=InputMediaVideo(
                    media=f_id,
                    file_ref=f_ref,
                    thumb=video_thumb,
                    caption=f"📹  <b>[{uploaded_vid.caption}]({yt_url})</b>",
                    supports_streaming=True,
                ),
                reply_markup=None,
            )

        await uploaded_vid.delete()


@pool.run_in_thread
def _tubeDl(url: list, starttime, uid):
    ydl_opts = {
        "addmetadata": True,
        "geo_bypass": True,
        "nocheckcertificate": True,
        "outtmpl": os.path.join(
            Config.DOWN_PATH, str(starttime), "%(title)s-%(format)s.%(ext)s"
        ),
        "logger": LOGGER,
        "format": f"{uid}+bestaudio/best",
        "writethumbnail": True,
        "prefer_ffmpeg": True,
        "postprocessors": [{"key": "FFmpegMetadata"}],
    }
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        try:
            x = ydl.download([url])
        except DownloadError as e:
            CHANNEL.log(str(e))
            x = None
    return x
