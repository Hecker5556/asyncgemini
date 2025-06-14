# Bare bones script for interacting with google's gemini
More customizable options and seeing how the API works instead of using SDK. Ability to use proxies and such.

## Why?
Wanted to use gemini in my discord bot and also use an american proxy because some of the models aren't avaliable in Europe

## How does it work?
Aiohttp requests like the API docs show

## What does it support?
I try to update to latest models, but for now the 2.5, 2.0 and 1.5 models (for free tier) are supported, with tts and image generation support
## Setup
I used python 3.10.9
```bash
git clone https://github.com/Hecker5556/asyncgemini
```
```bash
cd asyncgemini
```
```bash
pip install -r requirements.txt
```

## Usage
```python
async def main():
    response = await gemini("top 10 music artists", apikey, aiohttp_socks.ProxyConnector.from_url(proxy))
    files = response['data']
    text = response['text']
```