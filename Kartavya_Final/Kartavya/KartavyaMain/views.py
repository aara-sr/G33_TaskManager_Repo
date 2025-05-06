from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .forms import TaskForm
from .models import Task
import requests
from datetime import datetime

FLASK_API_BASE = 'http://localhost:5000/api'

def index(request):
    return render(request, 'index.html')

@login_required 
def dashboard(request):
    task_form = TaskForm()
    all_tasks = []
    flask_task_ids = set()

    try:
        auth_token = request.session.get('auth_token')
        if auth_token:
            headers = {'Authorization': f'Bearer {auth_token}'}
            response = requests.get(f'{FLASK_API_BASE}/tasks', headers=headers)
            
            if response.status_code == 200:
                flask_tasks = response.json().get('tasks', [])
                flask_task_ids = {task['id'] for task in flask_tasks}
                
                for task_data in flask_tasks:
                    try:
                        existing_task = Task.objects.get(id=task_data['id'])
                        existing_task.title = task_data['title']
                        existing_task.description = task_data.get('description', '')
                        existing_task.priority = task_data.get('priority', 1)
                        existing_task.completed = task_data.get('completed', False)
                        existing_task.due_date = datetime.strptime(task_data['due_date'], '%Y-%m-%d') if task_data.get('due_date') else None
                        existing_task.save()
                        all_tasks.append(existing_task)
                    except Task.DoesNotExist:
                        task = Task(
                            id=task_data['id'],
                            title=task_data['title'],
                            description=task_data.get('description', ''),
                            priority=task_data.get('priority', 1),
                            completed=task_data.get('completed', False),
                            user=request.user,
                            due_date=datetime.strptime(task_data['due_date'], '%Y-%m-%d') if task_data.get('due_date') else None
                        )
                        task.save()
                        all_tasks.append(task)

    except requests.RequestException:
        pass

    django_tasks = Task.objects.filter(user=request.user)
    for django_task in django_tasks:
        if django_task.id not in flask_task_ids:
            django_task.delete()
        elif not any(t.id == django_task.id for t in all_tasks):
            all_tasks.append(django_task)

    all_tasks.sort(key=lambda x: (-x.priority, x.completed))
    
    return render(request, 'dashboard.html', {
        'task_form': task_form, 
        'tasks': all_tasks
    })

def about(request):
    return render(request, 'about.html')
