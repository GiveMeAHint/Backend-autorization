from django.contrib import admin
from django.urls import path, include, re_path
from django.views.generic import TemplateView
from django.views.static import serve
from django.conf import settings
import os
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework_simplejwt.views import TokenRefreshView

schema_view = get_schema_view(
    openapi.Info(
        title="Auth API",
        default_version='v1',
        description="API для аутентификации",
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    # Главная страница - фронтенд
    path('', TemplateView.as_view(template_name='index.html'), name='home'),
    
    # Админка
    path('admin/', admin.site.urls),
    
    # API
    path('api/', include('accounts.urls')),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # Документация
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]

# Специальные маршруты для статических файлов фронтенда
# Эти пути должны соответствовать путям в вашем HTML
urlpatterns += [
    re_path(r'^styles/(?P<path>.*)$', serve, {
        'document_root': os.path.join(settings.BASE_DIR, 'frontend', 'styles'),
    }),
    re_path(r'^scripts/(?P<path>.*)$', serve, {
        'document_root': os.path.join(settings.BASE_DIR, 'frontend', 'scripts'),
    }),
    re_path(r'^images/(?P<path>.*)$', serve, {
        'document_root': os.path.join(settings.BASE_DIR, 'frontend', 'images'),
    }),
]

# Для всех остальных путей (SPA маршрутизация) - отдаём index.html
urlpatterns += [
    re_path(r'^(?!admin|api|swagger|redoc|styles|scripts|images).*$', 
            TemplateView.as_view(template_name='index.html')),
]

# В режиме разработки обслуживаем медиа файлы
if settings.DEBUG:
    from django.conf.urls.static import static
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)