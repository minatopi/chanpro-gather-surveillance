
import os
import requests

VERCEL_MONITOR_API = "chanpro-gather-management.vercel.app/api/monitor"
MONITOR_API_KEY = os.environ["MONITOR_API_KEY"]

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
