"""
Google Drive işlemleri için yardımcı fonksiyonlar
"""

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io
from PIL import Image
import sys

# Windows için UTF-8 encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Google Drive Folder ID
FOLDER_ID = '16dN4tQzpxoWvYY0UsZbmQy-0JH3YBrvV'

def get_drive_service():
    """Google Drive servisini döndürür"""
    SCOPES = ['https://www.googleapis.com/auth/drive']
    SERVICE_ACCOUNT_FILE = 'credentials.json'

    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)

    service = build('drive', 'v3', credentials=creds)
    return service

def optimize_image(image_source, is_path=False):
    """
    Görseli optimize eder
    - 1200x900 boyutuna küçült (yüksek kalite)
    - JPEG kalite 85%
    - BytesIO buffer döndür

    Args:
        image_source: PIL Image veya dosya yolu
        is_path: True ise image_source dosya yoludur
    """
    try:
        if is_path:
            image = Image.open(image_source)
        else:
            image = image_source

        # RGB'ye çevir (RGBA ise)
        if image.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', image.size, (255, 255, 255))
            if image.mode == 'P':
                image = image.convert('RGBA')
            background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
            image = background

        # Yüksek kalite boyutlandırma
        image.thumbnail((1200, 900), Image.Resampling.LANCZOS)

        # JPEG formatında buffer'a kaydet - Yüksek kalite
        buffer = io.BytesIO()
        image.save(buffer, format='JPEG', quality=85, optimize=True)
        buffer.seek(0)

        return buffer
    except Exception as e:
        print(f"⚠️  Görsel optimize edilirken hata: {e}")
        return None

def upload_image_to_drive(image_source, filename, is_path=False):
    """
    Görseli Google Drive'a yükler ve public URL döndürür

    Args:
        image_source: PIL Image, UploadedFile veya dosya yolu
        filename: Dosya adı (örn: 'experience_1.jpg')
        is_path: True ise image_source dosya yoludur

    Returns:
        Public görüntü URL'i veya None (hata durumunda)
    """
    try:
        # Görseli optimize et
        buffer = optimize_image(image_source, is_path=is_path)
        if not buffer:
            return None

        # Drive servisini al
        service = get_drive_service()

        # Dosya metadata
        file_metadata = {
            'name': filename,
            'parents': [FOLDER_ID]
        }

        # Medya dosyası
        media = MediaIoBaseUpload(buffer, mimetype='image/jpeg', resumable=True)

        # Dosyayı yükle
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()

        file_id = file.get('id')

        # Herkese açık yap (anyone with link can view)
        permission = {
            'type': 'anyone',
            'role': 'reader'
        }
        service.permissions().create(
            fileId=file_id,
            body=permission
        ).execute()

        # Public URL oluştur (direkt görüntü URL'i)
        image_url = f"https://drive.google.com/uc?export=view&id={file_id}"

        print(f"✅ Görsel Drive'a yüklendi: {filename}")
        print(f"   URL: {image_url}")

        return image_url

    except Exception as e:
        print(f"❌ Görsel Drive'a yüklenirken hata: {e}")
        return None

def delete_image_from_drive(file_id):
    """
    Google Drive'dan görseli siler

    Args:
        file_id: Drive file ID (URL'den çıkarılabilir)

    Returns:
        True (başarılı) veya False (hata)
    """
    try:
        service = get_drive_service()
        service.files().delete(fileId=file_id).execute()
        print(f"✅ Görsel Drive'dan silindi: {file_id}")
        return True
    except Exception as e:
        print(f"❌ Görsel Drive'dan silinirken hata: {e}")
        return False

def extract_file_id_from_url(url):
    """
    Drive URL'inden file ID'yi çıkarır

    Args:
        url: Drive image URL (örn: https://drive.google.com/uc?export=view&id=XXXXXX)

    Returns:
        File ID veya None
    """
    try:
        if 'id=' in url:
            return url.split('id=')[-1]
        return None
    except:
        return None
