from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Projects
    path('project/create/', views.create_project, name='create_project'),
    path('board/<int:project_id>/', views.board, name='board'),
    path('project/<int:project_id>/settings/', views.project_settings, name='project_settings'),
    path('project/<int:project_id>/delete/', views.delete_project, name='delete_project'),

    # Columns
    path('project/<int:project_id>/column/add/', views.add_column, name='add_column'),
    path('column/<int:column_id>/delete/', views.delete_column, name='delete_column'),

    # Tasks
    path('column/<int:column_id>/task/create/', views.create_task, name='create_task'),
    path('task/<int:task_id>/', views.task_detail, name='task_detail'),
    path('task/<int:task_id>/update/', views.update_task, name='update_task'),
    path('task/<int:task_id>/delete/', views.delete_task, name='delete_task'),
    path('task/<int:task_id>/move/', views.move_task, name='move_task'),
    path('task/<int:task_id>/comment/', views.add_comment, name='add_comment'),

    # Notifications
    path('notifications/', views.notifications_view, name='notifications'),
    path('notifications/count/', views.unread_count, name='unread_count'),
]
