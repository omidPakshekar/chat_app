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


class ChatConsumer(AsyncConsumer):

    async def fetch_messages(self, data):
        messages = await self.get_all_message()
        content = {
            'command': 'messages',
            'messages': await self.messages_to_json(messages)
        }
        await self.send_message(content)

    
    async def new_message(self, data):
        message_ = await self.create_message(data)
        content = {
            'command': 'new_message',
            'message':  await self.message_to_json(message_)
        }
        return await self.send_chat_message(content)

    @sync_to_async
    def messages_to_json(self, messages):
        result = []
        for message in messages:
            if message.item._meta.model_name == 'image':
                result.append({'id': message.id,
                    'sender': message.sender.username,
                    'type': 'image',
                    'message_text': ImageCreateSerializer(instance=message.item).data['content'],
                    'timestamp': str(message.timestamp)
                    })
            else:
                result.append({'id': message.id,
                    'sender': message.sender.username,
                    'message_text': message.item.content,
                    'timestamp': str(message.timestamp)
                })

        return result

    @sync_to_async
    def message_to_json(self, message):
        return {
            'id': message.id,
            'sender': message.sender.username,
            'message_text': message.item.content,
            'timestamp': str(message.timestamp)
        }

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
        self.sender = CustomUser.objects.get(username=data['sender'])
        reciever_ = UserMessage.objects.create()
        reciever_.users.add(*self.participants.friends.all()); reciever_.save()
        if data['message_type'] == 'text':
            text_ = Text.objects.create(owner=self.user,  content=data['message'])
            message_ = Message.objects.create(sender=self.sender, reciever=reciever_, item=text_)

        self.chat.messages.add(message_)
        return message_
    
    @sync_to_async
    def check_auth(self):
        return self.user in self.participants.friends.all() or self.user == self.participants.owner
        
    @sync_to_async
    def get_all_message(self):
        return self.chat.messages.all()
    


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