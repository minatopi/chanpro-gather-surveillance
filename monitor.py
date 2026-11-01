
import os
import requests

VERCEL_MONITOR_API = "chanpro-gather-management.vercel.app/api/monitor"
MONITOR_API_KEY = os.environ["MONITOR_API_KEY"]
TARGETS = [
    {"name": "chanpro-gather"},
    # {"name": "another-service"},
]

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "metrics.json")


# ─── データ読み込み ───
def load_existing_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


# ─── データ保存 ───
def save_data(data):
    temp_file = DATA_FILE + ".tmp"

    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    os.replace(temp_file, DATA_FILE)


# ─── Vercel監視API呼び出し ───
def check_target(name):
    try:
        response = requests.post(
            VERCEL_MONITOR_API,
            json={"name": name},
            headers={
                "Authorization": f"Bearer {MONITOR_API_KEY}"
            },
            timeout=15
        )

        response.raise_for_status()
        data = response.json()

        return (
            data.get("status_code"),
            data.get("response_time_ms"),
            data.get("is_up", False),
            data.get("error")
        )

    except requests.exceptions.RequestException as e:
        return None, None, False, str(e)


# ─── メイン処理 ───
def main():
    current_time = datetime.now(timezone.utc).isoformat()
    existing_data = load_existing_data()

    for target in TARGETS:
        name = target["name"]

        if name not in existing_data:
            existing_data[name] = {
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

        # Vercelから監視結果を取得
        status_code, response_time_ms, is_up, error_msg = check_target(name)

        # 統計更新
        stats["total_checks"] += 1

        if is_up:
            stats["success_checks"] += 1
        else:
            stats["failed_checks"] += 1

        stats["last_status"] = "UP" if is_up else "DOWN"
        stats["last_checked"] = current_time

        # 平均応答時間を更新
        if response_time_ms is not None:
            old_count = stats["total_checks"] - 1
            old_avg = stats["avg_response_time_ms"]

            stats["avg_response_time_ms"] = round(
                (old_avg * old_count + response_time_ms)
                / (old_count + 1),
                2
            )

        # 履歴を追加
        entry = {
            "timestamp": current_time,
            "status_code": status_code,
            "response_time_ms": response_time_ms,
            "is_up": is_up
        }

        if error_msg:
            entry["error"] = error_msg

        history.append(entry)

        # 最新100件だけ保持
        existing_data[name]["history"] = history[-100:]

        # 途中で停止しても結果を残せるよう都度保存
        save_data(existing_data)

        print(
            f"[{current_time}] {name}: "
            f"{'UP' if is_up else 'DOWN'} "
            f"({response_time_ms} ms)"
        )

    print(f"保存完了: {DATA_FILE}")


if __name__ == "__main__":
    main()
