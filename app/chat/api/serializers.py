from rest_framework import serializers

from chat.models import *

class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = ["friends"]


class ChatContactSerializer(serializers.ModelSerializer):

    class Meta:
        model = Chat
        fields = ('id', 'contact', )
        read_only = ('id')


class ChatSerializer(serializers.ModelSerializer):
    username = serializers.SerializerMethodField(read_only=True)
    class Meta:
        model = Chat
        fields = ['id', 'unique_code', 'username']
        read_only = ('id')

    def get_username(self, obj):
        user = self.context['request'].user
        if user == obj.participants.owner:
            return obj.participants.friends.first().username
        return obj.participants.owner.username
        

class ImageCreateSerializer(serializers.Serializer):
    chat_unique_code = serializers.CharField()
    content = serializers.ImageField()
        
class FileCreateSerializer(serializers.Serializer):
    chat_unique_code = serializers.CharField()
    content = serializers.FileField()
