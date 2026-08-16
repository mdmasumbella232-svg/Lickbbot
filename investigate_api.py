import requests
import json

def investigate():
    endpoints = {
        "soccer_odds": "https://inforadar.live/api/v1/soccer/game/odds?event_id=12384208&odds_market=8,5,6,1,2,3",
        "basketball_odds": "https://inforadar.live/api/v1/basketball/game/odds?event_id=12334349&odds_market=4,5,6,1,2,3"
    }

    results = {}
    for name, url in endpoints.items():
        try:
            r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
            results[name] = r.json()
        except Exception as e:
            results[name] = str(e)
            
    with open("api_odds_investigation.json", "w") as f:
        json.dump(results, f, indent=4)

if __name__ == "__main__":
    investigate()
