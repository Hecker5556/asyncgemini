import aiohttp, aiohttp_socks, json, base64, os
from PIL import Image
from datetime import datetime
import io
from typing import Literal
def get_connector(proxy: str):
    return aiohttp_socks.ProxyConnector.from_url(proxy) if proxy and proxy.startswith("socks") else aiohttp.TCPConnector()
async def gemini(prompt: str, apikey: str, model: Literal['gemini-1.5-flash', 'gemini-1.0-pro', 'gemini-1.5-pro'] = 'gemini-1.5-flash',proxy: str = None, image: str | bytes | io.BufferedReader = None, history: list[dict] = None, safety: Literal['none', 'low', 'medium', 'high'] = 'none'):
    """
    prompt (str): prompt to give [required]
    apikey (str): api key to use [get one here](https://makersuite.google.com/app/apikey) [required]
    model (Literal['gemini-1.5-flash', 'gemini-1.0-pro', 'gemini-1.5-pro']): model to use
    proxy (str): proxy to use (ignore if you dont know) [optional]
    image (str | bytes | io.BufferedReader): filepath/link/bytes/reader to an image to use with gemini pro vision [optional]
    history (list[dict]): history to provide to gemini, format: [{"role": "user", "text": "hello world"}, {"role": "model", "text": "greetings!"}]
    safety (Literal['none', 'low', 'medium', 'high']): safety type to use gemini with
    """
    if model == 'gemini-1.0-pro' and image:
        raise ValueError("Pro vision deprecated for gemini 1.0")
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
        imgbytes = io.BytesIO()
        img.save(imgbytes, format=imgformat)
        while imgbytes.getbuffer().nbytes > 4 *1024*1024:
            img = img.resize((int(img.width*0.8), int(img.height*0.8)), Image.LANCZOS)
            imgbytes = io.BytesIO()
            img.save(imgbytes, format=imgformat)
        if imgbytes.getbuffer().nbytes > 0:
            imgbytes.seek(0)
            readbytes = imgbytes.read()
            image = io.BufferedReader(imgbytes)
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
    mainurl = f'https://generativelanguage.googleapis.com/v1/models/{model}:streamGenerateContent'
    if image and not history:
        mainurl = f'https://generativelanguage.googleapis.com/v1/models/{model}:streamGenerateContent'
    elif history:
        mainurl = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:streamGenerateContent"
    async with aiohttp.ClientSession(connector=get_connector(proxy)) as session:
        async with session.post(mainurl, params=params, headers=headers, json=json_data, proxy=proxy if proxy and proxy.startswith('https') else None) as response:
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
        async for text in gemini("describe this image", apikey,'gemini-1.5-flash', proxy, image="image-1723407030.jpeg"):
            print(text, end="")
            f1.write(text)
async def chatting():
    history = []
    model = 'gemini-1.5-flash'
    models = ['gemini-1.5-flash', 'gemini-1.0-pro', 'gemini-1.5-pro']
    image = None
    prox = None
    while True:
        userinput = str(input(f"\n\x1b[32mPROMPT:\x1b[39m "))
        image = None
        if userinput.lower() == "model":
            for index, mdl in enumerate(models):
                print(f"[{index}] - {mdl}")
            print("select which model to use")
            userinput = int(input("MODEL NUMBER: "))
            model = models[userinput]
            print(f"selected {model}")
            continue
        elif userinput.lower() == "quit" or userinput.lower() == 'exit':
            break
        elif userinput == "image":
            image = str(input("path or url to image: "))
            userinput = str(input("prompt to go with image: "))
        elif userinput == "proxy":
            print("using proxy now")
            prox = proxy
            continue
        response = ""
        async for text in gemini(userinput, apikey,model, image=image, history=history, proxy=prox):
            print(text, end="")
            response += text
        if not response:
            continue
        history.append({"role": "user", "text": userinput})
        history.append({"role": "model", "text": response})
        
if __name__ == "__main__":
    from env import apikey, proxy
    import asyncio
    asyncio.run(chatting())