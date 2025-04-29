from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.utils.timezone import now
from datetime import timedelta
from KartavyaMain.forms import TaskForm
from KartavyaMain.models import Task
from django.http import JsonResponse
from django.template.loader import render_to_string
# Create your views here.

@login_required
def add_task(request):
    if request.method == 'POST':
        form = TaskForm(request.POST)
        if form.is_valid():
            task = form.save(commit=False)
            task.user = request.user 
            task.save()
    return redirect('dashboard')

@login_required
def update_task(request, task_id):
    task = get_object_or_404(Task, id=task_id, user=request.user)
    if request.method == 'POST':
        form = TaskForm(request.POST, instance=task)
        if form.is_valid():
            form.save()
            return redirect('dashboard')
    else:
        form = TaskForm(instance=task)
    return render(request, 'update_task.html', {'form': form})

@login_required
def delete_task(request, task_id):
    task = get_object_or_404(Task, id=task_id, user=request.user)
    task.delete()
    return redirect('dashboard')

@login_required
def complete_task(request, task_id):
    task = get_object_or_404(Task, id=task_id, user=request.user)
    task.completed = True
    task.save()
    return redirect('dashboard')

def filter_tasks(request):
    search_query = request.GET.get('search', '')
    filter_value = request.GET.get('filter', '')

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
    end_of_week = today + timedelta(days=6 - today.weekday())  # Sunday
    end_of_month = (today.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
    first_day_of_next_month = (today.replace(day=28) + timedelta(days=4)).replace(day=1)
    last_day_of_next_month = (first_day_of_next_month.replace(month=first_day_of_next_month.month + 1) - timedelta(days=1))

    user_tasks = Task.objects.filter(user=request.user, completed=False)

    today_tasks = user_tasks.filter(due_date=today)
    week_tasks = user_tasks.filter(due_date__range=(today, end_of_week))
    month_tasks = user_tasks.filter(due_date__range=(today, end_of_month))
    next_month_tasks = user_tasks.filter(due_date__range=(first_day_of_next_month, last_day_of_next_month))

    context = {
        'today_tasks': today_tasks,
        'week_tasks': week_tasks,
        'month_tasks': month_tasks,
        'next_month_tasks': next_month_tasks,
    }

    return render(request, 'upcoming.html', context)


def completed_tasks(request):
    completed = Task.objects.filter(completed=True).order_by('-updated_at') 
    return render(request, 'completed_tasks.html', {'completed_tasks': completed})

