from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from .models import UserProfile

class RegisterForm(UserCreationForm):
    email = forms.EmailField()
    age = forms.IntegerField(required=False)
    gender = forms.ChoiceField(choices=UserProfile.GENDER_CHOICES, required=False)
    mobile_number = forms.CharField(max_length=15, required=False)

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2', 'age', 'gender', 'mobile_number']

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Email already in use.")
        return email

class LoginForm(forms.Form):
    email = forms.EmailField(required=False, widget=forms.EmailInput(attrs={'placeholder': 'Email'}))
    username = forms.CharField(required=False, widget=forms.TextInput(attrs={'placeholder': 'Username'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Password'}))

    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email')
        username = cleaned_data.get('username')
        password = cleaned_data.get('password')

        if not password or not (email or username):
            raise forms.ValidationError("Please enter either email or username along with the password.")
        return cleaned_data

class UpdateProfileForm(forms.ModelForm):
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-control'}))
    username = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control'}))
    
    class Meta:
        model = UserProfile
        fields = ['profile_picture', 'age', 'gender', 'mobile_number']
        widgets = {
            'age': forms.NumberInput(attrs={'class': 'form-control'}),
            'gender': forms.Select(attrs={'class': 'form-control'}),
            'mobile_number': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.user:
            self.fields['email'].initial = self.instance.user.email
            self.fields['username'].initial = self.instance.user.username
            
    def save(self, commit=True):
        profile = super().save(commit=False)
        if commit:
            # Save user data
            user = profile.user
            user.email = self.cleaned_data['email']
            user.username = self.cleaned_data['username']
            user.save()
            profile.save()
        return profile
