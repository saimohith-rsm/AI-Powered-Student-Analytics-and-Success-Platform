from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from apps.accounts.views import LandingPageView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', LandingPageView.as_view(), name='landing'),
    path('accounts/', include('apps.accounts.urls', namespace='accounts')),
    path('', include('apps.analytics.urls', namespace='analytics')),
    path('students-manager/', include('apps.students.urls', namespace='students')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler403 = 'apps.accounts.views.custom_403_view'
handler404 = 'apps.accounts.views.custom_404_view'
