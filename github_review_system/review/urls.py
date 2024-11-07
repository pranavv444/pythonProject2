from tkinter.font import names

from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register, name='register'),
    path('index/', views.index, name='index'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('connect/', views.github_connect, name='github_connect'),
    path('connect/github_redirect/', views.github_redirect, name='github_redirect'),
    path('oauth/callback/', views.github_callback, name='github_callback'),
    path('webhook/', views.github_webhook, name='github_webhook'),  # Add the webhook URL here
    path('',views.home, name = 'home'),
    path('tutorial/',views.tutorial, name = 'tutorial'),
    path('code_review/',views.code_review, name = 'code_review'),
    path('code_review/analyze-code/', views.analyze_code, name='analyze_code'),

]
