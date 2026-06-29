import requests
import json
import hmac
import hashlib

api_url = "http://localhost:8080"
user_id = "f9e49f0b-1db3-4507-922b-0bb090ea0bb8"
ingest_token = "nxq_hmac_secret_token_123456789"

payload = {
    "kind": "heartbeat",
    "user_id": user_id,
    "payload": {
        "is_running": True,
        "broker_type": "binance",
        "testnet": True
    }
}

body_str = json.dumps(payload, separators=(',', ':'))
signature = hmac.new(
    ingest_token.encode('utf-8'),
    body_str.encode('utf-8'),
    hashlib.sha256
).hexdigest()

headers = {
    "Content-Type": "application/json",
    "x-user-id": user_id,
    "x-signature": signature
}

url = f"{api_url}/api/public/ingest"
try:
    response = requests.post(url, data=body_str, headers=headers, timeout=10)
    print(f"Status Code: {response.status_code}")
    print(f"Response Headers: {dict(response.headers)}")
    print(f"Response Body: {response.text}")
except Exception as e:
    print(f"Error connecting: {e}")
