import sqlite3
import json
from datetime import datetime
import logging
import os

logger = logging.getLogger(__name__)

class VideoDatabase:
    def __init__(self, db_path='data/videos.db'):
        """
        Инициализация базы данных
        :param db_path: путь к файлу базы данных
        """
        # Создаем директорию для базы данных
        db_dir = os.path.dirname(db_path)
        if db_dir:  # Проверяем, что путь не пустой
            os.makedirs(db_dir, exist_ok=True)
            
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        """Инициализация базы данных"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Таблица для хранения информации о видео
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS videos (
                        video_id TEXT PRIMARY KEY,
                        url TEXT NOT NULL,
                        title TEXT,
                        uploader TEXT,
                        duration INTEGER,
                        view_count INTEGER,
                        upload_date TEXT,
                        thumbnail TEXT,
                        description TEXT,
                        download_date TEXT,
                        download_path TEXT,
                        metadata TEXT
                    )
                ''')
                
                # Таблица для хранения информации о загруженных видео
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS uploaded_videos (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        local_path TEXT NOT NULL,
                        title TEXT NOT NULL,
                        vk_owner_id INTEGER,
                        vk_video_id INTEGER,
                        vk_url TEXT,
                        upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                conn.commit()
                logger.debug("База данных инициализирована")
        except Exception as e:
            logger.error(f"Ошибка при инициализации БД: {str(e)}")
            raise
    
    def add_video(self, video_info, download_path=None):
        """Добавление видео в базу"""
        try:
            video_id = video_info.get('id') or video_info['url'].split('=')[-1]
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT OR REPLACE INTO videos (
                        video_id, url, title, uploader, duration, view_count,
                        upload_date, thumbnail, description, download_date,
                        download_path, metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    video_id,
                    video_info.get('url', ''),
                    video_info.get('title', ''),
                    video_info.get('uploader', ''),
                    video_info.get('duration', 0),
                    video_info.get('view_count', 0),
                    video_info.get('upload_date', ''),
                    video_info.get('thumbnail', ''),
                    video_info.get('description', ''),
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    download_path,
                    json.dumps(video_info)
                ))
                
                logger.debug(f"Видео добавлено в БД: {video_id}")
        except Exception as e:
            logger.error(f"Ошибка при добавлении видео в БД: {str(e)}")
            raise
    
    def get_video(self, url):
        """Получение информации о видео из базы"""
        try:
            video_id = url.split('=')[-1]
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('SELECT metadata FROM videos WHERE video_id = ?', (video_id,))
                result = cursor.fetchone()
                
                if result:
                    return json.loads(result[0])
                return None
                
        except Exception as e:
            logger.error(f"Ошибка при получении видео из БД: {str(e)}")
            return None
    
    def get_downloaded_videos(self):
        """Получение списка скачанных видео"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT video_id, url, title, download_path, download_date 
                    FROM videos 
                    WHERE download_path IS NOT NULL 
                    ORDER BY download_date DESC
                ''')
                
                return cursor.fetchall()
                
        except Exception as e:
            logger.error(f"Ошибка при получении списка скачанных видео: {str(e)}")
            return []
    
    def update_download_path(self, url, path):
        """Обновление пути к скачанному файлу"""
        try:
            video_id = url.split('=')[-1]
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    UPDATE videos 
                    SET download_path = ?, download_date = ? 
                    WHERE video_id = ?
                ''', (path, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), video_id))
                
                conn.commit()
                logger.debug(f"Обновлен путь скачивания для видео: {video_id}")
                
        except Exception as e:
            logger.error(f"Ошибка при обновлении пути скачивания: {str(e)}")
            raise

    def add_uploaded_video(self, local_path, title, vk_owner_id, vk_video_id, vk_url):
        """Добавление информации о загруженном видео"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO uploaded_videos 
                    (local_path, title, vk_owner_id, vk_video_id, vk_url)
                    VALUES (?, ?, ?, ?, ?)
                ''', (local_path, title, vk_owner_id, vk_video_id, vk_url))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Ошибка при добавлении видео в БД: {str(e)}")
            return False
            
    def get_video_info(self, local_path):
        """Получение информации о загруженном видео"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT vk_owner_id, vk_video_id, vk_url
                    FROM uploaded_videos
                    WHERE local_path = ?
                ''', (local_path,))
                return cursor.fetchone()
        except Exception as e:
            logger.error(f"Ошибка при получении информации о видео: {str(e)}")
            return None 