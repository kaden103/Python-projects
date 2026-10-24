# Entry point. pygbag (the web build) looks for main.py and runs it, so the game
# loop is async and gives control back to the browser every frame.
import asyncio

from game import Game


async def main():
    game = Game()
    await game.run()


asyncio.run(main())
