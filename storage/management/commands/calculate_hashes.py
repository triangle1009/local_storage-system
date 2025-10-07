from django.core.management.base import BaseCommand
from storage.models import File
from django.db.models import Q


class Command(BaseCommand):
    help = '計算所有檔案的 hash 值'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='重新計算已有 hash 的檔案'
        )

    def handle(self, *args, **options):
        force = options['force']
        
        # 查詢需要計算 hash 的檔案
        if force:
            files = File.objects.filter(is_deleted=False)
            self.stdout.write('重新計算所有檔案的 hash...')
        else:
            files = File.objects.filter(
                Q(file_hash__isnull=True) | Q(file_hash=''),
                is_deleted=False
            )
            self.stdout.write('計算尚未有 hash 的檔案...')
        
        total = files.count()
        
        if total == 0:
            self.stdout.write(self.style.SUCCESS('✓ 所有檔案都已有 hash'))
            return
        
        self.stdout.write(f'找到 {total} 個檔案需要計算 hash')
        
        success = 0
        failed = 0
        
        for i, file in enumerate(files, 1):
            self.stdout.write(f'[{i}/{total}] 處理: {file.name}', ending=' ... ')
            
            hash_value = file.calculate_hash()
            
            if hash_value:
                file.file_hash = hash_value
                file.save(update_fields=['file_hash'])
                success += 1
                self.stdout.write(self.style.SUCCESS('✓'))
            else:
                failed += 1
                self.stdout.write(self.style.ERROR('✗'))
        
        self.stdout.write(self.style.SUCCESS(f'\n完成!'))
        self.stdout.write(f'  成功: {success}')
        if failed > 0:
            self.stdout.write(self.style.WARNING(f'  失敗: {failed}'))