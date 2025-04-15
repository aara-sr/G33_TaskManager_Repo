from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .forms import TaskForm
from .models import Task


def index(request):
    return render(request, 'index.html')


@login_required
def dashboard(request):
    task_form = TaskForm()
    tasks = Task.objects.filter(user=request.user)
    return render(request, 'dashboard.html', {'task_form': task_form, 'tasks': tasks})
 

def about(request):
    return render(request, 'about.html')
