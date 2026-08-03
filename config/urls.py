from django.contrib import admin
from django.urls import path, include

handler404 = 'knowledge.views.handler404'
handler500 = 'knowledge.views.handler500'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('knowledge.urls')),
]
