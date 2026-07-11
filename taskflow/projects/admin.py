from django.contrib import admin
from .models import Project, Column, Task, Comment, Notification

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'created_at')

@admin.register(Column)
class ColumnAdmin(admin.ModelAdmin):
    list_display = ('name', 'project', 'order')

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'column', 'priority', 'created_by', 'due_date')
    list_filter = ('priority',)

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('author', 'task', 'created_at')

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'message', 'is_read', 'created_at')
