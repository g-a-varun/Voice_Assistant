import asyncio

from src.assistant.interfaces import LLMToken
from src.assistant.response_manager import DefaultResponseManager


async def stream():
    yield LLMToken("Hello", 0)
    yield LLMToken(" world.", 1, is_final=True)


async def main():
    rm = DefaultResponseManager()

    async for chunk in rm.process(stream()):
        print(chunk)


asyncio.run(main())