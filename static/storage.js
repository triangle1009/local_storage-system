// ==========================================
// 核心導航功能
// ==========================================

console.log('storage.js loaded successfully!');

let pendingFiles = [];
let uploadQueue = [];
let isUploading = false;

// ==========================================
// 工具函數
// ==========================================

/**
 * 格式化文件大小
 */
function formatFileSize(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

/**
 * 設定資料夾名稱
 */
function setFolderName(name) {
    const folderNameInput = document.getElementById('folderName');
    if (folderNameInput) {
        folderNameInput.value = name;
        folderNameInput.focus();
    }
}

// ==========================================
// 導航切換功能
// ==========================================

/**
 * 觸發文件選擇
 */
function triggerFileUpload() {
    const fileInput = document.getElementById('fileInput');
    if (fileInput) {
        fileInput.click();
    }
}

/**
 * 手機版搜尋切換
 */
function toggleMobileSearch() {
    const searchBar = document.getElementById('mobileSearchBar');
    if (!searchBar) return;
    
    const body = document.body;
    searchBar.classList.toggle('show');
    body.classList.toggle('mobile-search-active');
    
    if (searchBar.classList.contains('show')) {
        setTimeout(() => {
            const input = searchBar.querySelector('.mobile-search-input');
            if (input) input.focus();
        }, 300);
    }
}

/**
 * 手機版選單切換
 */
function toggleMobileMenu() {
    const menu = document.getElementById('mobileMenu');
    const overlay = document.querySelector('.mobile-menu-overlay');
    if (!menu || !overlay) return;
    
    menu.classList.toggle('show');
    overlay.classList.toggle('show');
    
    if (menu.classList.contains('show')) {
        document.body.style.overflow = 'hidden';
    } else {
        document.body.style.overflow = '';
    }
}

/**
 * 側邊欄切換功能
 */
function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    if (!sidebar) return;
    
    sidebar.classList.toggle('show');
    
    if (sidebar.classList.contains('show')) {
        document.body.style.overflow = 'hidden';
    } else {
        document.body.style.overflow = '';
    }
}

/**
 * 刷新文件列表
 */
function refreshFileList() {
    location.reload();
}

// ==========================================
// Google Drive 風格上傳功能
// ==========================================

/**
 * 初始化上傳功能
 */
function initGoogleDriveStyleUpload() {
    const fileInput = document.getElementById('fileInput');
    const overlay = document.getElementById('dragDropOverlay');
    
    if (!fileInput) return;
    
    console.log('Initializing Google Drive style upload...');
    
    // 監聽文件選擇
    fileInput.addEventListener('change', function(e) {
        const files = Array.from(e.target.files);
        if (files.length > 0) {
            console.log('Files selected:', files.length);
            addToUploadQueue(files);
        }
    });
    
    // 全頁面拖曳功能
    let dragCounter = 0;
    
    document.addEventListener('dragenter', function(e) {
        e.preventDefault();
        dragCounter++;
        if (dragCounter === 1 && overlay) {
            overlay.style.display = 'flex';
        }
    });
    
    document.addEventListener('dragleave', function(e) {
        e.preventDefault();
        dragCounter--;
        if (dragCounter === 0 && overlay) {
            overlay.style.display = 'none';
        }
    });
    
    document.addEventListener('dragover', function(e) {
        e.preventDefault();
    });
    
    document.addEventListener('drop', function(e) {
        e.preventDefault();
        dragCounter = 0;
        if (overlay) overlay.style.display = 'none';
        
        const files = Array.from(e.dataTransfer.files);
        if (files.length > 0) {
            console.log('Files dropped:', files.length);
            addToUploadQueue(files);
        }
    });
}

/**
 * 添加到上傳隊列
 */
function addToUploadQueue(files) {
    files.forEach(file => {
        const uploadItem = {
            file: file,
            id: Date.now() + Math.random(),
            progress: 0,
            status: 'pending'
        };
        uploadQueue.push(uploadItem);
        addUploadItemToUI(uploadItem);
    });
    
    showUploadNotification();
    processUploadQueue();
}

/**
 * 顯示上傳通知
 */
function showUploadNotification() {
    const notification = document.getElementById('uploadNotification');
    if (notification) {
        notification.classList.add('show');
    }
}

/**
 * 關閉上傳通知
 */
function closeUploadNotification() {
    const notification = document.getElementById('uploadNotification');
    if (notification) {
        notification.classList.remove('show');
    }
}

/**
 * 添加上傳項目到UI
 */
function addUploadItemToUI(item) {
    const uploadList = document.getElementById('uploadList');
    if (!uploadList) return;
    
    const itemDiv = document.createElement('div');
    itemDiv.className = 'upload-item';
    itemDiv.id = `upload-item-${item.id}`;
    itemDiv.innerHTML = `
        <div class="upload-item-info">
            <i class="fas fa-file"></i>
            <span class="upload-item-name">${item.file.name}</span>
            <span class="upload-item-size">(${formatFileSize(item.file.size)})</span>
        </div>
        <div class="upload-item-progress">
            <div class="progress" style="height: 4px;">
                <div class="progress-bar" id="progress-${item.id}" style="width: 0%"></div>
            </div>
            <span class="upload-item-status" id="status-${item.id}">等待中...</span>
        </div>
    `;
    uploadList.appendChild(itemDiv);
}

/**
 * 處理上傳隊列
 */
async function processUploadQueue() {
    if (isUploading) return;
    
    isUploading = true;
    
    while (uploadQueue.length > 0) {
        const item = uploadQueue[0];
        await uploadFile(item);
        uploadQueue.shift();
    }
    
    isUploading = false;
    
    setTimeout(() => {
        closeUploadNotification();
        const uploadList = document.getElementById('uploadList');
        if (uploadList) uploadList.innerHTML = '';
        location.reload();
    }, 2000);
}

/**
 * 上傳單個文件
 */
function uploadFile(item) {
    return new Promise((resolve, reject) => {
        const formData = new FormData();
        formData.append('file', item.file);
        
        const folderId = document.getElementById('folderId');
        if (folderId && folderId.value) {
            formData.append('folder_id', folderId.value);
        }
        
        const xhr = new XMLHttpRequest();
        
        xhr.upload.addEventListener('progress', (e) => {
            if (e.lengthComputable) {
                const percentComplete = (e.loaded / e.total) * 100;
                updateProgress(item.id, percentComplete);
            }
        });
        
        xhr.addEventListener('load', () => {
            if (xhr.status === 200 || xhr.status === 302) {
                updateStatus(item.id, '完成', 'success');
                resolve();
            } else {
                updateStatus(item.id, '失敗', 'error');
                reject();
            }
        });
        
        xhr.addEventListener('error', () => {
            updateStatus(item.id, '失敗', 'error');
            reject();
        });
        
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');
        
        xhr.open('POST', '/upload/');
        if (csrfToken) {
            xhr.setRequestHeader('X-CSRFToken', csrfToken.value);
        }
        xhr.send(formData);
        
        updateStatus(item.id, '上傳中...', 'uploading');
    });
}

/**
 * 更新進度條
 */
function updateProgress(id, percent) {
    const progressBar = document.getElementById(`progress-${id}`);
    if (progressBar) {
        progressBar.style.width = percent + '%';
    }
}

/**
 * 更新狀態
 */
function updateStatus(id, text, type) {
    const statusSpan = document.getElementById(`status-${id}`);
    if (statusSpan) {
        statusSpan.textContent = text;
        statusSpan.className = `upload-item-status status-${type}`;
    }
}

// ==========================================
// 媒體功能
// ==========================================

/**
 * 切換媒體檔案
 */
function switchMedia(newFileId) {
    document.querySelectorAll('video, audio').forEach(media => {
        media.pause();
        media.currentTime = 0;
    });
    
    const currentModal = document.querySelector('.modal.show');
    if (currentModal) {
        const modal = bootstrap.Modal.getInstance(currentModal);
        if (modal) modal.hide();
    }
    
    setTimeout(() => {
        const newModalElement = document.getElementById('mediaModal' + newFileId);
        if (newModalElement) {
            const newModal = new bootstrap.Modal(newModalElement);
            newModal.show();
        }
    }, 150);
}

// ==========================================
// 批次操作相關函數
// ==========================================

/**
 * 更新批次操作按鈕顯示
 */
function updateBatchButtons() {
    // 檔案批次操作
    const fileCheckboxes = document.querySelectorAll('.file-checkbox:checked');
    const batchButtons = document.getElementById('batchButtons');
    const selectedCount = document.getElementById('selectedCount');
    
    if (fileCheckboxes.length > 0) {
        batchButtons.style.display = 'block';
        selectedCount.textContent = fileCheckboxes.length;
    } else {
        batchButtons.style.display = 'none';
    }
    
    // 資料夾批次操作
    const folderCheckboxes = document.querySelectorAll('.folder-checkbox:checked');
    const folderBatchButtons = document.getElementById('folderBatchButtons');
    const selectedFolderCount = document.getElementById('selectedFolderCount');
    
    if (folderCheckboxes.length > 0) {
        folderBatchButtons.style.display = 'block';
        selectedFolderCount.textContent = folderCheckboxes.length;
    } else {
        folderBatchButtons.style.display = 'none';
    }
}

/**
 * 資料夾全選
 */
function selectAllFolders() {
    const checkboxes = document.querySelectorAll('.folder-checkbox');
    checkboxes.forEach(cb => cb.checked = true);
    updateBatchButtons();
}

/**
 * 資料夾取消全選
 */
function deselectAllFolders() {
    const checkboxes = document.querySelectorAll('.folder-checkbox');
    checkboxes.forEach(cb => cb.checked = false);
    updateBatchButtons();
}

/**
 * 批量下載資料夾
 */
function batchDownloadFolders() {
    const checkboxes = document.querySelectorAll('.folder-checkbox:checked');
    if (checkboxes.length === 0) {
        alert('請選擇要下載的資料夾');
        return;
    }
    
    const folderIds = Array.from(checkboxes).map(cb => cb.value);
    const folderNames = Array.from(checkboxes).map(cb => cb.dataset.foldername).join(', ');
    
    if (!confirm(`確定要下載這 ${folderIds.length} 個資料夾嗎？\n${folderNames}\n\n將打包成 ZIP 檔案。`)) {
        return;
    }
    
    // 創建表單並提交
    const form = document.createElement('form');
    form.method = 'POST';
    form.action = '/batch-download-folders/';
    
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    const csrfInput = document.createElement('input');
    csrfInput.type = 'hidden';
    csrfInput.name = 'csrfmiddlewaretoken';
    csrfInput.value = csrfToken;
    form.appendChild(csrfInput);
    
    folderIds.forEach(id => {
        const input = document.createElement('input');
        input.type = 'hidden';
        input.name = 'folder_ids';
        input.value = id;
        form.appendChild(input);
    });
    
    document.body.appendChild(form);
    form.submit();
    document.body.removeChild(form);
}

/**
 * 批量刪除資料夾
 */
function batchDeleteFolders() {
    const checkboxes = document.querySelectorAll('.folder-checkbox:checked');
    if (checkboxes.length === 0) {
        alert('請選擇要刪除的資料夾');
        return;
    }
    
    const folderNames = Array.from(checkboxes).map(cb => cb.dataset.foldername).join('\n');
    
    if (!confirm(`危險操作！確定要刪除以下 ${checkboxes.length} 個資料夾及其所有內容嗎？\n此操作無法復原！\n\n${folderNames}`)) {
        return;
    }
    
    const folderIds = Array.from(checkboxes).map(cb => cb.value);
    
    // 創建表單並提交
    const form = document.createElement('form');
    form.method = 'POST';
    form.action = '/batch-delete-folders/';
    
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    const csrfInput = document.createElement('input');
    csrfInput.type = 'hidden';
    csrfInput.name = 'csrfmiddlewaretoken';
    csrfInput.value = csrfToken;
    form.appendChild(csrfInput);
    
    folderIds.forEach(id => {
        const input = document.createElement('input');
        input.type = 'hidden';
        input.name = 'folder_ids';
        input.value = id;
        form.appendChild(input);
    });
    
    document.body.appendChild(form);
    form.submit();
}

/**
 * 檔案全選
 */
function selectAll() {
    const checkboxes = document.querySelectorAll('.file-checkbox');
    checkboxes.forEach(cb => cb.checked = true);
    updateBatchButtons();
}

/**
 * 檔案取消全選
 */
function deselectAll() {
    const checkboxes = document.querySelectorAll('.file-checkbox');
    checkboxes.forEach(cb => cb.checked = false);
    updateBatchButtons();
}

/**
 * 批量下載檔案
 */
function batchDownload() {
    const checkboxes = document.querySelectorAll('.file-checkbox:checked');
    if (checkboxes.length === 0) {
        alert('請選擇要下載的檔案');
        return;
    }
    
    const fileIds = Array.from(checkboxes).map(cb => cb.value);
    
    // 如果只有一個檔案，直接下載
    if (fileIds.length === 1) {
        window.location.href = `/file/${fileIds[0]}/download/`;
        return;
    }
    
    // 多個檔案，詢問是否要壓縮
    if (confirm(`您選擇了 ${fileIds.length} 個檔案。是否打包成 ZIP 檔案下載？\n\n點擊「確定」下載 ZIP，點擊「取消」則分別下載。`)) {
        // 創建表單並提交（下載 ZIP）
        const form = document.createElement('form');
        form.method = 'POST';
        form.action = '/batch-download-zip/';
        
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
        const csrfInput = document.createElement('input');
        csrfInput.type = 'hidden';
        csrfInput.name = 'csrfmiddlewaretoken';
        csrfInput.value = csrfToken;
        form.appendChild(csrfInput);
        
        fileIds.forEach(id => {
            const input = document.createElement('input');
            input.type = 'hidden';
            input.name = 'file_ids';
            input.value = id;
            form.appendChild(input);
        });
        
        document.body.appendChild(form);
        form.submit();
        document.body.removeChild(form);
    } else {
        // 分別下載每個檔案
        fileIds.forEach((id, index) => {
            setTimeout(() => {
                window.open(`/file/${id}/download/`, '_blank');
            }, index * 500);
        });
    }
}

/**
 * 批量刪除檔案
 */
function batchDelete() {
    const checkboxes = document.querySelectorAll('.file-checkbox:checked');
    if (checkboxes.length === 0) {
        alert('請選擇要刪除的檔案');
        return;
    }
    
    const fileNames = Array.from(checkboxes).map(cb => cb.dataset.filename).join('\n');
    
    if (!confirm(`確定要刪除以下 ${checkboxes.length} 個檔案嗎？此操作無法復原！\n\n${fileNames}`)) {
        return;
    }
    
    const fileIds = Array.from(checkboxes).map(cb => cb.value);
    
    // 創建表單並提交
    const form = document.createElement('form');
    form.method = 'POST';
    form.action = '/batch-delete/';
    
    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
    const csrfInput = document.createElement('input');
    csrfInput.type = 'hidden';
    csrfInput.name = 'csrfmiddlewaretoken';
    csrfInput.value = csrfToken;
    form.appendChild(csrfInput);
    
    fileIds.forEach(id => {
        const input = document.createElement('input');
        input.type = 'hidden';
        input.name = 'file_ids';
        input.value = id;
        form.appendChild(input);
    });
    
    document.body.appendChild(form);
    form.submit();
}

/**
 * 更新主題圖示
 */
function updateThemeIcon(theme) {
    const icon = document.getElementById('themeIcon');
    if (icon) {
        icon.className = theme === 'dark' ? 'fas fa-sun' : 'fas fa-moon';
    }
}

// ==========================================
// 搜尋建議功能
// ==========================================

/**
 * 搜尋建議初始化函數
 */
function initSearchSuggestions(inputElement, suggestionsElement) {
    let timeout;
    
    inputElement.addEventListener('input', function(e) {
        const query = e.target.value;
        clearTimeout(timeout);
        
        const isTagMode = query.startsWith('@');
        const searchTerm = isTagMode ? query.substring(1).trim() : query.trim();
        
        if (searchTerm.length < 1) {
            suggestionsElement.classList.remove('show');
            return;
        }
        
        timeout = setTimeout(() => {
            const url = isTagMode 
                ? `/api/search-suggestions/?q=${encodeURIComponent(searchTerm)}&type=tag`
                : `/api/search-suggestions/?q=${encodeURIComponent(searchTerm)}`;
            
            fetch(url)
                .then(res => res.json())
                .then(data => {
                    if (!data.suggestions || data.suggestions.length === 0) {
                        suggestionsElement.classList.remove('show');
                        return;
                    }
                    
                    const html = data.suggestions.map(item => `
                        <a href="?search=${encodeURIComponent(item.name)}" class="suggestion-item">
                            <span class="suggestion-name">
                                ${isTagMode ? '<i class="fas fa-tag text-info"></i> ' : ''}${item.name}
                            </span>
                            <span class="suggestion-date">${item.date || ''}</span>
                        </a>
                    `).join('');
                    
                    suggestionsElement.innerHTML = html;
                    suggestionsElement.classList.add('show');
                })
                .catch(err => console.error(err));
        }, 300);
    });
    
    // 點擊外部關閉
    document.addEventListener('click', function(e) {
        if (!inputElement.contains(e.target) && !suggestionsElement.contains(e.target)) {
            suggestionsElement.classList.remove('show');
        }
    });
}

// ==========================================
// DOM 載入完成初始化
// ==========================================

document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM Content Loaded');
    
    // 初始化 Google Drive 風格上傳
    const fileInput = document.getElementById('fileInput');
    if (fileInput) {
        initGoogleDriveStyleUpload();
    }
    
    // 資料夾卡片點擊
    document.querySelectorAll('.folder-item').forEach(function(item) {
        item.addEventListener('click', function() {
            if (this.dataset.folderUrl) {
                window.location.href = this.dataset.folderUrl;
            }
        });
    });
    
    // Modal 自動聚焦
    const folderModal = document.getElementById('folderModal');
    if (folderModal) {
        folderModal.addEventListener('shown.bs.modal', function () {
            const folderNameInput = document.getElementById('folderName');
            if (folderNameInput) folderNameInput.focus();
        });
    }
    
    // 關閉通知按鈕
    const closeNotificationBtn = document.querySelector('.btn-close-notification');
    if (closeNotificationBtn) {
        closeNotificationBtn.addEventListener('click', function(e) {
            e.preventDefault();
            closeUploadNotification();
        });
    }
    
    // 初始化桌面版搜尋建議
    const searchInput = document.getElementById('searchInput');
    const searchSuggestions = document.getElementById('searchSuggestions');
    if (searchInput && searchSuggestions) {
        initSearchSuggestions(searchInput, searchSuggestions);
    }
    
    // 初始化手機版搜尋建議
    const mobileSearchInput = document.getElementById('mobileSearchInput');
    const mobileSearchSuggestions = document.getElementById('mobileSearchSuggestions');
    if (mobileSearchInput && mobileSearchSuggestions) {
        initSearchSuggestions(mobileSearchInput, mobileSearchSuggestions);
    }
    
    // 頁面載入時更新主題圖示
    const theme = localStorage.getItem('theme') || 'light';
    updateThemeIcon(theme);
});

// ==========================================
// 鍵盤事件
// ==========================================

document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
        const searchBar = document.getElementById('mobileSearchBar');
        if (searchBar && searchBar.classList.contains('show')) {
            toggleMobileSearch();
            return;
        }
        
        const menu = document.getElementById('mobileMenu');
        if (menu && menu.classList.contains('show')) {
            toggleMobileMenu();
            return;
        }
        
        const activeModal = document.querySelector('.modal.show');
        if (activeModal && activeModal.id.includes('mediaModal')) {
            const modal = bootstrap.Modal.getInstance(activeModal);
            if (modal) modal.hide();
        }
    }
});

// ==========================================
// 視窗大小改變
// ==========================================

window.addEventListener('resize', function() {
    if (window.innerWidth >= 1200) {
        const sidebar = document.getElementById('sidebar');
        if (sidebar) {
            sidebar.classList.remove('show');
            document.body.style.overflow = '';
        }
    }
    
    if (window.innerWidth >= 768) {
        const searchBar = document.getElementById('mobileSearchBar');
        if (searchBar && searchBar.classList.contains('show')) {
            searchBar.classList.remove('show');
            document.body.classList.remove('mobile-search-active');
        }
    }
});

// ==========================================
// Modal 事件
// ==========================================

document.addEventListener('hidden.bs.modal', function (event) {
    if (event.target.id.includes('mediaModal')) {
        const mediaElements = event.target.querySelectorAll('video, audio');
        mediaElements.forEach(media => {
            media.pause();
            media.currentTime = 0;
        });
    }
});