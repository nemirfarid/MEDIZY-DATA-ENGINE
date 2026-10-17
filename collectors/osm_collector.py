# OSM collector - Phase 8.2.2
from .base_collector import BaseCollector
class OSMCollector(BaseCollector):
    CATS = [('amenity','hospital'),('amenity','clinic'),('amenity','doctors'),('amenity','dentist'),('amenity','pharmacy')]
    def collect(self, **kwargs):
        pass
