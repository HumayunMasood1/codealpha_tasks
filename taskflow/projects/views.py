import json
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.db.models import Q
from .models import Project, Column, Task, Comment, Notification


# ── Notifications helper ─────────────────────────────────────────────────────
def send_notification(user, message, link=''):
    notif = Notification.objects.create(user=user, message=message, link=link)
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f'notifications_{user.id}',
        {'type': 'notification_message', 'message': message, 'link': link}
    )
    return notif


def broadcast_board(project_id, action, data):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f'project_{project_id}',
        {'type': 'board_update', 'action': action, 'data': data}
    )


# ── Dashboard ────────────────────────────────────────────────────────────────
@login_required
def dashboard(request):
    owned = Project.objects.filter(owner=request.user)
    member_of = Project.objects.filter(members=request.user)
    all_projects = (owned | member_of).distinct().order_by('-updated_at')
    my_tasks = Task.objects.filter(assignees=request.user).select_related('column__project').order_by('due_date')[:10]
    notifications = Notification.objects.filter(user=request.user, is_read=False)[:5]
    return render(request, 'projects/dashboard.html', {
        'projects': all_projects,
        'my_tasks': my_tasks,
        'notifications': notifications,
    })


# ── Projects ─────────────────────────────────────────────────────────────────
@login_required
def create_project(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        color = request.POST.get('color', '#7c3aed')
        if name:
            project = Project.objects.create(
                name=name, description=description,
                color=color, owner=request.user
            )
            # Default columns
            for i, col_name in enumerate(['To Do', 'In Progress', 'Review', 'Done']):
                Column.objects.create(project=project, name=col_name, order=i)
            return redirect('board', project_id=project.id)
    return render(request, 'projects/create_project.html')


@login_required
def board(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    if request.user != project.owner and request.user not in project.members.all():
        return redirect('dashboard')
    columns = project.columns.prefetch_related(
        'tasks', 'tasks__assignees', 'tasks__comments'
    )
    members = list(project.members.all()) + [project.owner]
    return render(request, 'projects/board.html', {
        'project': project,
        'columns': columns,
        'members': members,
    })


@login_required
def project_settings(request, project_id):
    project = get_object_or_404(Project, id=project_id, owner=request.user)
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'update':
            project.name = request.POST.get('name', project.name)
            project.description = request.POST.get('description', project.description)
            project.color = request.POST.get('color', project.color)
            project.save()
        elif action == 'invite':
            username = request.POST.get('username', '').strip()
            try:
                user = User.objects.get(username=username)
                if user != project.owner:
                    project.members.add(user)
                    send_notification(user, f'You were added to project "{project.name}"', f'/board/{project.id}/')
            except User.DoesNotExist:
                pass
        elif action == 'remove_member':
            uid = request.POST.get('user_id')
            try:
                user = User.objects.get(id=uid)
                project.members.remove(user)
            except User.DoesNotExist:
                pass
        return redirect('project_settings', project_id=project.id)
    members = project.members.all()
    return render(request, 'projects/project_settings.html', {'project': project, 'members': members})


@login_required
@require_POST
def delete_project(request, project_id):
    project = get_object_or_404(Project, id=project_id, owner=request.user)
    project.delete()
    return JsonResponse({'success': True})


# ── Columns ───────────────────────────────────────────────────────────────────
@login_required
@require_POST
def add_column(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    name = request.POST.get('name', '').strip()
    if name:
        order = project.columns.count()
        col = Column.objects.create(project=project, name=name, order=order)
        broadcast_board(project_id, 'column_added', {'id': col.id, 'name': col.name})
        return JsonResponse({'success': True, 'id': col.id, 'name': col.name})
    return JsonResponse({'success': False})


@login_required
@require_POST
def delete_column(request, column_id):
    col = get_object_or_404(Column, id=column_id)
    project_id = col.project_id
    col.delete()
    broadcast_board(project_id, 'column_deleted', {'id': column_id})
    return JsonResponse({'success': True})


# ── Tasks ─────────────────────────────────────────────────────────────────────
@login_required
@require_POST
def create_task(request, column_id):
    column = get_object_or_404(Column, id=column_id)
    title = request.POST.get('title', '').strip()
    if not title:
        return JsonResponse({'success': False})
    order = column.tasks.count()
    task = Task.objects.create(
        column=column, title=title, created_by=request.user,
        priority=request.POST.get('priority', 'medium'), order=order
    )
    # Notify project members
    for member in column.project.all_members():
        if member != request.user:
            send_notification(member, f'{request.user.username} created task "{title}"', f'/task/{task.id}/')
    broadcast_board(column.project_id, 'task_created', {
        'id': task.id, 'title': task.title,
        'column_id': column_id, 'priority': task.priority
    })
    return JsonResponse({
        'success': True, 'id': task.id, 'title': task.title,
        'priority': task.priority, 'column_id': column_id
    })


@login_required
def task_detail(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    project = task.column.project
    if request.user != project.owner and request.user not in project.members.all():
        return redirect('dashboard')
    comments = task.comments.select_related('author')
    members = list(project.members.all()) + [project.owner]
    return render(request, 'projects/task_detail.html', {
        'task': task, 'project': project,
        'comments': comments, 'members': members,
    })


@login_required
@require_POST
def update_task(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    data = json.loads(request.body)
    if 'title' in data:
        task.title = data['title']
    if 'description' in data:
        task.description = data['description']
    if 'priority' in data:
        task.priority = data['priority']
    if 'due_date' in data:
        task.due_date = data['due_date'] or None
    if 'column_id' in data:
        col = get_object_or_404(Column, id=data['column_id'])
        task.column = col
        task.order = data.get('order', task.order)
        # Notify assignees
        for assignee in task.assignees.all():
            if assignee != request.user:
                send_notification(assignee, f'Task "{task.title}" was moved to {col.name}', f'/task/{task.id}/')
    if 'assignee_id' in data:
        uid = data['assignee_id']
        if uid:
            user = User.objects.get(id=uid)
            task.assignees.add(user)
            if user != request.user:
                send_notification(user, f'You were assigned to "{task.title}"', f'/task/{task.id}/')
        broadcast_board(task.column.project_id, 'task_updated', {'id': task.id})
    task.save()
    broadcast_board(task.column.project_id, 'task_updated', {'id': task.id, 'column_id': task.column_id})
    return JsonResponse({'success': True})


@login_required
@require_POST
def delete_task(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    project_id = task.column.project_id
    title = task.title
    task.delete()
    broadcast_board(project_id, 'task_deleted', {'id': task_id})
    return JsonResponse({'success': True})


@login_required
@require_POST
def move_task(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    data = json.loads(request.body)
    new_column = get_object_or_404(Column, id=data['column_id'])
    old_column_name = task.column.name
    task.column = new_column
    task.order = data.get('order', 0)
    task.save()
    for assignee in task.assignees.all():
        if assignee != request.user:
            send_notification(assignee, f'Task "{task.title}" moved to {new_column.name}', f'/task/{task.id}/')
    broadcast_board(new_column.project_id, 'task_moved', {
        'id': task_id, 'column_id': new_column.id, 'order': task.order
    })
    return JsonResponse({'success': True})


# ── Comments ──────────────────────────────────────────────────────────────────
@login_required
@require_POST
def add_comment(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    content = request.POST.get('content', '').strip()
    if not content:
        return JsonResponse({'success': False})
    comment = Comment.objects.create(task=task, author=request.user, content=content)
    for assignee in task.assignees.all():
        if assignee != request.user:
            send_notification(assignee, f'{request.user.username} commented on "{task.title}"', f'/task/{task.id}/')
    return JsonResponse({
        'success': True,
        'author': request.user.username,
        'content': comment.content,
        'time_ago': comment.time_ago(),
    })


# ── Notifications ─────────────────────────────────────────────────────────────
@login_required
def notifications_view(request):
    notifs = Notification.objects.filter(user=request.user).order_by('-created_at')[:50]
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return render(request, 'projects/notifications.html', {'notifications': notifs})


@login_required
def unread_count(request):
    count = Notification.objects.filter(user=request.user, is_read=False).count()
    return JsonResponse({'count': count})


# ── Auth ──────────────────────────────────────────────────────────────────────
def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    error = None
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        p1 = request.POST.get('password1', '')
        p2 = request.POST.get('password2', '')
        if p1 != p2:
            error = 'Passwords do not match.'
        elif User.objects.filter(username=username).exists():
            error = 'Username already taken.'
        elif len(username) < 3:
            error = 'Username must be at least 3 characters.'
        else:
            user = User.objects.create_user(username=username, email=email, password=p1)
            login(request, user)
            return redirect('dashboard')
    return render(request, 'projects/register.html', {'error': error})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    error = None
    if request.method == 'POST':
        user = authenticate(request, username=request.POST.get('username'), password=request.POST.get('password'))
        if user:
            login(request, user)
            return redirect(request.GET.get('next', 'dashboard'))
        error = 'Invalid username or password.'
    return render(request, 'projects/login.html', {'error': error})


def logout_view(request):
    logout(request)
    return redirect('login')
