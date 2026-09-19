import json
import requests

MATCH_ID = "m_019qHk"

url = f"https://api.pitchapi.dev/v1/matches/{MATCH_ID}/events"

# Usamos la misma forma de autenticación que ya venís usando
# en tus scripts de PitchAPI.
API_KEY = "pk_test_QWMXbKvU6nK1x81cECn-kK4ePC781lEMFjyftvALsdI"

response = requests.get(
    url,
    headers={
        "X-API-KEY": API_KEY
    },
    timeout=30
)

print("Status:", response.status_code)
print()

try:
    data = response.json()

    print(
        json.dumps(
            data,
            ensure_ascii=False,
            indent=2
        )
    )

except Exception:
    print(response.text)