from include import *
from peewee import SqliteDatabase
import argparse, traceback, sys, datetime
from shutil import copyfile

from apscheduler.schedulers.background import BackgroundScheduler

from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
import telegram

def tguser_check(update, context):
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
    help_text='''
自动签到时间：每日0点5分
请在使用本 bot 前，确保已经正确提交过一次上报。
本 bot 的目标签到系统为：[app.bupt.edu.cn/ncov/...](https://app.bupt.edu.cn/ncov/wap/default/index)

/list
  列出所有签到用户
/checkin
  立即执行签到

/add\_by\_uid `用户名/学号` `密码` 
  用户信息为统一身份认证 UIS 系统
  通过用户名与密码添加签到用户
  **建议您[修改密码](https://auth.bupt.edu.cn/authserver/passwordChange.do)为随机密码后再进行本操作**
  例：/add\_by\_uid `2010211000 password123`

/add\_by\_cookie `eai-sess` `UUKey`
  通过[签到网站](https://app.bupt.edu.cn/ncov/wap/default/index) Cookie 信息添加用户 (eai-sess, UUKey)
  *如果您不明白这是什么，请使用上一条命令添加用户*
  例：/add\_by\_cookie `1cmgkrrcssge6edkkg3ucigj1m 44f522350f5e843fbac58b726753eb36`

/resume [id] ...
  （默认启用）
  恢复一个或全部签到用户的自动签到，未指定 id 则为全部
/pause [id] ...
  暂停一个或全部签到用户的自动签到，未指定 id 则为全部
/remove /all
/remove [id] ...
  删除一个或全部签到用户，指定 id，或使用 all 操作全部
    
以上功能的单用户操作正在开发中 #SOON

工作原理与位置变更须知：
从网页上获取上一次成功签到的数据，处理后再次提交。
因此，如果您改变了城市（如返回北京），请先使用 /pause 暂停自动签到，并 **【连续两天】** 手动签到成功后，再使用 /resume 恢复自动签到。
'''
    update.message.reply_markdown(help_text.strip(), disable_web_page_preview=True)

def list_entry(update, context, admin_all=False):
    first_message = update.message.reply_markdown(f"Working ...")
    if admin_all == True:
        users = BUPTUser.select().where(BUPTUser.status == BUPTUserStatus.normal)
    else:
        # users = BUPTUser.select().where(BUPTUser.owner == update.message.from_user.id).order_by(BUPTUser.id.asc())
        tguser = TGUser.get(
            userid = update.message.from_user.id
        )
        users = tguser.buptusers.where(BUPTUser.status != BUPTUserStatus.removed)
    ret_msg = ''
    for i, user in enumerate(users):
        ret_msg += f'ID: `{i+1}`\n'
        if user.username != None:
            ret_msg += f'Username: `{user.username}`\n' #Password: `{user.password}`\n'
        else:
            ret_msg += f'eai-sess: `{user.cookie_eaisess}`\n' #UUKey: `{user.cookie_uukey}`\n'
        if user.status == BUPTUserStatus.normal:
            ret_msg += f'自动签到: `启用`\n'
        else:
            ret_msg += f'自动签到: `暂停`\n'
        if user.latest_response_data == None:
            ret_msg += '从未尝试签到\n'
        else:
            ret_msg += f'最后签到时间: `{user.latest_response_time}`\n'
            ret_msg += f'最后签到返回: `{user.latest_response_data}`\n'
        ret_msg += "\n"
    if len(ret_msg) == 0:
        ret_msg = '用户列表为空'
    logger.debug(ret_msg)
    first_message.edit_text(ret_msg, parse_mode = telegram.ParseMode.MARKDOWN)
    

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

def checkin_entry(update, context):
    specified_checkin_target = len(context.args) > 0 # checkin for multiple accounts
    checkin_targets = []

    if specified_checkin_target:
        checkin_targets = list(map(int, context.args))
        # opid = context.args[0]
        # raise NotImplementedError('单个签到功能当前未实现')

    tguser = TGUser.get(
        userid = update.message.from_user.id
    )

    available_targets = tguser.buptusers.where(BUPTUser.status != BUPTUserStatus.removed)
    pending_targets = []

    if not specified_checkin_target:
        pending_targets = available_targets
    else:
        pending_targets = [available_targets[i-1] for i in checkin_targets]

    if tguser.buptusers.where(BUPTUser.status != BUPTUserStatus.removed).count() == 0:
        ret_msg = '用户列表为空'
        update.message.reply_markdown(ret_msg)
        return
    for buptuser in pending_targets:
        try:
            ret = buptuser.ncov_checkin(force=True)
            ret_msg = f"用户：`{buptuser.username or buptuser.cookie_eaisess or '[None]'}`\n签到成功！\n服务器返回：`{ret}`"
        except Exception as e:
            ret_msg = f"用户：`{buptuser.username or buptuser.cookie_eaisess or '[None]'}`\n签到失败！\n{e}"
        update.message.reply_markdown(ret_msg)

def pause_entry(update, context):
    specified_pause_target = len(context.args) > 0 # checkin for multiple accounts
    pause_targets = []
    if specified_pause_target:
        pause_targets = list(map(int, context.args))
    tguser = TGUser.get(
        userid = update.message.from_user.id
    )

    available_targets = tguser.buptusers.where(BUPTUser.status != BUPTUserStatus.removed)
    pending_targets = []

    if not specified_pause_target:
        pending_targets = available_targets
    else:
        pending_targets = [available_targets[i-1] for i in pause_targets]

    for buptuser in pending_targets:
        buptuser.status = BUPTUserStatus.stopped
        buptuser.save()
        ret_msg = f"用户：`{buptuser.username or buptuser.cookie_eaisess or '[None]'}`\n已暂停自动签到。"
        update.message.reply_markdown(ret_msg)

def resume_entry(update, context):
    specified_resume_target = len(context.args) > 0 # checkin for multiple accounts
    resume_targets = []
    if specified_resume_target:
        resume_targets = list(map(int, context.args))
    tguser = TGUser.get(
        userid = update.message.from_user.id
    )

    available_targets = tguser.buptusers.where(BUPTUser.status != BUPTUserStatus.removed)
    pending_targets = []

    if not specified_resume_target:
        pending_targets = available_targets
    else:
        pending_targets = [available_targets[i-1] for i in resume_targets]

    for buptuser in pending_targets:
        buptuser.status = BUPTUserStatus.normal
        buptuser.save()
        ret_msg = f"用户：`{buptuser.username or buptuser.cookie_eaisess or '[None]'}`\n已启用自动签到。"
        update.message.reply_markdown(ret_msg)

def remove_entry(update, context):
    assert len(context.args) > 0, "错误的命令，请用 /help 查看使用帮助。"
    specified_remove_target = not context.args[0].lower() == '/all'
    remove_targets = []
    if specified_remove_target:
        remove_targets = list(map(int, context.args))
    tguser = TGUser.get(
        userid = update.message.from_user.id
    )

    available_targets = tguser.buptusers.where(BUPTUser.status != BUPTUserStatus.removed)
    pending_targets = []

    if not specified_remove_target:
        pending_targets = available_targets
    else:
        pending_targets = [available_targets[i-1] for i in remove_targets]

    for buptuser in pending_targets:
        buptuser.status = BUPTUserStatus.removed
        buptuser.save()
        ret_msg = f"用户：`{buptuser.username or buptuser.cookie_eaisess or '[None]'}`\n已删除。"
        update.message.reply_markdown(ret_msg)

def error_callback(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s: %s"', update, context.error.__class__.__name__, context.error)
    update.message.reply_text("{}: {}".format(context.error.__class__.__name__,context.error))
    traceback.print_exc()

def tg_debug_logging(update,context):
    log_str = 'User %s %d: "%s"' % (update.message.from_user.username, update.message.from_user.id, update.message.text)
    logger.info(log_str)
    if update.message.from_user.id != TG_BOT_MASTER :
        updater.bot.send_message(chat_id=TG_BOT_MASTER, text="[LOG] "+ log_str)

def checkinall_entry(update, context):
    assert update.message.from_user.id == TG_BOT_MASTER
    checkin_all()

def listall_entry(update, context):
    assert update.message.from_user.id == TG_BOT_MASTER
    list_entry(update,context,admin_all=True)

def status_entry(update, context):
    assert update.message.from_user.id == TG_BOT_MASTER
    cron_data = "\n".join(["name: %s, trigger: %s, handler: %s, next: %s" % (job.name, job.trigger, job.func, job.next_run_time) for job in scheduler.get_jobs()])
    update.message.reply_text("Cronjob: " + cron_data)
    update.message.reply_text("System time: " + str(datetime.datetime.now()))

def backup_db():
    logger.info("backup started!")
    copyfile('./my_app.db', './backup/my_app.{}.db'.format(str(datetime.datetime.now()).replace(":","").replace(" ","_")))
    logger.info("backup finished!")

def checkin_all():
    try:
        backup_db()
    except:
        pass
    logger.info("checkin_all started!")
    for user in BUPTUser.select().where(BUPTUser.status == BUPTUserStatus.normal).prefetch(TGUser):
        ret_msg = ''
        try:
            ret = user.ncov_checkin()
            ret_msg = f"用户：`{user.username or user.cookie_eaisess or '[None]'}`\n自动签到成功！\n服务器返回：`{ret}`\n{datetime.datetime.now()}"
        except Exception as e:
            ret_msg = f'错误！\n{e}\n{datetime.datetime.now()}'
            traceback.print_exc()
        logger.debug(ret_msg)
        updater.bot.send_message(chat_id=user.owner.userid, text=ret_msg, parse_mode = telegram.ParseMode.MARKDOWN)
    logger.info("checkin_all finished!")

def main():
    global updater, scheduler
    parser = argparse.ArgumentParser(description='BUPT 2019-nCoV Report Bot')
    parser.add_argument('--initdb', default=False, action='store_true')
    args = parser.parse_args()
    
    database = SqliteDatabase('my_app.db')
    database_proxy.initialize(database)

    if args.initdb:
        db_init()
        exit(0)

    scheduler.add_job(func=checkin_all, id='checkin_all', trigger="cron", hour=0, minute=5, max_instances=1, replace_existing=False)
    scheduler.start()
    print(["name: %s, trigger: %s, handler: %s, next: %s" % (job.name, job.trigger, job.func, job.next_run_time) for job in scheduler.get_jobs()])

    updater = Updater(TG_BOT_TOKEN, request_kwargs=TG_BOT_PROXY, use_context=True)
    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    # dp.add_handler(MessageHandler(Filters.all, tg_debug_logging), -10)
    dp.add_handler(MessageHandler(Filters.all, tguser_check), -1)
    dp.add_handler(CommandHandler("start", start_entry))
    dp.add_handler(CommandHandler("help", help_entry))
    dp.add_handler(CommandHandler("list", list_entry))
    dp.add_handler(CommandHandler("add_by_uid", add_by_uid_entry))
    dp.add_handler(CommandHandler("add_by_cookie", add_by_cookie_entry))
    dp.add_handler(CommandHandler("checkin", checkin_entry))
    dp.add_handler(CommandHandler("pause", pause_entry))
    dp.add_handler(CommandHandler("resume", resume_entry))
    dp.add_handler(CommandHandler("remove", remove_entry))
    dp.add_handler(CommandHandler("checkinall", checkinall_entry))
    dp.add_handler(CommandHandler("listall", listall_entry))
    dp.add_handler(CommandHandler("status", status_entry))
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
    updater.idle()


if __name__ == "__main__":
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
        level=logging.DEBUG, 
        filename=f'log/{str(datetime.datetime.now()).replace(":","").replace(" ","_")}.log'
    )
    logger = logging.getLogger(__name__)

    sh = logging.StreamHandler(sys.stdout)
    sh.setLevel(logging.DEBUG)
    logger.addHandler(sh)

    scheduler = BackgroundScheduler()
    
    main()
