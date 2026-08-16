import requests
import time

import random

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1'
]

def get_live_games(sport_id):
    url = f"https://inforadar.live/api/v1/live_games?sport_id={sport_id}&page=1&per_page=100"
    for attempt in range(3):
        try:
            ua = random.choice(USER_AGENTS)
            r = requests.get(url, headers={'User-Agent': ua, 'Accept': 'application/json, text/plain, */*'}, timeout=30)
            data = r.json()
            if data.get("success") == 1:
                return data.get("results", [])
        except requests.exceptions.Timeout:
            time.sleep(2) # Wait a bit before retrying
        except Exception as e:
            print(f"Error fetching live games for sport {sport_id}: {e}")
            break
    return []

def get_game_odds(sport_name, event_id):
    url = f"https://inforadar.live/api/v1/{sport_name}/game/odds?event_id={event_id}&odds_market=8,5,6,1,2,3,4"
    for attempt in range(2):
        try:
            ua = random.choice(USER_AGENTS)
            r = requests.get(url, headers={'User-Agent': ua, 'Accept': 'application/json, text/plain, */*'}, timeout=15)
            return r.json()
        except requests.exceptions.Timeout:
            time.sleep(1) # Wait a bit before retrying
        except Exception as e:
            print(f"Error fetching odds for {event_id}: {e}")
            break
    return []

def is_standard_line(line_val):
    try:
        val = float(line_val)
        return (val * 100) % 50 == 0 # 1.5, 2.0, 2.5 etc. Avoid 2.25, 2.75
    except:
        return False

def get_total_score(score_str):
    try:
        parts = score_str.split('-')
        return int(parts[0]) + int(parts[1])
    except:
        return 0

def check_dropping_odds(odds_list, current_total_score, threshold=0.2):
    # odds_list is assumed to be sorted descending by time (newest first), which is typical for this API
    # Let's group by line (row2)
    lines = {}
    for entry in odds_list:
        line = entry.get('row2')
        if line is None or not is_standard_line(line):
            continue
            
        line_val = float(line)
        # Skip mathematically impossible or already resolved lines
        if line_val <= current_total_score:
            continue

        if line_val not in lines:
            lines[line_val] = []
        lines[line_val].append(entry)
        
    best_drop = None
    best_drop_val = 0
    
    for line_val, history in lines.items():
        if len(history) < 2:
            continue
            
        # First element is newest, last element is oldest
        current = history[0]
        opening = history[-1]
        
        try:
            curr_over = float(current.get('row1', 0))
            curr_under = float(current.get('row3', 0))
            open_over = float(opening.get('row1', 0))
            open_under = float(opening.get('row3', 0))
            
            drop_over = open_over - curr_over if open_over > 0 and curr_over > 0 else 0
            drop_under = open_under - curr_under if open_under > 0 and curr_under > 0 else 0
            
            if drop_over >= threshold and drop_over > best_drop_val:
                if 1.80 <= curr_over <= 2.10:
                    best_drop_val = drop_over
                    best_drop = {
                        'line': line_val,
                        'type': 'Over',
                        'opening': open_over,
                        'current': curr_over,
                        'drop': drop_over
                    }
                
            if drop_under >= threshold and drop_under > best_drop_val:
                if 1.80 <= curr_under <= 2.10:
                    best_drop_val = drop_under
                    best_drop = {
                        'line': line_val,
                        'type': 'Under',
                        'opening': open_under,
                        'current': curr_under,
                        'drop': drop_under
                    }
        except:
            pass
            
    return best_drop

# Time limits – only alert when a bet can realistically still be placed
# Soccer    : game_time must be <= MAX_SOCCER_MINUTE
# Basketball: time_obj['md'] is the quarter (1-4), alert only up to Q3
MAX_SOCCER_MINUTE  = 75
MAX_BASKETBALL_QTR = 3

def is_time_ok(sport_name, time_obj):
    """Return True only if there is enough game time left to place a bet."""
    if sport_name == 'soccer':
        minute = int(time_obj.get('tm', 0) or 0)
        return minute <= MAX_SOCCER_MINUTE
    elif sport_name == 'basketball':
        quarter = int(time_obj.get('md', 0) or 0)
        return quarter <= MAX_BASKETBALL_QTR
    return True

def scan_games():
    alerts = []
    sports = {1: 'soccer', 18: 'basketball'}
    
    for sport_id, sport_name in sports.items():
        games = get_live_games(sport_id)
        for game in games:
            event_id = game.get('id')
            home = game.get('home', {}).get('name', 'Unknown')
            away = game.get('away', {}).get('name', 'Unknown')
            league = game.get('league', {}).get('name', 'Unknown League')
            score = game.get('scores', '0-0')
            time_obj = game.get('time', {})
            game_time = time_obj.get('tm', 0)

            # Skip games that are too late to bet on
            if not is_time_ok(sport_name, time_obj):
                continue
            
            # Avoid hammering the API
            time.sleep(0.5)
            
            odds_data = get_game_odds(sport_name, event_id)
            if not isinstance(odds_data, list):
                continue
                
            for market in odds_data:
                if market.get('name') == 'Total':
                    history = market.get('odds', [])
                    current_total_score = get_total_score(score)
                    drop = check_dropping_odds(history, current_total_score)
                    if drop:
                            alerts.append({
                                'event_id': event_id,
                                'sport': sport_name,
                                'league': league,
                                'match': f"{home} vs {away}",
                                'score': score,
                                'time': f"{game_time}'",
                                'drop_info': drop
                            })
    return alerts

if __name__ == "__main__":
    print(scan_games())
