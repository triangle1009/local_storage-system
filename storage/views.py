from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login , update_session_auth_hash
from django.contrib import messages
from django.http import HttpResponse, Http404, JsonResponse ,FileResponse
from django.db.models import Q,Sum,Count
import os
import mimetypes
from .models import File, Folder, SharedLink ,UserProfile
from .forms import FileUploadForm, FolderCreateForm, FileEditForm, SharedLinkForm, CustomUserCreationForm , UserEditForm, UserProfileForm, CustomPasswordChangeForm
from django.contrib.auth import logout
import re
from django.urls import reverse
from django.db import IntegrityError
from django.contrib.auth.models import User
from django.utils import timezone
import zipfile
from io import BytesIO
# Create your views here.

def register(request):  #使用者註冊
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, '註冊成功！歡迎使用本地端儲存系統。')
            return redirect('storage:home')  # 改成這樣，使用命名空間
    else:
        form = CustomUserCreationForm()
    return render(request, 'registration/register.html', {'form': form})

@login_required
def home(request): #主頁面
    folder_id = request.GET.get('folder')
    search_query = request.GET.get('search', '').strip()  # 新增搜尋參數
    current_folder = None
    total_system_storage = 100 * 1024 * 1024 * 1024  # 100GB 系統總容量
    total_users = User.objects.count()
    user_quota = int((total_system_storage * 0.9) / total_users) if total_users > 0 else 0
    # 用戶已使用空間
    user_files = File.objects.filter(owner=request.user)
    total_size = sum(f.file_size for f in user_files)

    # 計算百分比
    usage_percentage = (total_size / user_quota * 100) if user_quota > 0 else 0
    usage_percentage = min(usage_percentage, 100)

    if folder_id:
        current_folder = get_object_or_404(Folder, pk=folder_id, owner=request.user)
    
    # 取得當前資料夾下的子資料夾
    folders = Folder.objects.filter(
        owner=request.user,
        parent=current_folder,
        is_deleted=False
    ).order_by('name')
    
    # 取得當前資料夾下的檔案
    files = File.objects.filter(
        owner=request.user,
        folder=current_folder,
        is_deleted=False
    )
    
    # 如果有搜尋查詢，則進行全域搜尋
    if search_query:
        files = File.objects.filter(
            owner=request.user
        ).filter(
            Q(name__icontains=search_query) | 
            Q(description__icontains=search_query) |
            Q(tags__icontains=search_query)
        )
        folders = Folder.objects.filter(
            owner=request.user
        ).filter(name__icontains=search_query)
        
        # 搜尋時顯示完整路徑
        for file in files:
            if file.folder:
                file.full_path = file.folder.get_path() + '/' + file.name
            else:
                file.full_path = file.name
    
    files = files.order_by('-created_at')
    
    # 取得所有資料夾供移動檔案使用
    all_folders = Folder.objects.filter(owner=request.user).order_by('name')
    
    # 為媒體檔案（圖片、影片和音樂）添加導航資訊
    media_files = [f for f in files if f.is_image() or f.is_video() or f.is_audio()]
    for i, media_file in enumerate(media_files):
        media_file.prev_media = media_files[i - 1] if i > 0 else None
        media_file.next_media = media_files[i + 1] if i < len(media_files) - 1 else None



    image_files = [f for f in files if f.is_image()]
    for i, file in enumerate(files): 
        if file.is_image():
            file_index = image_files.index(file)
            file.prev_image = image_files[file_index - 1] if file_index > 0 else None
            file.next_image = image_files[file_index + 1] if file_index < len(image_files) - 1 else None
    
    context = {
        'current_folder': current_folder,
        'folders': folders,
        'files': files,
        'all_folders': all_folders,
        'search_query': search_query,
        'is_search_result': bool(search_query),
        # 添加這些新變數
        'usage_percentage': usage_percentage,
        'total_size': total_size,
        'user_quota': user_quota,
        'total_users': total_users,}
    
    return render(request, 'storage/home.html', context)

@login_required
def file_upload(request):
    if request.method == 'POST':
        form = FileUploadForm(request.POST, request.FILES)
        if form.is_valid():
            file_obj = form.save(commit=False)
            file_obj.owner = request.user
            
            folder_id = request.POST.get('folder_id')
            if folder_id:
                file_obj.folder = get_object_or_404(Folder, pk=folder_id, owner=request.user)
            
            if file_obj.file:
                file_obj.file_type = mimetypes.guess_type(file_obj.file.name)[0] or 'unknown'
            
            # 配額檢查
            total_users = User.objects.count()
            user_quota = int((100 * 1024 * 1024 * 1024 * 0.9) / total_users) if total_users > 0 else 0
            user_files = File.objects.filter(owner=request.user)
            current_usage = sum(f.file_size for f in user_files)
            new_file_size = file_obj.file.size

            if current_usage + new_file_size > user_quota:
                messages.error(request, f'儲存空間不足!')
                return redirect('storage:home')
            
            file_obj.save()

            # 計算 hash（新增這段）
            hash_value = file_obj.calculate_hash()
            if hash_value:
                file_obj.file_hash = hash_value
                file_obj.save(update_fields=['file_hash'])
            messages.success(request, f'檔案 {file_obj.name} 上傳成功!')
        else:
            messages.error(request, '檔案上傳失敗')
    
    return redirect('storage:home')

@login_required
def folder_create(request): #資料夾建立
    if request.method == 'POST':
        form = FolderCreateForm(request.POST)
        if form.is_valid():
            folder = form.save(commit=False)
            folder.owner = request.user
            
            # 獲取 parent_id，並確保它是有效的數字
            parent_id = request.POST.get('parent_id')
            if parent_id and parent_id.isdigit():
                try:
                    parent_folder = get_object_or_404(Folder, pk=parent_id, owner=request.user)
                    folder.parent = parent_folder
                except Http404:
                    messages.error(request, '指定的上層資料夾不存在。')
                    return redirect('storage:home')
            else:
                # 當 parent_id 為 None、空字串或非數字時，將其設定為根目錄
                folder.parent = None 

            try:
                folder.save()
                parent_name = folder.parent.name if folder.parent else "根目錄"
                messages.success(request, f'資料夾 "{folder.name}" 已在 "{parent_name}" 中建立成功！')
                
                if folder.parent:
                    return redirect(f"{reverse('storage:home')}?folder={folder.parent.pk}")
                else:
                    return redirect('storage:home')
            
            except IntegrityError:
                messages.error(request, f'資料夾建立失敗：在同一層級下已存在名稱為 "{folder.name}" 的資料夾。')
            except Exception as e:
                messages.error(request, f'資料夾建立失敗：{str(e)}')
        
        else:
            messages.error(request, '資料夾建立失敗，請檢查輸入內容。')
    
    current_folder_id = request.POST.get('parent_id') or request.GET.get('folder')
    if current_folder_id and current_folder_id.isdigit():
        return redirect(f"{reverse('storage:home')}?folder={current_folder_id}")
    else:
        return redirect('storage:home')

@login_required
def file_download(request, pk): #檔案下載
    file_obj = get_object_or_404(File, pk=pk, owner=request.user)
    
    try:
        file_path = file_obj.file.path
        if os.path.exists(file_path):
            with open(file_path, 'rb') as fh:
                response = HttpResponse(fh.read(), content_type=mimetypes.guess_type(file_path)[0])
                response['Content-Disposition'] = f'attachment; filename="{file_obj.name}"'
                return response
    except:
        pass
    
    raise Http404("檔案不存在")

@login_required
def file_view(request, pk): #檔案預覽
    file_obj = get_object_or_404(File, pk=pk, owner=request.user)
    
    if file_obj.is_image():
        try:
            file_path = file_obj.file.path
            if os.path.exists(file_path):
                with open(file_path, 'rb') as fh:
                    response = HttpResponse(fh.read(), content_type=mimetypes.guess_type(file_path)[0])
                    return response
        except:
            pass
    
    return redirect('file_download', pk=pk)

@login_required
def file_edit(request, pk): #編輯檔案資訊
    file_obj = get_object_or_404(File, pk=pk, owner=request.user)
    
    if request.method == 'POST':
        form = FileEditForm(request.POST, instance=file_obj)
        if form.is_valid():
            form.save()
            messages.success(request, '檔案資訊更新成功！')
            return redirect('storage:home')
    else:
        form = FileEditForm(instance=file_obj)
    
    return render(request, 'storage/file_edit.html', {'form': form, 'file': file_obj})

@login_required
def storage_stats(request): #儲存空間統計
    user_files = File.objects.filter(owner=request.user)
    
    # 計算統計資料
    total_files = user_files.count()
    total_size = sum(f.file_size for f in user_files)
    
    # 動態計算儲存空間
    from django.contrib.auth.models import User
    total_system_storage = 100 * 1024 * 1024 * 1024
    total_users = User.objects.count()
    user_quota = int((total_system_storage * 0.9) / total_users) if total_users > 0 else 0
    
    # 計算使用百分比
    if user_quota > 0:
        usage_percentage = (total_size / user_quota) * 100
        usage_percentage = min(usage_percentage, 100)
    else:
        usage_percentage = 0
    
    # 確保用戶有 profile
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    # 按檔案類型分類
    file_types = {}
    for file in user_files:
        ext = file.get_file_extension()
        if ext in file_types:
            file_types[ext]['count'] += 1
            file_types[ext]['size'] += file.file_size
        else:
            file_types[ext] = {'count': 1, 'size': file.file_size}
    
    # 最近上傳的檔案
    recent_files = user_files.order_by('-created_at')[:10]
    
    context = {
        'total_files': total_files,
        'total_size': total_size,
        'user_quota': user_quota,
        'usage_percentage': usage_percentage,
        'total_users': total_users,
        'file_types': file_types,
        'recent_files': recent_files,
        'profile': profile,  # 添加這行
    }
    
    return render(request, 'storage/stats.html', context)

@login_required
def file_delete(request, pk): #檔案刪除
    file_obj = get_object_or_404(File, pk=pk, owner=request.user)
    
    if request.method == 'POST':
        # 標記為刪除，而非真的刪除
        file_obj.is_deleted = True
        file_obj.deleted_at = timezone.now()
        file_obj.save()
        
        messages.success(request, f'檔案 {file_obj.name} 已移至回收站')
        return redirect('storage:home')
    
    return render(request, 'storage/file_delete.html', {'file': file_obj})

@login_required
def folder_delete(request, pk): #資料夾刪除
    folder = get_object_or_404(Folder, pk=pk, owner=request.user)
    
    if request.method == 'POST':
        # 標記資料夾為刪除
        folder.is_deleted = True
        folder.deleted_at = timezone.now()
        folder.save()
        
        # 遞迴標記所有子內容為刪除
        def mark_deleted_recursive(folder):
            # 標記資料夾內的檔案
            File.objects.filter(folder=folder).update(
                is_deleted=True,
                deleted_at=timezone.now()
            )
            
            # 遞迴標記子資料夾
            subfolders = Folder.objects.filter(parent=folder)
            for subfolder in subfolders:
                subfolder.is_deleted = True
                subfolder.deleted_at = timezone.now()
                subfolder.save()
                mark_deleted_recursive(subfolder)
        
        mark_deleted_recursive(folder)
        
        messages.success(request, f'資料夾 {folder.name} 及其內容已移至回收站')
        
        if folder.parent:
            return redirect(f'/?folder={folder.parent.pk}')
        return redirect('storage:home')
    
    return render(request, 'storage/folder_delete.html', {'folder': folder})

@login_required
def create_share_link(request, pk): #建立分享連結
    file_obj = get_object_or_404(File, pk=pk, owner=request.user)
    
    if request.method == 'POST':
        form = SharedLinkForm(request.POST)
        if form.is_valid():
            share_link = form.save(commit=False)
            share_link.file = file_obj
            share_link.created_by = request.user
            share_link.save()
            
            share_url = request.build_absolute_uri(f'/share/{share_link.token}/')
            messages.success(request, f'分享連結已建立：{share_url}')
            return redirect('storage:home')
    else:
        form = SharedLinkForm()
    
    return render(request, 'storage/create_share.html', {'form': form, 'file': file_obj})

def shared_file_download(request, token): #透過分享連結下載檔案
    share_link = get_object_or_404(SharedLink, token=token)
    
    if not share_link.can_download():
        messages.error(request, '此分享連結已過期或已達到下載上限。')
        return render(request, 'storage/share_expired.html')
    
    # 增加下載次數
    share_link.download_count += 1
    share_link.save()
    
    file_obj = share_link.file
    try:
        file_path = file_obj.file.path
        if os.path.exists(file_path):
            with open(file_path, 'rb') as fh:
                response = HttpResponse(fh.read(), content_type=mimetypes.guess_type(file_path)[0])
                response['Content-Disposition'] = f'attachment; filename="{file_obj.name}"'
                return response
    except:
        pass
    
    raise Http404("檔案不存在")

@login_required
def ajax_file_info(request, pk): #AJAX 獲取檔案資訊
    file_obj = get_object_or_404(File, pk=pk, owner=request.user)
    
    data = {
        'name': file_obj.name,
        'size': file_obj.get_size_display(),
        'type': file_obj.file_type,
        'created_at': file_obj.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        'description': file_obj.description,
    }
    
    return JsonResponse(data)

def file_move(request, pk): #移動檔案到指定資料夾
    file_obj = get_object_or_404(File, pk=pk, owner=request.user)
    
    if request.method == 'POST':
        folder_id = request.POST.get('folder_id')
        if folder_id:
            target_folder = get_object_or_404(Folder, pk=folder_id, owner=request.user)
            file_obj.folder = target_folder
        else:
            file_obj.folder = None  # 移動到根目錄
        
        file_obj.save()
        messages.success(request, f'檔案 {file_obj.name} 已移動成功！')
    
    return redirect('storage:home')

def custom_logout(request): #自訂登出功能
    logout(request)
    messages.success(request, '您已成功登出')
    return redirect('storage:home')

@login_required
def file_preview(request, pk): #檔案預覽（支援影片和音樂範圍請求）
    file_obj = get_object_or_404(File, pk=pk, owner=request.user)    
    try:
        file_path = file_obj.file.path
        
        if os.path.exists(file_path):
            file_size = os.path.getsize(file_path)
            content_type = mimetypes.guess_type(file_path)[0]
            
            # 強制設定音樂檔案的 MIME 類型
            if file_obj.is_audio():
                ext = file_obj.get_file_extension()
                mime_map = {
                    '.mp3': 'audio/mpeg',
                    '.wav': 'audio/wav',
                    '.m4a': 'audio/mp4',
                    '.ogg': 'audio/ogg',
                    '.flac': 'audio/flac',
                    '.aac': 'audio/aac',
                    '.wma': 'audio/x-ms-wma'
                }
                content_type = mime_map.get(ext, 'audio/mpeg')
            
            # 處理範圍請求（影片和音樂播放控制需要）
            range_header = request.META.get('HTTP_RANGE')
            if range_header and (file_obj.is_video() or file_obj.is_audio()):
                range_match = re.match(r'bytes=(\d+)-(\d*)', range_header)
                if range_match:
                    start = int(range_match.group(1))
                    end = int(range_match.group(2)) if range_match.group(2) else file_size - 1
                    
                    with open(file_path, 'rb') as fh:
                        fh.seek(start)
                        data = fh.read(end - start + 1)
                    
                    response = HttpResponse(
                        data, 
                        status=206,
                        content_type=content_type
                    )
                    response['Content-Range'] = f'bytes {start}-{end}/{file_size}'
                    response['Accept-Ranges'] = 'bytes'
                    response['Content-Length'] = str(end - start + 1)
                    response['Content-Disposition'] = f'inline; filename="{file_obj.name}"'
                    return response
            
            # 一般請求
            with open(file_path, 'rb') as fh:
                response = HttpResponse(fh.read(), content_type=content_type)
                response['Content-Disposition'] = f'inline; filename="{file_obj.name}"'
                if file_obj.is_video() or file_obj.is_audio():
                    response['Accept-Ranges'] = 'bytes'
                response['Content-Length'] = str(file_size)
                return response
                
    except Exception as e:
        import traceback
        traceback.print_exc()
    
    return redirect('storage:file_download', pk=pk)

@login_required
def media_gallery(request, pk): #媒體檔案畫廊檢視
    file_obj = get_object_or_404(File, pk=pk, owner=request.user)
    
    # 取得同一資料夾內的所有圖片和影片檔案
    media_files = File.objects.filter(
        owner=request.user,
        folder=file_obj.folder
    ).filter(
        Q(file_type__startswith='image/') | Q(file_type__startswith='video/')
    ).order_by('name')
    
    # 找到當前檔案在列表中的位置
    file_list = list(media_files)
    try:
        current_index = file_list.index(file_obj)
    except ValueError:
        current_index = 0
    
    # 取得上一個和下一個檔案
    prev_file = file_list[current_index - 1] if current_index > 0 else None
    next_file = file_list[current_index + 1] if current_index < len(file_list) - 1 else None
    
    context = {
        'file': file_obj,
        'media_files': media_files,
        'current_index': current_index + 1,
        'total_files': len(file_list),
        'prev_file': prev_file,
        'next_file': next_file,
    }
    
    return render(request, 'storage/media_gallery.html', context)

@login_required
def user_profile(request): #顯示使用者個人資料（與統計頁面相同）
    # 取得使用者的所有檔案
    files = File.objects.filter(owner=request.user)
    
    # 計算總檔案數
    total_files = files.count()
    
    # 計算總使用空間
    total_size = files.aggregate(Sum('file_size'))['file_size__sum'] or 0
    
    # 取得最近上傳的 5 個檔案
    recent_files = files.order_by('-created_at')[:5]
    
    # 統計各種檔案類型
    file_types = {}
    for file in files:
        ext = file.get_file_extension()
        if ext not in file_types:
            file_types[ext] = {'count': 0, 'size': 0}
        file_types[ext]['count'] += 1
        file_types[ext]['size'] += file.file_size
    
    # 計算使用百分比（假設配額為 10GB）
    user_quota = 10 * 1024 * 1024 * 1024  # 10GB
    usage_percentage = (total_size / user_quota * 100) if user_quota > 0 else 0
    
    # 取得所有資料夾（用於側邊欄）
    folders = Folder.objects.filter(owner=request.user, parent=None)
    
    context = {
        'total_files': total_files,
        'total_size': total_size,
        'recent_files': recent_files,
        'file_types': file_types,
        'user_quota': user_quota,
        'usage_percentage': usage_percentage,
        'folders': folders,
    }
    
    return render(request, 'storage/stats.html', context)

@login_required
def change_password(request): #修改密碼
    if request.method == 'POST':
        form = CustomPasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # 保持登入狀態
            messages.success(request, '密碼修改成功！')
            return redirect('storage:user_profile')
    else:
        form = CustomPasswordChangeForm(request.user)
    
    return render(request, 'storage/change_password.html', {'form': form})

@login_required
def profile_edit(request): #編輯使用者個人資料
    from django import forms
    from django.contrib.auth.models import User
    
    # 定義使用者表單
    class UserEditForm(forms.ModelForm):
        class Meta:
            model = User
            fields = ['first_name', 'last_name', 'email']
            widgets = {
                'first_name': forms.TextInput(attrs={'class': 'form-control'}),
                'last_name': forms.TextInput(attrs={'class': 'form-control'}),
                'email': forms.EmailInput(attrs={'class': 'form-control'}),
            }
    
    # 定義個人資料表單
    class ProfileEditForm(forms.ModelForm):
        class Meta:
            model = UserProfile
            fields = ['avatar', 'bio', 'phone', 'location']
            widgets = {
                'avatar': forms.FileInput(attrs={'class': 'form-control'}),
                'bio': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
                'phone': forms.TextInput(attrs={'class': 'form-control'}),
                'location': forms.TextInput(attrs={'class': 'form-control'}),
            }
    
    # 確保用戶有 profile
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        user_form = UserEditForm(request.POST, instance=request.user)
        profile_form = ProfileEditForm(request.POST, request.FILES, instance=profile)
        
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, '個人資料已更新！')
            return redirect('storage:storage_stats')
    else:
        user_form = UserEditForm(instance=request.user)
        profile_form = ProfileEditForm(instance=profile)
    
    context = {
        'user_form': user_form,
        'profile_form': profile_form,
        'profile': profile,
    }
    
    return render(request, 'storage/profile_edit.html', context)


# ==================== 分享功能 ====================

@login_required
def create_share_link(request, pk): #建立檔案分享連結
    file = get_object_or_404(File, pk=pk, owner=request.user)
    
    if request.method == 'POST':
        form = SharedLinkForm(request.POST)
        if form.is_valid():
            # 建立分享連結
            share_link = form.save(commit=False)
            share_link.file = file
            share_link.created_by = request.user
            share_link.save()
            
            # 生成完整的分享 URL
            share_url = request.build_absolute_uri(
                f'/share/{share_link.token}/'
            )
            
            messages.success(request, f'分享連結已建立！')
            
            # 傳遞分享資訊到成功頁面
            context = {
                'share_link': share_link,
                'share_url': share_url,
                'file': file,
            }
            return render(request, 'storage/share_success.html', context)
    else:
        form = SharedLinkForm()
    
    context = {
        'form': form,
        'file': file,
    }
    return render(request, 'storage/create_share.html', context)

def shared_file_download(request, token): #透過分享連結下載檔案
    # 查找分享連結
    share_link = get_object_or_404(SharedLink, token=token)
    
    # 檢查是否可以下載
    if not share_link.can_download():
        return render(request, 'storage/share_expired.html', {
            'reason': '分享連結已失效'
        })
    
    # 如果是 GET 請求，顯示下載頁面
    if request.method == 'GET':
        context = {
            'share_link': share_link,
            'file': share_link.file,
        }
        return render(request, 'storage/shared_download.html', context)
    
    # 如果是 POST 請求，執行下載
    if request.method == 'POST':
        # 增加下載次數
        share_link.download_count += 1
        share_link.save()
        
        # 檢查是否達到下載上限，自動停用
        if share_link.max_downloads and share_link.download_count >= share_link.max_downloads:
            share_link.is_active = False
            share_link.save()
        
        # 提供檔案下載
        file = share_link.file
        response = FileResponse(file.file.open('rb'))
        response['Content-Type'] = 'application/octet-stream'
        response['Content-Disposition'] = f'attachment; filename="{file.name}"'
        return response

@login_required
def manage_shares(request): #管理我的分享連結
    # 取得使用者建立的所有分享連結
    share_links = SharedLink.objects.filter(
        created_by=request.user
    ).select_related('file').order_by('-created_at')
    
    context = {
        'share_links': share_links,
    }
    return render(request, 'storage/manage_shares.html', context)

@login_required
def toggle_share(request, pk): #啟用/停用分享連結
    share_link = get_object_or_404(SharedLink, pk=pk, created_by=request.user)
    
    # 切換啟用狀態
    share_link.is_active = not share_link.is_active
    share_link.save()
    
    status = "啟用" if share_link.is_active else "停用"
    messages.success(request, f'分享連結已{status}！')
    
    return redirect('storage:manage_shares')

@login_required
def delete_share(request, pk): #刪除分享連結
    share_link = get_object_or_404(SharedLink, pk=pk, created_by=request.user)
    
    if request.method == 'POST':
        share_link.delete()
        messages.success(request, '分享連結已刪除！')
        return redirect('storage:manage_shares')
    
    context = {
        'share_link': share_link,
    }
    return render(request, 'storage/share_delete_confirm.html', context)


# ==================== 檔案批次功能 ====================
@login_required
def batch_download_zip(request): #批量下載檔案（打包成 ZIP）
    if request.method == 'POST':
        file_ids = request.POST.getlist('file_ids')
        
        if not file_ids:
            messages.error(request, '沒有選擇任何檔案')
            return redirect('storage:home')
        
        # 取得選中的檔案
        files = File.objects.filter(pk__in=file_ids, owner=request.user)
        
        if not files.exists():
            messages.error(request, '找不到選中的檔案')
            return redirect('storage:home')
        
        # 創建 ZIP 檔案
        zip_buffer = BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for file_obj in files:
                try:
                    # 讀取檔案內容
                    file_path = file_obj.file.path
                    if os.path.exists(file_path):
                        # 添加到 ZIP，使用原始檔名
                        zip_file.write(file_path, file_obj.name)
                except Exception as e:
                    print(f'無法添加檔案 {file_obj.name}: {e}')
                    continue
        
        # 準備下載響應
        zip_buffer.seek(0)
        
        # 生成 ZIP 檔案名稱
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        zip_filename = f'files_{timestamp}.zip'
        
        response = HttpResponse(zip_buffer.getvalue(), content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename="{zip_filename}"'
        
        return response
    
    return redirect('storage:home')

@login_required
def batch_delete(request): #批量刪除
    if request.method == 'POST':
        file_ids = request.POST.getlist('file_ids')
        
        if not file_ids:
            messages.error(request, '沒有選擇任何檔案')
            return redirect('storage:home')
        
        # ✅ 只標記為已刪除，移到回收站
        files = File.objects.filter(pk__in=file_ids, owner=request.user)
        count = files.count()
        
        files.update(
            is_deleted=True,
            deleted_at=timezone.now()
        )
        
        messages.success(request, f'已將 {count} 個檔案移至回收站')
        return redirect('storage:home')
    
    return redirect('storage:home')

@login_required 
def batch_download_folders(request): #批量下載資料夾（打包成 ZIP）
    if request.method == 'POST':
        folder_ids = request.POST.getlist('folder_ids')
        
        if not folder_ids:
            messages.error(request, '沒有選擇任何資料夾')
            return redirect('storage:home')
        
        # 取得選中的資料夾
        folders = Folder.objects.filter(pk__in=folder_ids, owner=request.user)
        
        if not folders.exists():
            messages.error(request, '找不到選中的資料夾')
            return redirect('storage:home')
        
        # 創建 ZIP 檔案
        zip_buffer = BytesIO()
        
        def add_folder_to_zip(zip_file, folder, base_path=''):
            """遞歸添加資料夾內容到 ZIP"""
            folder_path = os.path.join(base_path, folder.name)
            
            # 添加資料夾內的檔案
            files = File.objects.filter(folder=folder, owner=request.user)
            for file_obj in files:
                try:
                    file_path = file_obj.file.path
                    if os.path.exists(file_path):
                        zip_path = os.path.join(folder_path, file_obj.name)
                        zip_file.write(file_path, zip_path)
                except Exception as e:
                    print(f'無法添加檔案 {file_obj.name}: {e}')
                    continue
            
            # 遞歸添加子資料夾
            subfolders = Folder.objects.filter(parent=folder, owner=request.user)
            for subfolder in subfolders:
                add_folder_to_zip(zip_file, subfolder, folder_path)
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for folder in folders:
                add_folder_to_zip(zip_file, folder)
        
        # 準備下載響應
        zip_buffer.seek(0)
        
        # 生成 ZIP 檔案名稱
        from datetime import datetime
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        zip_filename = f'folders_{timestamp}.zip'
        
        response = HttpResponse(zip_buffer.getvalue(), content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename="{zip_filename}"'
        
        return response
    
    return redirect('storage:home')


@login_required
def batch_delete_folders(request): #批量刪除資料夾
    if request.method == 'POST':
        folder_ids = request.POST.getlist('folder_ids')
        
        if not folder_ids:
            messages.error(request, '沒有選擇任何資料夾')
            return redirect('storage:home')
        
        folders = Folder.objects.filter(pk__in=folder_ids, owner=request.user)
        
        def mark_deleted_recursive(folder):
            """遞迴標記資料夾及其內容為已刪除"""
            # 標記資料夾
            folder.is_deleted = True
            folder.deleted_at = timezone.now()
            folder.save()
            
            # 標記資料夾內的檔案
            File.objects.filter(folder=folder).update(
                is_deleted=True,
                deleted_at=timezone.now()
            )
            
            # 遞迴標記子資料夾
            subfolders = Folder.objects.filter(parent=folder)
            for subfolder in subfolders:
                mark_deleted_recursive(subfolder)
        
        deleted_count = 0
        for folder in folders:
            try:
                mark_deleted_recursive(folder)
                deleted_count += 1
            except Exception as e:
                print(f'無法刪除資料夾 {folder.name}: {e}')
                continue
        
        messages.success(request, f'已將 {deleted_count} 個資料夾及其內容移至回收站')
        return redirect('storage:home')
    
    return redirect('storage:home')


# ==================== 垃圾桶功能 ====================
@login_required
def trash(request):
    """回收站"""
    files = File.objects.filter(
        owner=request.user, 
        is_deleted=True
    ).order_by('-deleted_at')
    
    context = {
        'files': files,
    }
    return render(request, 'storage/trash.html', context)

@login_required
def restore_file(request, pk): #還原檔案
    file_obj = get_object_or_404(File, pk=pk, owner=request.user, is_deleted=True)
    
    file_obj.is_deleted = False
    file_obj.deleted_at = None
    file_obj.save()
    
    messages.success(request, f'檔案 {file_obj.name} 已還原')
    return redirect('storage:trash')

@login_required
def restore_folder(request, pk): #還原資料夾
    folder = get_object_or_404(Folder, pk=pk, owner=request.user, is_deleted=True)
    
    # 還原資料夾及其所有內容
    def restore_recursive(folder):
        folder.is_deleted = False
        folder.deleted_at = None
        folder.save()
        
        # 還原資料夾內的檔案
        File.objects.filter(folder=folder).update(
            is_deleted=False,
            deleted_at=None
        )
        
        # 遞迴還原子資料夾
        subfolders = Folder.objects.filter(parent=folder)
        for subfolder in subfolders:
            restore_recursive(subfolder)
    
    restore_recursive(folder)
    
    messages.success(request, f'資料夾 {folder.name} 及其內容已還原')
    return redirect('storage:trash')

@login_required
def permanent_delete_file(request, pk): #永久刪除檔案
    file_obj = get_object_or_404(File, pk=pk, owner=request.user, is_deleted=True)
    
    if request.method == 'POST':
        # 刪除實際檔案
        if file_obj.file and os.path.exists(file_obj.file.path):
            os.remove(file_obj.file.path)
        
        # 刪除縮圖
        if file_obj.thumbnail and os.path.exists(file_obj.thumbnail.path):
            os.remove(file_obj.thumbnail.path)
        
        file_name = file_obj.name
        file_obj.delete()
        
        messages.success(request, f'檔案 {file_name} 已永久刪除')
        return redirect('storage:trash')
    
    return render(request, 'storage/permanent_delete_confirm.html', {
        'item': file_obj,
        'item_type': 'file'
    })

@login_required
def permanent_delete_folder(request, pk): #永久刪除資料夾
    folder = get_object_or_404(Folder, pk=pk, owner=request.user, is_deleted=True)
    
    if request.method == 'POST':
        # 遞迴刪除所有內容
        def delete_folder_recursive(folder):
            # 刪除資料夾內的檔案
            for file in folder.file_set.all():
                if file.file and os.path.exists(file.file.path):
                    os.remove(file.file.path)
                if file.thumbnail and os.path.exists(file.thumbnail.path):
                    os.remove(file.thumbnail.path)
                file.delete()
            
            # 遞迴刪除子資料夾
            for subfolder in folder.folder_set.all():
                delete_folder_recursive(subfolder)
            
            folder.delete()
        
        folder_name = folder.name
        delete_folder_recursive(folder)
        
        messages.success(request, f'資料夾 {folder_name} 及其內容已永久刪除')
        return redirect('storage:trash')
    
    return render(request, 'storage/permanent_delete_confirm.html', {
        'item': folder,
        'item_type': 'folder'
    })

@login_required
def empty_trash(request): #清空回收站
    if request.method == 'POST':
        # 刪除所有已刪除的檔案
        deleted_files = File.objects.filter(owner=request.user, is_deleted=True)
        count_files = deleted_files.count()
        
        for file in deleted_files:
            if file.file and os.path.exists(file.file.path):
                os.remove(file.file.path)
            if file.thumbnail and os.path.exists(file.thumbnail.path):
                os.remove(file.thumbnail.path)
            file.delete()
        
        # 刪除所有已刪除的資料夾
        deleted_folders = Folder.objects.filter(owner=request.user, is_deleted=True)
        count_folders = deleted_folders.count()
        deleted_folders.delete()
        
        messages.success(request, f'已清空回收站（{count_files} 個檔案，{count_folders} 個資料夾）')
        return redirect('storage:trash')
    
    return render(request, 'storage/empty_trash_confirm.html')

@login_required
def duplicates(request): #重複檔案頁面
    # 找出有重複 hash 的檔案（只看當前用戶的）
    duplicate_hashes = File.objects.filter(
        owner=request.user,
        is_deleted=False,
        file_hash__isnull=False
    ).exclude(
        file_hash=''
    ).values('file_hash').annotate(
        count=Count('id')
    ).filter(count__gt=1).values_list('file_hash', flat=True)
    
    # 整理重複檔案組
    duplicate_groups = []
    total_wasted_space = 0
    
    for hash_value in duplicate_hashes:
        files = File.objects.filter(
            owner=request.user,
            file_hash=hash_value,
            is_deleted=False
        ).order_by('created_at')
        
        original = files.first()
        duplicates = list(files[1:])
        
        wasted_space = sum(f.file_size for f in duplicates)
        total_wasted_space += wasted_space
        
        duplicate_groups.append({
            'hash': hash_value,
            'original': original,
            'duplicates': duplicates,
            'wasted_space': wasted_space,
        })
    
    context = {
        'duplicate_groups': duplicate_groups,
        'total_wasted_space': total_wasted_space,
    }
    
    return render(request, 'storage/duplicates.html', context)

@login_required
def delete_duplicate(request, pk): #刪除重複檔案
    file_obj = get_object_or_404(File, pk=pk, owner=request.user)
    
    if request.method == 'POST':
        # 移至回收站
        file_obj.is_deleted = True
        file_obj.deleted_at = timezone.now()
        file_obj.save()
        
        messages.success(request, f'已刪除重複檔案: {file_obj.name}')
        return redirect('storage:duplicates')
    
    return redirect('storage:duplicates')

@login_required
def search_suggestions(request):
    query = request.GET.get('q', '').strip()
    search_type = request.GET.get('type', 'all')  # all, tag
    
    if len(query) < 1:
        return JsonResponse({'suggestions': []})
    
    suggestions = []
    
    #如果是標籤模式，只搜尋標籤
    if search_type == 'tag':
        # 收集所有標籤
        tags_files = File.objects.filter(
            owner=request.user,
            is_deleted=False,
            tags__icontains=query
        ).values_list('tags', flat=True)
        
        all_tags = set()
        for tags_str in tags_files:
            if tags_str:
                for tag in tags_str.split(','):
                    tag = tag.strip()
                    if query.lower() in tag.lower():
                        all_tags.add(tag)
        
        for tag in list(all_tags)[:10]:
            # 計算有多少檔案使用這個標籤
            count = File.objects.filter(
                owner=request.user,
                is_deleted=False,
                tags__icontains=tag
            ).count()
            
            suggestions.append({
                'name': tag,
                'date': f'{count} 個檔案',
                'id': tag
            })
    
    # 一般模式，搜尋檔案名稱
    else:
        files = File.objects.filter(
            owner=request.user, 
            is_deleted=False,
            name__icontains=query
        ).order_by('-created_at')[:8]
        
        for file in files:
            suggestions.append({
                'name': file.name,
                'date': file.created_at.strftime('%Y/%m/%d'),
                'id': file.pk
            })
    
    return JsonResponse({'suggestions': suggestions})

@login_required
def permanent_delete(request, pk): #永久刪除單個檔案
    file = get_object_or_404(File, pk=pk, owner=request.user, is_deleted=True)
    file_name = file.name
    
    # 刪除實際檔案
    if file.file and os.path.exists(file.file.path):
        os.remove(file.file.path)
    
    # 刪除縮圖
    if file.thumbnail and os.path.exists(file.thumbnail.path):
        os.remove(file.thumbnail.path)
    
    # 刪除資料庫記錄
    file.delete()
    
    messages.success(request, f'檔案「{file_name}」已永久刪除')
    return redirect('storage:trash')

@login_required
def batch_restore(request): #批次還原
    if request.method == 'POST':
        file_ids = request.POST.getlist('file_ids')
        files = File.objects.filter(pk__in=file_ids, owner=request.user, is_deleted=True)
        count = files.count()
        
        files.update(is_deleted=False, deleted_at=None)
        
        messages.success(request, f'已還原 {count} 個檔案')
    return redirect('storage:trash')

@login_required
def batch_permanent_delete(request): #批次永久刪除
    if request.method == 'POST':
        file_ids = request.POST.getlist('file_ids')
        files = File.objects.filter(pk__in=file_ids, owner=request.user, is_deleted=True)
        count = files.count()
        
        for file in files:
            if file.file and os.path.exists(file.file.path):
                os.remove(file.file.path)
            if file.thumbnail and os.path.exists(file.thumbnail.path):
                os.remove(file.thumbnail.path)
            file.delete()
        
        messages.success(request, f'已永久刪除 {count} 個檔案')
    return redirect('storage:trash')