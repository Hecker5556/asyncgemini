import aiohttp, aiohttp_socks, json, base64, os
from PIL import Image
from datetime import datetime
import io
from typing import Literal
def get_connector(proxy: str):
    if proxy.startswith("https"):
        return aiohttp.TCPConnector()
    elif proxy.startswith("socks"):
        return aiohttp_socks.ProxyConnector.from_url(proxy)
async def gemini(prompt: str, apikey: str, proxy: str = None, image: str | bytes | io.BufferedReader = None, history: list[dict] = None, safety: Literal['none', 'low', 'medium', 'high'] = 'none'):
    """
    prompt (str): prompt to give [required]
    apikey (str): api key to use [get one here](https://makersuite.google.com/app/apikey) [required]
    proxy (str): proxy to use (ignore if you dont know) [optional]
    image (str | bytes | io.BufferedReader): filepath/link/bytes/reader to an image to use with gemini pro vision [optional]
    history (list[dict]): history to provide to gemini, format: [{"role": "user", "text": "hello world"}, {"role": "model", "text": "greetings!"}]
    safety (Literal['none', 'low', 'medium', 'high']): safety type to use gemini with
    """

    headers = {
    'Content-Type': 'application/json',
    }

    params = {
        'key': apikey,
    }
    if history and image:
        raise ValueError("cant do image and history")
    if not history:
        json_data = {
            'contents': [
                {
                    'parts': [
                        {
                            'text': prompt,
                        },
                    ],
                },
            ],
        }
    else:
        parsed = []
        for i in history:
            if not isinstance(i, dict):
                raise ValueError("bad history parsing: not dict")
            role = i.get('role')
            if not role:
                raise ValueError("bad history parsing: no role")
            htext = i.get('text')
            if not htext:
                raise ValueError("bad history parsing: no text")
            parsed.append({"role": role, "parts": [{"text": htext}]})
        parsed.append({"role": "user", "parts": [{"text": prompt}]})
        json_data = {
            'contents': parsed
        }
    json_data["safetySettings"] = []
    categories = ['HARM_CATEGORY_HARASSMENT', 'HARM_CATEGORY_HATE_SPEECH', 'HARM_CATEGORY_SEXUALLY_EXPLICIT', 'HARM_CATEGORY_DANGEROUS_CONTENT']
    thresholds = {
        "none": 'BLOCK_NONE',
        "low": 'BLOCK_ONLY_HIGH',
        "medium": 'BLOCK_MEDIUM_AND_ABOVE',
        "high": "BLOCK_LOW_AND_ABOVE"
    }
    threshold = thresholds.get(safety)
    for category in categories:
        
        json_data["safetySettings"].append({"category": category, "threshold": threshold})
    if image:
        islink: bool = False
        if not isinstance(image, bytes) and not isinstance(image, io.BufferedReader) and not os.path.exists(image):
            if image.startswith("https://"):
                with open("image", "wb") as f1:
                    async with aiohttp.ClientSession(connector=get_connector(proxy)) as session:
                        async with session.get(image, proxy=proxy if proxy.startswith('https') else None) as r:
                            while True:
                                chunk = await r.content.read(1024)
                                if not chunk:
                                    break
                                f1.write(chunk)
                    image = "image"
                    islink = True
            else:
                raise ValueError("cant find image")
        if isinstance(image, io.BufferedReader):
            readbytes = image.read()
        img = Image.open(io.BytesIO(image) if isinstance(image, bytes) else image if isinstance(image, str) else io.BytesIO(readbytes))
        imgformat = img.format
        if not imgformat:
            raise ValueError("invalid image")
        if imgformat.lower() not in ["png", "jpeg", "jpg", "webp", "heic", "heif"]:
            raise ValueError('not valid image format, needs to be one of these: "png", "jpeg", "jpg", "webp", "heic", "heif"')
        img.close()
        if isinstance(image, str):
            data = base64.b64encode(open(image, 'rb').read()).decode("utf-8")
        elif isinstance(image, bytes):
            data = base64.b64encode(image).decode('utf-8')
        elif isinstance(image, io.BufferedReader):
            data = base64.b64encode(readbytes).decode('utf-8')
        if islink:
            filename = f"image-{int(datetime.now().timestamp())}." + imgformat.lower()
            os.rename("image", filename)
            image = filename
        imgdata = {"inlineData": {
                    "mimeType": f"image/{imgformat.lower()}",
                    "data": data
        }}
        json_data["contents"][0]["parts"].append(imgdata)
    temp = ""
    mainurl = 'https://generativelanguage.googleapis.com/v1/models/gemini-pro:streamGenerateContent'
    if image and not history:
        mainurl = 'https://generativelanguage.googleapis.com/v1/models/gemini-pro-vision:streamGenerateContent'
    elif history:
        mainurl = "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:streamGenerateContent"
    async with aiohttp.ClientSession(connector=get_connector(proxy)) as session:
        async with session.post(mainurl, params=params, headers=headers, json=json_data, proxy=proxy if proxy.startswith('https') else None) as response:
            while True:
                chunk = await response.content.read(1024*10)
                if not chunk:
                    break
                if chunk == b']':
                    continue
                decoded = chunk.decode("utf-8")
                if decoded.startswith("[") or decoded.startswith(","):
                    decoded = decoded[1:]
                try:
                    a = json.loads(decoded)
                    if not a.get('candidates') or not a["candidates"][0].get("content"):
                        text = "BLOCKED!\n"
                        reasons = a["promptFeedback"]["safetyRatings"] if not a.get('candidates') else a['candidates'][0]['safetyRatings']
                        for reason in reasons:
                            text += f'{reason.get("category")}: {reason.get("probability")}\n'
                        yield text
                        continue
                    else:
                        text: str = a['candidates'][0]['content']['parts'][0]['text']
                        yield text
                    temp = ""
                except:
                    temp += decoded
async def main():
    with open("response.txt", "w") as f1:
        history = [
            {
                "role": "user",
                "text": "what day is it?"
            },
            {
                "role": "model",
                "text": "it is a saturday!"
            },
        ]
        async for text in gemini("top warcrimes commited by the USA and israel", apikey, proxy=proxy):
            print(text)
            f1.write(text)
if __name__ == "__main__":
    from env import apikey, proxy
    import asyncio
    asyncio.run(main())