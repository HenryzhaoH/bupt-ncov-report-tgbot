SQLITE_DB_FILE_PATH = 'my_app.db'

LOGIN_API = 'https://app.bupt.edu.cn/uc/wap/login/check'
REPORT_PAGE = 'https://app.bupt.edu.cn/ncov/wap/default/index'
REPORT_API = 'https://app.bupt.edu.cn/ncov/wap/default/save'
API_TIMEOUT = 20 # in seconds

XISU_REPORT_PAGE = 'https://app.bupt.edu.cn/site/ncov/xisudailyup'
XISU_HISTORY_DATA = 'https://app.bupt.edu.cn/xisuncov/wap/open-report/index'
XISU_REPORT_API = 'https://app.bupt.edu.cn/xisuncov/wap/open-report/save'

CRON_TIMEZONE = 'Asia/Shanghai'
CHECKIN_ALL_CRON_HOUR = 0
CHECKIN_ALL_CRON_MINUTE = 10
CHECKIN_ALL_CRON_RETRY_HOUR   = 0
CHECKIN_ALL_CRON_RETRY_MINUTE = 25

XISU_CHECKIN_ALL_CRON_NOON_HOUR = 12
XISU_CHECKIN_ALL_CRON_NOON_MINUTE = 10
XISU_CHECKIN_ALL_CRON_NOON_RETRY_HOUR = 12
XISU_CHECKIN_ALL_CRON_NOON_RETRY_MINUTE = 25

XISU_CHECKIN_ALL_CRON_NIGHT_HOUR = 18
XISU_CHECKIN_ALL_CRON_NIGHT_MINUTE = 10
XISU_CHECKIN_ALL_CRON_NIGHT_RETRY_HOUR = 18
XISU_CHECKIN_ALL_CRON_NIGHT_RETRY_MINUTE = 25

REASONABLE_LENGTH = 24

TG_BOT_PROXY = None # example: {'proxy_url': 'socks5h://127.0.0.1:1080/'}
TG_BOT_TOKEN = ""   # Bot Token
TG_BOT_MASTER = 0   # Master Telegram User ID

BOT_DEBUG = False

HELP_MARKDOWN='''
自动签到时间：每日0点10分
自动晨午晚检时间：每日12点10分、18点10分
请在使用本 bot 前，确保已经正确提交过一次上报。
本 bot 的目标签到系统为：[app.bupt.edu.cn/ncov/...](https://app.bupt.edu.cn/ncov/wap/default/index)
本 bot 的目标晨午晚检系统为：[app.bupt.edu.cn/site/...](https://app.bupt.edu.cn/site/ncov/xisudailyup)

/list
  列出所有签到用户
/checkin
  立即执行签到
/checkinxisu
  立即执行晨午晚检签到

/add\_by\_uid `用户名/学号` `密码` 
  用户信息为统一身份认证 UIS 系统
  通过用户名与密码添加签到用户
  **建议您[修改密码](https://auth.bupt.edu.cn/authserver/passwordChange.do)为随机密码后再进行本操作**
  例：/add\_by\_uid `2010211000 password123`

/add\_by\_cookie `eai-sess` `UUKey`
  通过[签到网站](https://app.bupt.edu.cn/ncov/wap/default/index) Cookie 信息添加用户 (eai-sess, UUKey)
  *如果您不明白这是什么，请使用上一条命令添加用户*
  例：/add\_by\_cookie `1cmgkrrcssge6edkkg3ucigj1m 44f522350f5e843fbac58b726753eb36`

工作原理与位置变更须知：
从网页上获取上一次成功签到的数据，处理后再次提交。
晨午晚检地理位置信息采取与原签到功能相同的数据。
因此，如果您改变了城市（如返回北京），请先使用 /pause 暂停自动签到，并 **【连续两天】** 手动签到成功后，再使用 /resume 恢复自动签到。
'''
