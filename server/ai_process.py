import argparse
import websockets
import asyncio

import airegistry

async def client(ai, uri):
    async with websockets.connect(uri) as websocket:
        while True:
            message = await websocket.recv()
            print(f"Message received by AI over websocket: {message[:100]}")
            result = ai.process(message)
            if result:
                await websocket.send( result )

parser = argparse.ArgumentParser()
parser.add_argument("ai_name")
parser.add_argument("faction")
parser.add_argument("--uri")
args = parser.parse_args()

ai_obj, ai_args = airegistry.ai_registry[args.ai_name]

ai = ai_obj(args.faction, ai_args)
uri = args.uri
if not uri:
    uri = "ws://localhost:9999"
asyncio.get_event_loop().run_until_complete(client(ai, uri))