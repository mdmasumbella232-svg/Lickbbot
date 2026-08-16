import json
import os
import requests

STATS_FILE = 'stats.json'

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

def get_finished_games(sport_id):
    url = f"https://inforadar.live/api/v1/finished_games/?sport_id={sport_id}&page=1&per_page=100"
    try:
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        return r.json()
    except Exception as e:
        print(f"Error fetching finished games: {e}")
        return []

def check_active_bet(state):
    bet = state.get('active_bet')
    if not bet:
        return None
        
    sport_id = 1 if bet['sport'].lower() == 'soccer' else 18
    finished_games = get_finished_games(sport_id)
    
    for game in finished_games:
        if str(game.get('id')) == str(bet['event_id']):
            scores = game.get('scores', '0-0').split('-')
            try:
                total_score = int(scores[0]) + int(scores[1])
                return resolve_bet(state, bet, total_score)
            except:
                pass
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
        # push doesn't affect streak usually

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
