import os
import logging
import tempfile
import subprocess
from dotenv import load_dotenv
from telegram import Update, constants
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes
)
from openai import OpenAI
from gtts import gTTS

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

openai_client = OpenAI(api_key=OPENAI_API_KEY)

MAX_VIDEO_SIZE_MB = 50


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Salaan!\n\n"
        "Waxaan ahay bot turjumaada muqaalada.\n\n"
        "📹 *Sida loo isticmaalo:*\n"
        "1. Dir muqaal (video) oo drama ah\n"
        "2. Waxaan kuu samaynayaa:\n"
        "   ✅ Qoraalka ka soo saara\n"
        "   ✅ Af-Soomaali u tarjumaa\n"
        "   ✅ Cod Af-Soomaali ah kuu diraa\n\n"
        "📌 *Xusuusin:* Muqaalku waa inuu ka yar yahay 50MB\n\n"
        "Bilow hada! Dir muqaalkaa 🎬",
        parse_mode=constants.ParseMode.MARKDOWN
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🆘 *Caawimada:*\n\n"
        "/start - Bilow bot-ka\n"
        "/help - Caawimada\n\n"
        "📹 Dir muqaal drama ah\n"
        "Bot-ku wuxuu:\n"
        "1. Codka ka soo saari\n"
        "2. Qoraal English ah sameeyi\n"
        "3. Af-Soomaali u tarjumi\n"
        "4. Cod Af-Soomaali ah kuu diri\n\n"
        "⚠️ Muqaalku waa inuu ka yar yahay 50MB",
        parse_mode=constants.ParseMode.MARKDOWN
    )


def extract_audio(video_path: str, audio_path: str) -> bool:
    try:
        result = subprocess.run(
            [
                "ffmpeg", "-i", video_path,
                "-vn",
                "-acodec", "libmp3lame",
                "-ar", "16000",
                "-ac", "1",
                "-q:a", "4",
                "-y", audio_path
            ],
            capture_output=True, text=True, timeout=120
        )
        return result.returncode == 0
    except Exception as e:
        logger.error(f"Audio extraction error: {e}")
        return False


def transcribe_audio(audio_path: str) -> str | None:
    try:
        with open(audio_path, "rb") as audio_file:
            transcript = openai_client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="en",
                response_format="text"
            )
        return transcript.strip()
    except Exception as e:
        logger.error(f"Transcription error: {e}")
        return None


def translate_to_somali(english_text: str) -> str | None:
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Adiga waxaad tahay turjubaan xirfadleh oo Af-Soomaali ku takhasusay. "
                        "Turjum qoraalka English ah oo aad siinayo Af-Soomaali heer sare ah, "
                        "si dabiici ah oo macquul ah. Ha isticmaalin erayo adag ama qalaad. "
                        "Kaliya soo celi qoraalka la tarjumay, wax kale ha ku darin."
                    )
                },
                {
                    "role": "user",
                    "content": f"Turjum Af-Soomaali:\n\n{english_text}"
                }
            ],
            max_tokens=2000,
            temperature=0.3
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Translation error: {e}")
        return None


def text_to_speech(somali_text: str, output_path: str) -> bool:
    try:
        tts = gTTS(text=somali_text, lang="so", slow=False)
        tts.save(output_path)
        return True
    except Exception as e:
        logger.error(f"TTS error: {e}")
        return False


async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    video = message.video or message.document

    if not video:
        await message.reply_text("❌ Fadlan dir muqaal (video) ah.")
        return

    file_size_mb = video.file_size / (1024 * 1024)
    if file_size_mb > MAX_VIDEO_SIZE_MB:
        await message.reply_text(
            f"❌ Muqaalku waa weyn yahay ({file_size_mb:.1f}MB).\n"
            f"Xadka ugu badan waa {MAX_VIDEO_SIZE_MB}MB."
        )
        return

    status_msg = await message.reply_text("⏳ Muqaalka waan heli karaa... Sug!")

    with tempfile.TemporaryDirectory() as tmpdir:
        video_path = os.path.join(tmpdir, "video.mp4")
        audio_path = os.path.join(tmpdir, "audio.mp3")
        voice_path = os.path.join(tmpdir, "somali_voice.mp3")

        try:
            await status_msg.edit_text("📥 Muqaalka soo dejinayaa...")
            tg_file = await context.bot.get_file(video.file_id)
            await tg_file.download_to_drive(video_path)
        except Exception as e:
            logger.error(f"Download error: {e}")
            await status_msg.edit_text("❌ Muqaalka soo dejinta way fashilantay.")
            return

        await status_msg.edit_text("🎵 Codka ka soo saaraya...")
        if not extract_audio(video_path, audio_path):
            await status_msg.edit_text("❌ Codka ka soo saarta way fashilantay.")
            return

        await status_msg.edit_text("📝 Qoraalka ka samainayaa (Whisper)...")
        english_text = transcribe_audio(audio_path)
        if not english_text:
            await status_msg.edit_text("❌ Qoraalka ka samaintu way fashilantay.")
            return

        await status_msg.edit_text("🌍 Af-Soomaali u tarjumayaa...")
        somali_text = translate_to_somali(english_text)
        if not somali_text:
            await status_msg.edit_text("❌ Tarjumaada way fashilantay.")
            return

        await status_msg.edit_text("🔊 Cod Af-Soomaali ah samainayaa...")
        tts_ok = text_to_speech(somali_text, voice_path)

        await status_msg.edit_text("✅ Diyaar! Natiijooyinka kuu diraya...")

        await message.reply_text(
            f"📝 *Qoraalka English (Asalka):*\n\n{english_text}",
            parse_mode=constants.ParseMode.MARKDOWN
        )

        await message.reply_text(
            f"🇸🇴 *Tarjumaada Af-Soomaali:*\n\n{somali_text}",
            parse_mode=constants.ParseMode.MARKDOWN
        )

        if tts_ok and os.path.exists(voice_path):
            with open(voice_path, "rb") as voice_file:
                await message.reply_voice(
                    voice=voice_file,
                    caption="🔊 Cod Af-Soomaali ah"
                )
        else:
            await message.reply_text("⚠️ Codka la samayn kari waayo.")

        await status_msg.delete()


async def handle_other(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📹 Fadlan dir *muqaal* (video) drama ah!\n"
        "Waxaan turjumi karaa: Chinese, Korean, Turkish, iyo kuwa kale.\n\n"
        "Caawimaad u baahan? /help",
        parse_mode=constants.ParseMode.MARKDOWN
    )


def main():
    if not TELEGRAM_TOKEN:
        raise ValueError("TELEGRAM_TOKEN ma jirto .env file-ka!")
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY ma jirto .env file-ka!")

    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.VIDEO | filters.Document.VIDEO, handle_video))
    app.add_handler(MessageHandler(filters.ALL, handle_other))

    logger.info("✅ Bot-ka wuu bilaabmay!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
