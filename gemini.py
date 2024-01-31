import aiohttp, aiohttp_socks, json, base64, os
from PIL import Image
from datetime import datetime
import io
async def gemini(prompt: str, apikey: str, connector: aiohttp.TCPConnector | aiohttp_socks.ProxyConnector = aiohttp.TCPConnector(), image: str | bytes | io.BufferedReader = None):
    """
    prompt (str): prompt to give [required]
    apikey (str): api key to use [get one here](https://makersuite.google.com/app/apikey) [required]
    connector (aiohttp.TCPConnector | aiohttp_socks.ProxyConnector): connector to use (ignore if you dont know) [optional]
    image (str | bytes | io.BufferedReader): filepath/link/bytes/reader to an image to use with gemini pro vision [optional]
    """
    
    headers = {
    'Content-Type': 'application/json',
    }

    params = {
        'key': apikey,
    }

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
    if image:
        islink: bool = False
        if not isinstance(image, bytes) and not isinstance(image, io.BufferedReader) and not os.path.exists(image):
            if image.startswith("https://"):
                with open("image", "wb") as f1:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(image) as r:
                            while True:
                                chunk = await r.content.read(1024)
                                if not chunk:
                                    break
                                f1.write(chunk)
                    image = "image"
                    islink = True
            else:
                yield "cant find image"
        if isinstance(image, io.BufferedReader):
            readbytes = image.read()
        img = Image.open(io.BytesIO(image) if isinstance(image, bytes) else image if isinstance(image, str) else io.BytesIO(readbytes))
        imgformat = img.format
        if not imgformat:
            yield "invalid image"
        if imgformat.lower() not in ["png", "jpeg", "jpg", "webp", "heic", "heif"]:
            yield 'not valid image format, needs to be one of these: "png", "jpeg", "jpg", "webp", "heic", "heif"'
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
    async with aiohttp.ClientSession(connector=connector) as session:
        async with session.post('https://generativelanguage.googleapis.com/v1/models/gemini-pro:streamGenerateContent' if not image else 'https://generativelanguage.googleapis.com/v1/models/gemini-pro-vision:streamGenerateContent', params=params, headers=headers, json=json_data) as response:
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
                    if not a.get('candidates'):
                        text = "BLOCKED!\n"
                        reasons = a["promptFeedback"]["safetyRatings"]
                        for reason in reasons:
                            text += f'{reason.get("category")}: {reason.get("probability")}\n'
                        yield text
                        continue
                    text: str = a['candidates'][0]['content']['parts'][0]['text']
                    yield text
                    temp = ""
                except:
                    temp += decoded
async def main():
    with open("response.txt", "w") as f1:
        async for text in gemini("describe this image", apikey, aiohttp_socks.ProxyConnector.from_url(proxy), image=open("image.jpeg", "rb").read()):
            print(text)
            f1.write(text)
if __name__ == "__main__":
    from env import apikey, proxy
    import asyncio
    asyncio.run(main())