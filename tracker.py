import json
import os
import logging
import requests

STATS_FILE = 'stats.json'
logger = logging.getLogger(__name__)

def load_state():
    if os.path.exists(STATS_FILE):
        try:
            with open(STATS_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return {
        'w': 0, 'l': 0, 'd': 0, 'bets': 0,
        'streak': 0, 'best_w': 0, 'best_l': 0,
        'active_bet': None
    }

def save_state(state):
    with open(STATS_FILE, 'w') as f:
        json.dump(state, f, indent=4)

def format_stats(state):
    w, l, d, bets = state['w'], state['l'], state['d'], state['bets']
    streak, best_w, best_l = state['streak'], state['best_w'], state['best_l']
    hit_rate = (w / bets * 100) if bets > 0 else 0.0
    return f"📊 W{w} / L{l} / D{d} | Bets: {bets} | Hit: {hit_rate:.1f}% | Streak: {streak} | BestW: {best_w} | BestL: {best_l}"

def get_finished_games(sport_id, pages=3):
    """Fetch finished games across multiple pages to avoid missing the target game."""
    results = []
    for page in range(1, pages + 1):
        url = f"https://inforadar.live/api/v1/finished_games/?sport_id={sport_id}&page={page}&per_page=100"
        try:
            r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
            data = r.json()
            if isinstance(data, dict):
                page_results = data.get('results', [])
                results.extend(page_results)
                # Stop early if this page had fewer than 100 results (last page)
                if len(page_results) < 100:
                    break
            elif isinstance(data, list):
                results.extend(data)
                break
        except Exception as e:
            logger.error(f"Error fetching finished games page {page}: {e}")
            break
    return results

def check_active_bet(state):
    bet = state.get('active_bet')
    if not bet:
        return None

    target_id = str(bet['event_id'])
    sport_name = bet['sport'].lower()
    sport_id = 1 if sport_name == 'soccer' else 18

    logger.info(f"Checking settlement for event_id={target_id} ({bet['match']})")
    finished_games = get_finished_games(sport_id)
    logger.info(f"Fetched {len(finished_games)} finished games for sport_id={sport_id}")

    for game in finished_games:
        game_id = str(game.get('id', ''))
        if game_id == target_id:
            scores = game.get('scores', '0-0').split('-')
            try:
                total_score = int(scores[0]) + int(scores[1])
                logger.info(f"Match found! Final score: {game.get('scores')} -> total={total_score}")
                return resolve_bet(state, bet, total_score)
            except Exception as e:
                logger.error(f"Error parsing score: {e}")
                return None

    logger.info(f"event_id={target_id} not found in finished games yet.")
    return None

def resolve_bet(state, bet, total_score):
    line = float(bet['line'])
    type_ = bet['type']

    result = 'Push'
    if type_ == 'Over':
        if total_score > line: result = 'Win'
        elif total_score < line: result = 'Loss'
    elif type_ == 'Under':
        if total_score < line: result = 'Win'
        elif total_score > line: result = 'Loss'

    # Update stats
    state['bets'] += 1
    if result == 'Win':
        state['w'] += 1
        state['streak'] = state['streak'] + 1 if state['streak'] > 0 else 1
        state['best_w'] = max(state['best_w'], state['streak'])
    elif result == 'Loss':
        state['l'] += 1
        state['streak'] = state['streak'] - 1 if state['streak'] < 0 else -1
        state['best_l'] = min(state['best_l'], state['streak'])
    else:
        state['d'] += 1
        # push doesn't affect streak

    state['active_bet'] = None
    save_state(state)

    return {
        'result': result,
        'match': bet['match'],
        'line': line,
        'type': type_,
        'total_score': total_score,
        'stats_str': format_stats(state)
    }

def lock_bot_with_bet(state, bet_info):
    state['active_bet'] = bet_info
    save_state(state)
