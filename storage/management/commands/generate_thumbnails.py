from django.core.management.base import BaseCommand
from storage.models import File

class Command(BaseCommand):
    help = '為所有圖片生成縮圖'

    def handle(self, *args, **kwargs):
        # 修改查詢：找 thumbnail 是 NULL 或空字串的
        files = File.objects.filter(thumbnail__isnull=True) | File.objects.filter(thumbnail='')
        files = files.distinct()
        total = files.count()
        
        self.stdout.write(f'檢查 {total} 個檔案')
        
        success = 0
        skipped = 0
        failed = 0
        
        for i, file in enumerate(files, 1):
            if file.is_image():
                try:
                    self.stdout.write(f'[{i}/{total}] 處理: {file.name}')
                    file.create_thumbnail()
                    success += 1
                except Exception as e:
                    failed += 1
                    self.stdout.write(self.style.ERROR(f'  ✗ 失敗: {e}'))
            else:
                skipped += 1
        
        self.stdout.write(self.style.SUCCESS(f'\n完成!'))
        self.stdout.write(f'  成功: {success}')
        self.stdout.write(f'  跳過: {skipped}')
        if failed > 0:
            self.stdout.write(self.style.WARNING(f'  失敗: {failed}'))