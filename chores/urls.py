from django.urls import path

from . import views

app_name = 'chores'

urlpatterns = [
    path('', views.board, name='board'),
    path('who/', views.who, name='who'),
    path('chores/<int:pk>/done/', views.done, name='done'),
    path('chores/<int:pk>/skip/', views.skip, name='skip'),
    path('history/', views.history, name='history'),
    path('chores/', views.chore_list, name='chore_list'),
    path('chores/new/', views.chore_new, name='chore_new'),
    path('chores/<int:pk>/edit/', views.chore_edit, name='chore_edit'),
    path('chores/<int:pk>/delete/', views.chore_delete, name='chore_delete'),
]
