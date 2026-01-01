import requests

response = requests.get("http://localhost:8000/health/database")
print(response.json())
