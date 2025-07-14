import aiohttp, aiohttp_socks, json, base64, os
from PIL import Image
from datetime import datetime
import io
from typing import Literal
import mimetypes
import asyncio
def get_connector(proxy: str):
    return aiohttp_socks.ProxyConnector.from_url(proxy) if proxy else aiohttp.TCPConnector()
voices = {
    "Zephyr": "Bright",
    "Puck": "Upbeat",
    "Charon": "Informative",
    "Kore": "Firm",
    "Fenrir": "Excitable",
    "Leda": "Youthful",
    "Orus": "Firm",
    "Aoede": "Breezy",
    "Callirrhoe": "Easy-going",
    "Autonoe": "Bright",
    "Enceladus": "Breathy",
    "Iapetus": "Clear",
    "Umbriel": "Easy-going",
    "Algieba": "Smooth",
    "Despina": "Smooth",
    "Erinome": "Clear",
    "Algenib": "Gravelly",
    "Rasalgethi": "Informative",
    "Laomedeia": "Upbeat",
    "Achernar": "Soft",
    "Alnilam": "Firm",
    "Schedar": "Even",
    "Gacrux": "Mature",
    "Pulcherrima": "Forward",
    "Achird": "Friendly",
    "Zubenelgenubi": "Casual",
    "Vindemiatrix": "Gentle",
    "Sadachbia": "Lively",
    "Sadaltager": "Knowledgeable",
    "Sulafat": "Warm"
}
async def gemini(prompt: str, apikey: str, model: Literal['gemini-2.5-flash-preview-05-20','gemini-2.5-flash-preview-tts', 'gemini-2.5-pro-preview-06-05', 'gemini-2.0-flash-preview-image-generation','gemini-2.0-flash','gemini-1.5-flash', 'gemini-1.0-pro', 'gemini-1.5-pro'] = 'gemini-2.0-flash',proxy: str = None, file: str | bytes | io.BufferedReader = None, history: list[dict] = None, safety: Literal['none', 'low', 'medium', 'high'] = 'none', voice: str = 'Sadachbia', searching_threshold: float = 0.8):
    """
    prompt (str): prompt to give [required]
    apikey (str): api key to use [get one here](https://makersuite.google.com/app/apikey) [required]
    model (Literal['gemini-2.0-flash','gemini-2.0-flash-lite','gemini-1.5-flash', 'gemini-1.0-pro', 'gemini-1.5-pro']): model to use
    proxy (str): proxy to use (ignore if you dont know) [optional]
    file (str | bytes | io.BufferedReader): filepath/link/bytes/reader to a file to use with gemini [optional]
    history (list[dict]): history to provide to gemini, format: [{"role": "user", "text": "hello world"}, {"role": "model", "text": "greetings!"}]
    safety (Literal['none', 'low', 'medium', 'high']): safety type to use gemini with
    searching_threshold (float): between 0 and 1, gemini assumes probability that query needs google search to have valid info, the higher searching_threshold, the more certainty gemini needs to perform a search
    """
    if model == 'gemini-1.0-pro' and file:
        raise ValueError("Pro vision deprecated for gemini 1.0")
    headers = {
    'Content-Type': 'application/json',
    }

    params = {
        'key': apikey,
    }
    if history and file:
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
    if model == 'gemini-2.0-flash-preview-image-generation':
        json_data.update({"generationConfig": {"responseModalities": ["TEXT", "IMAGE"]}})
    elif model == 'gemini-2.5-flash-preview-tts':
        if voice not in voices:
            raise ValueError(f"{voice} is not a recognized voice, try one of these: {list(voices.keys())}")
        json_data.update({"generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {
                "voiceConfig": {
                    "prebuiltVoiceConfig": {"voiceName": voice}
                }
            }
        },})
    if searching_threshold and model in ['gemini-2.5-flash-preview-05-20', 'gemini-2.5-pro-preview-06-05',]:
        json_data.update({"tools": [{"google_search_retrieval": {
                  "dynamic_retrieval_config": {
                    "mode": "MODE_DYNAMIC",
                    "dynamic_threshold": searching_threshold,
                }
            }
        }
    ]})
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
    if file:
        mimetype = None
        filename = None
        tempfile = None
        if not isinstance(file, bytes) and not isinstance(file, io.BufferedReader) and not os.path.exists(file):
            if file.startswith("https://"):
                    async with aiohttp.ClientSession(connector=get_connector(proxy)) as session:
                        async with session.get(file) as r:
                            file = f"file{mimetypes.guess_extension(r.headers.get('content-type'))}"
                            with open(file, "wb") as f1:
                                while True:
                                    chunk = await r.content.read(1024)
                                    if not chunk:
                                        break
                                    f1.write(chunk)
                            mimetype = mimetypes.guess_type(file)
                            if not mimetype[0]:
                                mimetype = [r.headers.get('content-type'), None]
                            filename = file
            else:
                raise FileNotFoundError("cant find file")
        elif isinstance(file, str) and os.path.exists(file):
            mimetype = mimetypes.guess_type(file)
            filename = file
        else:
            tempfile = f"temp-{datetime.now().timestamp():.0f}"
            if isinstance(file, io.BufferedReader):
                with open(tempfile, "wb") as f1:
                    f1.write(file.read())
            elif isinstance(file, bytes):
                with open(tempfile, "wb") as f1:
                    f1.write(file)
            mimetype = mimetypes.guess_type(tempfile)
            filename = f"file{mimetypes.guess_extension(mimetype)}"
            os.rename(tempfile, filename)
        if not mimetype:
            raise Exception(f"Couldn't recognize type of file")
        if "image" in mimetype:
            img: Image.Image = Image.open(filename)
            imgbytes = io.BytesIO()
            img.save(imgbytes, format=img.format)
            while imgbytes.getbuffer().nbytes > 4 *1024*1024:
                img = img.resize((int(img.width*0.8), int(img.height*0.8)), Image.LANCZOS)
                imgbytes = io.BytesIO()
                img.save(imgbytes, format=img.format)
            img.save(filename)
            img.close()

        data = base64.b64encode(open(file, 'rb').read()).decode("utf-8")
        filedata = {"inline_data": {
                    "mime_type": mimetype[0],
                    "data": data
        }}
        json_data["contents"][0]["parts"].append(filedata)
    mainurl = f'https://generativelanguage.googleapis.com/v1/models/{model}:generateContent'
    if file and not history:
        mainurl = f'https://generativelanguage.googleapis.com/v1/models/{model}:generateContent'
    if history or model in ['gemini-2.5-flash-preview-tts', 'gemini-2.5-pro-preview-06-05', 'gemini-2.0-flash-preview-image-generation', 'gemini-2.5-flash-preview-05-20']:
        mainurl = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    async with aiohttp.ClientSession(connector=get_connector(proxy)) as session:
        async with session.post(mainurl, params=params, headers=headers, json=json_data,) as response:
            result = await response.json()
            with open("response.json", "w", encoding="utf-8") as f1:
                json.dump(result, f1, ensure_ascii=False)
            if result.get('error'):
                if result['error']['status'] == 'RESOURCE_EXHAUSTED':
                    result['error']['message'] += f"\n{result['error']['details'][0]['violations'][0].get('quotaValue')} rpd exhausted"
                return {"text": result['error']['message'], "data": []}
            if not result.get('candidates') or not result["candidates"][0].get("content"):
                text = "BLOCKED!\n"
                reasons = result["promptFeedback"]["safetyRatings"] if not result.get('candidates') else result['candidates'][0]['safetyRatings']
                for reason in reasons:
                    text += f'{reason.get("category")}: {reason.get("probability")}\n'
                return {"text": text}
            if isinstance(result['candidates'][0]['content']['parts'], list):
                info = {"text": "", "data": []}
                for i in result['candidates'][0]['content']['parts']:
                    if not i.get("inlineData"):
                        info['text'] += i['text']
                    else:
                        info['data'] += [{
                            "base64": i['inlineData']['data'],
                            "mimeType": i['inlineData']['mimeType']
                        }]
                for i in info['data']:
                    ext = mimetypes.guess_extension(i['mimeType'])
                    if not ext:
                        if "codec=pcm" in i['mimeType']:
                            ext = ".pcm"
                    tempfile = f"temp-file-{datetime.now().timestamp():.0f}{ext}"
                    with open(tempfile, 'wb') as f1:
                        f1.write(base64.b64decode(i['base64']))
                    if ext == ".pcm":
                        result_file = f"tts-audio-{datetime.now().timestamp():.0f}.wav"
                        args = "-f s16le -ar 24000 -ac 1 -i".split() + [tempfile, result_file]
                        process = await asyncio.subprocess.create_subprocess_exec("ffmpeg", *args)
                        await process.communicate()
                        i['filename'] = result_file
                        os.remove(tempfile)
                    elif "image" in i['mimeType']:
                        filename = f"image-{datetime.now().timestamp():.0f}{ext}"
                        os.rename(tempfile, filename)
                        i['filename'] = filename
                    del i['base64']
                return info
            return {"text": result['candidates'][0]['content']['parts']['text'], "data": []}

            # if not a.get('candidates') or not a["candidates"][0].get("content"):
            #     text = "BLOCKED!\n"
            #     reasons = a["promptFeedback"]["safetyRatings"] if not a.get('candidates') else a['candidates'][0]['safetyRatings']
            #     for reason in reasons:
            #         text += f'{reason.get("category")}: {reason.get("probability")}\n'
            #     yield text
            #     continue
            # else:
            #     text: str = a['candidates'][0]['content']['parts'][0]['text']
            #     yield text


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
    if not os.path.exists("cache.json"):
        cache = {}
    else:
        with open("cache.json", "r") as f1:
            try:
                cache = json.load(f1)
            except Exception as e:
                print(e)
                cache = {}
    history = []
    model = 'gemini-2.0-flash'
    models = ['gemini-2.5-flash-preview-05-20','gemini-2.5-flash-preview-tts', 'gemini-2.5-pro-preview-06-05', 'gemini-2.0-flash-preview-image-generation','gemini-2.0-flash','gemini-1.5-flash', 'gemini-1.0-pro', 'gemini-1.5-pro']
    file = None
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
        elif userinput == "file":
            file = str(input("path or url to file: "))
            if cache.get(file) and os.path.exists(cache.get(file)):
                file = cache.get(file)
            else:
                if not os.path.exists(file):
                    async with aiohttp.ClientSession(connector=get_connector(prox)) as session:
                        async with session.get(file) as r:
                            filename = f"image-{int(datetime.now().timestamp())}"
                            if ext := mimetypes.guess_extension(r.headers.get("content-type")):
                                filename += ext
                            elif r.headers.get("content-type").lower() == "image/webp":
                                filename += ".webp"
                            else:
                                raise ValueError(f"Couldnt get ext for {r.headers.get('content-type')}")
                            with open(filename, 'wb') as f1:
                                while True:
                                    chunk = await r.content.read(1024)
                                    if not chunk:
                                        break
                                    f1.write(chunk)
                    cache[file] = filename
                    with open("cache.json", "w") as f1:
                        json.dump(cache, f1)
                    file = filename
            userinput = str(input("prompt to go with file: "))
        elif userinput == "proxy":
            print("using proxy now")
            prox = proxy
            continue
        response = await gemini(userinput, apikey,model, file=file, history=None if file or model in ['gemini-2.5-flash-preview-tts'] else history, proxy=prox)
        print(response)
        if not response:
            continue
        if "image" in model:
            a = {"role": "user", "text": userinput}
            a.update({"generationConfig": {"responseModalities": ["TEXT", "IMAGE"]}})
            history.append(a)
            b = {"role": "model", "text": response['text']}
            b.update({"generationConfig": {"responseModalities": ["TEXT", "IMAGE"]}})
            history.append(b)
        else:
            history.append({"role": "user", "text": userinput})
            history.append({"role": "model", "text": response['text']})
        
if __name__ == "__main__":
    from env import apikey, proxy
    asyncio.run(chatting())