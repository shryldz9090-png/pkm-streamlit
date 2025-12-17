"""
imgbb.com kullanarak görsel yükleme
Ücretsiz, API key gerektiriyor: https://api.imgbb.com/
"""

import requests
import base64
from PIL import Image
import io
import sys

# Windows için UTF-8 encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# imgbb API Key - https://api.imgbb.com/ adresinden alabilirsin
IMGBB_API_KEY = "eae6d590925076dff64ba4d166a6c0b3"  # API key eklendi! ✅

def optimize_image_for_imgbb(image_source, is_path=False):
    """
    Görseli yüksek kaliteyle optimize eder
    - 1920x1440 boyutuna kadar (full HD kalite)
    - JPEG kalite 90%
    - Base64 string döndür (imgbb için gerekli)

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

        # Yüksek kalite boyutlandırma (Full HD)
        image.thumbnail((1920, 1440), Image.Resampling.LANCZOS)

        # JPEG formatında buffer'a kaydet - Yüksek kalite
        buffer = io.BytesIO()
        image.save(buffer, format='JPEG', quality=90, optimize=True)

        # Base64'e çevir (imgbb API gereksinimi)
        base64_image = base64.b64encode(buffer.getvalue()).decode()

        return base64_image
    except Exception as e:
        print(f"⚠️  Görsel optimize edilirken hata: {e}")
        return None

def upload_image_to_imgbb(image_source, filename="image", is_path=False):
    """
    Görseli imgbb'ye yükler ve URL döndürür

    Args:
        image_source: PIL Image, UploadedFile veya dosya yolu
        filename: Dosya adı (isteğe bağlı)
        is_path: True ise image_source dosya yoludur

    Returns:
        {
            'url': 'https://i.ibb.co/xxxxx/image.jpg',  # Direkt görüntü URL'i
            'delete_url': 'https://ibb.co/xxxxx/delete_token',  # Silme URL'i
            'thumb': 'https://i.ibb.co/xxxxx/image_thumb.jpg'  # Thumbnail
        }
        veya None (hata durumunda)
    """
    try:
        if IMGBB_API_KEY == "YOUR_API_KEY_HERE":
            print("❌ imgbb API key eklenmemiş! imgbb_utils.py dosyasını düzenle.")
            return None

        # Görseli optimize et ve Base64'e çevir
        base64_image = optimize_image_for_imgbb(image_source, is_path=is_path)
        if not base64_image:
            return None

        # imgbb API endpoint
        url = "https://api.imgbb.com/1/upload"

        # Request parametreleri
        payload = {
            "key": IMGBB_API_KEY,
            "image": base64_image,
            "name": filename
        }

        # API'ye gönder
        response = requests.post(url, data=payload)

        if response.status_code == 200:
            data = response.json()

            if data['success']:
                image_data = data['data']

                result = {
                    'url': image_data['url'],  # Direkt görüntü linki
                    'display_url': image_data['display_url'],  # Display sayfası
                    'delete_url': image_data['delete_url'],  # Silme linki
                    'thumb': image_data.get('thumb', {}).get('url', '')  # Thumbnail
                }

                print(f"✅ Görsel imgbb'ye yüklendi!")
                print(f"   URL: {result['url']}")

                return result
            else:
                print(f"❌ imgbb yükleme hatası: {data.get('error', {}).get('message', 'Bilinmeyen hata')}")
                return None
        else:
            print(f"❌ imgbb API hatası: {response.status_code}")
            print(f"   Response: {response.text}")
            return None

    except Exception as e:
        print(f"❌ Görsel yüklenirken hata: {e}")
        return None

def delete_image_from_imgbb(delete_url):
    """
    imgbb'den görseli siler

    Args:
        delete_url: Silme URL'i (upload sırasında dönen delete_url)

    Returns:
        True (başarılı) veya False (hata)
    """
    try:
        # imgbb delete endpoint'i basit bir GET request
        response = requests.get(delete_url)

        if response.status_code == 200:
            print(f"✅ Görsel imgbb'den silindi")
            return True
        else:
            print(f"❌ Silme hatası: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Görsel silinirken hata: {e}")
        return False
