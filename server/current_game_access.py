server = None
def set_gameserver(svr):
    global server
    server = svr
def get_current_game():
    return server.game