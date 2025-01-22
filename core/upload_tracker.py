import os
from requests_toolbelt import MultipartEncoder, MultipartEncoderMonitor

class UploadTracker:
    def __init__(self, callback=None):
        self.callback = callback
        self.last_progress = 0
        
    def create_callback(self, encoder):
        def callback(monitor):
            progress = int(monitor.bytes_read * 100 / monitor.len)
            if progress > self.last_progress:
                self.last_progress = progress
                if self.callback:
                    self.callback(progress)
        return callback
        
    def create_monitor(self, fields):
        encoder = MultipartEncoder(fields=fields)
        monitor = MultipartEncoderMonitor(encoder, self.create_callback(encoder))
        return monitor, encoder.content_type 