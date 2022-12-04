# # chat/consumers.py
from django.contrib.auth import get_user_model
from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer
from channels.db import database_sync_to_async
from channels.consumer import SyncConsumer, AsyncConsumer
from channels.exceptions import StopConsumer
from asgiref.sync import sync_to_async

import json

from .api.serializers import ImageCreateSerializer
from .models import *
import base64
from accounts.models import CustomUser


User = get_user_model()



class ChatConsumer2(AsyncConsumer):

    async def fetch_messages(self, data):
        messages = await self.get_all_message()
        content = {
            'command': 'messages',
            'messages': await self.messages_to_json(messages)
        }
        print('****\n', content, "\n*****")
        await self.send_message(content)

    
    async def new_message(self, data):
        message_ = await self.create_message(data)
        content = {
            'command': 'new_message',
            'message':  await self.message_to_json(message_)
        }
        print('new_message\n', content)
        return await self.send_chat_message(content)
    
    @sync_to_async
    def message_to_json(self, message):

        return {
            '_id': message.id,
            'senderId': message.sender.id,
            'username': message.sender.username,
            'content': message.item.content,
            'type' : 'text',
            'timestamp': str(message.timestamp),
            "date": str(message.date)
        }

    def parent_message_to_json(self, message):
        if message == None:
            return {}
        return {
            '_id': message.id,
            'senderId': message.sender.id,
            'username': message.sender.username,
            'content': message.item.content,
            'type' : 'text',
            'timestamp': str(message.timestamp),
            "date": str(message.date)
        }

    @sync_to_async
    def messages_to_json(self, messages):
        result = []
        for message in messages:
            if message.item._meta.model_name == 'image':
                result.append({'_id': message.id,
                    'senderId': message.sender.id,
                    'username': message.sender.username,
                    'type': 'image',
                    'content': ImageCreateSerializer(instance=message.item).data['content'],
                    'timestamp': str(message.timestamp),
                    "date": str(message.date),
                    'replyMessage':  self.parent_message_to_json(message.parent_message)
                    })
            else:
                print('&&&&&&&&&&&&&&&&&&&')
                print(message.timestamp)
                print('&&&&&&&&&&&&&&&&&&&')
                
                result.append({'_id': message.id,
                    'senderId': message.sender.id,
                    'username': message.sender.username,
                    'content': message.item.content,
                    'timestamp': str(message.timestamp),
                    "date": str(message.date),
                    'type' : 'text',
                    'replyMessage':  self.parent_message_to_json(message.parent_message)
                })

        return result

    

    commands = {
        'fetch_messages': fetch_messages,
        'new_message': new_message
    }
    
    
    @sync_to_async
    def get_user1(self, username):
        return CustomUser.objects.get(username=username)

    async def websocket_connect(self, event):
        print()
        self.user = await self.get_user1(username=self.scope['url_route']['kwargs']['username'])
        self.chat_id = self.scope['url_route']['kwargs']['chat_id']
        self.chat = await self.get_chat()
        self.chat_room_id = f"chat_{self.chat_id}"
        if self.chat:
            if await self.check_auth():
                await self.channel_layer.group_add(
                    self.chat_room_id,
                    self.channel_name
                )
                await self.send({'type': 'websocket.accept'})
            else:
                await self.send({'type': 'websocket.close'})
        else:
            await self.send({'type': 'websocket.close'})

    async def websocket_disconnect(self, close_code):
        await (self.channel_layer.group_discard)(
            self.chat_room_id,
            self.channel_name
        )
        raise StopConsumer()


    async def websocket_receive(self, event):
        text_data = event.get('text', None)
        data = json.loads(text_data)
        if  data['command'] == 'new_message' :
            if not data['message'] == '':
                await self.new_message(data)
        # elif data['command'] == 'delete_message':
        #     if data['type'] == 'one_way':
        #         await self.delete_one_way(data)
        #     else :
        #         pass
        else:
            await self.fetch_messages(data)

    async def send_chat_message(self, message):
        await self.channel_layer.group_send(
            self.chat_room_id,
            {
                'type': 'chat_message',
                'message': message,
                'sender_channel_name': self.channel_name
            }
        )

    async def send_message(self, message):
        await self.send({
            'type' : 'websocket.send',
            'text' :json.dumps(message)
            })

    async def chat_message(self, event):
        message = event['message']
        if self.channel_name != event['sender_channel_name']:
            await self.send({
            'type' : 'websocket.send',
            'text' :json.dumps(message)
            })
    @database_sync_to_async
    def get_chat(self):
        try:
            chat = Chat.objects.get(unique_code=self.chat_id)
            self.participants = chat.participants
            return chat
        except Chat.DoesNotExist:
            return None

    @database_sync_to_async
    def create_message(self, data):
        message_ = None 
        print(data)
        self.sender = CustomUser.objects.get(username=data['username'])
        reciever_ = UserMessage.objects.create()
        reciever_.users.add(*self.participants.friends.all()); reciever_.save()
        if data['message_type'] == 'text':
            parent = None 
            if 'parent_message' in data:
                if data['parent_message'] != None:
                    parent_id = int(data['parent_message'])
                    parent = Message.objects.get(id=parent_id)
            text_ = Text.objects.create(owner=self.user,  content=data['message'])
            message_ = Message.objects.create(sender=self.sender, reciever=reciever_, item=text_, parent_message=parent)

        self.chat.messages.add(message_)
        return message_
    
    @sync_to_async
    def check_auth(self):
        return self.user in self.participants.friends.all() or self.user == self.participants.owner
        
    @sync_to_async
    def get_all_message(self):
        return self.chat.messages.all()
    

class ChatConsumer(AsyncConsumer):

    async def fetch_messages(self, data):
        messages = await self.get_all_message()
        content = {
            'command': 'messages',
            'messages': await self.messages_to_json(messages)
        }
        print('****\n', content, "\n*****")
        await self.send_message(content)

    
    async def new_message(self, data):
        message_ = await self.create_message(data)
        content = {
            'command': 'new_message',
            'message':  await self.message_to_json(message_)
        }
        print('new_message\n', content)
        return await self.send_chat_message(content)
    
    @sync_to_async
    def message_to_json(self, message):
        return {
            '_id': message.id,
            'senderId': message.sender.id,
            'username': message.sender.username,
            'content': message.item.content,
            'type' : 'text',
            'timestamp': str(message.timestamp),
        }

    def parent_message_to_json(self, message):
        if message == None:
            return {}
        return {
            '_id': message.id,
            'senderId': message.sender.id,
            'username': message.sender.username,
            'content': message.item.content,
            'type' : 'text',
            'timestamp': str(message.timestamp)
        }

    @sync_to_async
    def messages_to_json(self, messages):
        result = []
        for message in messages:
            if message.item._meta.model_name == 'image':
                result.append({'_id': message.id,
                    'senderId': message.sender.id,
                    'username': message.sender.username,
                    'type': 'image',
                    'content': ImageCreateSerializer(instance=message.item).data['content'],
                    'timestamp': str(message.timestamp),
                    'replyMessage':  self.parent_message_to_json(message.parent_message)
                    })
            else:
                result.append({'_id': message.id,
                    'senderId': message.sender.id,
                    'username': message.sender.username,
                    'content': message.item.content,
                    'timestamp': str(message.timestamp),
                    'type' : 'text',
                    'replyMessage':  self.parent_message_to_json(message.parent_message)
                })

        return result

    

    commands = {
        'fetch_messages': fetch_messages,
        'new_message': new_message
    }

    async def websocket_connect(self, event):
        self.user = self.scope['user']
        self.chat_id = self.scope['url_route']['kwargs']['chat_id']
        self.chat = await self.get_chat()
        self.chat_room_id = f"chat_{self.chat_id}"
        if self.chat:
            if await self.check_auth():
                await self.channel_layer.group_add(
                    self.chat_room_id,
                    self.channel_name
                )
                await self.send({'type': 'websocket.accept'})
            else:
                await self.send({'type': 'websocket.close'})
        else:
            await self.send({'type': 'websocket.close'})

    async def websocket_disconnect(self, close_code):
        await (self.channel_layer.group_discard)(
            self.chat_room_id,
            self.channel_name
        )
        raise StopConsumer()


    async def websocket_receive(self, event):
        text_data = event.get('text', None)
        data = json.loads(text_data)
        if  data['command'] == 'new_message' :
            if not data['message'] == '':
                await self.new_message(data)
        # elif data['command'] == 'delete_message':
        #     if data['type'] == 'one_way':
        #         await self.delete_one_way(data)
        #     else :
        #         pass
        else:
            await self.fetch_messages(data)

    async def send_chat_message(self, message):
        await self.channel_layer.group_send(
            self.chat_room_id,
            {
                'type': 'chat_message',
                'message': message
            }
        )

    async def send_message(self, message):
        await self.send({
            'type' : 'websocket.send',
            'text' :json.dumps(message)
            })

    async def chat_message(self, event):
        message = event['message']
        await self.send({
            'type' : 'websocket.send',
            'text' :json.dumps(message)
            })
    @database_sync_to_async
    def get_chat(self):
        try:
            chat = Chat.objects.get(unique_code=self.chat_id)
            self.participants = chat.participants
            return chat
        except Chat.DoesNotExist:
            return None

    @database_sync_to_async
    def create_message(self, data):
        message_ = None 
        print(data)
        self.sender = CustomUser.objects.get(username=data['username'])
        reciever_ = UserMessage.objects.create()
        reciever_.users.add(*self.participants.friends.all()); reciever_.save()
        if data['message_type'] == 'text':
            parent = None 
            if 'parent_message' in data:
                parent_id = int(data['parent_message'])
                parent = Message.objects.get(id=parent_id)
            text_ = Text.objects.create(owner=self.user,  content=data['message'])
            message_ = Message.objects.create(sender=self.sender, reciever=reciever_, item=text_, parent_message=parent)

        self.chat.messages.add(message_)
        return message_
    
    @sync_to_async
    def check_auth(self):
        return self.user in self.participants.friends.all() or self.user == self.participants.owner
        
    @sync_to_async
    def get_all_message(self):
        return self.chat.messages.all()
    



class RoomConsumer(AsyncConsumer):

    async def fetch_room(self, data):
        rooms = await self.get_all_room()
        content = {
            'command': 'rooms',
            'rooms': await self.rooms_to_json(rooms)
        }
        await self.send_message(content)

    async def fetch_one_room(self, data):
        room = await self.get_one_chat(data['chat_id'])
        content = {
            'command': 'new_room',
            'room': await self.room_to_json(room)
        }
        await self.send({
            'type' : 'websocket.send',
            'text' :json.dumps(content)
            })


    @sync_to_async
    def get_one_chat(self, chat_id):
        return Chat.objects.get(id=int(chat_id))

    async def new_room(self, data):
        message_ = await self.create_new_room(data)
        content = {
            'command': 'new_room',
            'room':  await self.room_to_json(message_)
        }
        return await self.send_room_message(content)

    @sync_to_async
    def rooms_to_json(self, rooms):
        result = []
        for room in rooms:
            # user = None
            roomName = None
            if self.user == room.participants.owner:
                roomName = room.participants.friends.first().username
            else:
                roomName =  room.participants.owner.username
            message = room.messages.last()
            last_message = None
            if message != None:
                last_message = {'_id' : message.id,
                                'sender' : message.sender.username,
                                'content' : message.item.content,
                                'timestamp': str(message.timestamp)}
            result.append({'roomId': room.id,
                'roomName': roomName,
                'unique_code': room.unique_code,
                'last_message': last_message
            })

        return result

    @sync_to_async
    def room_to_json(self, room):
        roomName = None
        if self.user == room.participants.owner:
            roomName = room.participants.friends.first().username
        else:
            roomName =  room.participants.owner.username
        return {
            'roomId': room.id,
            'roomName': roomName,
            'unique_code': room.unique_code
        }

    commands = {
        'fetch_room': fetch_room,
        'new_room': new_room
    }

    async def websocket_connect(self, event):
        self.user = self.scope['user']
        self.chat = await self.get_chat()
        self.chat_room_id = f"notification_{self.user.id}"
        if self.user.is_authenticated:
                await self.channel_layer.group_add(
                    self.chat_room_id,
                    self.channel_name
                )
                await self.send({'type': 'websocket.accept'})
        else:
            await self.send({'type': 'websocket.close'})

    async def websocket_disconnect(self, close_code):
        await (self.channel_layer.group_discard)(
            self.chat_room_id,
            self.channel_name
        )
        raise StopConsumer()


    async def websocket_receive(self, event):
        text_data = event.get('text', None)
        data = json.loads(text_data)
        if  data['command'] == 'new_room' :
            if not data['message'] == '':
                await self.new_room(data)
        else:
            await self.fetch_room(data)

    async def send_room_message(self, message):
        await self.channel_layer.group_send(
            self.chat_room_id,
            {
                'type': 'room_message',
                'message': message
            }
        )

    async def send_message(self, message):
        await self.send({
            'type' : 'websocket.send',
            'text' :json.dumps(message)
            })

    async def room_message(self, event):
        message = event['message']
        await self.send({
            'type' : 'websocket.send',
            'text' :json.dumps(message)
            })
            

    @database_sync_to_async
    def create_new_room(self, data):
        message_ = None 
        # print(data)
        # self.sender = CustomUser.objects.get(username=data['sender'])
        # reciever_ = UserMessage.objects.create()
        # reciever_.users.add(*self.participants.friends.all()); reciever_.save()
        # if data['message_type'] == 'text':
        #     text_ = Text.objects.create(owner=self.user,  content=data['message'])
        #     message_ = Message.objects.create(sender=self.sender, reciever=reciever_, item=text_)

        # self.chat.messages.add(message_)
        return message_
    
    @database_sync_to_async
    def get_chat(self):
        try:
            chat = Chat.objects.all()
            return chat
        except Chat.DoesNotExist:
            return None

    @sync_to_async
    def get_all_room(self):
        return self.chat


# import json
# from channels.generic.websocket import AsyncWebsocketConsumer

# class ChatConsumer(AsyncWebsocketConsumer):
#     async def connect(self):
#         self.room_name = self.scope['url_route']['kwargs']['room_name']
#         self.room_group_name = 'chat_%s' % self.room_name

#         # Join room group
#         await self.channel_layer.group_add(
#             self.room_group_name,
#             self.channel_name
#         )

#         await self.accept()

#     async def disconnect(self, close_code):
#         # Leave room group
#         await self.channel_layer.group_discard(
#             self.room_group_name,
#             self.channel_name
#         )

#     # Receive message from WebSocket
#     async def receive(self, text_data):
#         text_data_json = json.loads(text_data)
#         message = text_data_json['message']

#         # Send message to room group
#         await self.channel_layer.group_send(
#             self.room_group_name,
#             {
#                 'type': 'chat_message',
#                 'message': message
#             }
#         )

#     # Receive message from room group
#     async def chat_message(self, event):
#         message = event['message']

#         # Send message to WebSocket
#         await self.send(text_data=json.dumps({
#             'message': message
#         }))