import os
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from google import genai

# Shid galka xogta sirta ah (.env)
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Hubi in furayaashu jiraan
if not all([TELEGRAM_TOKEN, GEMINI_API_KEY]):
    raise ValueError("Fadlan hubi TELEGRAM_TOKEN iyo GEMINI_API_KEY inay ku jiraan Variables-kaaga!")

# Shid diiwaanka khaladaadka (Logging)
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Shid Client-ka Google Gemini
gemini_client = genai.Client(api_key=GEMINI_API_KEY)

# 1. Amarka /start marka uu qofku bixiyo
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.effective_user.first_name
    await update.message.reply_text(
        f"Ksoo dhawaaw boowe {user_name}! 👋\n\n"
        f"Kani waa Bot-ka rasmiga ah ee **JF Jiice Films** [Gemini Only]. 🎬\n"
        f"Ii soo dir qoraalka (Script-ga) aad rabto inaan kuugu turjumno Af-Soomaali dabiici ah oo bilaash ah!"
    )

# 2. Turjumaadda Qoraalka ee Google Gemini
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_text = update.message.text
    
    processing_message = await update.message.reply_text("Sug yar boowe, Google Gemini ayaa tarjumaya... ⏳")
    
    try:
        # Google Gemini Turjumaad
        response = gemini_client.models.generate_content(
            model='gemini-1.5-flash',
            contents=f"Waxaad tahay turjumaan filimada koobbiya oo u turjuma Af-Soomaali aad u dabiici ah, xamaasad leh, oo dadka soo jiita. U turjum qoraalkan soo socda Af-Soomaali dabiici ah oo filimada lagu sharxo:\n\n{user_text}"
        )
        somali_text = response.text
        
        # U soo dir qoraalka la turjumay saaxiibkay
        await update.message.reply_text(f"📝 **Turjumaadda Af-Soomaaliga (Gemini):**\n\n{somali_text}", parse_mode="Markdown")
        
        # Masax fariintii "Sug yar"
        await processing_message.delete()

    except Exception as e:
        logger.error(f"Cilad ayaa dhacday: {e}")
        await update.message.reply_text(f"Raali ahoow boowe, cilad ayaa dhacday: {str(e)}")

# 3. Kicinta Mashiinka
def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("Bot-kii wuxuu u ordayaa si toos ah...")
    app.run_polling()

if __name__ == "__main__":
    main()
