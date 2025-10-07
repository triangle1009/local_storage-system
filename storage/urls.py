from django.urls import path
from storage import views
from . import views

app_name = 'storage'

urlpatterns = [

    # API 路徑
    path('api/search-suggestions/', views.search_suggestions, name='search_suggestions'),
    
    # 首頁和主要功能
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    # 檔案操作
    path('upload/', views.file_upload, name='file_upload'),
    path('file/<int:pk>/download/', views.file_download, name='file_download'),
    path('file/<int:pk>/view/', views.file_view, name='file_view'),
    path('file/<int:pk>/edit/', views.file_edit, name='file_edit'),
    path('file/<int:pk>/delete/', views.file_delete, name='file_delete'),
    path('file/<int:pk>/info/', views.ajax_file_info, name='file_info'),
    path('file/<int:pk>/move/', views.file_move, name='file_move'),
    path('file/<int:pk>/preview/', views.file_preview, name='file_preview'),
    # 資料夾操作
    path('create-folder/', views.folder_create, name='folder_create'),
    path('folder/<int:pk>/delete/', views.folder_delete, name='folder_delete'),
    # 分享功能
    path('file/<int:pk>/share/', views.create_share_link, name='create_share'),
    path('share/<uuid:token>/', views.shared_file_download, name='shared_download'),
    path('shares/', views.manage_shares, name='manage_shares'),
    path('share/<int:pk>/toggle/', views.toggle_share, name='toggle_share'),
    path('share/<int:pk>/delete/', views.delete_share, name='delete_share'),
    # 統計與個人資料功能
    path('stats/', views.storage_stats, name='storage_stats'),
    path('profile/', views.user_profile, name='user_profile'),
    path('profile/edit/', views.profile_edit, name='profile_edit'),
    path('profile/change-password/', views.change_password, name='change_password'),
    # 登出
    path('logout/', views.custom_logout, name='custom_logout'),
    #批次檔案
    path('batch-download-zip/', views.batch_download_zip, name='batch_download_zip'),
    path('batch-delete/', views.batch_delete, name='batch_delete'),
    # 資料夾批量操作
    path('batch-download-folders/', views.batch_download_folders, name='batch_download_folders'),
    path('batch-delete-folders/', views.batch_delete_folders, name='batch_delete_folders'),
    # 回收站功能
    path('trash/', views.trash, name='trash'),
    path('file/<int:pk>/restore/', views.restore_file, name='restore_file'),
    path('folder/<int:pk>/restore/', views.restore_folder, name='restore_folder'),
    path('file/<int:pk>/permanent-delete/', views.permanent_delete_file, name='permanent_delete_file'),
    path('folder/<int:pk>/permanent-delete/', views.permanent_delete_folder, name='permanent_delete_folder'),
    path('trash/empty/', views.empty_trash, name='empty_trash'),
    path('batch-restore/', views.batch_restore, name='batch_restore'),
    path('batch-permanent-delete/', views.batch_permanent_delete, name='batch_permanent_delete'),
    
    #檔案去重複
    path('duplicates/', views.duplicates, name='duplicates'),
    path('file/<int:pk>/delete-duplicate/', views.delete_duplicate, name='delete_duplicate'),
]