from django.urls import path

from .views import signup
from django.contrib.auth.views import LoginView, LogoutView

urlpatterns = [
    path("registro/", signup, name="signup"),
    path('login/', LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', LogoutView.as_view(next_page='login'), name='logout'),
]