import imaplib
import email
import re
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = "8887237691:AAFzr8qivtOGhcCnSymPay8stJ3TUUGmqx8"

# ─── إيميلاتك مع باسورداتها ────────────────
EMAIL_ACCOUNTS = {
    "sambatest215@hotmail.com": "pmgqyqglgburnent",
    "user2@yourdomain.com": "pass2",
    "user3@yourdomain.com": "pass3",
    # أضف كمان...
}

IMAP_SERVER = "imap.hotmail.com"  # غيّره حسب مزودك
# ────────────────────────────────────────────

user_selected_email = {}  # {chat_id: email}

def get_latest_email(email_addr: str):
    """يدخل على الإيميل ويجيب آخر رسالة"""
    password = EMAIL_ACCOUNTS.get(email_addr)
    if not password:
        return None, "إيميل غير موجود في النظام"

    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(email_addr, password)
        mail.select("inbox")

        # آخر رسالة غير مقروءة
        _, data = mail.search(None, "UNSEEN")
        ids = data[0].split()

        if not ids:
            # لو ما في غير مقروءة، جيب آخر رسالة عموماً
            _, data = mail.search(None, "ALL")
            ids = data[0].split()

        if not ids:
            mail.logout()
            return None, "📭 ما في رسايل في الصندوق"

        # آخر رسالة
        _, msg_data = mail.fetch(ids[-1], "(RFC822)")
        msg = email.message_from_bytes(msg_data[0][1])

        sender  = msg["From"]
        subject = msg["Subject"] or "(بدون موضوع)"
        body    = ""

        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    body = part.get_payload(decode=True).decode(errors="ignore")
                    break
        else:
            body = msg.get_payload(decode=True).decode(errors="ignore")

        mail.logout()
        return {
            "from": sender,
            "subject": subject,
            "body": body[:2000]
        }, None

    except Exception as e:
        return None, f"خطأ: {str(e)}"

def extract_code(text: str):
    """يستخرج الكود من الرسالة (أرقام 4-8 خانات)"""
    codes = re.findall(r'\b\d{4,8}\b', text)
    return codes[0] if codes else None

# ─── أوامر البوت ───────────────────────────

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 أهلاً!\n\n"
        "📧 أرسل لي الإيميل اللي أعطاك إياه النظام\n"
        "وبعدها اكتب /code لما تبي الكود"
    )

async def handle_email_input(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """لما الزبون يرسل الإيميل"""
    chat_id = update.effective_chat.id
    text = update.message.text.strip().lower()

    # تحقق إنه إيميل
    if "@" not in text:
        return

    if text not in EMAIL_ACCOUNTS:
        await update.message.reply_text(
            "❌ هذا الإيميل غير موجود في النظام\n"
            "تأكد من الإيميل وأعد المحاولة"
        )
        return

    user_selected_email[chat_id] = text
    await update.message.reply_text(
        f"✅ تم!\n📧 إيميلك: `{text}`\n\n"
        f"بعد ما تسجل في الموقع اكتب /code وبيجيلك الكود",
        parse_mode="Markdown"
    )

async def get_code(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """يجيب الكود للزبون"""
    chat_id = update.effective_chat.id

    if chat_id not in user_selected_email:
        await update.message.reply_text("❌ أرسل لي الإيميل أول!")
        return

    email_addr = user_selected_email[chat_id]
    await update.message.reply_text("🔍 أجيب الكود...")

    result, error = get_latest_email(email_addr)

    if error:
        await update.message.reply_text(f"⚠️ {error}")
        return

    # حاول تستخرج الكود تلقائياً
    code = extract_code(result["body"])

    if code:
        await update.message.reply_text(
            f"✅ *الكود الخاص بك:*\n\n"
            f"🔢 `{code}`\n\n"
            f"📌 الموضوع: {result['subject']}",
            parse_mode="Markdown"
        )
    else:
        # لو ما لقى كود واضح، أرسل كامل الرسالة
        await update.message.reply_text(
            f"📨 *آخر رسالة:*\n\n"
            f"👤 من: {result['from']}\n"
            f"📌 {result['subject']}\n\n"
            f"{result['body']}",
            parse_mode="Markdown"
        )

async def clear(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """يمسح الإيميل المحفوظ"""
    chat_id = update.effective_chat.id
    user_selected_email.pop(chat_id, None)
    await update.message.reply_text("🗑️ تم المسح، أرسل إيميل جديد")

# ─── تشغيل ─────────────────────────────────

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("code", get_code))
    app.add_handler(CommandHandler("clear", clear))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_email_input))
    print("✅ البوت شغّال!")
    app.run_polling()

if __name__ == "__main__":
    main()
