import requests
import time

def get_live_games(sport_id):
    url = f"https://inforadar.live/api/v1/live_games?sport_id={sport_id}&page=1&per_page=100"
    try:
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        data = r.json()
        if data.get("success") == 1:
            return data.get("results", [])
    except Exception as e:
        print(f"Error fetching live games for sport {sport_id}: {e}")
    return []

def get_game_odds(sport_name, event_id):
    url = f"https://inforadar.live/api/v1/{sport_name}/game/odds?event_id={event_id}&odds_market=8,5,6,1,2,3,4"
    try:
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        return r.json()
    except Exception as e:
        print(f"Error fetching odds for {event_id}: {e}")
    return []

def is_standard_line(line_val):
    try:
        val = float(line_val)
        return (val * 100) % 50 == 0 # 1.5, 2.0, 2.5 etc. Avoid 2.25, 2.75
    except:
        return False

def check_dropping_odds(odds_list, threshold=0.2):
    # odds_list is assumed to be sorted descending by time (newest first), which is typical for this API
    # Let's group by line (row2)
    lines = {}
    for entry in odds_list:
        line = entry.get('row2')
        if line is None or not is_standard_line(line):
            continue
            
        line_val = float(line)
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
                best_drop_val = drop_over
                best_drop = {
                    'line': line_val,
                    'type': 'Over',
                    'opening': open_over,
                    'current': curr_over,
                    'drop': drop_over
                }
                
            if drop_under >= threshold and drop_under > best_drop_val:
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

def scan_games():
    alerts = []
    sports = {1: 'soccer', 18: 'basketball'}
    
    for sport_id, sport_name in sports.items():
        games = get_live_games(sport_id)
        for game in games:
            event_id = game.get('id')
            home = game.get('home', {}).get('name', 'Unknown')
            away = game.get('away', {}).get('name', 'Unknown')
            score = game.get('scores', '0-0')
            time_obj = game.get('time', {})
            game_time = time_obj.get('tm', 0)
            
            odds_data = get_game_odds(sport_name, event_id)
            if not isinstance(odds_data, list):
                continue
                
            for market in odds_data:
                if market.get('name') == 'Total':
                    history = market.get('odds', [])
                    drop = check_dropping_odds(history)
                    if drop:
                            alerts.append({
                                'event_id': event_id,
                                'sport': sport_name,
                                'match': f"{home} vs {away}",
                                'score': score,
                                'time': f"{game_time}'",
                                'drop_info': drop
                            })
    return alerts

if __name__ == "__main__":
    print(scan_games())
