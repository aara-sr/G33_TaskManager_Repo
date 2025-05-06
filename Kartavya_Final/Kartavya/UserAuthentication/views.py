import requests
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, update_session_auth_hash, authenticate
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib import messages
from .forms import RegisterForm, LoginForm, UpdateProfileForm
from .models import UserProfile

FLASK_API_BASE = 'http://localhost:5000/api'

def register_view(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            password1 = form.cleaned_data['password1']
            password2 = form.cleaned_data['password2']
            if password1 != password2:
                form.add_error('password2', 'Passwords do not match.')
            else:
                flask_data = {
                    'username': form.cleaned_data['username'],
                    'email': form.cleaned_data['email'],
                    'password': password1
                }
                
                try:
                    response = requests.post(f'{FLASK_API_BASE}/register', json=flask_data)
                    if response.status_code != 201:
                        messages.error(request, response.json().get('error', 'Failed to register with task manager'))
                        return render(request, 'register.html', {'form': form})
                        
                    user = form.save(commit=False)
                    user.set_password(password1)
                    user.save()

                    profile = UserProfile.objects.create(
                        user=user,
                        age=form.cleaned_data.get('age'),
                        gender=form.cleaned_data.get('gender'),
                        mobile_number=form.cleaned_data.get('mobile_number')
                    )

                    login(request, user)
                    login_data = {
                        'email': user.email,
                        'password': password1
                    }
                    login_response = requests.post(f'{FLASK_API_BASE}/login', json=login_data)
                    if login_response.status_code == 200:
                        request.session['auth_token'] = login_response.json().get('token')
                    
                    return redirect('dashboard')
                    
                except requests.RequestException as e:
                    messages.error(request, f'Error connecting to task manager: {str(e)}')
                    return render(request, 'register.html', {'form': form})
                    
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = RegisterForm()

    return render(request, 'register.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('email')
            username = form.cleaned_data.get('username')
            password = form.cleaned_data['password']

            try:
                if email:
                    try:
                        username = User.objects.get(email=email).username
                    except User.DoesNotExist:
                        messages.error(request, "No user found with this email.")
                        return render(request, 'login.html', {'form': form})
                
                user = authenticate(username=username, password=password)
                if user is not None:
                    login(request, user)
                    messages.success(request, 'Login successful.')

                    try:
                        response = requests.post(f'{FLASK_API_BASE}/login', 
                            json={'username': username, 'password': password})
                        if response.status_code == 200:
                            request.session['auth_token'] = response.json().get('token')
                        else:
                            messages.warning(request, 'Connected to Django but Flask sync failed')
                    except requests.RequestException:
                        messages.warning(request, 'Connected to Django but Flask sync failed')
                    
                    return redirect('dashboard')
                
                else:
                    try:
                        login_data = {
                            'username': username,
                            'email': email,
                            'password': password
                        }
                        response = requests.post(f'{FLASK_API_BASE}/login', json=login_data)
                        
                        if response.status_code == 200:
                            user_data = response.json().get('user', {})
                            
                            try:
                                user = User.objects.get(username=user_data['username'])
                            except User.DoesNotExist:
                                user = User.objects.create_user(
                                    username=user_data['username'],
                                    email=user_data['email'],
                                    password=password
                                )
                                UserProfile.objects.create(user=user)
                            
                            request.session['auth_token'] = response.json().get('token')
                            login(request, user)
                            messages.success(request, 'Login successful')
                            return redirect('dashboard')
                        else:
                            messages.error(request, 'Invalid credentials')
                    except requests.RequestException as e:
                        messages.error(request, f'Error connecting to Task Manager: {str(e)}')
            except Exception as e:
                messages.error(request, f'Login error: {str(e)}')
    else:
        form = LoginForm()

    return render(request, 'login.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('index')

@login_required
def profile_view(request):
    user = request.user
    try:
        profile = user.profile
    except UserProfile.DoesNotExist:
        profile = UserProfile.objects.create(user=user)
    
    if request.method == 'POST':
        if 'profile_picture' in request.FILES:
            profile.profile_picture = request.FILES['profile_picture']
            profile.save()
            messages.success(request, 'Profile picture updated successfully.')
            return redirect('profile')
            
        form = UpdateProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile has been updated successfully.')
            return redirect('profile')
    else:
        form = UpdateProfileForm(instance=profile)

    # Get task statistics from Flask API
    task_stats = {'total_tasks': 0, 'completed_tasks': 0}
    try:
        auth_token = request.session.get('auth_token')
        if auth_token:
            headers = {'Authorization': f'Bearer {auth_token}'}
            response = requests.get(f'{FLASK_API_BASE}/tasks/stats', headers=headers)
            if response.status_code == 200:
                task_stats = response.json()
    except requests.RequestException:
        pass

    password_form = PasswordChangeForm(user=user)
    context = {
        'form': form,
        'password_form': password_form,
        'task_stats': task_stats,
        'profile': profile
    }
    return render(request, 'profile.html', context)

@login_required
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Your password was successfully updated!')
        else:
            messages.error(request, 'Please correct the error below.')
    return redirect('profile')

@login_required
def delete_account(request):
    user = request.user
    logout(request)
    user.delete()
    messages.success(request, "Your account has been permanently deleted.")
    return redirect('login')
