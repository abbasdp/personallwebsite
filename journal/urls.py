from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("tag/<str:slug>/", views.tag_detail, name="tag"),
    path("<slug:slug>/", views.post_detail, name="post"),
]
