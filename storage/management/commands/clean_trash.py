from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from storage.models import File, Folder
import os


class Command(BaseCommand):
    help = '清理回收站中超過 30 天的項目'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='刪除超過指定天數的項目（預設 30 天）'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='僅顯示會被刪除的項目，不實際刪除'
        )

    def handle(self, *args, **options):
        days = options['days']
        dry_run = options['dry_run']
        
        # 計算截止日期
        cutoff_date = timezone.now() - timedelta(days=days)
        
        self.stdout.write(f'清理超過 {days} 天的回收站項目')
        self.stdout.write(f'截止日期: {cutoff_date.strftime("%Y-%m-%d %H:%M:%S")}')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('⚠ 測試模式 - 不會實際刪除'))
        
        # 找出過期的檔案
        expired_files = File.objects.filter(
            is_deleted=True,
            deleted_at__lt=cutoff_date
        )
        
        # 找出過期的資料夾
        expired_folders = Folder.objects.filter(
            is_deleted=True,
            deleted_at__lt=cutoff_date
        )
        
        file_count = expired_files.count()
        folder_count = expired_folders.count()
        total_size = sum(f.file_size for f in expired_files)
        
        self.stdout.write(f'\n找到:')
        self.stdout.write(f'  檔案: {file_count} 個 ({self.format_size(total_size)})')
        self.stdout.write(f'  資料夾: {folder_count} 個')
        
        if file_count == 0 and folder_count == 0:
            self.stdout.write(self.style.SUCCESS('\n✓ 沒有需要清理的項目'))
            return
        
        if dry_run:
            self.stdout.write('\n將被刪除的檔案:')
            for file in expired_files[:10]:
                days_old = (timezone.now() - file.deleted_at).days
                self.stdout.write(f'  • {file.name} ({file.get_size_display()}) - {days_old} 天前刪除')
            
            if file_count > 10:
                self.stdout.write(f'  ... 還有 {file_count - 10} 個檔案')
            
            self.stdout.write('\n將被刪除的資料夾:')
            for folder in expired_folders[:10]:
                days_old = (timezone.now() - folder.deleted_at).days
                self.stdout.write(f'  • {folder.name} - {days_old} 天前刪除')
            
            if folder_count > 10:
                self.stdout.write(f'  ... 還有 {folder_count - 10} 個資料夾')
            
            return
        
        # 實際刪除
        self.stdout.write('\n開始清理...')
        
        deleted_files = 0
        deleted_size = 0
        
        # 刪除檔案
        for file in expired_files:
            try:
                # 刪除實體檔案
                if file.file and os.path.exists(file.file.path):
                    file_size = file.file_size
                    os.remove(file.file.path)
                    deleted_size += file_size
                
                # 刪除縮圖
                if file.thumbnail and os.path.exists(file.thumbnail.path):
                    os.remove(file.thumbnail.path)
                
                # 從資料庫刪除
                file.delete()
                deleted_files += 1
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'  ✗ 刪除 {file.name} 失敗: {e}')
                )
        
        # 刪除資料夾
        deleted_folders = expired_folders.count()
        expired_folders.delete()
        
        # 顯示結果
        self.stdout.write(self.style.SUCCESS(f'\n✓ 清理完成!'))
        self.stdout.write(f'  刪除檔案: {deleted_files} 個 ({self.format_size(deleted_size)})')
        self.stdout.write(f'  刪除資料夾: {deleted_folders} 個')
    
    def format_size(self, size):
        """格式化檔案大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"