from django.db import models
from .models import Post, Group, Comment
from django import forms



class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ['group', 'text', 'image']
        required = {
            "group": False,
        }
        labels = {
            "text": "Текст записи",        
            "group": "Сообщества",
            "image": "Картинки"
        }
        

class CommentForm(forms.ModelForm):
    text = forms.CharField(widget=forms.Textarea)
    
    class Meta:
        model = Comment
        fields = ('text',)
        labels = {
            'text': 'Текст'
        }