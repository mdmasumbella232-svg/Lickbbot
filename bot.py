import asyncio
import logging
from telegram import Bot
from scanner import scan_games
import tracker

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
        state = tracker.load_state()
        
        if state['active_bet']:
            logger.info("Bot is locked. Checking if active bet has settled...")
            settlement = tracker.check_active_bet(state)
            if settlement:
                res_msg = (
                    f"✅ **Bet Settled: {settlement['result']}**\n\n"
                    f"⚽ {settlement['match']}\n"
                    f"Final Total Score: {settlement['total_score']} (Line was {settlement['line']} {settlement['type']})\n\n"
                    f"{settlement['stats_str']}"
                )
                try:
                    await bot.send_message(chat_id=CHAT_ID, text=res_msg, parse_mode='Markdown')
                except Exception as e:
                    logger.error(f"Error sending settlement msg: {e}")
            else:
                logger.info("Bet not settled yet.")
            
            await asyncio.sleep(180)
            continue
            
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
                    
                    
                    dashboard_url = f"https://inforadar.live/#/dashboard/{sport.lower()}/game/{alert['event_id']}"
                    
                    msg = (
                        f"🚨 **Dropping Odds Alert!** 🚨\n\n"
                        f"🏆 **Sport:** {sport}\n"
                        f"⚽ **Match:** {match}\n"
                        f"⏱ Time: {time_val}  |  Score: {score}\n\n"
                        f"📉 **Market:** Total {line} ({type_})\n"
                        f"🔓 **Opening Odds:** {opening:.2f}\n"
                        f"🔒 **Current Odds:** {current:.2f}\n"
                        f"🔻 **Drop:** {drop_amt:.2f}\n\n"
                        f"🔗 [Open Match]({dashboard_url}), Status: Bot is locked. No new picks until this bet settles.\n\n"
                        f"{tracker.format_stats(state)}"
                    )
                    
                    try:
                        await bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode='Markdown', disable_web_page_preview=True)
                        logger.info(f"Alert sent for {match}")
                        tracker.lock_bot_with_bet(state, {
                            'event_id': alert['event_id'],
                            'sport': sport,
                            'match': match,
                            'line': line,
                            'type': type_
                        })
                        break # Exit scanning loop, wait for next cycle to check settlement
                    except Exception as e:
                        logger.error(f"Error sending alert: {e}")
                    
        except Exception as e:
            logger.error(f"Error during scan: {e}")
            
        logger.info("Scan complete. Waiting for next cycle (3 minutes).")
        await asyncio.sleep(180) # 3 minutes

if __name__ == '__main__':
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        logger.info("Bot stopped.")
