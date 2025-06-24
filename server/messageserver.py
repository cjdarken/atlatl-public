#  A MessageServer exchanges JSON objects between clients which may
#    be functions or separate processes communicating over a websocket.
#    The server is a finite state machine driven by client messages.
#
#  Behavior: Cycles through each client. If there is are messages, 
#    it processes the first one, and may send a message to one or more clients.
#
#  MessageServer(client_functions, message_handler, new_client_handler)
#    Optional arguments: ip, port, verbose
#    async send(self, message_O, clientw) sends to one client
#    async broadcast(self, message_O) sends to all clients
#    async relay(self, message_O, originator) sends to all clients except one (originator)
#
#  client_functions = [client_function, ...]
#
#  client_function(message_string), returns string
#
#  async message_handler(message_O, clientw, server)
#    Server response to messages
#    message_O is an object that can be losslessly converted to JSON
#    clientw is a ClientWrapper with property id and method send_to_client
#    server is a MessageServer
# 
#  async new_client_handler(clientw, server)
#    Allows server to take actions when a new client connects

import json
import asyncio
import websockets
import signal
import sys

SLEEP_TIME = 0.0

def signal_handler(sig, frame):
    print(' You pressed Ctrl+C!')
    asyncio.get_event_loop().stop()
    sys.exit(0)

class ClientWrapper:
    next_id = 0
    def __init__(self, type, client):
        self.id = ClientWrapper.next_id
        ClientWrapper.next_id += 1
        self.type = type # "websocket" or "function"
        self.client = client # message-handling websocket or function
        self.from_client = []
    async def send_to_client(self, message_O, verbose=False):
        message_S = json.dumps(message_O)
        if verbose:
            print(f"S->{self.id} {message_S[:100]}")
        if self.type == "websocket":
            await self.client.send(message_S)
        else: # self.type == "function"
            returned_message_S = self.client(message_S, response_fn=self.send_to_server)
            if returned_message_S: # Checking to make sure it's not None
                self.from_client.append( json.loads(returned_message_S) ) # Invoke the function
    def send_to_server(self, message_O): # For sending messages that are not in response to a message
        if type(message_O)!=type({}):
            raise Exception(f"send_to_server message_O argument must be dict, not {type(message_O)}")
        self.from_client.append( message_O )

def serve_function_factory(message_handler, new_client_handler, server, verbose=False):
    async def serve(websocket, path):
        global SLEEP_TIME
        # More sleep when a web client is present to save on cpu load
        SLEEP_TIME = 0.01
        clientw = ClientWrapper("websocket", websocket)
        server.clients.append( clientw )
        await new_client_handler(clientw, server)
        async for message_S in websocket:
            if verbose:
                print(f'{clientw.id}->S {message_S[:100]}')
            message_O = json.loads(message_S)
            await message_handler(message_O, clientw, server)
    return serve

async def process_function_client(clientw, message_handler, new_client_handler, server, verbose):
    await new_client_handler(clientw, server)
    while True:
        while clientw.from_client:
            message_O = clientw.from_client.pop(0)
            if message_O and verbose:
                print(f'{clientw.id}->S {message_O}')
            await message_handler(message_O, clientw, server)
        await asyncio.sleep(SLEEP_TIME) # Yield to other tasks

# message_handler(message_O, clientw, server) handles message from client and sends responses via server

class MessageServer:
    def __init__(self, client_functions, message_handler, new_client_handler,
                ip="127.0.0.1", port="9999", openSocket=False, verbose=False):
        self.clients = []
        self.verbose = verbose
        if openSocket:
            serve = serve_function_factory(message_handler, new_client_handler, self, verbose)
            start_wsserver = websockets.serve(serve, ip, port)
            asyncio.get_event_loop().run_until_complete(start_wsserver)
        for func in client_functions:
            clientw = ClientWrapper("function", func)
            self.clients.append( clientw )
            asyncio.get_event_loop().create_task(process_function_client(clientw, message_handler, new_client_handler, self, verbose))
    def run(self):
        asyncio.get_event_loop().run_forever()
    async def send(self, message_O, clientw):
        await clientw.send_to_client(message_O, self.verbose)
    async def broadcast(self, message_O):
        for clientw in self.clients:
            await self.send(message_O, clientw)
    async def relay(self, message_O, originator):
        for clientw in self.clients:
            if clientw != originator:
                await self.send(message_O, clientw)

if __name__=="__main__":
    verbose = True
    signal.signal(signal.SIGINT, signal_handler)

    # Client functions take a string and return a string or None
    def client_function_A(message, response_fn=None):
        return json.dumps({"message":"responseA"})
    def client_function_B(message, response_fn=None):
        messageO = json.loads(message)
        if messageO['message']=="init":
            return None
        return json.dumps({"message":"responseB"})
    # Message handlers use the server to send return messages
    #   message_O and clientw are None on first invocation 
    async def server_message_handler(message_O, clientw, server):
        if message_O is None:
            return
        await server.relay({"message":"stimulus"}, clientw)
    async def new_client_handler(clientw, server):
        await clientw.send_to_client({"message":"init"}, verbose)

    server = MessageServer([client_function_A, client_function_B], server_message_handler, new_client_handler, verbose=verbose)
    server.run()