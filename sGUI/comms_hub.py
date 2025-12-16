import os
import json
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
import webbrowser
import threading
import sGUI.timers as timers
import threading
import traceback

def my_excepthook(args):
    print("Thread exception caught:\n",
          "".join(traceback.format_exception(args.exc_type,
                                             args.exc_value,
                                             args.exc_traceback)))
threading.excepthook = my_excepthook


def start_UI(UI_filename, UI_callback):
    threading.Thread(target=start_UI_page_server, daemon=True).start()
    threading.Thread(target=start_UI_ws_server, args=(UI_callback,)).start()
    webbrowser.open("http://localhost:8080/" + UI_filename)

#===================================================================================
# HTTP server for UI page
#===================================================================================
def start_UI_page_server():
    server = ThreadingHTTPServer(("localhost", 8080), SimpleHTTPRequestHandler)
    server.serve_forever()
    
#===================================================================================
# Python <-> JS communication via websockets
#===================================================================================
import asyncio
from websockets.asyncio.server import serve
global message_queue, loop, UI_callback
loop = None

def start_UI_ws_server(callback):
    global UI_callback
    import asyncio
    from websockets import serve
    timers.timedLog("[comms_hub] Starting websockets server")
    UI_callback = callback
    async def ws_server():
        global message_queue, loop
        loop = asyncio.get_running_loop()
        message_queue = asyncio.Queue()
        async with serve(_handle_client, "localhost", 5678):
            await asyncio.Future()  # run forever
    asyncio.run(ws_server())

def send_to_ui_ws(topic, message, silent = True):
    if not isinstance(message, dict):
        message = {}    # should really raise exception here 
    if loop and loop.is_running():
        if(topic == 'decode_dict'):
            for k,v in message.items():
                if (type(v) != "<class 'str'>"):
                    message[k]=str(v)
        full_message = {"topic": topic, **message}
       # timers.timedLog(f"[WebsocketsServer] {full_message}", silent = silent, logfile = 'ws.log')
        asyncio.run_coroutine_threadsafe(message_queue.put(full_message), loop)

async def _handle_client(websocket):
    # connection between here and the browser JS
    # launch two coroutines: one for sending, one for receiving
    send_task = asyncio.create_task(_send_queue_to_browser(websocket))
    recv_task = asyncio.create_task(_call_callback_on_rx_from_browser(websocket))
    done, pending = await asyncio.wait(
        [send_task, recv_task],
        return_when=asyncio.FIRST_COMPLETED
    )
    for task in pending:
        task.cancel()

async def _send_queue_to_browser(websocket):
    while True:
        message = await message_queue.get()
        try:
            await websocket.send(json.dumps(message))
        except Exception as e:
            timers.timedLog(f"[WebsocketsServer] couldn't send message", 'websockets.log')
        message_queue.task_done()

async def _call_callback_on_rx_from_browser(websocket):
    async for message in websocket:
        cmd = json.loads(message)
        UI_callback(cmd)




