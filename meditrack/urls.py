from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),

    # Social login (Google) using allauth
    path('accounts/', include('allauth.urls')),

    # Accounts app (login, signup, password reset)
    path('auth/', include('accounts.urls', namespace='accounts')),

    # Hospital app (landing page, dashboards, staff management)
    path('', include('hospital.urls', namespace='hospital')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
