from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse
import os
import uuid
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from django.utils import timezone
from datetime import timedelta


def user_directory_path(instance, filename):
    return f'user_{instance.owner.id}/{filename}'


class Folder(models.Model):
    name = models.CharField(max_length=255, verbose_name='資料夾名稱')
    owner = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='擁有者')
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.CASCADE, verbose_name='上層資料夾')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='建立時間')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新時間')
    is_deleted = models.BooleanField(default=False, verbose_name='是否刪除')
    deleted_at = models.DateTimeField(null=True, blank=True, verbose_name='刪除時間')
    
    class Meta:
        verbose_name = '資料夾'
        verbose_name_plural = '資料夾'
        unique_together = ['name', 'parent', 'owner']
    
    def __str__(self):
        return self.name
    
    def get_absolute_url(self):
        return reverse('folder_detail', kwargs={'pk': self.pk})
    
    def get_path(self):
        path = []
        folder = self
        while folder:
            path.append(folder.name)
            folder = folder.parent
        return '/'.join(reversed(path))


class File(models.Model):
    name = models.CharField(max_length=255, verbose_name='檔案名稱')
    file = models.FileField(upload_to='', verbose_name='檔案')
    folder = models.ForeignKey(Folder, null=True, blank=True, on_delete=models.CASCADE, verbose_name='所在資料夾')
    owner = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='擁有者')
    file_type = models.CharField(max_length=100, blank=True, verbose_name='檔案類型')
    file_size = models.BigIntegerField(default=0, verbose_name='檔案大小')
    description = models.TextField(blank=True, verbose_name='描述')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='上傳時間')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新時間')
    is_shared = models.BooleanField(default=False, verbose_name='是否分享')
    share_token = models.UUIDField(default=uuid.uuid4, unique=True, verbose_name='分享代碼')
    thumbnail = models.ImageField(upload_to='thumbnails/', blank=True, null=True, verbose_name='縮圖')
    is_deleted = models.BooleanField(default=False, verbose_name='是否刪除')
    deleted_at = models.DateTimeField(null=True, blank=True, verbose_name='刪除時間')
    file_hash = models.CharField(max_length=64, blank=True, null=True, db_index=True, verbose_name='檔案 Hash')
    tags = models.CharField(max_length=500, blank=True, verbose_name='標籤')
    
    class Meta:
        verbose_name = '檔案'
        verbose_name_plural = '檔案'
    
    def __str__(self):
        return self.name
    
    def get_absolute_url(self):
        return reverse('file_detail', kwargs={'pk': self.pk})
    
    def get_file_extension(self):
        return os.path.splitext(self.file.name)[1].lower()
    
    def is_document(self):
        doc_extensions = ['.pdf', '.doc', '.docx', '.txt', '.rtf']
        return self.get_file_extension() in doc_extensions
    
    def is_image(self):
        image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg']
        return self.get_file_extension() in image_extensions

    def is_video(self):
        video_extensions = ['.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm', '.mkv', '.m4v']
        return self.get_file_extension() in video_extensions

    def is_audio(self):
        audio_extensions = ['.mp3', '.wav', '.flac', '.aac', '.ogg', '.wma', '.m4a']
        return self.get_file_extension() in audio_extensions

    def is_media(self):
        return self.is_image() or self.is_video() or self.is_audio()
    
    def get_size_display(self):
        size = self.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
    
    def get_tags_list(self):
        if self.tags:
            return [tag.strip() for tag in self.tags.split(',') if tag.strip()]
        return []

    def days_until_delete(self):
        if self.deleted_at:
            delete_date = self.deleted_at + timedelta(days=30)
            remaining = (delete_date - timezone.now()).days
            return max(0, remaining)
        return 30
    
    def calculate_hash(self):
        import hashlib
        
        if not self.file or not os.path.exists(self.file.path):
            return None
        
        sha256_hash = hashlib.sha256()
        
        try:
            with open(self.file.path, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except Exception as e:
            print(f"計算 hash 失敗 {self.name}: {e}")
            return None
    
    def save(self, *args, **kwargs):

        is_new = not self.pk
        if self.file:
            self.file_size = self.file.size
            if not self.name:
                self.name = self.file.name
        super().save(*args, **kwargs)

        # 新文件且为图片时生成缩图
        if is_new and self.is_image():
            self.create_thumbnail()

    def create_thumbnail(self):
        from PIL import Image
        from django.core.files.base import ContentFile
        import io
        
        if not self.is_image():
            return
        
        try:
            # 确保 thumbnails 目录存在
            thumb_dir = os.path.join(settings.MEDIA_ROOT, 'thumbnails')
            os.makedirs(thumb_dir, exist_ok=True)
            
            # 打开原图
            image_path = self.file.path
            if not os.path.exists(image_path):
                print(f"圖片不存在: {image_path}")
                return
            
            img = Image.open(image_path)
            
            # 转换 RGBA 为 RGB
            if img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                if img.mode in ('RGBA', 'LA'):
                    background.paste(img, mask=img.split()[-1])
                    img = background
            
            # 生成缩图
            img.thumbnail((300, 300), Image.Resampling.LANCZOS)
            
            # 储存到记忆体
            thumb_io = io.BytesIO()
            img.save(thumb_io, format='JPEG', quality=85)
            
            # 产生档名
            thumb_filename = f"thumb_{self.id}.jpg"
            
            # 储存
            self.thumbnail.save(
                thumb_filename,
                ContentFile(thumb_io.getvalue()),
                save=False
            )
            
            File.objects.filter(pk=self.pk).update(thumbnail=self.thumbnail)
            print(f"✓ 縮圖已生成: {thumb_filename}")
            
        except Exception as e:
            print(f"✗ 生成縮圖失敗 {self.name}: {e}")
            import traceback
            traceback.print_exc()
    
    def get_thumbnail_url(self):
        if self.thumbnail:
            return self.thumbnail.url
        elif self.is_image():
            return self.file.url
        return None


class SharedLink(models.Model):
    file = models.ForeignKey(File, on_delete=models.CASCADE, verbose_name='檔案')
    token = models.UUIDField(default=uuid.uuid4, unique=True, verbose_name='分享代碼')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='建立者')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='建立時間')
    expires_at = models.DateTimeField(null=True, blank=True, verbose_name='到期時間')
    download_count = models.IntegerField(default=0, verbose_name='下載次數')
    max_downloads = models.IntegerField(null=True, blank=True, verbose_name='最大下載次數')
    is_active = models.BooleanField(default=True, verbose_name='是否啟用')
    
    class Meta:
        verbose_name = '分享連結'
        verbose_name_plural = '分享連結'
    
    def __str__(self):
        return f"{self.file.name} - {self.token}"
    
    def is_expired(self):
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False
    
    def can_download(self):
        if not self.is_active or self.is_expired():
            return False
        if self.max_downloads and self.download_count >= self.max_downloads:
            return False
        return True


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True, verbose_name='大頭貼')
    bio = models.TextField(blank=True, max_length=500, verbose_name='個人簡介')
    phone = models.CharField(max_length=20, blank=True, verbose_name='電話')
    location = models.CharField(max_length=100, blank=True, verbose_name='地點')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='建立時間')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新時間')
    
    class Meta:
        verbose_name = '用戶資料'
        verbose_name_plural = '用戶資料'
    
    def __str__(self):
        return f"{self.user.username} 的資料"
    
    def get_avatar_url(self):#獲取頭像
        if self.avatar:
            return self.avatar.url
        return None


# 信號處理
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs): 
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs): 
        instance.profile.save()