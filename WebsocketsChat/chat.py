#!/usr/bin/env python3
import json

from aiohttp import web
from aiohttp.web import FileResponse, Request

class Message:
    def __init__(self, type, id, text, no_send_ids):
        self.type = type
        self.id = id
        self.text = text
        self.no_send = no_send_ids
    
    def make_msg_dict(self):
        msg_dict = {'mtype': self.type, 'id': self.id}
        if self.text != None:
            msg_dict['text'] = self.text
        return msg_dict
    

class socketChat:
    def __init__(self, host='127.0.0.1', port=80):
        self.host = host
        self.port = port
        self.conns = dict()

    async def main_page(self, request):
        return FileResponse('./index.html')

    async def chat(self, request: Request):
        socket = web.WebSocketResponse(autoping=False)
        if not socket.can_prepare(request):
            return
        await socket.prepare(request)

        async for message in socket:
            type = message.data
            if type == "ping":
                await socket.send_str("pong")
                await self.check_not_close()
            elif data := json.loads(type):
                if data['mtype'] == "TEXT":
                    if data['to'] is None:
                        await self.send_message(data)
                    else:
                        await self.send_direct_message(data)
                elif data['mtype'] == "INIT":
                    await self.send_new_user_msg(data, socket)

    async def send_common_message(self, message: Message):
        await self.check_not_close()
        for id, socket in list(self.conns.items()):
            if message.no_send != None and id in message.no_send:
                continue
            try:
                await socket.send_json(message.make_msg_dict())
            except ConnectionResetError:
                await self.send_leave_message(id)

    async def send_new_user_msg(self, data, socket):
        self.conns[data['id']] = socket
        message = Message('USER_ENTER', data['id'], None, data['id'])
        await self.send_common_message(message)
    
    async def send_leave_message(self, id):
        self.conns.pop(id)
        message = Message('USER_LEAVE', id, None, None)
        await self.send_common_message(message)

    async def send_message(self, data):
        message = Message('MSG', data['id'], data['text'], data['id'])
        await self.send_common_message(message)

    async def send_direct_message(self, data):
        message = Message('DM', data['id'], data['text'], None)
        await self.conns[data['to']].send_json(message.make_msg_dict())

    async def check_not_close(self):
        for id, socket in list(self.conns.items()):
            if socket.closed:
                await self.send_leave_message(id)

    def run(self):
        app = web.Application()

        app.router.add_get('/', self.main_page)
        app.router.add_get('/chat', self.chat)

        web.run_app(app, host=self.host, port=self.port)



if __name__ == '__main__':
    socketChat('127.0.0.1', 80).run()
