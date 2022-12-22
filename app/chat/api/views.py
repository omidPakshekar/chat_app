from functools import partial
from django.contrib.auth import get_user_model
from django.db.models import Q, Count

from rest_framework.response import Response
from rest_framework import permissions
from rest_framework.permissions import IsAuthenticated
from rest_framework import generics, status, views, permissions, viewsets

from chat.models import Chat, Contact
from .serializers import *
from asgiref.sync import async_to_sync

from channels.layers import get_channel_layer


User = get_user_model()



# update and partial update and add delete for owner and admin
class ChatViewSet(viewsets.ModelViewSet):
    queryset = Chat.objects.all()
    serializer_class = ChatSerializer
    permission_classes = (permissions.IsAuthenticated, )
    contact = None 

    def get_serializer_class(self):
        if self.action == 'create':
            return ContactSerializer
        return ChatSerializer
    
    # def get_queryset(self):
    #     print(self.queryset.filter(self.request.user in partic))
    #     return self.queryset.filter(Q(participants__owner=self.request.user))

    def create(self, request, *args, **kwargs):
        serializer = ContactSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        cs = serializer.validated_data['friends']
        contact_ = Contact.objects.annotate(
            nusers=Count('friends'),
            nusers_match=Count('friends', filter=Q(friends__in=cs))
        ).filter(
            nusers=len(cs),
            nusers_match=len(cs)
        )
        if contact_.count() == 0:
            contact = serializer.save(owner=self.request.user)
            chat_ = Chat.objects.create(participants=contact)
            print('***unique_code=', chat_.id, chat_.unique_code)
            channel_layer = get_channel_layer()
            user = request.user.id
            async_to_sync(channel_layer.group_send)(
                    f'notification_{request.user.id}',
                    {
                        'type': 'fetch_one_room',
                        'chat_id': chat_.id
                    }
                )
            for i in chat_.participants.friends.all():
                async_to_sync(channel_layer.group_send)(
                    f'notification_{i.id}',
                    {
                        'type': 'fetch_one_room',
                        'chat_id': chat_.id
                    }
                )
            return Response(data = {'chat_id': chat_.unique_code}, status=status.HTTP_201_CREATED)
        

        return Response(data = {'chat_id': contact_[0].chats.all()[0].unique_code}, status=status.HTTP_200_OK)
        

class ImageCreateView(generics.GenericAPIView):
    queryset = Image.objects.all()
    serializer_class = ImageCreateSerializer
    permission_classes = [IsAuthenticated]

    def post(self, *args, **kwargs):
        chat_ = Chat.objects.get(unique_code=self.request.data['chat_unique_code'])
        image_ = Image.objects.create(owner=self.request.user, content=self.request.data['content'])
        reciever_ = UserMessage.objects.create()
        reciever_.users.add(*chat_.participants.friends.all())
        reciever_.save()
        Message.objects.create(item=image_, sender=self.request.user, reciever=reciever_)
        return Response({'detail' : "it's created"}, status=status.HTTP_201_CREATED)

class FileCreateView(generics.CreateAPIView):
    serializer_class = FileCreateSerializer
    permission_classes = [IsAuthenticated]

    def post(self, *args, **kwargs):
        chat_ = Chat.objects.get(unique_code=self.request.data['chat_unique_code'])
        image_ = File.objects.create(owner=self.request.user, content=self.request.data['content'])
        reciever_ = UserMessage.objects.create()
        reciever_.users.add(*chat_.participants.friends.all())
        reciever_.save()
        Message.objects.create(item=image_, sender=self.request.user, reciever=reciever_)
        return Response({'detail' : "it's created"}, status=status.HTTP_201_CREATED)




class DeleteMessageView(generics.GenericAPIView):
    queryset = Message.objects.all()
    serializer_class = MessageIdSerializer


    def post(self, *args, **kwargs):
        obj = Message.objects.get(id=int(self.request.data['message_id']))
        channel_layer = get_channel_layer()
        if self.request.user == obj.sender:
            chat_ = obj.chat_set.last()
            obj.delete()
            async_to_sync(channel_layer.group_send)(
                f'chat_{chat_.id}',
                {
                'type': 'fetch_messages_view',
                 "command": "messages",
                }
            )
            return Response({'detail': 'message delete succsessfully'}, status=status.HTTP_200_OK)

        return Response({'detail': 'you are not owner'}, status=status.HTTP_400_BAD_REQUEST)





   
# class AddUserContact(views.APIView):
#     queryset = Contact.objects.all()
#     serializer_class = ContactSerializer
#     # authentication_classes = 
#     def post(self, request, format=None):





