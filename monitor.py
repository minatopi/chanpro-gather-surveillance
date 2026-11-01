import os
import json
import time
from datetime import datetime
import requests

# ─── 設定 ───
TARGETS = [
    {"name": "chanpro-gather", "url": "https://chanpro-gather.vercel.app/api/health?token=minato126"}
    # 必要に応じてここに対象を追加してください
]
DATA_FILE = "metrics.json"

def load_existing_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}
    return {}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def main():
    current_time = datetime.utcnow().isoformat() + "Z"
    existing_data = load_existing_data()

    for target in TARGETS:
        name = target["name"]
        url = target["url"]
        
        if name not in existing_data:
            existing_data[name] = {
                "config": {"url": url},
                "stats": {
                    "total_checks": 0,
                    "success_checks": 0,
                    "failed_checks": 0,
                    "avg_response_time_ms": 0.0,
                    "last_status": None,
                    "last_checked": None
                },
                "history": []
            }
        
        stats = existing_data[name]["stats"]
        history = existing_data[name]["history"]
        
        # 測定開始
        start_time = time.time()
        status_code = None
        response_time_ms = None
        is_up = False
        error_msg = None
        
        try:
            # タイムアウトは10秒に設定
            response = requests.get(url, timeout=10)
            status_code = response.status_code
            response_time_ms = round((time.time() - start_time) * 1000, 2)
            
            try:
                response_data = response.json()
                is_up = response_data.get("status") == "ok"
            except (ValueError, AttributeError):
                is_up = False
        except requests.exceptions.RequestException as e:
            response_time_ms = round((time.time() - start_time) * 1000, 2)
            is_up = False
            error_msg = str(e)
        
        # 統計データの更新
        stats["total_checks"] += 1
        if is_up:
            stats["success_checks"] += 1
        else:
            stats["failed_checks"] += 1
            
        stats["last_status"] = "UP" if is_up else "DOWN"
        stats["last_checked"] = current_time
        
        # 平均応答時間の再計算（今回の成功・失敗問わず計測できた時間で計算）
        total_checks = stats["total_checks"]
        prev_avg = stats["avg_response_time_ms"]
        stats["avg_response_time_ms"] = round(((prev_avg * (total_checks - 1)) + response_time_ms) / total_checks, 2)
        
        # 履歴の追加（データが肥大化しすぎないよう直近100件を保持）
        history_entry = {
            "timestamp": current_time,
            "status_code": status_code,
            "response_time_ms": response_time_ms,
            "is_up": is_up
        }
        if error_msg:
            history_entry["error"] = error_msg
            
        history.append(history_entry)
        if len(history) > 100:  # 必要に応じて件数は調整してください
            history.pop(0)

    save_data(existing_data)
    print(f"[{current_time}] Monitoring completed and saved to {DATA_FILE}")

if __name__ == "__main__":
    main()
