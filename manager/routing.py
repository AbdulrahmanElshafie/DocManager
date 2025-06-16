from django.urls import re_path

def get_websocket_urlpatterns():
    from . import consumers
    return [
        re_path(r'ws/document/(?P<document_id>[^/]+)/$', consumers.DocumentEditConsumer.as_asgi()),
    ]

websocket_urlpatterns = get_websocket_urlpatterns() 