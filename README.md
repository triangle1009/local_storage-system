# 📦 本地端儲存系統

一個基於 Django 開發的個人雲端儲存系統，擁有 Google Drive 風格的現代化介面。

## 🎥 專案展示

> **功能展示影片**: [點擊觀看](https://youtu.be/BgB7bYCsa7g)

---

## ✨ 功能特色

- 📤 **檔案上傳** - 支援拖曳上傳、批次上傳、即時進度顯示
- 📁 **資料夾管理** - 建立、刪除、移動資料夾，支援巢狀結構
- 📥 **批次操作** - 批次下載、刪除、壓縮打包
- 🔗 **分享連結** - 產生限時/限次數的檔案分享連結
- 🗑️ **回收站** - 已刪除檔案保留 30 天可還原
- 🔍 **智慧搜尋** - 支援檔名、標籤、描述搜尋
- 🏷️ **標籤系統** - 為檔案添加標籤便於分類
- 🔄 **去重功能** - 自動偵測並清理重複檔案
- 📊 **儲存統計** - 即時查看空間使用情況
- 📱 **響應式設計** - 完美支援桌面、平板、手機

---

## 🛠️ 技術棧

- **後端框架**: Django 5.2
- **資料庫**: MySQL 8.0+
- **前端框架**: Bootstrap 5.3.2
- **圖示庫**: Font Awesome 6.4.0
- **程式語言**: Python 3.x

---

## 📋 系統需求

- Python 3.8 或以上
- MySQL 8.0 或以上
- pip（Python 套件管理工具）

---
## 1.建立虛擬環境 (可用可不用)
Windows:
```bash
python -m venv venv
venv\Scripts\activate
```
macOS/Linux:
```bash
python3 -m venv venv
source venv/bin/activate
```
## 2.安裝相依套件
```bash
pip install -r requirements.txt
```
## 3.設定環境變數
```bash
copy .env.example .env  # Windows
cp .env.example .env    # macOS/Linux
```
編輯 .env 檔案，填入你的設定： 
- SECRET_KEY=你的Django密鑰
- DEBUG=True
- DB_NAME=local_storage_db   
- DB_USER=root
- DB_PASSWORD=你的MySQL密碼
- DB_HOST=localhost
- DB_PORT=3306

## 4.執行資料庫遷移
```bash
python manage.py migrate
```
## 5.建立管理員帳號
```bash
python manage.py createsuperuser
```
## 6.填加IP位置
在setting.py 中增加這行 (或是在ALLOWED_HOSTS中更改也可以)
```python
ALLOWED_HOSTS += ['Your device IP', 'your-domain.com']
```
## 7.啟動開發伺服器
```bash
python manage.py runserver
```

## ⚙️ 進階設定
修改儲存配額
編輯 storage/views.py 中的 get_user_quota 函數：
```python
pythontotal_system_storage = 100 * 1024 * 1024 * 1024  # 改為你想要的容量
```
修改檔案上傳大小限制
編輯 settings.py：
```python
pythonFILE_UPLOAD_MAX_MEMORY_SIZE = 52428800  # 50MB（單位：bytes）
DATA_UPLOAD_MAX_MEMORY_SIZE = 52428800  # 50MB
```
## 🐛 常見問題
<details>
<summary><b>Q: 上傳檔案失敗怎麼辦？</b></summary>
A: 檢查以下項目：

media/ 資料夾是否存在且有寫入權限
檔案大小是否超過限制（預設 50MB）
儲存空間是否已滿

</details>
<details>
<summary><b>Q: 圖片縮圖無法顯示？</b></summary>
A: 確認已安裝 Pillow 套件：
bashpip install Pillow
</details>
<details>
<summary><b>Q: 資料庫連線錯誤？</b></summary>
A: 檢查：

MySQL 服務是否啟動
.env 中的資料庫帳號密碼是否正確
資料庫是否已建立
</details>


## 👨‍💻 作者
- GitHub: @triangle1009
- Email:  chenwilly1009@gmail.com
