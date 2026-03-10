import requests
import uuid
import os

PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")

IMAGE_FOLDER = "static/images"

os.makedirs(IMAGE_FOLDER, exist_ok=True)

def fetch_image(query):

    url = "https://api.pexels.com/v1/search"

    headers = {
        "Authorization": PEXELS_API_KEY
    }

    params = {
        "query": query,
        "per_page": 1
    }

    r = requests.get(url, headers=headers, params=params)

    data = r.json()

    if not data["photos"]:
        return None

    img_url = data["photos"][0]["src"]["large"]

    img_data = requests.get(img_url).content

    filename = f"{uuid.uuid4()}.jpg"
    path = os.path.join(IMAGE_FOLDER, filename)

    with open(path, "wb") as f:
        f.write(img_data)

    return path