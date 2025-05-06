from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.utils.timezone import now
from datetime import timedelta, datetime
from KartavyaMain.forms import TaskForm
from KartavyaMain.models import Task
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.contrib import messages
import requests

FLASK_API_BASE = 'http://localhost:5000/api'

def sync_task_with_flask(task_id, auth_token):
    """Helper function to get latest task state from Flask"""
    if not auth_token:
        return None
        
    headers = {'Authorization': f'Bearer {auth_token}'}
    try:
        response = requests.get(f'{FLASK_API_BASE}/tasks', headers=headers)
        if response.status_code == 200:
            flask_tasks = response.json().get('tasks', [])
            # Find matching task
            for task_data in flask_tasks:
                if task_data['id'] == task_id:
                    return task_data
    except requests.RequestException:
        pass
    return None

@login_required
def add_task(request):
    if request.method == 'POST':
        form = TaskForm(request.POST)
        if form.is_valid():
            try:
                auth_token = request.session.get('auth_token')
                if auth_token:
                    headers = {'Authorization': f'Bearer {auth_token}'}
                    task_data = {
                        'title': form.cleaned_data['title'],
                        'description': form.cleaned_data['description'],
                        'priority': form.cleaned_data['priority'],
                        'due_date': form.cleaned_data['due_date'].strftime('%Y-%m-%d') if form.cleaned_data.get('due_date') else None
                    }
                    response = requests.post(f'{FLASK_API_BASE}/tasks', json=task_data, headers=headers)
                    
                    if response.status_code == 201:
                        flask_task = response.json()['task']
                        task = form.save(commit=False)
                        task.id = flask_task['id']  
                        task.user = request.user
                        task.save()
                        messages.success(request, 'Task created successfully!')
                    else:
                        messages.error(request, 'Failed to create task in Task Manager')
                else:
                    messages.error(request, 'Authentication token missing. Please log in again.')
            except requests.RequestException as e:
                messages.error(request, f'Error creating task: {str(e)}')
    return redirect('dashboard')

@login_required
def update_task(request, task_id):
    auth_token = request.session.get('auth_token')
    flask_task = sync_task_with_flask(task_id, auth_token)
    
    if not flask_task:
        messages.error(request, 'Task not found or was deleted')
        return redirect('dashboard')
        
    task = get_object_or_404(Task, id=task_id, user=request.user)
    
    if request.method == 'POST':
        form = TaskForm(request.POST, instance=task)
        if form.is_valid():
            updated_task = form.save()

            try:
                if auth_token:
                    headers = {'Authorization': f'Bearer {auth_token}'}
                    task_data = {
                        'title': updated_task.title,
                        'description': updated_task.description,
                        'priority': updated_task.priority,
                        'due_date': updated_task.due_date.strftime('%Y-%m-%d') if updated_task.due_date else None
                    }
                    response = requests.put(f'{FLASK_API_BASE}/tasks/{task_id}', json=task_data, headers=headers)
                    if response.status_code != 200:
                        if flask_task:
                            task.title = flask_task['title']
                            task.description = flask_task.get('description', '')
                            task.priority = flask_task.get('priority', 0)
                            task.due_date = datetime.strptime(flask_task['due_date'], '%Y-%m-%d') if flask_task.get('due_date') else None
                            task.save()
                        messages.warning(request, 'Failed to sync task update with Task Manager')
                        return render(request, 'update_task.html', {'form': form})
            except requests.RequestException as e:
                messages.warning(request, f'Task update sync failed: {str(e)}')
            return redirect('dashboard')
    else:
        if flask_task:
            task.title = flask_task['title']
            task.description = flask_task.get('description', '')
            task.priority = flask_task.get('priority', 0)
            task.due_date = datetime.strptime(flask_task['due_date'], '%Y-%m-%d') if flask_task.get('due_date') else None
            task.save()
        form = TaskForm(instance=task)
    return render(request, 'update_task.html', {'form': form})

@login_required
def delete_task(request, task_id):
    auth_token = request.session.get('auth_token')
    
    task = get_object_or_404(Task, id=task_id, user=request.user)
    
    try:
        if auth_token:
            headers = {'Authorization': f'Bearer {auth_token}'}
            response = requests.delete(f'{FLASK_API_BASE}/tasks/{task_id}', headers=headers)
            if response.status_code != 200:
                messages.warning(request, 'Task deleted locally but failed to sync with Task Manager')
    except requests.RequestException as e:
        messages.warning(request, f'Task deleted locally but sync failed: {str(e)}')
    
    task.delete()
    messages.success(request, 'Task deleted successfully')
    
    return redirect('dashboard')

@login_required
def complete_task(request, task_id):
    auth_token = request.session.get('auth_token')
    flask_task = sync_task_with_flask(task_id, auth_token)
    
    if not flask_task:
        messages.error(request, 'Task not found or was deleted')
        return redirect('dashboard')
        
    task = get_object_or_404(Task, id=task_id, user=request.user)
    
    task.completed = True
    task.save()

    try:
        if auth_token:
            headers = {'Authorization': f'Bearer {auth_token}'}
            task_data = {
                'completed': True
            }
            response = requests.put(f'{FLASK_API_BASE}/tasks/{task_id}', json=task_data, headers=headers)
            if response.status_code != 200:
                if flask_task:
                    task.completed = flask_task.get('completed', False)
                    task.save()
                messages.warning(request, 'Failed to sync task completion with Task Manager')
                return redirect('dashboard')
    except requests.RequestException as e:
        messages.warning(request, f'Task completion sync failed: {str(e)}')
    
    return redirect('dashboard')

def filter_tasks(request):
    search_query = request.GET.get('search', '')
    filter_value = request.GET.get('filter', '')

    try:
        auth_token = request.session.get('auth_token')
        if auth_token:
            headers = {'Authorization': f'Bearer {auth_token}'}
            params = {}
            if search_query:
                params['search'] = search_query
            if filter_value:
                params['filter'] = filter_value
                
            response = requests.get(f'{FLASK_API_BASE}/tasks', headers=headers, params=params)
            if response.status_code == 200:
                tasks = response.json().get('tasks', [])
                task_objects = []
                for task_data in tasks:
                    task = Task(
                        id=task_data['id'],
                        title=task_data['title'],
                        description=task_data.get('description', ''),
                        priority=task_data.get('priority', 0),
                        completed=task_data.get('completed', False),
                        due_date=datetime.strptime(task_data['due_date'], '%Y-%m-%d') if task_data.get('due_date') else None
                    )
                    task_objects.append(task)
                html = render_to_string('partials/_task_list.html', {'tasks': task_objects})
                return JsonResponse({'html': html})
    except requests.RequestException:
        pass  

    tasks = Task.objects.filter(user=request.user)
    if search_query:
        tasks = tasks.filter(title__icontains=search_query)
    if filter_value == 'completed':
        tasks = tasks.filter(completed=True)
    elif filter_value == 'incomplete':
        tasks = tasks.filter(completed=False)
    elif filter_value == 'priority_high':
        tasks = tasks.filter(priority=3)
    elif filter_value == 'priority_medium':
        tasks = tasks.filter(priority=2)
    elif filter_value == 'priority_low':
        tasks = tasks.filter(priority=1)

    html = render_to_string('partials/_task_list.html', {'tasks': tasks})
    return JsonResponse({'html': html})

@login_required
def upcoming_tasks(request):
    today = now().date()
    end_of_week = today + timedelta(days=6 - today.weekday())
    end_of_month = (today.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
    first_day_of_next_month = (today.replace(day=28) + timedelta(days=4)).replace(day=1)
    last_day_of_next_month = (first_day_of_next_month.replace(day=1) + timedelta(days=32)).replace(day=1) - timedelta(days=1)

    all_tasks = []
    
    # Get tasks from Django DB
    django_tasks = Task.objects.filter(user=request.user, completed=False)
    all_tasks.extend(list(django_tasks))
    
    # Get tasks from Flask API
    try:
        auth_token = request.session.get('auth_token')
        if auth_token:
            headers = {'Authorization': f'Bearer {auth_token}'}
            response = requests.get(f'{FLASK_API_BASE}/tasks', headers=headers)
            if response.status_code == 200:
                flask_tasks = response.json().get('tasks', [])
                for task_data in flask_tasks:
                    if not task_data.get('completed', False):
                        task_exists = any(t.id == task_data['id'] for t in all_tasks)
                        if not task_exists:
                            try:
                                due_date = datetime.strptime(task_data['due_date'], '%Y-%m-%d').date() if task_data.get('due_date') else None
                                task = Task(
                                    id=task_data['id'],
                                    title=task_data['title'],
                                    description=task_data.get('description', ''),
                                    priority=task_data.get('priority', 0),
                                    completed=False,
                                    user=request.user,
                                    due_date=due_date
                                )
                                task.save()
                                all_tasks.append(task)
                            except Exception as e:
                                print(f"Error saving task: {str(e)}")
                                continue
    except requests.RequestException as e:
        print(f"Error fetching tasks from Flask API: {str(e)}")
        pass

    # Filter tasks by date ranges
    today_tasks = [t for t in all_tasks if t.due_date and t.due_date.date() == today]
    week_tasks = [t for t in all_tasks if t.due_date and today < t.due_date.date() <= end_of_week]
    month_tasks = [t for t in all_tasks if t.due_date and end_of_week < t.due_date.date() <= end_of_month]
    next_month_tasks = [t for t in all_tasks if t.due_date and first_day_of_next_month <= t.due_date.date() <= last_day_of_next_month]

    # Remove duplicates and sort by due date
    for task_list in [today_tasks, week_tasks, month_tasks, next_month_tasks]:
        task_list.sort(key=lambda x: (x.due_date is None, x.due_date, -x.priority))

    context = {
        'today_tasks': today_tasks,
        'week_tasks': week_tasks,
        'month_tasks': month_tasks,
        'next_month_tasks': next_month_tasks,
    }
    return render(request, 'upcoming.html', context)

def completed_tasks(request):
    all_completed_tasks = []
    
    django_tasks = Task.objects.filter(completed=True, user=request.user).order_by('-updated_at')
    all_completed_tasks.extend(list(django_tasks))
    
    try:
        auth_token = request.session.get('auth_token')
        if auth_token:
            headers = {'Authorization': f'Bearer {auth_token}'}
            response = requests.get(f'{FLASK_API_BASE}/tasks', headers=headers, params={'filter': 'completed'})
            if response.status_code == 200:
                flask_tasks = response.json().get('tasks', [])
                for task_data in flask_tasks:
                    task_exists = any(t.id == task_data['id'] for t in all_completed_tasks)
                    if not task_exists:
                        task = Task(
                            id=task_data['id'],
                            title=task_data['title'],
                            description=task_data.get('description', ''),
                            priority=task_data.get('priority', 0),
                            completed=True,
                            user=request.user,
                            due_date=datetime.strptime(task_data['due_date'], '%Y-%m-%d') if task_data.get('due_date') else None
                        )
                        try:
                            task.save()
                        except:
                            pass
                        all_completed_tasks.append(task)
    except requests.RequestException:
        pass

    all_completed_tasks.sort(key=lambda x: x.updated_at if x.updated_at else datetime.min, reverse=True)
    
    return render(request, 'completed_tasks.html', {'completed_tasks': all_completed_tasks})

