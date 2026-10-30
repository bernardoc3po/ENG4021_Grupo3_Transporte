"""
URL configuration for UniRideSite project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path

from UniRideSite import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.login, name='login'),
    path('inicio/', views.home, name='home'),
    path('trajeto/', views.cadastrar_trajeto, name='cadastrar-trajeto'),
    path('caronas/', views.caronas_encontradas, name='caronas-encontradas'),
    path('carona/<int:id>/', views.detalhes_carona, name='detalhes-carona'),
    path('minhas-caronas/', views.minhas_caronas, name='minhas-caronas'),
    path('perfil/', views.perfil, name='perfil'),
]
