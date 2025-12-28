# users/forms.py
from django import forms
from .models import CustomUser

class UserForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['email', 'first_name', 'last_name', 'is_active', 'role']
        widgets = {
            'role': forms.Select(attrs={'class': 'form-control'}),
        }
