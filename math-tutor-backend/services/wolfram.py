import requests
import os
import re

def ask_wolfram(query: str) -> dict:
    wolfram_app_id = os.getenv("WOLFRAM_APP_ID")
    res = requests.get(
        "https://www.wolframalpha.com/api/v1/llm-api",
        params={"input": query, "appid": wolfram_app_id}
    )
    
    if res.status_code != 200:
        return None
    
    # parse image links ออกมา
    text = res.text
    image_links = re.findall(r'image: (https://\S+\.png)', text)
    
    return {
        "raw": text,
        "images": image_links
    }