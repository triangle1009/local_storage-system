from django.core.files.storage import FileSystemStorage
from django.conf import settings
import os

class MultiLocationStorage(FileSystemStorage):
    """支援多個儲存位置的自訂 Storage"""
    
    def __init__(self, location=None, base_url=None, *args, **kwargs):
        self.location_key = location or 'disk1'
        storage_config = settings.STORAGE_LOCATIONS.get(
            self.location_key, 
            settings.STORAGE_LOCATIONS['disk1']
        )
        
        super().__init__(
            location=storage_config['path'],
            base_url='/media/',
            *args, 
            **kwargs
        )
    
    def get_available_name(self, name, max_length=None):
        """確保目錄存在"""
        full_path = self.path(name)
        dir_name = os.path.dirname(full_path)
        if not os.path.exists(dir_name):
            os.makedirs(dir_name, exist_ok=True)
        return super().get_available_name(name, max_length)