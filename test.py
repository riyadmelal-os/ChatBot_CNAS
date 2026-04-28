import requests

r = requests.post("http://localhost:8000/chat", json={"message": "retraite"})
print("Status:", r.status_code)
print("Answer:", r.json())