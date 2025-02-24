import requests

def validate_google_token(token: str) -> [bool, dict]:
    url = f"https://www.googleapis.com/oauth2/v3/tokeninfo?access_token={token}"
    response = requests.get(url)
    if response.status_code != 200: return False, {}
    response_data = response.json()
    return True, response_data


def get_username_from_email(email: str) -> str:
    return email.split("@")[0]