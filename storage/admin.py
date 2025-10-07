from django.contrib import admin
from .models import File, Folder, SharedLink ,UserProfile

@admin.register(File)
class FileAdmin(admin.ModelAdmin):
    list_display = ['name', 'owner', 'folder', 'file_size', 'created_at']
    list_filter = ['file_type', 'created_at', 'owner']
    search_fields = ['name', 'description']
    readonly_fields = ['file_size', 'share_token', 'created_at', 'updated_at']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(owner=request.user)

@admin.register(Folder)
class FolderAdmin(admin.ModelAdmin):
    list_display = ['name', 'owner', 'parent', 'created_at']
    list_filter = ['created_at', 'owner']
    search_fields = ['name']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(owner=request.user)

@admin.register(SharedLink)
class SharedLinkAdmin(admin.ModelAdmin):
    list_display = ['file', 'token', 'created_by', 'expires_at', 'download_count', 'is_active']
    list_filter = ['is_active', 'created_at', 'expires_at']
    readonly_fields = ['token', 'download_count', 'created_at']

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'phone', 'location', 'created_at']
    search_fields = ['user__username', 'phone']