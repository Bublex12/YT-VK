import os
import logging
import traceback
import requests
import subprocess
from typing import Optional, Tuple
from yt_dlp import YoutubeDL
from config import *
import time
import random
from database import VideoDatabase

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.FileHandler('video_transfer.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# В начале файла добавим инициализацию БД
db = VideoDatabase()

def check_ffmpeg():
    """Проверка и установка ffmpeg"""
    try:
        subprocess.run(['ffmpeg', '-version'], capture_output=True)
        logger.debug("ffmpeg уже установлен")
        return True
    except FileNotFoundError:
        logger.info("ffmpeg не найден")
        return False

def download_thumbnail(url: str, output_dir: str, video_title: str = None) -> Optional[str]:
    """Скачивание превью видео"""
    try:
        response = requests.get(url)
        response.raise_for_status()
        
        # Создаем уникальное имя файла из названия видео или timestamp
        if video_title:
            safe_title = "".join(c for c in video_title if c.isalnum() or c in (' ', '-', '_')).rstrip()
            thumbnail_name = f"{safe_title}_thumb_{int(time.time())}.jpg"
        else:
            thumbnail_name = f"thumbnail_{int(time.time())}.jpg"
            
        thumbnail_path = os.path.join(output_dir, thumbnail_name)
        
        with open(thumbnail_path, 'wb') as f:
            f.write(response.content)
            
        logger.debug(f"Превью сохранено: {thumbnail_path}")
        return thumbnail_path
    except Exception as e:
        logger.error(f"Ошибка при скачивании превью: {str(e)}")
        return None

def download_only_thumbnail(url: str, output_dir: str = OUTPUT_DIR) -> Optional[str]:
    """
    Скачивание только превью видео с YouTube
    """
    logger.debug(f"Получение превью для видео: {url}")
    try:
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
        }
        
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            thumbnail_url = info.get('thumbnail')
            title = info.get('title', '')
            
            if thumbnail_url:
                return download_thumbnail(thumbnail_url, output_dir, title)
            else:
                logger.error("Превью не найдено")
                return None
    except Exception as e:
        logger.error(f"Ошибка при получении превью: {str(e)}")
        return None

def check_video_has_audio(formats: list) -> bool:
    """Проверка наличия аудио в форматах видео"""
    for format in formats:
        if format.get('acodec') != 'none':
            return True
    return False

def get_available_formats(url: str) -> list:
    """Получение списка доступных форматов видео"""
    logger.debug(f"Получение форматов для видео: {url}")
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
        }
        
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            formats = []
            
            # Получаем лучший аудио формат
            best_audio = None
            for f in info.get('formats', []):
                if f.get('vcodec', '') == 'none' and f.get('acodec', 'none') != 'none':
                    if best_audio is None or f.get('filesize', 0) > best_audio.get('filesize', 0):
                        best_audio = f
            
            # Фильтруем и группируем форматы
            for f in info.get('formats', []):
                # Пропускаем аудио-форматы
                if f.get('vcodec', '') == 'none':
                    continue
                    
                format_id = f.get('format_id', '')
                ext = f.get('ext', '')
                resolution = f.get('resolution', 'unknown')
                filesize = f.get('filesize', 0)
                filesize_mb = filesize / (1024 * 1024) if filesize else 0
                has_audio = f.get('acodec', 'none') != 'none'
                
                # Если формат без звука и есть лучший аудио формат, создаем комбинированный формат
                if not has_audio and best_audio:
                    combined_format_id = f"{format_id}+{best_audio['format_id']}"
                    combined_filesize = filesize + best_audio.get('filesize', 0)
                    combined_filesize_mb = combined_filesize / (1024 * 1024) if combined_filesize else 0
                    
                    format_str = f"{resolution} ({ext}) + 🔊"
                    if combined_filesize_mb > 0:
                        format_str += f" - {combined_filesize_mb:.1f}MB"
                    
                    formats.append({
                        'format_id': combined_format_id,
                        'ext': ext,
                        'resolution': resolution,
                        'filesize': combined_filesize,
                        'has_audio': True,
                        'display': format_str
                    })
                
                # Добавляем оригинальный формат
                format_str = f"{resolution} ({ext})"
                if filesize_mb > 0:
                    format_str += f" - {filesize_mb:.1f}MB"
                if has_audio:
                    format_str += " 🔊"
                else:
                    format_str += " 🔇"
                
                formats.append({
                    'format_id': format_id,
                    'ext': ext,
                    'resolution': resolution,
                    'filesize': filesize,
                    'has_audio': has_audio,
                    'display': format_str
                })
            
            # Сортируем по качеству и размеру
            def sort_key(x):
                # Извлекаем числовое значение разрешения (например, из "1920x1080" получаем 1080)
                res = x['resolution']
                height = int(res.split('x')[1]) if 'x' in res else 0
                return (x['has_audio'], height, x['filesize'] if x['filesize'] else 0)
            
            formats.sort(key=sort_key, reverse=True)
            
            return formats
            
    except Exception as e:
        logger.error(f"Ошибка при получении форматов: {str(e)}")
        raise

def download_youtube_video(url: str, output_dir: str = OUTPUT_DIR, title: str = None) -> Tuple[str, Optional[str]]:
    """
    Скачивание видео с YouTube используя yt-dlp
    Пытается скачать в Full HD (1080p), если недоступно - берет максимальное качество
    """
    logger.debug(f"Начало функции download_youtube_video с URL: {url}")
    try:
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        # Получаем информацию о видео для создания папки
        with YoutubeDL({'quiet': True}) as ydl:
            info = ydl.extract_info(url, download=False)
            video_title = title or info['title']
            timestamp = f"{int(time.time())}_{random.randint(1000, 9999)}"
            video_dir = os.path.join(output_dir, f"{video_title}_{timestamp}")
            
            # Создаем отдельную папку для видео
            os.makedirs(video_dir, exist_ok=True)
            logger.debug(f"Создана папка для видео: {video_dir}")
            
        # Сначала пробуем скачать в Full HD
        ydl_opts = {
            'format': 'bestvideo[height=1080][ext=mp4]+bestaudio[ext=m4a]/best[height=1080][ext=mp4]/best[ext=mp4]/best',
            'outtmpl': os.path.join(video_dir, f"{video_title}.%(ext)s"),
            'merge_output_format': 'mp4',
            'postprocessors': [{
                'key': 'FFmpegVideoConvertor',
                'preferedformat': 'mp4',
            }],
            'quiet': True,
            'no_warnings': True,
            'writethumbnail': True,
        }
        
        try:
            # Пробуем скачать в Full HD
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                logger.info("Видео успешно скачано в Full HD качестве")
        except Exception as e:
            logger.info("Не удалось скачать в Full HD, пробуем максимальное качество")
            # Если не получилось, скачиваем в максимальном качестве
            ydl_opts['format'] = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                logger.info("Видео успешно скачано в максимальном доступном качестве")
        
        video_path = os.path.join(video_dir, f"{video_title}.mp4")
        video_path = os.path.normpath(video_path)
        
        # Проверяем существование файла
        if not os.path.exists(video_path):
            logger.error(f"Файл не найден после скачивания: {video_path}")
            # Пробуем найти файл в директории
            mp4_files = [f for f in os.listdir(video_dir) if f.endswith('.mp4')]
            if mp4_files:
                video_path = os.path.join(video_dir, mp4_files[0])
                video_path = os.path.normpath(video_path)
                logger.info(f"Найден альтернативный файл: {video_path}")
            else:
                raise FileNotFoundError(f"Видео не найдено в директории: {video_dir}")
        
        # Удаляем все лишние файлы, оставляем только MP4 и превью
        for file in os.listdir(video_dir):
            file_path = os.path.join(video_dir, file)
            if file_path != video_path and not file.endswith(('.jpg', '.png', '.webp')):
                try:
                    os.remove(file_path)
                    logger.debug(f"Удален временный файл: {file_path}")
                except Exception as e:
                    logger.warning(f"Не удалось удалить файл {file_path}: {str(e)}")
        
        # Скачиваем превью
        thumbnail_url = info.get('thumbnail')
        thumbnail_path = None
        if thumbnail_url:
            thumbnail_path = download_thumbnail(thumbnail_url, video_dir, video_title)
        
        logger.info(f"Видео успешно скачано: {video_path}")
        if thumbnail_path:
            logger.info(f"Превью сохранено: {thumbnail_path}")
        
        return video_path, thumbnail_path
        
    except Exception as e:
        logger.error(f"Ошибка при скачивании видео: {str(e)}")
        logger.error(f"Полный стек ошибки:\n{traceback.format_exc()}")
        raise

def download_progress_hook(d):
    """Отображение прогресса скачивания для yt-dlp"""
    if d['status'] == 'downloading':
        total = d.get('total_bytes')
        downloaded = d.get('downloaded_bytes', 0)
        if total:
            percentage = (downloaded / total) * 100
            print(f"\rПрогресс: {percentage:.1f}%", end="")
    elif d['status'] == 'finished':
        print("\nЗагрузка завершена!")

def get_video_info(url: str) -> dict:
    """Получение информации о видео"""
    logger.debug(f"Получение информации о видео: {url}")
    
    # Сначала пробуем получить из БД
    cached_info = db.get_video(url)
    if cached_info:
        logger.debug("Информация получена из кэша")
        return cached_info
    
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
        }
        
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            # Сохраняем в БД
            db.add_video(info)
            return info
    except Exception as e:
        logger.error(f"Ошибка при получении информации о видео: {str(e)}")
        raise

def search_youtube_videos(query: str, min_views: int = 0, excluded_words: list = None, max_results: int = 50) -> list:
    """
    Поиск видео на YouTube по заданным критериям
    """
    logger.debug(f"Поиск видео по запросу: {query}, мин. просмотров: {min_views}, макс. результатов: {max_results}")
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'force_generic_extractor': False,
        }
        
        with YoutubeDL(ydl_opts) as ydl:
            # Поиск видео
            search_query = f"ytsearch{min(max_results * 2, 100)}:{query}"
            results = ydl.extract_info(search_query, download=False)
            
            if not results or 'entries' not in results:
                logger.warning("Ничего не найдено")
                return []
            
            # Фильтрация результатов
            filtered_videos = []
            excluded_words = [word.lower() for word in (excluded_words or [])]
            
            # Список украинских маркеров
            ukrainian_markers = [
                # Доменные зоны и сокращения
                'ua', '.ua', 'укр', 'ukr',
                
                # Города
                'київ', 'киев', 'львів', 'львов', 'харків', 'харьков', 
                'одеса', 'одесса', 'дніпро', 'днепр', 'запоріжжя', 'запорожье',
                
                # Языковые маркеры
                'україн', 'украин', 'украïн',
                'украïнською', 'украïнська', 'українською', 'українська',
                'украинский', 'украинская', 'по-украински',
                
                # Каналы и медиа
                'тсн', 'громадське', 'общественное',
                '1+1', 'інтер', 'интер', 'новий', 'новый',
                'україна', 'украина', 'ukrainian',
                
                # Распространенные слова
                'перемога', 'незалежність', 'майдан',
                'слава україні', 'слава украине',
                'вісті', 'вести', 'новини', 'новости украины'
            ]
            
            for video in results['entries']:
                if len(filtered_videos) >= max_results:
                    break
                    
                if not video:
                    continue
                
                # Проверяем различные поля на наличие украинских маркеров
                is_ukrainian = False
                
                # Проверяем название канала
                channel_name = video.get('channel', '').lower()
                channel_title = video.get('channel_title', '').lower()
                uploader = video.get('uploader', '').lower()
                
                for channel_identifier in [channel_name, channel_title, uploader]:
                    if any(marker in channel_identifier for marker in ukrainian_markers):
                        is_ukrainian = True
                        logger.debug(f"Обнаружен украинский канал: {video.get('channel', 'Неизвестно')}")
                        break
                
                # Проверяем язык канала
                channel_lang = video.get('channel_language', '').lower()
                if channel_lang in ['uk', 'ua']:
                    is_ukrainian = True
                    logger.debug(f"Обнаружен украинский язык канала: {channel_lang}")
                
                # Проверяем страну канала
                channel_country = video.get('channel_country', '').lower()
                if channel_country in ['ua', 'ukr', 'ukraine', 'україна', 'украина']:
                    is_ukrainian = True
                    logger.debug(f"Обнаружена украинская страна канала: {channel_country}")
                
                # Проверяем описание канала
                channel_description = video.get('channel_description', '').lower()
                if any(marker in channel_description for marker in ukrainian_markers):
                    is_ukrainian = True
                    logger.debug(f"Обнаружены украинские маркеры в описании канала")
                
                # Проверяем название и описание видео
                title = video.get('title', '').lower()
                description = video.get('description', '').lower()
                
                if any(marker in title for marker in ukrainian_markers):
                    is_ukrainian = True
                    logger.debug(f"Обнаружены украинские маркеры в названии видео: {video.get('title')}")
                
                if any(marker in description for marker in ukrainian_markers):
                    is_ukrainian = True
                    logger.debug(f"Обнаружены украинские маркеры в описании видео")
                
                # Пропускаем украинские видео
                if is_ukrainian:
                    logger.debug(f"Пропущено украинское видео: {video.get('title')}")
                    continue
                
                view_count = video.get('view_count', 0)
                
                # Проверяем критерии
                if view_count < min_views:
                    continue
                    
                if excluded_words and any(word in description for word in excluded_words):
                    continue
                
                # Сохраняем в БД для кэширования
                try:
                    db.add_video(video)
                except Exception as e:
                    logger.error(f"Ошибка при сохранении видео в БД: {str(e)}")
                
                filtered_videos.append({
                    'url': f"https://www.youtube.com/watch?v={video['id']}",
                    'title': video.get('title', 'Без названия'),
                    'views': view_count,
                    'duration': video.get('duration', 0),
                    'thumbnail': video.get('thumbnail'),
                    'uploader': video.get('uploader', 'Неизвестно'),
                    'description': video.get('description', ''),
                    'upload_date': video.get('upload_date', '')
                })
            
            logger.info(f"Найдено видео: {len(filtered_videos)}")
            return filtered_videos[:max_results]
            
    except Exception as e:
        logger.error(f"Ошибка при поиске видео: {str(e)}")
        logger.debug(f"Полный стек ошибки:\n{traceback.format_exc()}")
        raise

def get_channel_videos(channel_url: str, max_videos: int = 50) -> list:
    """Получение списка видео с канала"""
    logger.debug(f"Получение видео с канала: {channel_url}")
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
            'force_generic_extractor': False,
            'playlistend': max_videos  # Ограничиваем количество видео
        }
        
        with YoutubeDL(ydl_opts) as ydl:
            # Получаем информацию о канале и его видео
            channel_info = ydl.extract_info(
                channel_url,
                download=False,
                process=False
            )
            
            videos = []
            entries = list(channel_info.get('entries', []))  # Преобразуем генератор в список
            
            # Обрабатываем каждое видео
            for entry in entries:
                try:
                    # Получаем полную информацию о видео
                    video_info = ydl.extract_info(
                        entry['url'],
                        download=False,
                        process=False
                    )
                    
                    if not video_info:
                        continue
                    
                    videos.append({
                        'url': f"https://www.youtube.com/watch?v={video_info['id']}",
                        'title': video_info.get('title', 'Без названия'),
                        'views': video_info.get('view_count', 0),
                        'duration': video_info.get('duration', 0),
                        'thumbnail': video_info.get('thumbnail'),
                        'uploader': video_info.get('uploader', 'Неизвестно'),
                        'description': video_info.get('description', ''),
                        'upload_date': video_info.get('upload_date', '')
                    })
                    
                    # Сохраняем в БД для кэширования
                    try:
                        db.add_video(video_info)
                    except Exception as e:
                        logger.error(f"Ошибка при сохранении видео в БД: {str(e)}")
                    
                    # Проверяем достижение лимита
                    if len(videos) >= max_videos:
                        break
                        
                except Exception as e:
                    logger.error(f"Ошибка при получении информации о видео: {str(e)}")
                    continue
            
            logger.info(f"Найдено видео на канале: {len(videos)}")
            return videos
            
    except Exception as e:
        logger.error(f"Ошибка при получении видео с канала: {str(e)}")
        logger.debug(f"Полный стек ошибки:\n{traceback.format_exc()}")
        raise

if __name__ == "__main__":
    try:
        youtube_video_url = input("Введите ссылку на YouTube видео: ")
        video_path, thumb_path = download_youtube_video(youtube_video_url)
        print(f"Видео сохранено: {video_path}")
        if thumb_path:
            print(f"Превью сохранено: {thumb_path}")
    except KeyboardInterrupt:
        logger.info("Процесс прерван пользователем")
    except Exception as e:
        logger.error(f"Критическая ошибка: {str(e)}")
