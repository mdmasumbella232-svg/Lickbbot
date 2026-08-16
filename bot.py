import asyncio
import logging
from telegram import Bot
from scanner import scan_games

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = "8732520800:AAGGwFl59xIVKzr5XkGs8NVVWvipYX7E584"
CHAT_ID = "7200809630"

# Keep track of already alerted matches to avoid spamming the same match
# We will use a set of strings like "Soccer:Team A vs Team B:Over:2.5"
alerted_events = set()

async def run_bot():
    bot = Bot(token=TOKEN)
    logger.info("Bot started! Sending startup message...")
    try:
        await bot.send_message(chat_id=CHAT_ID, text="🤖 Prediction Bot is now online! Scanning for dropping odds in Over/Under markets...")
    except Exception as e:
        logger.error(f"Failed to send startup message. Check token and chat id: {e}")
        return

    while True:
        logger.info("Scanning games...")
        try:
            alerts = scan_games()
            for alert in alerts:
                sport = alert['sport']
                match = alert['match']
                score = alert['score']
                time_val = alert['time']
                drop_info = alert['drop_info']
                
                line = drop_info['line']
                type_ = drop_info['type']
                opening = drop_info['opening']
                current = drop_info['current']
                drop_amt = drop_info['drop']
                
                # Unique identifier for the alert
                alert_key = f"{sport}:{match}:{type_}:{line}"
                
                if alert_key not in alerted_events:
                    alerted_events.add(alert_key)
                    
                    msg = (
                        f"🚨 **Dropping Odds Alert!** 🚨\n\n"
                        f"🏆 **Sport:** {sport}\n"
                        f"⚽ **Match:** {match}\n"
                        f"⏱️ **Time:** {time_val} | Score: {score}\n\n"
                        f"📉 **Market:** Total {line} ({type_})\n"
                        f"🔓 **Opening Odds:** {opening:.2f}\n"
                        f"🔒 **Current Odds:** {current:.2f}\n"
                        f"🔻 **Drop:** {drop_amt:.2f}\n"
                    )
                    
                    await bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode='Markdown')
                    logger.info(f"Alert sent for {match}")
                    
        except Exception as e:
            logger.error(f"Error during scan: {e}")
            
        logger.info("Scan complete. Waiting for next cycle (3 minutes).")
        await asyncio.sleep(180) # 3 minutes

if __name__ == '__main__':
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        logger.info("Bot stopped.")
