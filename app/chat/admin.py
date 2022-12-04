from django.contrib import admin
from .models import *

# Register your models here.

class ChatAdmin(admin.ModelAdmin):
    list_display = ['id', 'unique_code']


admin.site.register(Message)
admin.site.register(Contact)
admin.site.register(Chat, ChatAdmin)
