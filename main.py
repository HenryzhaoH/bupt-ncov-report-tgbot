from include import *
from peewee import SqliteDatabase
import argparse, traceback, sys, datetime, requests
from shutil import copyfile

from apscheduler.schedulers.background import BackgroundScheduler

from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, DispatcherHandlerStop
import telegram

def tguser_check(update, context):
    if BOT_DEBUG == True and update.message.from_user.id != TG_BOT_MASTER:
        update.message.reply_text("DEBUGGING, Try again later.")
        raise DispatcherHandlerStop()

    user, _ = TGUser.get_or_create(
        userid = update.message.from_user.id
    )
    now_username = update.message.from_user.username or update.message.from_user.first_name
    if user.username != now_username:
        user.username = now_username
        user.save()

def start_entry(update, context):
    """Send a message when the command /start is issued."""
    update.message.reply_text("Welcome, {}. try /help.\nSpecial Thanks to https://github.com/ipid/bupt-ncov-report".format(update.message.from_user.username or update.message.from_user.first_name or ''), disable_web_page_preview=True)
    help_entry(update, context)

def help_entry(update, context):
    """Send a message when the command /help is issued."""
    update.message.reply_markdown(HELP_MARKDOWN.strip(), disable_web_page_preview=True)

def list_entry(update, context, admin_all=False):
    first_message = update.message.reply_markdown(f"用户列表查询中 ...")
    if admin_all == True:
        users = BUPTUser.select().where(BUPTUser.status != BUPTUserStatus.removed).prefetch(TGUser)
    else:
        # users = BUPTUser.select().where(BUPTUser.owner == update.message.from_user.id).order_by(BUPTUser.id.asc())
        tguser = TGUser.get(
            userid = update.message.from_user.id
        )
        users = tguser.buptusers.where(BUPTUser.status != BUPTUserStatus.removed)
    ret_msgs = []
    ret_msg = ''
    for i, user in enumerate(users):
        if i % 10 == 0 and i != 0:
            ret_msgs.append(ret_msg)
            ret_msg = ''
        id = i+1
        ret_msg += f'ID: `{id}`\n'
        if user.username != None:
            ret_msg += f'Username: `{user.username}`\n' #Password: `{user.password}`\n'
        else:
            ret_msg += f'eai-sess: `{user.cookie_eaisess}`\n' #UUKey: `{user.cookie_uukey}`\n'
        if admin_all:
            ret_msg += f'Owner: `{user.owner.userid}` `{user.owner.username.replace("`","")}`\n'
        if user.status == BUPTUserStatus.normal:
            ret_msg += f'自动签到: `启用`\n'
        else:
            ret_msg += f'自动签到: `暂停`\n'
        if user.latest_response_data == None:
            ret_msg += '从未尝试签到\n'
        else:
            ret_msg += f'最后签到时间: `{user.latest_response_time}`\n'
            ret_msg += f'最后签到返回: `{user.latest_response_data[:100]}`\n'

        if user.latest_xisu_checkin_response_data == None:
            ret_msg += '从未尝试晨午晚检签到\n'
        else:
            ret_msg += f'最后晨午晚检签到时间: `{user.latest_xisu_checkin_response_time}`\n'
            ret_msg += f'最后晨午晚检签到返回: `{user.latest_xisu_checkin_response_data[:100]}`\n'

        if not admin_all:
            ret_msg += f'暂停 /pause\_{id}   恢复 /resume\_{id}\n签到 /checkin\_{id} 删除 /remove\_{id}\n晨午晚检签到 /checkinxisu\_{id}\n'
        ret_msg += "\n"
    ret_msgs.append(ret_msg)

    if len(users) == 0:
        ret_msgs = ['用户列表为空']
    if len(users) >= 2 and not admin_all:
        ret_msgs[-1] += f'恢复全部 /resume  暂停全部 /pause\n签到全部 /checkin  删除全部 /remove\_all \n晨午晚检签到 /checkinxisu'
    logger.debug(ret_msgs)

    first_message.delete()
    for msg in ret_msgs:
        update.message.reply_markdown(msg)


def add_by_cookie_entry(update, context):
    if len(context.args) != 2:
        first_message = update.message.reply_markdown(f"例：/add\_by\_cookie `1cmgkrrcssge6edkkg3ucigj1m` `44f522350f5e843fbac58b726753eb36`")
        return
    eaisess = context.args[0]
    uukey = context.args[1]
    first_message = update.message.reply_markdown(f"Adding ...")

    tguser = TGUser.get(
        userid = update.message.from_user.id
    )

    buptuser, _ = BUPTUser.get_or_create(
        owner = tguser,
        cookie_eaisess = eaisess,
        cookie_uukey = uukey,
        status = BUPTUserStatus.normal
    )

    first_message.edit_text('添加成功！', parse_mode = telegram.ParseMode.MARKDOWN)
    list_entry(update, context)

def add_by_uid_entry(update, context):
    if len(context.args) != 2:
        first_message = update.message.reply_markdown(f"例：/add\_by\_uid `2010211000` `password123`")
        return
    username = context.args[0]
    password = context.args[1]
    first_message = update.message.reply_markdown(f"Adding ...")

    tguser = TGUser.get(
        userid = update.message.from_user.id
    )

    buptuser, _ = BUPTUser.get_or_create(
        owner = tguser,
        username = username,
        password = password,
        status = BUPTUserStatus.normal
    )

    first_message.edit_text('添加成功！', parse_mode = telegram.ParseMode.MARKDOWN)
    list_entry(update, context)

def checkin_entry(update, context):
    tguser = TGUser.get(
        userid = update.message.from_user.id
    )
    if len(context.args) > 0:
        targets = tguser.get_buptusers_by_seqids(list(map(int, context.args)))
    else:
        targets = tguser.get_buptusers()

    if len(targets) == 0:
        ret_msg = '用户列表为空'
        update.message.reply_markdown(ret_msg)
        return
    for buptuser in targets:
        try:
            ret = buptuser.ncov_checkin(force=True)[:100]
            ret_msg = f"用户：`{buptuser.username or buptuser.cookie_eaisess or '[None]'}`\n签到成功！\n服务器返回：`{ret}`"
        except requests.exceptions.Timeout as e:
            ret_msg = f"用户：`{buptuser.username or buptuser.cookie_eaisess or '[None]'}`\n签到失败，服务器错误！\n`{e}`"
        except Exception as e:
            ret_msg = f"用户：`{buptuser.username or buptuser.cookie_eaisess or '[None]'}`\n签到异常！\n服务器返回：`{e}`"
        update.message.reply_markdown(ret_msg)

def checkinxisu_entry(update, context):
    tguser = TGUser.get(
        userid = update.message.from_user.id
    )
    if len(context.args) > 0:
        targets = tguser.get_buptusers_by_seqids(list(map(int, context.args)))
    else:
        targets = tguser.get_buptusers()

    if len(targets) == 0:
        ret_msg = '用户列表为空'
        update.message.reply_markdown(ret_msg)
        return
    for buptuser in targets:
        try:
            ret = buptuser.xisu_ncov_checkin(force=True)[:100]
            ret_msg = f"用户：`{buptuser.username or buptuser.cookie_eaisess or '[None]'}`\n晨午晚检成功！\n服务器返回：`{ret}`"
        except requests.exceptions.Timeout as e:
            ret_msg = f"用户：`{buptuser.username or buptuser.cookie_eaisess or '[None]'}`\n晨午晚检失败，服务器错误！\n`{e}`"
        except Exception as e:
            ret_msg = f"用户：`{buptuser.username or buptuser.cookie_eaisess or '[None]'}`\n晨午晚检异常！\n服务器返回：`{e}`"
        update.message.reply_markdown(ret_msg)

def pause_entry(update, context):
    tguser = TGUser.get(
        userid = update.message.from_user.id
    )
    if len(context.args) > 0:
        targets = tguser.get_buptusers_by_seqids(list(map(int, context.args)))
    else:
        targets = tguser.get_buptusers()

    for buptuser in targets:
        buptuser.status = BUPTUserStatus.stopped
        buptuser.save()
        ret_msg = f"用户：`{buptuser.username or buptuser.cookie_eaisess or '[None]'}`\n已暂停自动签到。"
        update.message.reply_markdown(ret_msg)

def resume_entry(update, context):
    tguser = TGUser.get(
        userid = update.message.from_user.id
    )
    if len(context.args) > 0:
        targets = tguser.get_buptusers_by_seqids(list(map(int, context.args)))
    else:
        targets = tguser.get_buptusers()

    for buptuser in targets:
        buptuser.status = BUPTUserStatus.normal
        buptuser.save()
        ret_msg = f"用户：`{buptuser.username or buptuser.cookie_eaisess or '[None]'}`\n已启用自动签到。"
        update.message.reply_markdown(ret_msg)

def remove_entry(update, context):
    assert len(context.args) > 0, "错误的命令，请用 /help 查看使用帮助。"

    tguser = TGUser.get(
        userid = update.message.from_user.id
    )
    if context.args[0].lower() != 'all':
        targets = tguser.get_buptusers_by_seqids(list(map(int, context.args)))
    else:
        targets = tguser.get_buptusers()

    for buptuser in targets:
        buptuser.status = BUPTUserStatus.removed
        buptuser.save()
        ret_msg = f"用户：`{buptuser.username or buptuser.cookie_eaisess or '[None]'}`\n已删除。"
        update.message.reply_markdown(ret_msg)

    list_entry(update, context)

def error_callback(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s: %s"', update, context.error.__class__.__name__, context.error)
    update.message.reply_text("{}: {}".format(context.error.__class__.__name__,context.error))
    traceback.print_exc()

def tg_debug_logging(update,context):
    log_str = 'User %s `%d`: "%s"' % (update.message.from_user.username, update.message.from_user.id, update.message.text)
    logger.info(log_str)

    # Skip forwarding when command call.
    if update.message.text is not None and update.message.text.startswith('/'):
        return
    # Skip master message
    if update.message.from_user.id == TG_BOT_MASTER:
        return

    updater.bot.send_message(chat_id=TG_BOT_MASTER, text="[LOG] "+ log_str, parse_mode = telegram.ParseMode.MARKDOWN)
    # Forward non-text message, like stickers.
    if update.message.text is None:
        updater.bot.forward_message(TG_BOT_MASTER, update.message.chat_id, update.message.message_id)

def checkinall_entry(update, context):
    assert update.message.from_user.id == TG_BOT_MASTER
    if len(context.args) > 0:
        if context.args[0] == 'retry':
            checkin_all_retry()
    else:
        checkin_all()

def checkinallxisu_entry(update, context):
    assert update.message.from_user.id == TG_BOT_MASTER
    if len(context.args) > 0:
        if context.args[0] == 'retry':
            checkin_all_xisu_retry()
    else:
        checkin_all_xisu()

def listall_entry(update, context):
    assert update.message.from_user.id == TG_BOT_MASTER
    list_entry(update,context,admin_all=True)

def status_entry(update, context):
    assert update.message.from_user.id == TG_BOT_MASTER
    cron_data = "\n".join(["name: %s, trigger: %s, handler: %s, next: %s" % (job.name, job.trigger, job.func, job.next_run_time) for job in scheduler.get_jobs()])
    update.message.reply_text("Cronjob: " + cron_data)
    update.message.reply_text("System time: " + str(datetime.datetime.now()))

def send_message_entry(update, context):
    assert update.message.from_user.id == TG_BOT_MASTER
    updater.bot.send_message(chat_id=context.args[0], text=' '.join(update.message.text.split(' ')[2:]))

def broadcast_entry(update, context):
    assert update.message.from_user.id == TG_BOT_MASTER
    active_userids = set()
    for user in BUPTUser.select().where(
        (BUPTUser.status == BUPTUserStatus.normal)
    ).prefetch(TGUser):
        active_userids.add(user.owner.userid)
    for userid in active_userids:
        updater.bot.send_message(chat_id=userid, text=' '.join(update.message.text.split(' ')[1:]))

def text_command_entry(update, context):
    req_args = update.message.text.strip(f'@{updater.bot.username}').split('_')
    command = req_args[0][1:]
    context.args = list(filter(lambda i: i != '', req_args[1:]))
    getattr(sys.modules[__name__], "%s_entry" % command)(update, context)

def backup_db():
    logger.info("backup started!")
    copyfile('./my_app.db', './backup/my_app.{}.db'.format(str(datetime.datetime.now()).replace(":","").replace(" ","_")))
    logger.info("backup finished!")

def checkin_all_retry():
    logger.info("checkin_all_retry started!")
    for user in BUPTUser.select().where(
        (BUPTUser.status == BUPTUserStatus.normal)
        & (BUPTUser.latest_response_time < datetime.datetime.combine(datetime.date.today(), datetime.datetime.min.time()))
    ).prefetch(TGUser):
        ret_msg = ''
        try:
            ret = user.ncov_checkin()[:100]
            ret_msg = f"用户：`{user.username or user.cookie_eaisess or '[None]'}`\n重试签到成功！\n服务器返回：`{ret}`\n{datetime.datetime.now()}"
        except requests.exceptions.Timeout as e:
            ret_msg = f"用户：`{user.username or user.cookie_eaisess or '[None]'}`\n重试签到失败，服务器错误，请尝试手动签到！\nhttps://app.bupt.edu.cn/ncov/wap/default/index\n`{e}`\n{datetime.datetime.now()}"
            traceback.print_exc()
        except Exception as e:
            ret_msg = f"用户：`{user.username or user.cookie_eaisess or '[None]'}`\n重试签到异常！\n服务器返回：`{e}`\n{datetime.datetime.now()}"
            traceback.print_exc()
        logger.info(ret_msg)
        updater.bot.send_message(chat_id=user.owner.userid, text=ret_msg, parse_mode = telegram.ParseMode.MARKDOWN)
    logger.info("checkin_all_retry finished!")

def checkin_all():
    try:
        backup_db()
    except:
        pass
    logger.info("checkin_all started!")
    for user in BUPTUser.select().where(BUPTUser.status == BUPTUserStatus.normal).prefetch(TGUser):
        ret_msg = ''
        try:
            ret = user.ncov_checkin()[:100]
            ret_msg = f"用户：`{user.username or user.cookie_eaisess or '[None]'}`\n自动签到成功！\n服务器返回：`{ret}`\n{datetime.datetime.now()}"
        except requests.exceptions.Timeout as e:
            ret_msg = f"用户：`{user.username or user.cookie_eaisess or '[None]'}`\n自动签到失败，服务器错误，将重试！\n`{e}`\n{datetime.datetime.now()}"
            traceback.print_exc()
        except Exception as e:
            ret_msg = f"用户：`{user.username or user.cookie_eaisess or '[None]'}`\n自动签到异常！\n服务器返回：`{e}`\n{datetime.datetime.now()}"
            traceback.print_exc()
        logger.info(ret_msg)
        updater.bot.send_message(chat_id=user.owner.userid, text=ret_msg, parse_mode = telegram.ParseMode.MARKDOWN)
    logger.info("checkin_all finished!")

def checkin_all_xisu_retry():
    global logger, updater
    logger.info("xisu_checkin_all_retry started!")
    for user in BUPTUser.select().where(
            (BUPTUser.status == BUPTUserStatus.normal)
            & (BUPTUser.latest_xisu_checkin_response_time < datetime.datetime.combine(datetime.date.today(), datetime.datetime.min.time()))
    ).prefetch(TGUser):
        ret_msg = ''
        try:
            ret = user.xisu_ncov_checkin()[:100]
            ret_msg = f"用户：`{user.username or user.cookie_eaisess or '[None]'}`\n重试晨午晚检成功！\n服务器返回：`{ret}`\n{datetime.datetime.now()}"
        except requests.exceptions.Timeout as e:
            ret_msg = f"用户：`{user.username or user.cookie_eaisess or '[None]'}`\n重试晨午晚检失败，服务器错误，请尝试手动签到！\n{config.XISU_REPORT_PAGE}\n`{e}`\n{datetime.datetime.now()}"
            traceback.print_exc()
        except Exception as e:
            ret_msg = f"用户：`{user.username or user.cookie_eaisess or '[None]'}`\n重试晨午晚检异常！\n服务器返回：`{e}`\n{datetime.datetime.now()}"
            traceback.print_exc()
        logger.info(ret_msg)
        updater.bot.send_message(chat_id=user.owner.userid, text=ret_msg, parse_mode = telegram.ParseMode.MARKDOWN)
    logger.info("xisu_checkin_all_retry finished!")

def checkin_all_xisu():
    global logger, updater
    try:
        backup_db()
    except:
        pass
    logger.info("xisu_checkin_all started!")
    for user in BUPTUser.select().where(BUPTUser.status == BUPTUserStatus.normal).prefetch(TGUser):
        ret_msg = ''
        try:
            ret = user.xisu_ncov_checkin()[:100]
            ret_msg = f"用户：`{user.username or user.cookie_eaisess or '[None]'}`\n自动晨午晚检成功！\n服务器返回：`{ret}`\n{datetime.datetime.now()}"
        except requests.exceptions.Timeout as e:
            ret_msg = f"用户：`{user.username or user.cookie_eaisess or '[None]'}`\n自动晨午晚检失败，服务器错误，将重试！\n`{e}`\n{datetime.datetime.now()}"
            traceback.print_exc()
        except Exception as e:
            ret_msg = f"用户：`{user.username or user.cookie_eaisess or '[None]'}`\n自动晨午晚检异常！\n服务器返回：`{e}`\n{datetime.datetime.now()}"
            traceback.print_exc()
        logger.info(ret_msg)
        updater.bot.send_message(chat_id=user.owner.userid, text=ret_msg, parse_mode = telegram.ParseMode.MARKDOWN)
    logger.info("xisu_checkin_all finished!")

def main():
    global updater, scheduler
    parser = argparse.ArgumentParser(description='BUPT 2019-nCoV Report Bot')
    parser.add_argument('--initdb', default=False, action='store_true')
    args = parser.parse_args()

    database = SqliteDatabase(config.SQLITE_DB_FILE_PATH)
    database_proxy.initialize(database)

    if args.initdb:
        db_init()
        exit(0)

    updater = Updater(TG_BOT_TOKEN, request_kwargs=TG_BOT_PROXY, use_context=True)
    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    dp.add_handler(MessageHandler(Filters.all, tg_debug_logging), -10)
    dp.add_handler(MessageHandler(Filters.all, tguser_check), -1)
    dp.add_handler(CommandHandler("start", start_entry))
    dp.add_handler(CommandHandler("help", help_entry))
    dp.add_handler(CommandHandler("list", list_entry))
    dp.add_handler(CommandHandler("add_by_uid", add_by_uid_entry))
    dp.add_handler(CommandHandler("add_by_cookie", add_by_cookie_entry))
    dp.add_handler(CommandHandler("checkin", checkin_entry))
    dp.add_handler(CommandHandler("checkinxisu", checkinxisu_entry))
    dp.add_handler(CommandHandler("pause", pause_entry))
    dp.add_handler(CommandHandler("resume", resume_entry))
    dp.add_handler(CommandHandler("remove", remove_entry))
    dp.add_handler(MessageHandler(Filters.regex(r'^/(remove|resume|pause|checkin|checkinxisu)_.*$'), text_command_entry))
    dp.add_handler(CommandHandler("checkinall", checkinall_entry))
    dp.add_handler(CommandHandler("checkinallxisu", checkinallxisu_entry))
    dp.add_handler(CommandHandler("listall", listall_entry))
    dp.add_handler(CommandHandler("status", status_entry))
    dp.add_handler(CommandHandler("sendmsg", send_message_entry))
    dp.add_handler(CommandHandler("broadcast", broadcast_entry))
    #dp.add_handler(MessageHandler(Filters.command, no_such_command),10)

    # on noncommand i.e message - echo the message on Telegram
    #dp.add_handler(MessageHandler(Filters.text, echo))

    # log all errors
    dp.add_error_handler(error_callback)

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.

    scheduler.add_job(
        func=checkin_all,
        id='checkin_all',
        trigger="cron",
        hour=CHECKIN_ALL_CRON_HOUR,
        minute=CHECKIN_ALL_CRON_MINUTE,
        max_instances=1,
        replace_existing=False,
        misfire_grace_time=10,
    )
    scheduler.add_job(
        func=checkin_all_retry,
        id='checkin_all_retry',
        trigger="cron",
        hour=CHECKIN_ALL_CRON_RETRY_HOUR,
        minute=CHECKIN_ALL_CRON_RETRY_MINUTE,
        max_instances=1,
        replace_existing=False,
        misfire_grace_time=10,
    )

    # xisu checkin noon cron job group
    scheduler.add_job(
        func=checkin_all_xisu,
        id='xisu_checkin_all_noon',
        trigger="cron",
        hour=XISU_CHECKIN_ALL_CRON_NOON_HOUR,
        minute=XISU_CHECKIN_ALL_CRON_NOON_MINUTE,
        max_instances=1,
        replace_existing=False,
        misfire_grace_time=10,
    )
    scheduler.add_job(
        func=checkin_all_xisu_retry,
        id='xisu_checkin_all_noon_retry',
        trigger="cron",
        hour=XISU_CHECKIN_ALL_CRON_NOON_RETRY_HOUR,
        minute=XISU_CHECKIN_ALL_CRON_NOON_RETRY_MINUTE,
        max_instances=1,
        replace_existing=False,
        misfire_grace_time=10,
    )

    # xisu checkin night cron job group
    scheduler.add_job(
        func=checkin_all_xisu,
        id='xisu_checkin_all_night',
        trigger="cron",
        hour=XISU_CHECKIN_ALL_CRON_NIGHT_HOUR,
        minute=XISU_CHECKIN_ALL_CRON_NIGHT_MINUTE,
        max_instances=1,
        replace_existing=False,
        misfire_grace_time=10,
    )
    scheduler.add_job(
        func=checkin_all_xisu_retry,
        id='xisu_checkin_all_night_retry',
        trigger="cron",
        hour=XISU_CHECKIN_ALL_CRON_NIGHT_RETRY_HOUR,
        minute=XISU_CHECKIN_ALL_CRON_NIGHT_RETRY_MINUTE,
        max_instances=1,
        replace_existing=False,
        misfire_grace_time=10,
    )

    scheduler.start()
    logger.info(["name: %s, trigger: %s, handler: %s, next: %s" % (job.name, job.trigger, job.func, job.next_run_time) for job in scheduler.get_jobs()])

    updater.idle()


if __name__ == "__main__":
    logging.basicConfig(
        handlers=[
            logging.handlers.TimedRotatingFileHandler(
                "log/main", when='midnight', backupCount=30, encoding='utf-8',
                atTime=datetime.time(hour=0, minute=0)
            ),
            logging.StreamHandler(sys.stdout)
        ],
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    logger = logging.getLogger(__name__)

    scheduler = BackgroundScheduler(timezone=CRON_TIMEZONE)

    main()
