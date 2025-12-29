from django.views.static import serve
from django.conf import settings
from django.urls import re_path

def serve_frontend(request, path):
    return serve(request, path, document_root=settings.STATICFILES_DIRS[0])