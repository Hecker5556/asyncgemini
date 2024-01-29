# Asynchronous python code that streams gemini ai output
The code creates a generator which you can iterate through

## Why?
I wrote this because I wanted to be able to stream output in an asynchronous way for my discord bot and also give it an option to use a proxy as gemini ai api isn't avaliable in europe yet.

## How does it work?
It streams the response in chunks of 10kb, and if json parsing fails, adds to a temporary string next chunks until json parsing works and yields the text

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
async for text in gemini("top 10 music artists", apikey, aiohttp_socks.ProxyConnector.from_url(proxy)):
    print(text)
```