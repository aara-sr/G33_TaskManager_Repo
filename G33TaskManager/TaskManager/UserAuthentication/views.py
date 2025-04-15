from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib import messages
from django.shortcuts import render, redirect
from .forms import RegisterForm, LoginForm, UpdateProfileForm
from .models import  UserProfile
# Create your views here.

def register_view(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            # profile = UserProfile.objects.create(
            #     user=user,
            #     age=form.cleaned_data.get('age'),
            #     gender=form.cleaned_data.get('gender'),
            #     mobile_number=form.cleaned_data.get('mobile_number')
            # )
            login(request, user)
            return redirect('dashboard')
    else:
        form = RegisterForm()
    return render(request, 'register.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request.POST) 
        if form.is_valid():
            login(request, form.get_user())
            return redirect('dashboard')
    else:
        form = LoginForm()
    
    return render(request, 'login.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('index')

@login_required
def profile_view(request):
    user = request.user
    if request.method == 'POST':
        form = UpdateProfileForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile has been updated.')
            return redirect('profile')
    else:
        form = UpdateProfileForm(instance=user)
    
    password_form = PasswordChangeForm(user=user)
    return render(request, 'profile.html', {
        'form': form,
        'password_form': password_form
    })

@login_required
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Your password was successfully updated.')
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