import smtplib
import os
from email.header import Header
from email.mime.text import MIMEText
from email.utils import formataddr
import requests
from datetime import datetime, timedelta, timezone
from loguru import logger

def format_push_message(all_results):
    content = ["### Bilibili 任务报告\n"]
    
    for result in all_results:
        user_info = result.get('user_info')
        if user_info:
            account_name = user_info['uname']
            content.append(f"--- \n#### 账号: {account_name} (Lv.{user_info['level_info']['current_level']})")
        else:
            account_name = f"账号 {result['account_index']}"
            content.append(f"--- \n#### {account_name}")

        for name, (success, message) in result['tasks'].items():
            status_icon = "✅" if success else "❌"
            reason = f" - {message}" if message else ""
            content.append(f"- **{name}**: {status_icon}{reason}")
            
        if user_info:
            content.append(f"- **硬币余额**: {user_info['money']}")
    
    beijing_time = datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M:%S')
    content.append(f"\n> 报告时间: {beijing_time}")
    
    return "\n".join(content)

def send_to_pushplus(token, title, content):
    url = "http://www.pushplus.plus/send"
    data = {"token": token, "title": title, "content": content, "template": "markdown"}
    try:
        res = requests.post(url, json=data)
        if res.json().get('code') == 200:
            logger.info('PushPlus 推送成功！')
        else:
            logger.error(f'PushPlus 推送失败: {res.json().get("msg", "未知错误")}')
    except Exception as e:
        logger.error(f'PushPlus 推送异常: {e}')


def send_to_email(title, content, sender=None, authcode=None, receiver=None, smtp_server='smtp.qq.com', smtp_port=465):
    """通过 SMTP 发送邮件（默认 QQ 邮箱，支持授权码）。

    参数均可从环境变量读取，方便在 GitHub Actions 中配置：
      SMTP_QQ_EMAIL     发件邮箱地址
      SMTP_QQ_AUTHCODE  发件邮箱 SMTP 授权码（16位）
      SMTP_TO_EMAIL     收件邮箱地址
      SMTP_SERVER       SMTP 服务器，默认 smtp.qq.com
      SMTP_PORT         SMTP 端口，默认 465
    """
    sender = sender or os.environ.get('SMTP_QQ_EMAIL')
    authcode = authcode or os.environ.get('SMTP_QQ_AUTHCODE')
    receiver = receiver or os.environ.get('SMTP_TO_EMAIL')
    smtp_server = os.environ.get('SMTP_SERVER') or smtp_server
    try:
        smtp_port = int(os.environ.get('SMTP_PORT') or smtp_port)
    except ValueError:
        smtp_port = 465

    if not sender or not authcode or not receiver:
        logger.error("邮件配置不完整：缺少 SMTP_QQ_EMAIL / SMTP_QQ_AUTHCODE / SMTP_TO_EMAIL，跳过邮件发送")
        return False

    # 将 Markdown 报告转为纯文本，便于邮件阅读
    plain_content = content.replace('### ', '').replace('#### ', '')
    msg = MIMEText(plain_content, 'plain', 'utf-8')
    msg['From'] = formataddr((str(Header('Bilibili 打卡', 'utf-8')), sender))
    msg['To'] = receiver
    msg['Subject'] = Header(title, 'utf-8')

    try:
        if smtp_port == 465:
            server = smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=15)
        else:
            server = smtplib.SMTP(smtp_server, smtp_port, timeout=15)
            server.starttls()
        server.login(sender, authcode)
        server.sendmail(sender, [receiver], msg.as_string())
        server.quit()
        logger.info(f'邮件发送成功 → {receiver}')
        return True
    except Exception as e:
        logger.error(f'邮件发送异常: {e}')
        return False