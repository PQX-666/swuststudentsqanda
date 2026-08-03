from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('search/', views.search, name='search'),
    path('category/<slug:slug>/', views.category_detail, name='category_detail'),
    path('question/<int:pk>/', views.question_detail, name='question_detail'),
    path('question/<int:pk>/feedback/', views.submit_feedback, name='submit_feedback'),
    path('submit-question/', views.submit_question, name='submit_question'),
    path('about/', views.about, name='about'),
]
