from django import forms
from .models import File, Folder, SharedLink, UserProfile
from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm
from django.contrib.auth.models import User


class FileUploadForm(forms.ModelForm):
    """檔案上傳表單"""
    class Meta:
        model = File
        fields = ['file', 'description']
        widgets = {
            'file': forms.FileInput(attrs={'class': 'form-control-file'}),
            'description': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 3,
                'placeholder': '輸入檔案描述（選填）'
            }),
        }
        labels = {
            'file': '選擇檔案',
            'description': '檔案描述',
        }


class FolderCreateForm(forms.ModelForm):
    """資料夾建立表單"""
    class Meta:
        model = Folder
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': '資料夾名稱',
                'autocomplete': 'off'
            }),
        }
        labels = {
            'name': '資料夾名稱',
        }


class FileEditForm(forms.ModelForm):
    """檔案編輯表單"""
    class Meta:
        model = File
        fields = ['name', 'description', 'tags']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '檔案名稱'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 3,
                'placeholder': '檔案描述（選填）'
            }),
            'tags': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': '用逗號分隔，例如：工作, 重要, 2024'
            }),
        }
        labels = {
            'name': '檔案名稱',
            'description': '檔案描述',
            'tags': '標籤',
        }


class SharedLinkForm(forms.ModelForm):
    """分享連結建立表單"""
    class Meta:
        model = SharedLink
        fields = ['expires_at', 'max_downloads']
        widgets = {
            'expires_at': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local',
                'placeholder': '留空表示永不過期'
            }),
            'max_downloads': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '留空表示無限制',
                'min': '1'
            }),
        }
        labels = {
            'expires_at': '過期時間',
            'max_downloads': '最大下載次數',
        }


class CustomUserCreationForm(UserCreationForm):
    """自訂使用者註冊表單"""
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': '電子郵件'
        }),
        label='電子郵件'
    )
    
    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '使用者名稱'
            }),
        }
        labels = {
            'username': '使用者名稱',
        }
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 為所有欄位添加 Bootstrap 樣式
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'
        
        # 設定密碼欄位的 placeholder
        self.fields['password1'].widget.attrs['placeholder'] = '密碼'
        self.fields['password2'].widget.attrs['placeholder'] = '確認密碼'
        
        # 設定欄位標籤
        self.fields['password1'].label = '密碼'
        self.fields['password2'].label = '確認密碼'


class UserProfileForm(forms.ModelForm):
    """使用者資料編輯表單"""
    class Meta:
        model = UserProfile
        fields = ['avatar', 'bio', 'phone', 'location']
        widgets = {
            'avatar': forms.FileInput(attrs={
                'class': 'form-control', 
                'accept': 'image/*'
            }),
            'bio': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 4,
                'placeholder': '簡短介紹你自己...'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '聯絡電話'
            }),
            'location': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '所在地點'
            }),
        }
        labels = {
            'avatar': '大頭貼',
            'bio': '個人簡介',
            'phone': '電話',
            'location': '地點',
        }


class UserEditForm(forms.ModelForm):
    """使用者基本資訊編輯表單"""
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '名字'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '姓氏'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': '電子郵件'
            }),
        }
        labels = {
            'first_name': '名字',
            'last_name': '姓氏',
            'email': '電子郵件',
        }


class CustomPasswordChangeForm(PasswordChangeForm):
    """自訂密碼修改表單"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 為所有欄位添加 Bootstrap 樣式
        for field_name, field in self.fields.items():
            field.widget.attrs['class'] = 'form-control'
            
        # 設定 placeholder 和標籤
        self.fields['old_password'].widget.attrs['placeholder'] = '目前密碼'
        self.fields['new_password1'].widget.attrs['placeholder'] = '新密碼'
        self.fields['new_password2'].widget.attrs['placeholder'] = '確認新密碼'
        
        self.fields['old_password'].label = '目前密碼'
        self.fields['new_password1'].label = '新密碼'
        self.fields['new_password2'].label = '確認新密碼'