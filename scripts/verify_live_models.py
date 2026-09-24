import requests

api_url = "https://w6qubbix87.execute-api.ap-south-1.amazonaws.com"
headers = {"X-API-Key": "prometheus-admin", "Content-Type": "application/json"}

policy = requests.get(f"{api_url}/api/v1/policies", headers=headers).json()["policy"]
allowed = policy.get("allowed_models", [])

print(f"Testing {len(allowed)} allowed models...")
results = {}

for m in allowed:
    try:
        r = requests.post(f"{api_url}/api/v1/chat", json={"query": "Hello", "model": m}, headers=headers, timeout=12)
        results[m] = r.status_code
        print(f"{m} -> {r.status_code}")
    except Exception as e:
        results[m] = str(e)
        print(f"{m} -> {e}")

live_working = [m for m, s in results.items() if s == 200]
print("\n=============================")
print(f"LIVE 200 OK MODELS ({len(live_working)}):")
for m in sorted(live_working):
    print(f'    "{m}",')
print(f"\nNOT 200 ({len(results) - len(live_working)}):")
for m, s in results.items():
    if s != 200:
        print(f"    {m}: {s}")
