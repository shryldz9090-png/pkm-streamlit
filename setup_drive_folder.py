"""
Google Drive'da Trade Asistanı için klasör oluşturur
"""

from google.oauth2 import service_account
from googleapiclient.discovery import build
import sys

# Windows için UTF-8 encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

def setup_drive_folder():
    """Google Drive'da 'Trade_Asistani_Images' klasörü oluşturur"""

    # Credentials
    SCOPES = ['https://www.googleapis.com/auth/drive']
    SERVICE_ACCOUNT_FILE = 'credentials.json'

    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)

    service = build('drive', 'v3', credentials=creds)

    print("Google Drive'a bağlanıldı...")

    # Klasör var mı kontrol et
    folder_name = 'Trade_Asistani_Images'

    query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    results = service.files().list(q=query, fields="files(id, name)").execute()
    folders = results.get('files', [])

    if folders:
        folder_id = folders[0]['id']
        print(f"✅ Klasör zaten mevcut: {folder_name}")
        print(f"   Klasör ID: {folder_id}")
    else:
        # Klasör oluştur
        file_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder'
        }

        folder = service.files().create(body=file_metadata, fields='id').execute()
        folder_id = folder.get('id')

        print(f"✅ Yeni klasör oluşturuldu: {folder_name}")
        print(f"   Klasör ID: {folder_id}")

        # Klasörü herkese açık yap (anyone with link can view)
        permission = {
            'type': 'anyone',
            'role': 'reader'
        }
        service.permissions().create(
            fileId=folder_id,
            body=permission
        ).execute()

        print("✅ Klasör herkese açık yapıldı (anyone with link can view)")

    print("\n" + "="*60)
    print("Klasör ID'yi bir yere kaydet, lazım olacak!")
    print(f"FOLDER_ID = '{folder_id}'")
    print("="*60)

    return folder_id

if __name__ == "__main__":
    print("🔧 Google Drive Klasör Kurulumu")
    print("="*60)
    setup_drive_folder()
