# Base collector for multi-source
import os
import json
from pathlib import Path
from abc import ABC, abstractmethod

class BaseCollector(ABC):
    def __init__(self, name, staging_db):
        self.name = name
        self.staging_db = staging_db
        self.checkpoint_dir = Path('C:/SANTE_DZ_SCRAPER/checkpoints')
        self.checkpoint_dir.mkdir(exist_ok=True)
    
    @abstractmethod
    def collect(self, **kwargs):
        pass
    
    def normalize_phone(self, phone):
        if not phone: return None
        # basic normalization
        return str(phone).strip()
    
    def normalize_text(self, text):
        if not text: return None
        return ' '.join(str(text).split()).strip()
