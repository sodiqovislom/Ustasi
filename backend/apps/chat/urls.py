from django.urls import path
from .views import MessageListCreateView, ConversationListView

urlpatterns = [
    path('', MessageListCreateView.as_view(), name='message-list-create'),
    path('conversations/', ConversationListView.as_view(), name='conversation-list'),
]
