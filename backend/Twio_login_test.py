import requests

# API endpoint
url = "https://api.twitterapi.io/twitter/user_login_v2"

# Replace the <placeholders> with your real data
payload = {
    "user_name": "",   X username
    "email": "",      # the email tied to your Twitter account
    "password": "",       # your Twitter password
    "totp_secret": "",                      # only if you use 2FA (leave empty if not)
    "proxy": "http://fyteiwgh:dlxh5x285kg7@23.95.150.145:6114
"                             # e.g. "http://user:pass@host:port" (leave "" if not needed)
}

headers = {
    "X-API-Key": "your_api_key_here",       # your API key from twitterapi.io
    "Content-Type": "application/json"
}

# Make the request
try:
    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()  # raise error if status != 200
    print("Response JSON:")
    print(response.json())
except requests.exceptions.HTTPError as http_err:
    print(f"HTTP error: {http_err}")
    print(response.text)
except Exception as e:
    print(f"Error: {e}")
