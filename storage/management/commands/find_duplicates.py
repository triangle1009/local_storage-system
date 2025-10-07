from django.core.management.base import BaseCommand
from storage.models import File
from django.db.models import Count
from collections import defaultdict


class Command(BaseCommand):
    help = '查找重複的檔案'

    def handle(self, *args, **options):
        self.stdout.write('查找重複檔案...\n')
        
        # 找出有重複 hash 的檔案
        duplicate_hashes = File.objects.filter(
            is_deleted=False,
            file_hash__isnull=False
        ).exclude(
            file_hash=''
        ).values('file_hash').annotate(
            count=Count('id')
        ).filter(count__gt=1).values_list('file_hash', flat=True)
        
        if not duplicate_hashes:
            self.stdout.write(self.style.SUCCESS('✓ 沒有發現重複檔案'))
            return
        
        # 統計資訊
        total_duplicates = 0
        total_wasted_space = 0
        duplicate_groups = defaultdict(list)
        
        for hash_value in duplicate_hashes:
            files = File.objects.filter(
                file_hash=hash_value,
                is_deleted=False
            ).order_by('created_at')
            
            # 第一個是原始檔案，其餘是重複的
            original = files.first()
            duplicates = list(files[1:])
            
            total_duplicates += len(duplicates)
            total_wasted_space += sum(f.file_size for f in duplicates)
            
            duplicate_groups[hash_value] = {
                'original': original,
                'duplicates': duplicates
            }
        
        # 顯示結果
        self.stdout.write(self.style.WARNING(f'發現 {len(duplicate_groups)} 組重複檔案'))
        self.stdout.write(f'重複檔案總數: {total_duplicates}')
        self.stdout.write(f'浪費空間: {self.format_size(total_wasted_space)}\n')
        
        # 顯示詳細資訊
        for i, (hash_value, group) in enumerate(duplicate_groups.items(), 1):
            original = group['original']
            duplicates = group['duplicates']
            
            self.stdout.write(f'\n--- 重複組 {i} ---')
            self.stdout.write(f'檔案大小: {original.get_size_display()}')
            self.stdout.write(f'Hash: {hash_value[:16]}...')
            
            self.stdout.write(f'\n原始檔案:')
            self.stdout.write(f'  • {original.name}')
            self.stdout.write(f'    上傳於: {original.created_at.strftime("%Y-%m-%d %H:%M")}')
            self.stdout.write(f'    擁有者: {original.owner.username}')
            
            self.stdout.write(f'\n重複檔案 ({len(duplicates)} 個):')
            for dup in duplicates:
                self.stdout.write(f'  • {dup.name}')
                self.stdout.write(f'    上傳於: {dup.created_at.strftime("%Y-%m-%d %H:%M")}')
                self.stdout.write(f'    擁有者: {dup.owner.username}')
        
        self.stdout.write(self.style.SUCCESS(f'\n提示: 使用網頁介面來處理重複檔案'))
    
    def format_size(self, size):
        """格式化檔案大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"