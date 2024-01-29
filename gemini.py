import aiohttp, aiohttp_socks, json
from env import apikey, proxy
async def gemini(prompt: str, apikey: str, connector: aiohttp.TCPConnector | aiohttp_socks.ProxyConnector = aiohttp.TCPConnector()):
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
    temp = ""
    async with aiohttp.ClientSession(connector=connector) as session:
        async with session.post('https://generativelanguage.googleapis.com/v1/models/gemini-pro:streamGenerateContent', params=params, headers=headers, json=json_data) as response:
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
                    text: str = a['candidates'][0]['content']['parts'][0]['text']
                    yield text
                    temp = ""
                except:
                    temp += decoded
async def main():
    with open("response.txt", "w") as f1:
        async for text in gemini("top 10 music artists from the united states", apikey, aiohttp_socks.ProxyConnector.from_url(proxy)):
            print(text)
            f1.write(text)
if __name__ == "__main__":
    import asyncio
    asyncio.run(main())