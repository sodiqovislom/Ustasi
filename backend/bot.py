import os
import sys
import io
import json
import math
import time
import html
import ssl
import certifi
import threading
import urllib.request
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from pathlib import Path

try:
    import soundfile as sf
    import speech_recognition as sr
    HAS_VOICE_AI = True
except Exception as e:
    HAS_VOICE_AI = False
    print(f"Ovozli AI kutubxonalari faol emas: {e}")

import telebot
from telebot import types
from telebot.handler_backends import BaseMiddleware
import telebot.apihelper as apihelper
from django.utils.text import slugify
from django.db.models import Q
from django.conf import settings

# 0. Windows SSL sertifikatlarini certifi bilan sinxronlash (Faqat Windows uchun)
def sync_system_ssl_certificates():
    if sys.platform != "win32":
        return
    try:
        ca_path = certifi.where()
        with open(ca_path, 'r', encoding='utf-8') as f:
            existing_pem = f.read()

        new_certs = []
        for store in ['ROOT', 'CA']:
            for cert_bytes, encoding_type, trust in ssl.enum_certificates(store):
                try:
                    pem = ssl.DER_cert_to_PEM_cert(cert_bytes)
                    body = pem.split('-----BEGIN CERTIFICATE-----')[1].split('-----END CERTIFICATE-----')[0].strip()
                    if body not in existing_pem and body not in ''.join(new_certs):
                        new_certs.append(f'\n# Windows Certificate Store ({store})\n' + pem)
                except Exception:
                    pass

        if new_certs:
            with open(ca_path, 'a', encoding='utf-8') as f:
                f.write('\n' + '\n'.join(new_certs))
    except Exception as e:
        print(f"Warning during SSL sync: {e}")

    os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()
    os.environ['SSL_CERT_FILE'] = certifi.where()

sync_system_ssl_certificates()

# 0.1. TeleBot uchun tarmoq va timeout sozlamalari (Qotib qolish va sekinlashuvni oldini olish)
apihelper.SESSION_TIME_TO_LIVE = 180  # Har 3 daqiqada eski/o'lik soketlarni avtomatik yangilash
apihelper.READ_TIMEOUT = 15           # Telegram so'rovlari maksimal 15 soniya kutadi
apihelper.CONNECT_TIMEOUT = 10        # Ulanish maksimal 10 soniya kutadi
apihelper.RETRY_ON_ERROR = True       # Xatolik yuz berganda avtomatik qayta urinish

# 0.2. Render Free Tier serveri 15 daqiqada uxlab qolmasligi uchun doimiy Self-Ping (Keep-Alive)
def start_render_keep_alive():
    external_url = os.getenv("RENDER_EXTERNAL_URL")
    if not external_url:
        return

    def ping_loop():
        # Server to'liq yuklanguncha 45 soniya kutish
        time.sleep(45)
        print(f"[Keep-Alive] Render 24/7 uyqudan saqlash xizmati ishga tushdi: {external_url}", flush=True)
        while True:
            try:
                # Har 10 daqiqada (600s) Render tashqi domeniga so'rov yuboriladi
                time.sleep(600)
                resp = requests.get(f"{external_url}/api/categories/", timeout=15)
                print(f"[Keep-Alive] Render ping muvaffaqiyatli: {resp.status_code}", flush=True)
            except Exception as ex:
                print(f"[Keep-Alive] Ping xatosi (muammo emas): {ex}", flush=True)

    t = threading.Thread(target=ping_loop, daemon=True)
    t.start()

start_render_keep_alive()

# 1. Django muhitini sozlash
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ustasi_core.settings')

import django
django.setup()

from django.db import close_old_connections

# 2. Django modellarini import qilish
from apps.masters.models import Category, Master, Service, Rating, PortfolioWork
from apps.users.models import User, normalize_phone_number
from apps.chat.models import Message

# Bot tokeni va admin paroli
BOT_TOKEN = os.getenv("BOT_TOKEN", "8996853557:AAHqmkZCUOyNHGQZthdvBu-SP1noU-hftOk")
ADMIN_SECRET = os.getenv("ADMIN_SECRET", "admin_jack1900")
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://ustasi.uz")
bot = telebot.TeleBot(BOT_TOKEN, num_threads=8, parse_mode="HTML", use_class_middlewares=True)

# 0.2. Django DB ulanishlarini tozalash middleware (SQLite qotib qolishini oldini oladi)
class DjangoDBMiddleware(BaseMiddleware):
    def __init__(self):
        super().__init__()
        self.update_sensitive = False
        self.update_types = ['message', 'callback_query']

    def pre_process(self, message, data):
        close_old_connections()

    def post_process(self, message, data, exception):
        close_old_connections()

    def pre_process_message(self, message, data):
        close_old_connections()

    def post_process_message(self, message, data, exception):
        close_old_connections()

    def pre_process_callback_query(self, call, data):
        close_old_connections()

    def post_process_callback_query(self, call, data, exception):
        close_old_connections()

bot.setup_middleware(DjangoDBMiddleware())

# Ma'lumotlarni saqlash fayllari
ADMINS_FILE = BASE_DIR / "bot_admins.json"
SUBSCRIBERS_FILE = BASE_DIR / "bot_subscribers.json"
MASTER_TG_FILE = BASE_DIR / "master_telegram_ids.json"
LANG_FILE = BASE_DIR / "bot_user_languages.json"
TENDERS_FILE = BASE_DIR / "bot_tenders.json"

# Foydalanuvchi holatlarini vaqtinchalik saqlash
user_states = {}

# Geolokatsiya koordinatalari (Phase 2)
DISTRICT_COORDS = {
    # Toshkent shahri tumanlari
    "Yunusobod tumani": (41.3645, 69.2875),
    "Mirzo Ulug'bek tumani": (41.3283, 69.3344),
    "Chilonzor tumani": (41.2750, 69.2050),
    "Shayxontohur tumani": (41.3200, 69.2300),
    "Yakkasaroy tumani": (41.2750, 69.2550),
    "Mirobod tumani": (41.2850, 69.2800),
    "Sergeli tumani": (41.2200, 69.2200),
    "Olmazor tumani": (41.3450, 69.2200),
    "Uchtepa tumani": (41.2900, 69.1700),
    "Yashnobod tumani": (41.2950, 69.3300),
    "Bektemir tumani": (41.2200, 69.3300),
    "Yangihayot tumani": (41.1900, 69.2100),
    # Viloyatlar markazlari
    "Toshkent shahri": (41.2995, 69.2401),
    "Toshkent viloyati": (41.2500, 69.3500),
    "Samarqand viloyati": (39.6270, 66.9750),
    "Farg'ona viloyati": (40.3842, 71.7843),
    "Andijon viloyati": (40.7821, 72.3442),
    "Namangan viloyati": (40.9983, 71.6726),
    "Buxoro viloyati": (39.7747, 64.4286),
    "Qashqadaryo viloyati": (38.8606, 65.7891),
    "Surxondaryo viloyati": (37.2242, 67.2783),
    "Xorazm viloyati": (41.5504, 60.6314),
    "Navoiy viloyati": (40.0844, 65.3792),
    "Jizzax viloyati": (40.1158, 67.8422),
    "Sirdaryo viloyati": (40.5000, 68.6667),
    "Qoraqalpog'iston Resp.": (42.4619, 59.6166),
    "Qoraqalpog'iston Respublikasi": (42.4619, 59.6166)
}


def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def get_master_coords(m):
    if m.latitude is not None and m.longitude is not None:
        try:
            return (float(m.latitude), float(m.longitude))
        except (ValueError, TypeError):
            pass
    if m.district in DISTRICT_COORDS:
        return DISTRICT_COORDS[m.district]
    for d_name, coords in DISTRICT_COORDS.items():
        if m.district and (d_name.lower() in m.district.lower() or m.district.lower() in d_name.lower()):
            return coords
    if m.region in DISTRICT_COORDS:
        return DISTRICT_COORDS[m.region]
    for r_name, coords in DISTRICT_COORDS.items():
        if m.region and (r_name.lower() in m.region.lower() or m.region.lower() in r_name.lower()):
            return coords
    return (41.2995, 69.2401)


def get_category_pin_style(category_name):
    cat = (category_name or '').lower()
    if any(k in cat for k in ['santexnik', 'plumber', 'suv', 'quvur', 'kran']):
        return 'pm2rdm'   # Qizil belgi (Santexnik)
    elif any(k in cat for k in ['elektr', 'tok', 'chiroq', 'signal', 'avtomat']):
        return 'pm2ywm'   # Sariq belgi (Elektrik)
    elif any(k in cat for k in ['quruvchi', 'tamir', 'remont', 'mebel', 'bino']):
        return 'pm2orgm'  # To'q sariq belgi (Quruvchi / Ta'mirchi)
    elif any(k in cat for k in ['telefon', 'kompyuter', 'texnika', 'tv', 'maishiy']):
        return 'pm2blm'   # Ko'k belgi (Telefon / Maishiy texnika)
    return 'pm2gnm'       # Yashil belgi (Boshqa sohalar)


def build_masters_map_data():
    """
    Tizimdagi barcha faol ustalarni koordinatalari va Yandex Map pinlari bilan tayyorlaydi.
    """
    masters = list(Master.objects.filter(status__in=['active', 'busy']).select_related('category', 'user'))
    tashkent_pins = []
    all_pins = []

    for m in masters:
        lat, lon = get_master_coords(m)
        pin_style = get_category_pin_style(m.category.name if m.category else "")
        pin_entry = f"{lon:.4f},{lat:.4f},{pin_style}"
        all_pins.append(pin_entry)
        reg_str = f"{m.region or ''} {m.district or ''}".lower()
        if 'toshkent' in reg_str or (41.15 <= lat <= 41.45 and 69.10 <= lon <= 69.45):
            tashkent_pins.append(pin_entry)

    target_pins = tashkent_pins if tashkent_pins else all_pins
    tashkent_pt_str = "~".join(target_pins)
    all_pt_str = "~".join(all_pins)

    static_map_url = f"https://static-maps.yandex.ru/1.x/?l=map&size=600,350&ll=69.2600,41.3100&z=11&pt={tashkent_pt_str}"
    yandex_tashkent_url = f"https://yandex.uz/maps/?ll=69.2600,41.3100&z=11&pt={tashkent_pt_str}"
    yandex_all_url = f"https://yandex.uz/maps/?pt={all_pt_str}" if all_pins else yandex_tashkent_url

    return {
        'total_count': len(masters),
        'tashkent_count': len(target_pins),
        'static_map_url': static_map_url,
        'yandex_tashkent_url': yandex_tashkent_url,
        'yandex_all_url': yandex_all_url
    }


# ==========================================
# 🤖 AI INTENT & CATEGORY CLASSIFIER (Feature 1)
# ==========================================
INTENT_CATEGORIES = {
    'Santexnik': [
        'santex', 'santeh', 'sant', 'kran', 'suv', 'trub', 'turb', 'quvur', 
        'oqyapti', 'oqmoq', 'oqdi', 'yoril', 'yoriq', 'tiqil', 'tiqilib', 'tozlash',
        'unitaz', 'vanna', 'dush', 'smesitel', 'kanalizats', 'ariston', 'boyler', 
        'kotyol', 'otoplen', 'radiator', 'batareya', 'nasos', 'filtr', 'chanoq', 
        'rakovina', 'jo\'mrak', 'jomrak', 'sliv', 'sifon', 'gofra', 'trap',
        'водопровод', 'кран', 'смеситель', 'унитаз', 'ванна', 'душ', 'отопление', 'радиатор', 
        'канализация', 'сантехник', 'труба', 'трубы', 'протечка', 'засор', 'прорвало', 'течет'
    ],
    'Elektrik': [
        'elektr', 'elektrik', 'elektrika', 'tok', 'rozetka', 'viklyuchatel', 'vklyuchatel',
        'avtomat', 'provod', 'sim', 'chiroq', 'lyustra', 'svet', 'ochib qoldi', 'yonmayapti', 'o\'chdi', 'ochdi',
        'generator', 'stabilizator', 'shit', 'shitok', 'montaj', 'qisqa tutashuv', 'zamikanie', 'kabel', 
        'schotchik', 'hisoblagich', 'lampochka',
        'signalizats', 'signalizatsiya', 'kamera', 'domofon', 'datchik', 'pult', 'oxrana', 
        'videokamera', 'videonablyudeniye', 'shlagbaum', 'magicar', 'starline',
        'konditsioner', 'konditsoner', 'xolodilnik', 'muzlatgich', 'stiralnaya', 'kir yuvish',
        'электрик', 'электрика', 'розетка', 'выключатель', 'провод', 'свет', 'люстра', 
        'короткое замыкание', 'щиток', 'кабель', 'счетчик', 'лампочка', 'ток', 'автомат',
        'сигнализация', 'камера', 'домофон', 'датчик', 'видеонаблюдение'
    ],
    'Quruvchi': [
        'qurilish', 'quruvchi', 'tamir', 'ta\'mir', 'remont', 'stroyka', 'shpaklyovka', 'shpaklevka', 
        'oboy', 'kraska', 'kafel', 'patalok', 'potolok', 'gipsokarton', 'gips', 'pol', 'laminat', 
        'linoleum', 'eshik', 'rom', 'oyna', 'suvoq', 'shuvoq', 'malyar', 'beton', 'g\'isht', 'gisht', 
        'fasad', 'pardozlash', 'uy tamiri', 'shifer', 'tom', 'krovlya', 'plitka', 'styajka',
        'ремонт', 'стройка', 'строительство', 'строитель', 'шпаклевка', 'обои', 'краска', 
        'кафель', 'ламинат', 'потолок', 'гипсокартон', 'маляр', 'штукатурка', 'стяжка', 'плитка', 'фасад'
    ],
    'Telefon ustasi': [
        'telefon', 'ayfon', 'iphone', 'samsung', 'redmi', 'xiaomi', 'ekran', 'display', 
        'sensor', 'batareyka', 'akkumulyator', 'zaryad', 'zaryadka', 'plata', 'proshivka',
        'steklo', 'shisha', 'dinamik', 'kamera', 'korpus',
        'телефон', 'смартфон', 'экран', 'дисплей', 'батарея', 'зарядка', 'айфон', 'прошивка', 'стекло'
    ]
}

DISTRICT_KEYWORDS = {
    'Chilonzor tumani': ['chilonzor', 'chilanzar', 'чиланзар', 'чилонзор', 'oqtepa', 'октеpa'],
    'Yunusobod tumani': ['yunusobod', 'yunusabad', 'юнусабад', 'юнусобод'],
    'Mirzo Ulug\'bek tumani': ['mirzo ulug\'bek', 'mirzo ulugbek', 'maksim gorkiy', 'buyuk ipak yo\'li', 'мирзо улугбек', 'ulugbek'],
    'Shayxontohur tumani': ['shayxontohur', 'shayxontoxur', 'shayhantohur', 'шейхантахур', 'шайхонтохур', 'chorsu', 'чорсу'],
    'Yakkasaroy tumani': ['yakkasaroy', 'yakkasaray', 'яккасарай', 'яккасарой'],
    'Mirobod tumani': ['mirobod', 'миробад', 'миробод', 'oybek', 'ойбек'],
    'Sergeli tumani': ['sergeli', 'sirg\'ali', 'sirgali', 'сергели', 'сиргали'],
    'Olmazor tumani': ['olmazor', 'almazar', 'алмазар', 'олмазор', 'qoraqamish', 'каракамыш'],
    'Uchtepa tumani': ['uchtepa', 'учтепа'],
    'Yashnobod tumani': ['yashnobod', 'yashnabad', 'яшнабад', 'яшнобод', 'kadisheva', 'кадышева'],
    'Bektemir tumani': ['bektemir', 'бектемир', 'qo\'yliq', 'куйлюк'],
    'Yangihayot tumani': ['yangihayot', 'янгихаёт']
}

def detect_intent_and_district(raw_text):
    if not raw_text:
        return None, None
    t_clean = raw_text.lower()

    detected_cat = None
    for cat_name, keywords in INTENT_CATEGORIES.items():
        for kw in keywords:
            if kw in t_clean:
                # 'ekran' so'zi ichidagi 'kran' ni noto'g'ri santexnikka olmaslik
                if kw == 'kran' and 'ekran' in t_clean and 'kran' not in t_clean.replace('ekran', ''):
                    continue
                detected_cat = cat_name
                break
        if detected_cat:
            break

    detected_district = None
    for dist_name, keywords in DISTRICT_KEYWORDS.items():
        if any(kw in t_clean for kw in keywords):
            detected_district = dist_name
            break

    return detected_cat, detected_district


def transcribe_voice_file(file_id):
    """
    Telegram voice/audio faylini yuklab oladi va SoundFile + SpeechRecognition
    yordamida o'zbek/rus tilida matnga aylantiradi.
    """
    if not file_id:
        return "", None
    if not HAS_VOICE_AI:
        return "", None
    try:
        file_info = bot.get_file(file_id)
        file_bytes = bot.download_file(file_info.file_path)

        # 1. Mahalliy media papkaga saqlash
        ext = "mp3" if file_info.file_path.endswith(".mp3") else "ogg"
        voice_dir = Path(settings.MEDIA_ROOT) / "voice_orders"
        voice_dir.mkdir(parents=True, exist_ok=True)
        filename = f"voice_{int(time.time())}_{file_id[:8]}.{ext}"
        filepath = voice_dir / filename
        with open(filepath, "wb") as f:
            f.write(file_bytes)
        media_url = f"/media/voice_orders/{filename}"

        # 2. Soundfile orqali OGG Opus ni WAV ga aylantirish (xotirada)
        ogg_bio = io.BytesIO(file_bytes)
        data, samplerate = sf.read(ogg_bio)

        wav_bio = io.BytesIO()
        sf.write(wav_bio, data, samplerate, format='WAV', subtype='PCM_16')
        wav_bio.seek(0)

        # 3. SpeechRecognition orqali Google STT
        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_bio) as source:
            audio = recognizer.record(source)

        text = None
        # O'zbek tili
        try:
            text = recognizer.recognize_google(audio, language="uz-UZ")
        except Exception:
            pass

        # Rus tili
        if not text:
            try:
                text = recognizer.recognize_google(audio, language="ru-RU")
            except Exception:
                pass

        return (text or "").strip(), media_url
    except Exception as e:
        print(f"Ovozni tahlil qilishda xatolik: {e}")
        return "", None


UZBEKISTAN_REGIONS = [
    "Toshkent shahri", "Toshkent viloyati",
    "Samarqand viloyati", "Farg'ona viloyati",
    "Andijon viloyati", "Namangan viloyati",
    "Buxoro viloyati", "Qashqadaryo viloyati",
    "Surxondaryo viloyati", "Xorazm viloyati",
    "Navoiy viloyati", "Jizzax viloyati",
    "Sirdaryo viloyati", "Qoraqalpog'iston Resp."
]

REGION_DISTRICTS = {
    "Toshkent shahri": [
        "Yunusobod tumani", "Mirzo Ulug'bek tumani", "Chilonzor tumani",
        "Shayxontohur tumani", "Yakkasaroy tumani", "Mirobod tumani",
        "Sergeli tumani", "Olmazor tumani", "Uchtepa tumani",
        "Yashnobod tumani", "Bektemir tumani", "Yangihayot tumani"
    ],
    "Toshkent viloyati": [
        "Chirchiq shahri", "Olmaliq shahri", "Angren shahri",
        "Qibray tumani", "Zangiota tumani", "Bo'stonliq tumani",
        "Yangiyo'l tumani", "Bekobod tumani"
    ],
    "Samarqand viloyati": [
        "Samarqand shahri", "Urgut tumani", "Pastdarg'om tumani",
        "Bulung'ur tumani", "Kattaqo'rg'on shahri"
    ],
    "Farg'ona viloyati": [
        "Farg'ona shahri", "Marg'ilon shahri", "Qo'qon shahri",
        "Quva tumani", "Oltiariq tumani"
    ],
    "Andijon viloyati": [
        "Andijon shahri", "Asaka tumani", "Shahrixon tumani", "Xo'jaobod tumani"
    ],
    "Namangan viloyati": [
        "Namangan shahri", "Chust tumani", "Kosonsoy tumani", "To'raqo'rg'on tumani"
    ],
    "Buxoro viloyati": [
        "Buxoro shahri", "G'ijduvon tumani", "Kogon shahri"
    ],
    "Qashqadaryo viloyati": [
        "Qarshi shahri", "Shahrisabz shahri", "Kitob tumani", "Koson tumani"
    ],
    "Surxondaryo viloyati": [
        "Termiz shahri", "Denov tumani", "Sherobod tumani"
    ],
    "Xorazm viloyati": [
        "Urganch shahri", "Xiva shahri", "Xonqa tumani"
    ],
    "Navoiy viloyati": [
        "Navoiy shahri", "Zarafshon shahri", "Karmana tumani"
    ],
    "Jizzax viloyati": [
        "Jizzax shahri", "Zomin tumani", "G'allaorol tumani"
    ],
    "Sirdaryo viloyati": [
        "Guliston shahri", "Yangiyer shahri", "Boyovut tumani"
    ],
    "Qoraqalpog'iston Resp.": [
        "Nukus shahri", "Xo'jayli tumani", "Beruniy tumani", "To'rtko'l tumani"
    ]
}


# ==========================================
# 🌐 3 TILLI TIZIM (I18N: UZ / RU / EN)
# ==========================================
I18N = {
    'uz': {
        'btn_categories': "🛠 Kategoriyalar",
        'btn_top': "⭐ Eng yaxshi ustalar",
        'btn_reg_master': "👷‍♂️ Usta bo'lib ro'yxatdan o'tish",
        'btn_profile': "👤 Profilim",
        'btn_lang': "🌐 Tilni o'zgartirish",
        'btn_help': "ℹ️ Ma'lumot",
        'btn_admin': "🔐 Admin Panel",
        'btn_back': "⬅️ Asosiy menyu",
        'btn_cancel': "❌ Bekor qilish",
        'btn_all_regions': "🇺🇿 Barcha hududlar",
        'btn_all_districts': "🏙 Butun shahar/viloyat bo'yicha",
        'btn_back_to_cats': "⬅️ Kategoriyalarga qaytish",
        'btn_back_to_regions': "⬅️ Boshqa viloyatni tanlash",
        'btn_prev': "⬅️ Oldingi",
        'btn_next': "Keyingi ➡️",
        'btn_send_msg': "💬 Xabar yozish",
        'btn_rate': "⭐ Baholash (1-5)",
        'btn_back_to_list': "⬅️ Ro'yxatga qaytish",
        'btn_share_phone': "📱 Telefon raqamimni yuborish",
        'btn_update_phone': "📱 Telefon raqamimni yangilash",
        'welcome': "Assalomu alaykum, <b>{name}</b>!\n\n<b>'Ustasi'</b> platformasining rasmiy Telegram botiga xush kelibsiz.\nBu yerda siz eng mohir ustalarni topishingiz, ularga to'g'ridan-to'g'ri xabar yozishingiz yoki <b>usta sifatida ro'yxatdan o'tishingiz</b> mumkin.\n\n⚡️ <b>ENG TEZKOR USUL (AI OVOZLI BUYURTMA):</b>\nSoha yoki tumanlarni qidirish shart emas! Shunchaki <b>pastdagi mikrofonni bosib</b> o'z muammoingizni gapiring (masalan: <i>«Chilonzorda santexnik kerak, krant oqyapti»</i>) — AI tizimimiz vazifani darhol kerakli ustalarga yetkazadi!",
        'input_placeholder': "🎙 Mikrofonni bosib gapiring yoki yozing...",
        'select_cat': "🛠 <b>Kerakli xizmat kategoriyasini tanlang:</b>",
        'prompt_region': "📍 <b>{cat}</b> bo'yicha qaysi hududdan usta qidiryapsiz?\n\nO'z viloyatingizni tanlang:",
        'prompt_district': "📍 <b>{reg}</b> bo'yicha qaysi tumandan usta qidiryapsiz?\n\nO'zingizga yaqin tumanni tanlang:",
        'no_masters': "🛠 <b>{cat}</b> bo'yicha <b>{loc}</b>da hozircha faol ustalar topilmadi.\n\nBoshqa tuman yoki butun viloyat bo'yicha qidiring.",
        'total_found': "🛠 <b>{cat} ustalari ({loc}):</b>\n📊 Jami: <b>{count} ta usta</b> (Sahifa {page}/{total_pages})\n────────────────────────\n",
        'click_master_hint': "────────────────────────\n<i>Batafsil ko'rish, bog'lanish yoki baholash uchun usta tugmasini bosing:</i>",
        'specialty': "Mutaxassislik",
        'experience': "Ish tajribasi",
        'price': "Boshlang'ich narx",
        'rating': "Reyting",
        'phone': "Telefon",
        'contact': "Aloqa",
        'about': "Usta haqida",
        'region_district': "Hudud",
        'rate_master_prompt': "⭐️ <b>{name}</b> xizmatini baholang:\n\n1 dan 5 gacha yulduzchani tanlang:",
        'rating_success': "✅ <b>Rahmat! Bahongiz muvaffaqiyatli qabul qilindi.</b>\n\nUsta: <b>{name}</b>\nSiz bergan baho: <b>{score} ⭐</b>\nUstanining yangi reytingi: <b>{avg} ⭐</b> ({count} ta baho)",
        'msg_prompt': "📝 <b>{name}</b> ga xabaringizni yozing:\n\n<i>(Ushbu xabar usta profiliga va Telegramiga darhol yetkaziladi)</i>",
        'msg_sent': "✅ Xabaringiz <b>{name}</b> ga yetkazildi! Usta tez orada javob yozadi.",
        'master_already_reg': "✅ <b>Siz allaqachon usta sifatida ro'yxatdan o'tgansiz!</b>",
        'reg_step_name': "👷‍♂️ <b>Usta sifatida ro'yxatdan o'tish</b>\n\n1-qadam: <b>Ism va familiyangizni</b> kiriting (masalan: <i>Alisher Vohidov</i>):",
        'reg_step_phone': "Rahmat, <b>{name}</b>!\n\n2-qadam: <b>Telefon raqamingizni yuboring</b>:",
        'reg_step_cat': "3-qadam: <b>Mutaxassisligingiz (Kategoriya)ni tanlang:</b>",
        'reg_step_reg': "4-qadam: <b>Qaysi viloyat / shaharda xizmat ko'rsatasiz?</b>",
        'reg_step_dist': "4.5-qadam: <b>Qaysi tumanda faoliyat ko'rsatasiz?</b>",
        'reg_step_exp': "5-qadam: <b>Necha yillik ish tajribangiz bor?</b> (masalan: <code>3</code>):",
        'reg_step_price': "6-qadam: <b>Boshlang'ich xizmat narxingiz qancha (so'mda)?</b> (masalan: <code>50000</code>):",
        'reg_step_desc': "7-qadam: <b>Xizmatingiz haqida qisqacha ma'lumot yozing:</b>",
        'reg_success': "🎉 <b>TABRIKLAYMIZ! Siz rasmiy USTA sifatida ro'yxatdan o'tdingiz.</b>\n\nProfilingiz darhol saytda va botda aks etdi!",
        'btn_gps': "📍 Eng yaqin ustalar (GPS)",
        'btn_order': "🎙 Tezkor AI Buyurtma",
        'btn_map': "🗺 Jonli Xarita",
        'btn_send_loc': "📍 Geolokatsiyamni yuborish",
        'btn_portfolio': "📸 Ish namunalari (Portfolio)",
        'btn_add_portfolio': "➕ Ish namunasi qo'shish",
        'btn_toggle_status': "🔄 Holatni o'zgartirish (Band/Bo'sh)",
        'btn_update_loc': "📍 Lokatsiyamni saqlash (GPS)",
        'btn_view_map': "🗺 Xaritada ko'rish",
        'gps_prompt': "📍 <b>Eng yaqin ustalarni topish (GPS):</b>\n\nO'zingizga yaqin hududdagi ustalarni ko'rish uchun pastdagi <b>'📍 Geolokatsiyamni yuborish'</b> tugmasini bosing.\n\n⚠️ <b>DIQQAT:</b> Agar tugma bosilganda lokatsiya yuborilmasa:\n1. Telefoningiz sozlamalaridan <b>GPS (Geolokatsiya / Joylashuv)</b> xizmati yoqilganligini tekshiring.\n2. Yoki Telegram <b>📎 (skrepka)</b> orqali xaritadan joyingizni tanlang.\n3. Yoki pastdagi tumanlar ro'yxatidan tanlang:",
        'gps_found': "📍 <b>Sizga eng yaqin ustalar:</b>\n<i>(Masofa bo'yicha saralangan)</i>\n────────────────────────",
        'no_gps_masters': "📍 Hozircha yaqin atrofda faol ustalar topilmadi.",
        'order_select_cat': "⚡️ <b>Tezkor buyurtma berish:</b>\n\nQaysi soha bo'yicha usta kerak? Quyidagi kategoriyalardan birini tanlang:",
        'order_step_dist': "📍 <b>Qaysi tuman yoki manzilda joylashgansiz?</b>\n(Masalan: <i>Chilonzor tumani, 9-mavze</i> yoki yozib yuboring):",
        'order_step_desc': "📝 <b>Bajarilishi kerak bo'lgan ishni matn sifatida yozing yoki OVOZLI XABAR (Voice) yuboring:</b>\n\n<i>(Vaqtdan yutish uchun mikrofon tugmasini bosib ovozli xabar qoldirishingiz mumkin, u ustalarga darhol yetkaziladi)</i>",
        'order_step_phone': "📱 <b>Ustalar siz bilan bog'lanishi uchun telefon raqamingizni yuboring:</b>",
        'order_broadcast_success': "✅ <b>Tezkor buyurtmangiz muvaffaqiyatli qabul qilindi!</b>\n\nUshbu sohadagi <b>{count} nafar</b> ustaga darhol bildirishnoma yuborildi. Usta buyurtmani qabul qilishi bilanoq bot orqali sizga xabar beramiz.",
        'portfolio_empty': "Ushbu usta hali fotosuratlar yuklamagan.",
        'portfolio_title': "📸 <b>{name}</b> ning ish namunalari (Portfolio):\nJami: <b>{count} ta namuna</b>\n────────────────────────"
    },
    'ru': {
        'btn_categories': "🛠 Категории",
        'btn_top': "⭐ Лучшие мастера",
        'btn_reg_master': "👷‍♂️ Стать мастером",
        'btn_profile': "👤 Мой профиль",
        'btn_lang': "🌐 Сменить язык",
        'btn_help': "ℹ️ О сервисе",
        'btn_admin': "🔐 Админ панель",
        'btn_back': "⬅️ Главное меню",
        'btn_cancel': "❌ Отмена",
        'btn_all_regions': "🇺🇿 Все регионы",
        'btn_all_districts': "🏙 По всему городу/области",
        'btn_back_to_cats': "⬅️ К категориям",
        'btn_back_to_regions': "⬅️ Выбрать другой регион",
        'btn_prev': "⬅️ Назад",
        'btn_next': "Вперед ➡️",
        'btn_send_msg': "💬 Написать",
        'btn_rate': "⭐ Оценить (1-5)",
        'btn_back_to_list': "⬅️ Вернуться к списку",
        'btn_share_phone': "📱 Отправить мой номер",
        'btn_update_phone': "📱 Обновить номер телефона",
        'welcome': "Здравствуйте, <b>{name}</b>!\n\nДобро пожаловать в официальный бот платформы <b>'Ustasi'</b>.\nЗдесь вы можете найти лучших специалистов, написать им напрямую или <b>зарегистрироваться мастером</b>.\n\n⚡️ <b>САМЫЙ БЫСТРЫЙ СПОСОБ (AI ГОЛОСОВОЙ ЗАКАЗ):</b>\nНе нужно искать категории и районы! Просто <b>зажмите микрофон</b> и наговорите задачу (например: <i>«В Чиланзаре нужен сантехник»</i>) — наш AI мгновенно найдет нужных мастеров!",
        'input_placeholder': "🎙 Зажмите микрофон или напишите...",
        'select_cat': "🛠 <b>Выберите категорию услуг:</b>",
        'prompt_region': "📍 В каком регионе вы ищете мастера по <b>{cat}</b>?\n\nВыберите ваш регион:",
        'prompt_district': "📍 В каком районе <b>{reg}</b> вам нужен мастер?\n\nВыберите район:",
        'no_masters': "🛠 В <b>{loc}</b> по направлению <b>{cat}</b> пока нет активных мастеров.\n\nПопробуйте выбрать другой район.",
        'total_found': "🛠 <b>Мастера по {cat} ({loc}):</b>\n📊 Всего найдено: <b>{count} мастеров</b> (Стр. {page}/{total_pages})\n────────────────────────\n",
        'click_master_hint': "────────────────────────\n<i>Нажмите на кнопку мастера для просмотра подробностей, связи или оценки:</i>",
        'specialty': "Специальность",
        'experience': "Опыт работы",
        'price': "Начальная цена",
        'rating': "Рейтинг",
        'phone': "Телефон",
        'contact': "Связь",
        'about': "О мастере",
        'region_district': "Регион / Район",
        'rate_master_prompt': "⭐️ Оцените работу мастера <b>{name}</b>:\n\nВыберите оценку от 1 до 5 звезд:",
        'rating_success': "✅ <b>Спасибо! Ваша оценка принята.</b>\n\nМастер: <b>{name}</b>\nВаша оценка: <b>{score} ⭐</b>\nНовый рейтинг: <b>{avg} ⭐</b> ({count} оценок)",
        'msg_prompt': "📝 Напишите ваше сообщение для <b>{name}</b>:\n\n<i>(Сообщение будет мгновенно доставлено мастеру в профиль и Telegram)</i>",
        'msg_sent': "✅ Ваше сообщение отправлено <b>{name}</b>! Мастер скоро ответит.",
        'master_already_reg': "✅ <b>Вы уже зарегистрированы как мастер!</b>",
        'reg_step_name': "👷‍♂️ <b>Регистрация в качестве мастера</b>\n\nШаг 1: Введите ваши <b>имя и фамилию</b> (например: <i>Алишер Вохидов</i>):",
        'reg_step_phone': "Спасибо, <b>{name}</b>!\n\nШаг 2: <b>Отправьте ваш номер телефона</b>:",
        'reg_step_cat': "Шаг 3: <b>Выберите вашу категорию (специальность):</b>",
        'reg_step_reg': "Шаг 4: <b>В каком регионе/городе вы работаете?</b>",
        'reg_step_dist': "Шаг 4.5: <b>В каком районе вы работаете?</b>",
        'reg_step_exp': "Шаг 5: <b>Сколько лет у вас опыта работы?</b> (например: <code>3</code>):",
        'reg_step_price': "Шаг 6: <b>Ваша начальная цена услуги (в сумах)?</b> (например: <code>50000</code>):",
        'reg_step_desc': "Шаг 7: <b>Напишите кратко о ваших услугах:</b>",
        'reg_success': "🎉 <b>ПОЗДРАВЛЯЕМ! Вы успешно зарегистрированы как МАСТЕР.</b>\n\nВаш профиль уже доступен на сайте и в боте!",
        'btn_gps': "📍 Ближайшие мастера (GPS)",
        'btn_order': "🎙 Быстрый AI заказ",
        'btn_map': "🗺 Живая карта",
        'btn_send_loc': "📍 Отправить мою геолокацию",
        'btn_portfolio': "📸 Примеры работ (Портфолио)",
        'btn_add_portfolio': "➕ Добавить фото работы",
        'btn_toggle_status': "🔄 Сменить статус (Занят/Свободен)",
        'btn_update_loc': "📍 Сохранить локацию (GPS)",
        'btn_view_map': "🗺 На карте",
        'gps_prompt': "📍 <b>Поиск ближайших мастеров (GPS):</b>\n\nЧтобы увидеть мастеров рядом с вами, нажмите кнопку <b>'📍 Отправить мою геолокацию'</b> ниже.\n\n⚠️ <b>ВНИМАНИЕ:</b> Если после нажатия кнопки геопозиция не отправляется:\n1. Включите <b>GPS (Геолокацию / Местоположение)</b> в настройках телефона.\n2. Или отправьте точку через меню <b>📎 (скрепки)</b> на карте.\n3. Или выберите ваш район из списка ниже:",
        'gps_found': "📍 <b>Ближайшие к вам мастера:</b>\n<i>(Отсортировано по расстоянию)</i>\n────────────────────────",
        'no_gps_masters': "📍 Поблизости активных мастеров пока не найдено.",
        'order_select_cat': "⚡️ <b>Быстрый заказ мастера:</b>\n\nВыберите категорию необходимых услуг:",
        'order_step_dist': "📍 <b>В каком районе или по какому адресу вы находитесь?</b>\n(Например: <i>Чиланзарский район, 9-й квартал</i>):",
        'order_step_desc': "📝 <b>Опишите задачу текстом или отправьте ГОЛОСОВОЕ СООБЩЕНИЕ:</b>\n\n<i>(Для экономии времени зажмите микрофон и наговорите задачу, голосовое сообщение мгновенно передается мастерам)</i>",
        'order_step_phone': "📱 <b>Отправьте контактный номер телефона:</b>",
        'order_broadcast_success': "✅ <b>Ваш быстрый заказ успешно принят!</b>\n\nУведомление мгновенно отправлено <b>{count} мастерам</b> этой категории. Как только мастер примет заказ, бот сразу сообщит вам.",
        'portfolio_empty': "Мастер пока не добавил фотографии работ.",
        'portfolio_title': "📸 Примеры работ мастера <b>{name}</b>:\nВсего: <b>{count} фото</b>\n────────────────────────"
    },
    'en': {
        'btn_categories': "🛠 Categories",
        'btn_top': "⭐ Top Masters",
        'btn_reg_master': "👷‍♂️ Register as Master",
        'btn_profile': "👤 My Profile",
        'btn_lang': "🌐 Change Language",
        'btn_help': "ℹ️ About Service",
        'btn_admin': "🔐 Admin Panel",
        'btn_back': "⬅️ Main Menu",
        'btn_cancel': "❌ Cancel",
        'btn_all_regions': "🇺🇿 All Regions",
        'btn_all_districts': "🏙 Entire city/region",
        'btn_back_to_cats': "⬅️ Back to categories",
        'btn_back_to_regions': "⬅️ Select another region",
        'btn_prev': "⬅️ Previous",
        'btn_next': "Next ➡️",
        'btn_send_msg': "💬 Send Message",
        'btn_rate': "⭐ Rate (1-5)",
        'btn_back_to_list': "⬅️ Back to list",
        'btn_share_phone': "📱 Share phone number",
        'btn_update_phone': "📱 Update phone number",
        'welcome': "Hello, <b>{name}</b>!\n\nWelcome to the official <b>'Ustasi'</b> platform bot.\nHere you can find skilled professionals, contact them directly, or <b>register as a master</b>.\n\n⚡️ <b>FASTEST WAY (AI VOICE ORDER):</b>\nNo need to search through categories! Simply <b>hold the microphone</b> and speak your task (e.g. <i>«Need a plumber in Chilonzor»</i>) — our AI will instantly deliver your request to masters!",
        'input_placeholder': "🎙 Hold mic to speak or type...",
        'select_cat': "🛠 <b>Select a service category:</b>",
        'prompt_region': "📍 In which region are you looking for a <b>{cat}</b> master?\n\nSelect your region:",
        'prompt_district': "📍 In which district of <b>{reg}</b> do you need a master?\n\nSelect a district:",
        'no_masters': "🛠 Currently no active masters found for <b>{cat}</b> in <b>{loc}</b>.\n\nTry selecting another district or the entire city.",
        'total_found': "🛠 <b>{cat} masters ({loc}):</b>\n📊 Total found: <b>{count} masters</b> (Page {page}/{total_pages})\n────────────────────────\n",
        'click_master_hint': "────────────────────────\n<i>Click on a master button below to view details, contact or rate:</i>",
        'specialty': "Specialty",
        'experience': "Experience",
        'price': "Starting price",
        'rating': "Rating",
        'phone': "Phone",
        'contact': "Contact",
        'about': "About master",
        'region_district': "Location",
        'rate_master_prompt': "⭐️ Rate the master <b>{name}</b>:\n\nSelect a rating from 1 to 5 stars:",
        'rating_success': "✅ <b>Thank you! Your rating has been recorded.</b>\n\nMaster: <b>{name}</b>\nYour rating: <b>{score} ⭐</b>\nNew rating: <b>{avg} ⭐</b> ({count} ratings)",
        'msg_prompt': "📝 Write your message for <b>{name}</b>:\n\n<i>(This message will be instantly delivered to the master's profile and Telegram)</i>",
        'msg_sent': "✅ Your message has been sent to <b>{name}</b>! The master will reply shortly.",
        'master_already_reg': "✅ <b>You are already registered as a master!</b>",
        'reg_step_name': "👷‍♂️ <b>Register as a Master</b>\n\nStep 1: Enter your <b>first and last name</b> (e.g. <i>Alisher Vohidov</i>):",
        'reg_step_phone': "Thank you, <b>{name}</b>!\n\nStep 2: <b>Send your phone number</b>:",
        'reg_step_cat': "Step 3: <b>Select your category (specialty):</b>",
        'reg_step_reg': "Step 4: <b>In which region/city do you provide services?</b>",
        'reg_step_dist': "Step 4.5: <b>In which district do you work?</b>",
        'reg_step_exp': "Step 5: <b>How many years of experience do you have?</b> (e.g. <code>3</code>):",
        'reg_step_price': "Step 6: <b>What is your starting price (in UZS)?</b> (e.g. <code>50000</code>):",
        'reg_step_desc': "Step 7: <b>Write a brief description of your services:</b>",
        'reg_success': "🎉 <b>CONGRATULATIONS! You have successfully registered as a MASTER.</b>\n\nYour profile is now live on the website and bot!",
        'btn_gps': "📍 Nearest Masters (GPS)",
        'btn_order': "🎙 Quick AI Order",
        'btn_map': "🗺 Live Map",
        'btn_send_loc': "📍 Send my location",
        'btn_portfolio': "📸 Portfolio Works",
        'btn_add_portfolio': "➕ Add Portfolio Photo",
        'btn_toggle_status': "🔄 Change Status (Busy/Available)",
        'btn_update_loc': "📍 Save Location (GPS)",
        'btn_view_map': "🗺 View on Map",
        'gps_prompt': "📍 <b>Find Nearest Masters (GPS):</b>\n\nTo find masters close to you, click the <b>'📍 Send my location'</b> button below.\n\n⚠️ <b>NOTE:</b> If location is not sent after clicking the button:\n1. Enable <b>GPS (Location Services)</b> in your phone settings.\n2. Or send your location via the <b>📎 (paperclip)</b> menu from the map.\n3. Or pick your district from the list below:",
        'gps_found': "📍 <b>Nearest masters found:</b>\n<i>(Sorted by distance)</i>\n────────────────────────",
        'no_gps_masters': "📍 No active masters found nearby.",
        'order_select_cat': "⚡️ <b>Quick Master Request:</b>\n\nSelect a service category:",
        'order_step_dist': "📍 <b>What is your district or address?</b>\n(e.g.: <i>Chilonzor district, block 9</i>):",
        'order_step_desc': "📝 <b>Describe your task with text or send a VOICE MESSAGE:</b>\n\n<i>(To save time, hold the mic icon and speak, the voice note will be delivered directly to masters)</i>",
        'order_step_phone': "📱 <b>Send your contact phone number:</b>",
        'order_broadcast_success': "✅ <b>Your quick request has been submitted!</b>\n\nInstant notification sent to <b>{count} masters</b> in this category. We will alert you immediately when a master accepts.",
        'portfolio_empty': "This master has not uploaded portfolio photos yet.",
        'portfolio_title': "📸 Portfolio of <b>{name}</b>:\nTotal: <b>{count} items</b>\n────────────────────────"
    }
}


def load_json_set(file_path):
    if file_path.exists():
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except Exception:
            return set()
    return set()


def save_json_set(file_path, data_set):
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(list(data_set), f)
    except Exception as e:
        print(f"Faylga saqlashda xatolik: {e}")


def load_json_dict(file_path):
    if file_path.exists():
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_json_dict(file_path, data_dict):
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data_dict, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Faylga saqlashda xatolik: {e}")


master_tg_map = load_json_dict(MASTER_TG_FILE)
user_languages = load_json_dict(LANG_FILE)
admin_ids = load_json_set(ADMINS_FILE)
subscribers = load_json_set(SUBSCRIBERS_FILE)
active_tenders = load_json_dict(TENDERS_FILE)


def get_user_lang(chat_id):
    return user_languages.get(str(chat_id), 'uz')


def set_user_lang(chat_id, lang):
    user_languages[str(chat_id)] = lang
    try:
        with open(LANG_FILE, "w", encoding="utf-8") as f:
            json.dump(user_languages, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Tilni saqlashda xatolik: {e}")


def t(chat_id, key, **kwargs):
    lang = get_user_lang(chat_id)
    text = I18N.get(lang, I18N['uz']).get(key, I18N['uz'].get(key, key))
    if kwargs:
        return text.format(**kwargs)
    return text


def is_btn(text, key):
    return text in [I18N['uz'].get(key), I18N['ru'].get(key), I18N['en'].get(key)]


def save_master_tg_id(user_id, chat_id):
    master_tg_map[str(user_id)] = chat_id
    try:
        with open(MASTER_TG_FILE, "w", encoding="utf-8") as f:
            json.dump(master_tg_map, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Master TG ID saqlashda xatolik: {e}")


def register_subscriber(chat_id):
    if chat_id not in subscribers:
        subscribers.add(chat_id)
        save_json_set(SUBSCRIBERS_FILE, subscribers)


def is_admin(user_id):
    return user_id in admin_ids


def get_or_create_tg_user(from_user, phone=None):
    if phone:
        clean_phone = normalize_phone_number(phone)
        user = User.objects.filter(phone=clean_phone).first()
        if user:
            return user

    tg_email = f"tg_{from_user.id}@ustasi.uz"
    user = User.objects.filter(email=tg_email).first()
    if not user:
        user = User.objects.create_user(
            email=tg_email,
            phone=normalize_phone_number(phone) if phone else None,
            first_name=from_user.first_name or "Mijoz",
            last_name=from_user.last_name or "",
            role='client'
        )
    return user


def get_main_keyboard(user_id):
    """Foydalanuvchi tanlagan tildagi asosiy reply klaviatura"""
    placeholder = t(user_id, 'input_placeholder')
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2, input_field_placeholder=placeholder)
    btn_categories = types.KeyboardButton(t(user_id, 'btn_categories'))
    btn_gps = types.KeyboardButton(t(user_id, 'btn_gps'))
    btn_order = types.KeyboardButton(t(user_id, 'btn_order'))
    btn_map = types.KeyboardButton(t(user_id, 'btn_map'))
    btn_top = types.KeyboardButton(t(user_id, 'btn_top'))
    btn_profile = types.KeyboardButton(t(user_id, 'btn_profile'))
    btn_reg_master = types.KeyboardButton(t(user_id, 'btn_reg_master'))
    btn_lang = types.KeyboardButton(t(user_id, 'btn_lang'))
    btn_help = types.KeyboardButton(t(user_id, 'btn_help'))
    markup.add(btn_order)
    markup.add(btn_categories, btn_gps)
    markup.add(btn_map, btn_top)
    markup.add(btn_profile, btn_reg_master)
    markup.add(btn_lang, btn_help)

    if is_admin(user_id):
        btn_admin = types.KeyboardButton(t(user_id, 'btn_admin'))
        markup.add(btn_admin)

    return markup


# ==========================================
# 🌐 TILNI TANLASH VA O'ZGARTIRISH
# ==========================================
def send_language_selection(chat_id, is_edit=False, message_id=None):
    text = (
        "🇺🇿 <b>Iltimos, muloqot tilini tanlang:</b>\n"
        "🇷🇺 <b>Пожалуйста, выберите язык общения:</b>\n"
        "🇬🇧 <b>Please select your language:</b>"
    )
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("🇺🇿 O'zbekcha", callback_data="setlang_uz"),
        types.InlineKeyboardButton("🇷🇺 Русский", callback_data="setlang_ru"),
        types.InlineKeyboardButton("🇬🇧 English", callback_data="setlang_en")
    )
    if is_edit and message_id:
        try:
            bot.edit_message_text(text, chat_id=chat_id, message_id=message_id, parse_mode="HTML", reply_markup=markup)
            return
        except Exception:
            pass
    bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith('setlang_'))
def handle_set_language_callback(call):
    lang = call.data.split('_')[1]
    set_user_lang(call.message.chat.id, lang)

    lang_names = {'uz': "O'zbek tili", 'ru': "Русский язык", 'en': "English"}
    bot.answer_callback_query(call.id, f"{lang_names.get(lang)} tanlandi!")

    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass

    send_welcome_message(call.message.chat.id, call.from_user.first_name)


def send_welcome_message(chat_id, first_name=""):
    welcome_text = t(chat_id, 'welcome', name=first_name or "Foydalanuvchi")
    bot.send_message(
        chat_id,
        welcome_text,
        parse_mode="HTML",
        reply_markup=get_main_keyboard(chat_id)
    )


@bot.message_handler(commands=['language', 'lang'])
@bot.message_handler(func=lambda msg: is_btn(msg.text, 'btn_lang'))
def handle_change_language(message):
    send_language_selection(message.chat.id)


# ==========================================
# 🔐 ADMIN DASHBOARD
# ==========================================
def get_master_admin_card(m):
    status_icon = "🟢 Faol" if m.status == "active" else "🔴 Nofaol"
    tg_status = "⚡️ TG Ulangan" if str(m.user.id) in master_tg_map else "🌐 Faqat sayt"
    
    info = (
        f"👷‍♂️ <b>{m.full_name}</b> (ID: {m.id})\n"
        f"🔧 Mutaxassislik: {m.category.name}\n"
        f"📍 Hudud: {m.region}\n"
        f"📞 Tel: <code>{m.phone or 'Mavjud emas'}</code>\n"
        f"💰 Boshlang'ich narx: <b>{m.price:,} so'm</b>\n"
        f"⏳ Ish tajribasi: <b>{m.experience} yil</b>\n"
        f"⭐️ Reyting: {m.average_rating} ({m.ratings_count} ta) | Holat: <b>{status_icon}</b>\n"
        f"📡 {tg_status}"
    )

    markup = types.InlineKeyboardMarkup(row_width=2)
    toggle_text = "🔴 Nofaol qilish" if m.status == 'active' else "🟢 Faollashtirish"
    btn_toggle = types.InlineKeyboardButton(toggle_text, callback_data=f"adm_toggle_m_{m.id}")
    btn_delete = types.InlineKeyboardButton("🗑 O'chirish", callback_data=f"adm_del_m_confirm_{m.id}")
    btn_edit = types.InlineKeyboardButton("✏️ Tahrirlash", callback_data=f"adm_edit_m_menu_{m.id}")
    markup.add(btn_toggle, btn_delete)
    markup.add(btn_edit)
    return info, markup


def get_admin_dashboard_markup():
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_stats = types.InlineKeyboardButton("📊 Keng Statistika", callback_data="admin_stats")
    btn_broadcast = types.InlineKeyboardButton("📢 Xabar tarqatish", callback_data="admin_broadcast")
    btn_tenders = types.InlineKeyboardButton("⚡️ Tezkor buyurtmalar", callback_data="admin_tenders_manage")
    btn_masters = types.InlineKeyboardButton("👷‍♂️ Ustalarni boshqarish", callback_data="admin_masters_manage")
    btn_users = types.InlineKeyboardButton("👥 Foydalanuvchilar", callback_data="admin_users_manage")
    btn_cats = types.InlineKeyboardButton("🛠 Kategoriyalar", callback_data="admin_cats_manage")
    btn_msgs = types.InlineKeyboardButton("💬 Oxirgi xabarlar", callback_data="admin_recent_messages")
    btn_search = types.InlineKeyboardButton("🔍 Qidirish (Tel/Ism)", callback_data="admin_search_prep")

    markup.add(btn_stats, btn_broadcast)
    markup.add(btn_tenders)
    markup.add(btn_masters, btn_users)
    markup.add(btn_cats, btn_msgs)
    markup.add(btn_search)
    return markup


@bot.message_handler(commands=['admin_login'])
def handle_admin_login(message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        bot.send_message(
            message.chat.id,
            "Parolni kiriting. Masalan: <code>/admin_login [parol]</code>",
            parse_mode="HTML"
        )
        return

    password = args[1].strip()
    if password == ADMIN_SECRET:
        admin_ids.add(message.chat.id)
        save_json_set(ADMINS_FILE, admin_ids)
        bot.send_message(
            message.chat.id,
            "🎉 <b>Tabriklaymiz! Siz muvaffaqiyatli Admin bo'ldingiz.</b>\n\n"
            "Endi sizda <b>🔐 Admin Panel</b> menyusi faollashdi.",
            parse_mode="HTML",
            reply_markup=get_main_keyboard(message.chat.id)
        )
        send_admin_panel(message.chat.id)
    else:
        bot.send_message(message.chat.id, "❌ Noto'g'ri parol! Qayta urinib ko'ring.")


@bot.message_handler(commands=['admin'])
@bot.message_handler(func=lambda msg: is_btn(msg.text, 'btn_admin'))
def handle_admin_menu(message):
    register_subscriber(message.chat.id)
    if not is_admin(message.chat.id):
        bot.send_message(
            message.chat.id,
            f"🔒 <b>Ushbu bo'lim faqat administratorlar uchun.</b>\n\n"
            f"Sizning Telegram ID: <code>{message.chat.id}</code>\n"
            "Admin huquqini faollashtirish uchun parolingizni kiriting:\n"
            "👉 <code>/admin_login [parolingiz]</code>",
            parse_mode="HTML"
        )
        return

    send_admin_panel(message.chat.id)


def send_admin_panel(chat_id):
    bot.send_message(
        chat_id,
        "<b>🔐 Ustasi Platformasi — Admin Boshqaruv Markazi</b>\n\n"
        "Platformani to'liq boshqarish uchun quyidagi bo'limlardan birini tanlang:",
        parse_mode="HTML",
        reply_markup=get_admin_dashboard_markup()
    )


# --- ADMIN CALLBACK QUERY HANDLERS ---
@bot.callback_query_handler(func=lambda call: call.data == "admin_stats")
def callback_admin_stats(call):
    if not is_admin(call.message.chat.id):
        return

    total_users = User.objects.count()
    clients_count = User.objects.filter(role='client').count()
    masters_count = Master.objects.count()
    active_masters = Master.objects.filter(status='active').count()
    categories_count = Category.objects.count()
    messages_count = Message.objects.count()
    ratings_count = Rating.objects.count()
    bot_subs_count = len(subscribers)
    tg_connected_masters = len(master_tg_map)

    stats_text = (
        "📊 <b>PLATFORMA VA BOTNING KENG STATISTIKASI:</b>\n\n"
        f"🤖 Botdagi jami obunachilar: <b>{bot_subs_count} ta</b>\n"
        f"👥 Baza foydalanuvchilari: <b>{total_users} ta</b>\n"
        f"   • Mijozlar: <b>{clients_count} ta</b>\n"
        f"   • Ustalar (Jami): <b>{masters_count} ta</b>\n"
        f"   • Faol ustalar: <b>{active_masters} ta</b>\n"
        f"   • Telegrami ulangan ustalar: <b>{tg_connected_masters} ta</b>\n\n"
        f"🛠 Kategoriyalar: <b>{categories_count} ta</b>\n"
        f"⭐ Berilgan baholar: <b>{ratings_count} ta</b>\n"
        f"💬 Jami xabarlar (Chat): <b>{messages_count} ta</b>\n"
    )
    bot.answer_callback_query(call.id)
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("⬅️ Admin menyuga qaytish", callback_data="admin_back_to_menu"))
    bot.send_message(call.message.chat.id, stats_text, parse_mode="HTML", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data == "admin_tenders_manage")
def callback_admin_tenders_manage(call):
    if not is_admin(call.message.chat.id):
        bot.answer_callback_query(call.id, "Ruxsat yo'q.")
        return

    bot.answer_callback_query(call.id)
    total_tenders = len(active_tenders)
    accepted_tenders = sum(1 for o in active_tenders.values() if o.get('accepted_by') is not None)
    pending_tenders = total_tenders - accepted_tenders

    text = (
        f"⚡️ <b>TEZKOR BUYURTMALAR MONITORINGI:</b>\n\n"
        f"📊 <b>Statistika:</b>\n"
        f"• Jami buyurtmalar: <b>{total_tenders} ta</b>\n"
        f"• Qabul qilingan: <b>{accepted_tenders} ta</b>\n"
        f"• Kutayotganlar: <b>{pending_tenders} ta</b>\n"
        f"────────────────────────\n"
    )

    if not active_tenders:
        text += "<i>Hozircha faol buyurtmalar yo'q. Yangi tezkor buyurtma tushganda, sizga avtomatik tarzda Telegramingizga to'liq tafsilotlari va ovozli xabar nusxasi keladi.</i>"
    else:
        text += "<b>Oxirgi buyurtmalar ro'yxati:</b>\n\n"
        for ord_id, o in list(active_tenders.items())[-5:]:
            st_icon = "✅ Qabul qilindi" if o.get('accepted_by') else "⏳ Kutmoqda"
            desc_short = o['desc'][:35] + "..." if len(o['desc']) > 35 else o['desc']
            text += (
                f"• <b>{o['cat_name']}</b> ({o['district']}): {st_icon}\n"
                f"  Vazifa: <i>{desc_short}</i>\n"
                f"  Aloqa: <code>{o['phone']}</code>\n\n"
            )

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("⬅️ Admin menyuga qaytish", callback_data="admin_back_to_menu"))
    bot.send_message(call.message.chat.id, text, parse_mode="HTML", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data == "admin_masters_manage")
def callback_admin_masters_manage(call):
    if not is_admin(call.message.chat.id):
        return

    masters = Master.objects.select_related('user', 'category').all()[:15]
    bot.answer_callback_query(call.id)

    if not masters.exists():
        bot.send_message(call.message.chat.id, "Bazada ustalar mavjud emas.")
        return

    bot.send_message(
        call.message.chat.id,
        "👷‍♂️ <b>Ustalarni boshqarish bo'limi:</b>\n"
        "Har bir usta holatini (Faol/Nofaol) o'zgartirishingiz, tahrirlashingiz yoki tizimdan o'chirishingiz mumkin:",
        parse_mode="HTML"
    )

    for m in masters:
        info, markup = get_master_admin_card(m)
        bot.send_message(call.message.chat.id, info, parse_mode="HTML", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith('adm_restore_m_card_'))
def handle_admin_restore_master_card(call):
    master_id = int(call.data.split('_')[4])
    master = Master.objects.filter(id=master_id).first()
    bot.answer_callback_query(call.id)
    if master:
        info, markup = get_master_admin_card(master)
        try:
            bot.edit_message_text(
                info,
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                parse_mode="HTML",
                reply_markup=markup
            )
        except Exception:
            pass


@bot.callback_query_handler(func=lambda call: call.data.startswith('adm_toggle_m_'))
def handle_admin_toggle_master(call):
    if not is_admin(call.message.chat.id):
        return

    master_id = int(call.data.split('_')[3])
    master = Master.objects.filter(id=master_id).first()
    if not master:
        bot.answer_callback_query(call.id, "Usta topilmadi.")
        return

    master.status = 'inactive' if master.status == 'active' else 'active'
    master.save()
    status_str = "faol qilindi 🟢" if master.status == 'active' else "nofaol qilindi 🔴"
    bot.answer_callback_query(call.id, f"Usta {status_str}!", show_alert=True)

    info, markup = get_master_admin_card(master)
    try:
        bot.edit_message_text(
            info,
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            parse_mode="HTML",
            reply_markup=markup
        )
    except Exception:
        pass


@bot.callback_query_handler(func=lambda call: call.data.startswith('adm_edit_m_menu_'))
def handle_admin_edit_master_menu(call):
    if not is_admin(call.message.chat.id):
        return

    master_id = int(call.data.split('_')[4])
    master = Master.objects.filter(id=master_id).first()
    if not master:
        bot.answer_callback_query(call.id, "Usta topilmadi.")
        return

    bot.answer_callback_query(call.id)
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_price = types.InlineKeyboardButton("💰 Narxni o'zgartirish", callback_data=f"adm_edfield_{master.id}_price")
    btn_phone = types.InlineKeyboardButton("📞 Telefonni o'zgartirish", callback_data=f"adm_edfield_{master.id}_phone")
    btn_name = types.InlineKeyboardButton("👤 Ismni o'zgartirish", callback_data=f"adm_edfield_{master.id}_name")
    btn_exp = types.InlineKeyboardButton("⏳ Tajribani o'zgartirish", callback_data=f"adm_edfield_{master.id}_exp")
    btn_desc = types.InlineKeyboardButton("📝 Tavsifni o'zgartirish", callback_data=f"adm_edfield_{master.id}_desc")
    btn_back = types.InlineKeyboardButton("⬅️ Orqaga", callback_data=f"adm_restore_m_card_{master.id}")

    markup.add(btn_price, btn_phone)
    markup.add(btn_name, btn_exp)
    markup.add(btn_desc)
    markup.add(btn_back)

    edit_menu_text = (
        f"✏️ <b>{master.full_name}</b> ma'lumotlarini tahrirlash:\n\n"
        f"• Hozirgi narxi: <b>{master.price:,} so'm</b>\n"
        f"• Hozirgi telefoni: <code>{master.phone}</code>\n"
        f"• Hozirgi tajribasi: <b>{master.experience} yil</b>\n\n"
        "Qaysi ma'lumotni o'zgartirmoqchisiz? Quyidagi tugmalardan birini tanlang:"
    )

    try:
        bot.edit_message_text(
            edit_menu_text,
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            parse_mode="HTML",
            reply_markup=markup
        )
    except Exception:
        bot.send_message(call.message.chat.id, edit_menu_text, parse_mode="HTML", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith('adm_edfield_'))
def handle_admin_edit_field_select(call):
    if not is_admin(call.message.chat.id):
        return

    parts = call.data.split('_')
    master_id = int(parts[2])
    field = parts[3]

    master = Master.objects.filter(id=master_id).first()
    if not master:
        bot.answer_callback_query(call.id, "Usta topilmadi.")
        return

    bot.answer_callback_query(call.id)
    user_states[call.message.chat.id] = {
        'action': 'admin_saving_master_edit',
        'master_id': master_id,
        'field': field,
        'msg_id': call.message.message_id
    }

    field_names = {
        'price': "yangi boshlang'ich narxni (so'mda, masalan: 60000)",
        'phone': "yangi telefon raqamini (masalan: +998901234567)",
        'name': "yangi ism va familiyani (masalan: Rustam Karimov)",
        'exp': "yangi ish tajribasini (yillarda, masalan: 5)",
        'desc': "yangi xizmat tavsifini"
    }

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("⬅️ Bekor qilish", callback_data=f"adm_restore_m_card_{master.id}"))

    prompt_text = (
        f"📝 <b>{master.full_name}</b> uchun {field_names.get(field, 'yangi qiymatni')} kiriting:\n\n"
        "<i>Pastdagi yozish joyiga yangi qiymatni yozib yuboring (yoki bekor qilishni bosing).</i>"
    )

    try:
        bot.edit_message_text(
            prompt_text,
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            parse_mode="HTML",
            reply_markup=markup
        )
    except Exception:
        bot.send_message(call.message.chat.id, prompt_text, parse_mode="HTML", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith('adm_del_m_confirm_'))
def handle_admin_del_master_confirm(call):
    if not is_admin(call.message.chat.id):
        return

    master_id = int(call.data.split('_')[4])
    master = Master.objects.filter(id=master_id).first()
    if not master:
        bot.answer_callback_query(call.id, "Usta topilmadi.")
        return

    bot.answer_callback_query(call.id)
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_yes = types.InlineKeyboardButton("⚠️ Ha, O'chirilsin", callback_data=f"adm_del_m_yes_{master.id}")
    btn_no = types.InlineKeyboardButton("❌ Bekor qilish", callback_data=f"adm_restore_m_card_{master.id}")
    markup.add(btn_yes, btn_no)

    confirm_text = f"❓ Rostdan ham <b>{master.full_name}</b> (Mutaxassislik: {master.category.name}) ni <b>platformadan BUTUNLAY O'CHIRMOQCHIMISIZ</b>?"

    try:
        bot.edit_message_text(
            confirm_text,
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            parse_mode="HTML",
            reply_markup=markup
        )
    except Exception:
        bot.send_message(call.message.chat.id, confirm_text, parse_mode="HTML", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith('adm_del_m_yes_'))
def handle_admin_del_master_yes(call):
    if not is_admin(call.message.chat.id):
        return

    master_id = int(call.data.split('_')[4])
    master = Master.objects.filter(id=master_id).first()
    if not master:
        bot.answer_callback_query(call.id, "Usta topilmadi.")
        return

    name = master.full_name
    user = master.user
    master.delete()
    user.delete()

    bot.answer_callback_query(call.id, "Usta o'chirildi!", show_alert=True)
    try:
        bot.edit_message_text(
            f"✅ Usta <b>{name}</b> platformadan va ma'lumotlar bazasidan butunlay o'chirildi.",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            parse_mode="HTML"
        )
    except Exception:
        pass


@bot.callback_query_handler(func=lambda call: call.data == "admin_users_manage")
def callback_admin_users_manage(call):
    if not is_admin(call.message.chat.id):
        return

    users = User.objects.filter(role='client').order_by('-created_at')[:10]
    bot.answer_callback_query(call.id)

    if not users.exists():
        bot.send_message(call.message.chat.id, "Hozircha mijozlar mavjud emas.")
        return

    bot.send_message(call.message.chat.id, "👥 <b>Oxirgi ro'yxatdan o'tgan mijozlar:</b>", parse_mode="HTML")

    for u in users:
        phone_txt = u.phone or u.email or "Bog'lanmagan"
        info = (
            f"👤 <b>{u.full_name}</b> (ID: {u.id})\n"
            f"📞 Aloqa: <code>{phone_txt}</code>\n"
            f"📅 Ro'yxatdan o'tgan: {u.created_at.strftime('%d.%m.%Y %H:%M')}"
        )

        markup = types.InlineKeyboardMarkup()
        btn_del = types.InlineKeyboardButton("🗑 O'chirish", callback_data=f"adm_del_u_confirm_{u.id}")
        markup.add(btn_del)

        bot.send_message(call.message.chat.id, info, parse_mode="HTML", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith('adm_del_u_confirm_'))
def handle_admin_del_user_confirm(call):
    if not is_admin(call.message.chat.id):
        return

    user_id = int(call.data.split('_')[4])
    user = User.objects.filter(id=user_id).first()
    if not user:
        bot.answer_callback_query(call.id, "Foydalanuvchi topilmadi.")
        return

    bot.answer_callback_query(call.id)
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_yes = types.InlineKeyboardButton("⚠️ Ha, O'chirilsin", callback_data=f"adm_del_u_yes_{user.id}")
    btn_no = types.InlineKeyboardButton("❌ Bekor qilish", callback_data="admin_cancel_del")
    markup.add(btn_yes, btn_no)

    bot.send_message(
        call.message.chat.id,
        f"❓ Foydalanuvchi <b>{user.full_name}</b> ni platformadan o'chirmoqchimisiz?",
        parse_mode="HTML",
        reply_markup=markup
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith('adm_del_u_yes_'))
def handle_admin_del_user_yes(call):
    if not is_admin(call.message.chat.id):
        return

    user_id = int(call.data.split('_')[4])
    user = User.objects.filter(id=user_id).first()
    if not user:
        bot.answer_callback_query(call.id, "Foydalanuvchi topilmadi.")
        return

    name = user.full_name
    user.delete()
    bot.answer_callback_query(call.id, "Foydalanuvchi o'chirildi!", show_alert=True)
    try:
        bot.edit_message_text(
            f"✅ Foydalanuvchi <b>{name}</b> platformadan o'chirildi.",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            parse_mode="HTML"
        )
    except Exception:
        pass


@bot.callback_query_handler(func=lambda call: call.data == "admin_cancel_del")
def handle_admin_cancel_del(call):
    bot.answer_callback_query(call.id, "O'chirish bekor qilindi.")
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass


@bot.callback_query_handler(func=lambda call: call.data == "admin_cats_manage")
def callback_admin_cats_manage(call):
    if not is_admin(call.message.chat.id):
        return

    categories = Category.objects.all().order_by('order', 'name')
    bot.answer_callback_query(call.id)

    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_add = types.InlineKeyboardButton("➕ Yangi Kategoriya qo'shish", callback_data="admin_add_category")
    markup.add(btn_add)

    bot.send_message(
        call.message.chat.id,
        "🛠 <b>Kategoriyalarni boshqarish:</b>\n"
        "Mavjud kategoriyalar ro'yxati:",
        parse_mode="HTML",
        reply_markup=markup
    )

    for cat in categories:
        status_txt = "🟢 Faol" if cat.is_active else "🔴 Nofaol"
        masters_in_cat = Master.objects.filter(category=cat).count()
        info = f"🔧 <b>{cat.name}</b> ({status_txt})\n   • Ustalar soni: {masters_in_cat} ta"

        cat_markup = types.InlineKeyboardMarkup()
        btn_del_cat = types.InlineKeyboardButton(f"🗑 {cat.name} ni o'chirish", callback_data=f"adm_del_cat_{cat.id}")
        cat_markup.add(btn_del_cat)

        bot.send_message(call.message.chat.id, info, parse_mode="HTML", reply_markup=cat_markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith('adm_del_cat_'))
def handle_admin_del_category(call):
    if not is_admin(call.message.chat.id):
        return

    cat_id = int(call.data.split('_')[3])
    cat = Category.objects.filter(id=cat_id).first()
    if not cat:
        bot.answer_callback_query(call.id, "Kategoriya topilmadi.")
        return

    name = cat.name
    cat.delete()
    bot.answer_callback_query(call.id, "Kategoriya o'chirildi!", show_alert=True)
    try:
        bot.edit_message_text(
            f"✅ <b>{name}</b> kategoriyasi muvaffaqiyatli o'chirildi.",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            parse_mode="HTML"
        )
    except Exception:
        pass


@bot.callback_query_handler(func=lambda call: call.data == "admin_recent_messages")
def callback_admin_recent_messages(call):
    if not is_admin(call.message.chat.id):
        return

    messages = Message.objects.select_related('sender', 'receiver').order_by('-created_at')[:8]
    bot.answer_callback_query(call.id)

    if not messages.exists():
        bot.send_message(call.message.chat.id, "Hozircha yozilgan xabarlar yo'q.")
        return

    msg_text = "💬 <b>Oxirgi yozilgan chat xabarlari (Jonli monitoring):</b>\n\n"
    for m in messages:
        dt = m.created_at.strftime("%d.%m %H:%M")
        msg_text += (
            f"🕒 <i>{dt}</i>\n"
            f"👤 <b>{m.sender.full_name}</b> ➡️ 👷‍♂️ <b>{m.receiver.full_name}</b>:\n"
            f"💬 <i>\"{m.text[:80]}\"</i>\n"
            "--------------------------\n"
        )

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("⬅️ Admin menyuga qaytish", callback_data="admin_back_to_menu"))
    bot.send_message(call.message.chat.id, msg_text, parse_mode="HTML", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data == "admin_search_prep")
def callback_admin_search_prep(call):
    if not is_admin(call.message.chat.id):
        return

    user_states[call.message.chat.id] = {'action': 'admin_waiting_search_query'}
    bot.answer_callback_query(call.id)
    bot.send_message(
        call.message.chat.id,
        "🔍 <b>Foydalanuvchi yoki Ustani qidirish:</b>\n\n"
        "Qidirilayotgan shaxsning <b>ism-familiyasi</b> yoki <b>telefon raqamini</b> yozing:\n"
        "(Masalan: <i>Alisher</i> yoki <i>+998901234567</i>)\n\n"
        "Bekor qilish uchun: /cancel",
        parse_mode="HTML"
    )


@bot.callback_query_handler(func=lambda call: call.data == "admin_broadcast")
def callback_admin_broadcast(call):
    if not is_admin(call.message.chat.id):
        return

    user_states[call.message.chat.id] = {'action': 'waiting_for_broadcast'}
    bot.answer_callback_query(call.id)
    bot.send_message(
        call.message.chat.id,
        f"📢 <b>Xabar tarqatish (Rassilka) bo'limi:</b>\n\n"
        f"Hozir botda <b>{len(subscribers)} ta</b> faol foydalanuvchi bor.\n"
        "Barcha foydalanuvchilarga yubormoqchi bo'lgan xabaringizni yozing:\n"
        "(Bekor qilish uchun /cancel deb yozing)",
        parse_mode="HTML"
    )


@bot.callback_query_handler(func=lambda call: call.data == "admin_add_category")
def callback_admin_add_category(call):
    if not is_admin(call.message.chat.id):
        return

    user_states[call.message.chat.id] = {'action': 'waiting_for_category_name'}
    bot.answer_callback_query(call.id)
    bot.send_message(
        call.message.chat.id,
        "➕ <b>Yangi kategoriya qo'shish:</b>\n\n"
        "Yangi kategoriya nomini yozing (Masalan: <code>Mebel ustasi</code>):\n"
        "(Bekor qilish uchun /cancel deb yozing)",
        parse_mode="HTML"
    )


@bot.callback_query_handler(func=lambda call: call.data == "admin_back_to_menu")
def callback_admin_back_to_menu(call):
    bot.answer_callback_query(call.id)
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass
    send_admin_panel(call.message.chat.id)


# ==========================================
# 🛠 KATEGORIYALAR, HUDUDLAR VA KATALOG
# ==========================================
def get_categories_markup():
    categories = Category.objects.filter(is_active=True).order_by('order', 'name')
    markup = types.InlineKeyboardMarkup(row_width=2)
    buttons = []
    for cat in categories:
        buttons.append(types.InlineKeyboardButton(text=f"🔧 {cat.name}", callback_data=f"cat_{cat.id}"))
    markup.add(*buttons)
    return markup


def get_category_regions_markup(cat_id, chat_id):
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_all = types.InlineKeyboardButton(t(chat_id, 'btn_all_regions'), callback_data=f"cd_{cat_id}_all_all")
    markup.add(btn_all)

    reg_buttons = []
    for idx, reg in enumerate(UZBEKISTAN_REGIONS):
        short_name = reg.replace(" viloyati", "").replace(" Respublikasi", "")
        reg_buttons.append(types.InlineKeyboardButton(f"📍 {short_name}", callback_data=f"cr_{cat_id}_{idx}"))
    markup.add(*reg_buttons)

    btn_back = types.InlineKeyboardButton(t(chat_id, 'btn_back_to_cats'), callback_data="back_to_cats")
    markup.add(btn_back)
    return markup


def get_category_districts_markup(cat_id, reg_idx, chat_id):
    reg_name = UZBEKISTAN_REGIONS[reg_idx]
    districts = REGION_DISTRICTS.get(reg_name, [])

    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_all_dist = types.InlineKeyboardButton(f"🏙 {t(chat_id, 'btn_all_districts')}", callback_data=f"cd_{cat_id}_{reg_idx}_all")
    markup.add(btn_all_dist)

    dist_buttons = []
    for d_idx, d_name in enumerate(districts):
        short_d = d_name.replace(" tumani", "").replace(" shahri", "")
        dist_buttons.append(types.InlineKeyboardButton(f"📍 {short_d}", callback_data=f"cd_{cat_id}_{reg_idx}_{d_idx}"))
    markup.add(*dist_buttons)

    btn_back = types.InlineKeyboardButton(t(chat_id, 'btn_back_to_regions'), callback_data=f"cat_{cat_id}")
    markup.add(btn_back)
    return markup


def build_masters_catalog(cat_id, reg_code, dist_code, chat_id, page=1):
    PAGE_SIZE = 4
    cat = Category.objects.filter(id=cat_id).first()
    if not cat:
        return "Kategoriya topilmadi.", None

    qs = Master.objects.filter(category=cat, status='active').select_related('user', 'category')

    region_title = t(chat_id, 'btn_all_regions')
    district_title = ""

    if reg_code != 'all':
        try:
            reg_idx = int(reg_code)
            region_name = UZBEKISTAN_REGIONS[reg_idx]
            qs = qs.filter(region__icontains=region_name.split()[0])
            region_title = region_name

            if dist_code != 'all':
                dist_idx = int(dist_code)
                dist_name = REGION_DISTRICTS[region_name][dist_idx]
                clean_dist = dist_name.replace(" tumani", "").replace(" shahri", "")
                qs = qs.filter(Q(district__icontains=clean_dist) | Q(address__icontains=clean_dist))
                district_title = f", {dist_name}"
        except Exception:
            pass

    qs = qs.order_by('-average_rating', '-ratings_count', '-created_at')
    total_count = qs.count()

    loc_header = f"{region_title}{district_title}"

    if total_count == 0:
        text = t(chat_id, 'no_masters', cat=cat.name, loc=loc_header)
        markup = types.InlineKeyboardMarkup()
        if reg_code != 'all':
            markup.add(types.InlineKeyboardButton(f"🏙 {region_title}", callback_data=f"cd_{cat_id}_{reg_code}_all"))
            markup.add(types.InlineKeyboardButton(t(chat_id, 'btn_back_to_regions'), callback_data=f"cr_{cat_id}_{reg_code}"))
        markup.add(types.InlineKeyboardButton(t(chat_id, 'btn_back_to_cats'), callback_data="back_to_cats"))
        return text, markup

    total_pages = (total_count + PAGE_SIZE - 1) // PAGE_SIZE
    page = max(1, min(page, total_pages))
    offset = (page - 1) * PAGE_SIZE
    current_masters = list(qs[offset:offset + PAGE_SIZE])

    text = t(chat_id, 'total_found', cat=cat.name, loc=loc_header, count=total_count, page=page, total_pages=total_pages)

    number_emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣"]
    select_buttons = []

    for i, m in enumerate(current_masters):
        num_icon = number_emojis[i]
        rating_star = f"⭐️ {m.average_rating}" if m.average_rating > 0 else "🆕"
        loc = m.district if m.district and m.district != 'Markaz' else m.region

        status_icon = "🟢" if m.status == "active" else "🔴"
        text += (
            f"{num_icon} <b>{m.full_name}</b> {status_icon}\n"
            f"   {rating_star} ({m.ratings_count}) | 📍 {loc}\n"
            f"   💰 {t(chat_id, 'price')}: <b>{m.price:,}</b> | ⏳ {m.experience} y.\n\n"
        )
        first_name_short = m.full_name.split()[0]
        select_buttons.append(types.InlineKeyboardButton(f"👷‍♂️ {i+1}. {first_name_short}", callback_data=f"vm_{m.id}_{cat_id}_{reg_code}_{dist_code}_{page}"))

    text += t(chat_id, 'click_master_hint')

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(*select_buttons)

    nav_buttons = []
    if page > 1:
        nav_buttons.append(types.InlineKeyboardButton(t(chat_id, 'btn_prev'), callback_data=f"cp_{cat_id}_{reg_code}_{dist_code}_{page-1}"))
    nav_buttons.append(types.InlineKeyboardButton(f"📄 {page} / {total_pages}", callback_data="noop"))
    if page < total_pages:
        nav_buttons.append(types.InlineKeyboardButton(t(chat_id, 'btn_next'), callback_data=f"cp_{cat_id}_{reg_code}_{dist_code}_{page+1}"))
    markup.row(*nav_buttons)

    if reg_code != 'all':
        btn_change_dist = types.InlineKeyboardButton(t(chat_id, 'btn_back_to_regions'), callback_data=f"cr_{cat_id}_{reg_code}")
        markup.row(btn_change_dist)
    btn_all_cats = types.InlineKeyboardButton(t(chat_id, 'btn_back_to_cats'), callback_data="back_to_cats")
    markup.row(btn_all_cats)

    return text, markup


def get_detailed_master_card(m, chat_id, back_callback=None, distance_km=None):
    rating_stars = "⭐" * int(round(float(m.average_rating or 0))) or "Baho yo'q"
    phone_display = m.phone or "Ko'rsatilmagan"
    is_tg_connected = str(m.user.id) in master_tg_map
    status_tg = "⚡️ Telegram faol" if is_tg_connected else "🌐 Sayt orqali"
    status_badge = "🟢 Bo'sh" if m.status == 'active' else ("🔴 Band" if m.status == 'busy' else "⚪️ Nofaol")

    clean_name = html.escape(str(m.full_name or ""))
    clean_cat = html.escape(str(m.category.name or ""))
    clean_reg = html.escape(str(m.region or ""))
    clean_dist = html.escape(str(m.district or ""))
    clean_desc = html.escape(str(m.description or ""))
    clean_phone = html.escape(str(phone_display))
    price_val = f"{int(m.price):,}" if m.price else "Kelishilgan"
    exp_val = m.experience or 0
    if not clean_desc:
        clean_desc = "Ma'lumot ko'rsatilmagan"

    dist_str = ""
    if distance_km is not None:
        if distance_km < 1.0:
            dist_str = f"📍 <b>Masofa:</b> ~{int(distance_km * 1000)} metr\n"
        else:
            dist_str = f"📍 <b>Masofa:</b> ~{distance_km:.1f} km\n"

    card_text = (
        f"👷‍♂️ <b>{clean_name}</b> ({status_badge})\n"
        f"{dist_str}"
        f"💼 <b>{t(chat_id, 'specialty')}:</b> {clean_cat}\n"
        f"📍 <b>{t(chat_id, 'region_district')}:</b> {clean_reg}, {clean_dist}\n"
        f"⏳ <b>{t(chat_id, 'experience')}:</b> {exp_val} yil\n"
        f"💰 <b>{t(chat_id, 'price')}:</b> {price_val} so'm\n"
        f"⭐️ <b>{t(chat_id, 'rating')}:</b> {m.average_rating} ({rating_stars}) - {m.ratings_count} ta\n"
        f"📞 <b>{t(chat_id, 'phone')}:</b> <code>{clean_phone}</code>\n"
        f"📡 <b>{t(chat_id, 'contact')}:</b> <i>{status_tg}</i>\n\n"
        f"📝 <b>{t(chat_id, 'about')}:</b>\n<i>\"{clean_desc}\"</i>"
    )

    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_msg = types.InlineKeyboardButton(t(chat_id, 'btn_send_msg'), callback_data=f"msg_to_{m.user.id}")
    btn_rate = types.InlineKeyboardButton(t(chat_id, 'btn_rate'), callback_data=f"rate_prep_{m.id}")
    markup.add(btn_msg, btn_rate)

    works_count = m.portfolio.count()
    port_label = f"📸 Portfolio ({works_count})" if works_count > 0 else t(chat_id, 'btn_portfolio')
    btn_port = types.InlineKeyboardButton(port_label, callback_data=f"m_port_{m.id}")
    btn_map = types.InlineKeyboardButton(t(chat_id, 'btn_view_map'), callback_data=f"show_map_{m.id}")
    markup.add(btn_port, btn_map)

    if back_callback:
        btn_back = types.InlineKeyboardButton(t(chat_id, 'btn_back_to_list'), callback_data=back_callback)
        markup.add(btn_back)
    return card_text, markup


# ==========================================
# ASOSIY BUYRUQLAR
# ==========================================
@bot.message_handler(commands=['cancel'])
def handle_cancel(message):
    if message.chat.id in user_states:
        user_states.pop(message.chat.id, None)
        bot.send_message(message.chat.id, "Amal bekor qilindi.", reply_markup=get_main_keyboard(message.chat.id))


@bot.message_handler(commands=['start'])
def handle_start(message):
    register_subscriber(message.chat.id)
    # Agar yangi foydalanuvchi bo'lsa, avval tilni so'raymiz!
    if str(message.chat.id) not in user_languages:
        send_language_selection(message.chat.id)
    else:
        send_welcome_message(message.chat.id, message.from_user.first_name)


@bot.message_handler(func=lambda msg: is_btn(msg.text, 'btn_categories'))
def handle_categories(message):
    register_subscriber(message.chat.id)
    markup = get_categories_markup()
    if not markup.keyboard:
        bot.send_message(message.chat.id, "Hozircha kategoriya mavjud emas.")
        return

    bot.send_message(
        message.chat.id,
        t(message.chat.id, 'select_cat'),
        parse_mode="HTML",
        reply_markup=markup
    )


@bot.callback_query_handler(func=lambda call: call.data == "back_to_cats")
def callback_back_to_cats(call):
    bot.answer_callback_query(call.id)
    markup = get_categories_markup()
    try:
        bot.edit_message_text(
            t(call.message.chat.id, 'select_cat'),
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            parse_mode="HTML",
            reply_markup=markup
        )
    except Exception:
        pass


@bot.callback_query_handler(func=lambda call: call.data.startswith('cat_'))
def handle_category_click(call):
    cat_id = int(call.data.split('_')[1])
    category = Category.objects.filter(id=cat_id).first()
    if not category:
        bot.answer_callback_query(call.id, "Kategoriya topilmadi.")
        return

    bot.answer_callback_query(call.id)
    markup = get_category_regions_markup(cat_id, call.message.chat.id)
    prompt = t(call.message.chat.id, 'prompt_region', cat=category.name)

    try:
        bot.edit_message_text(
            prompt,
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            parse_mode="HTML",
            reply_markup=markup
        )
    except Exception:
        bot.send_message(call.message.chat.id, prompt, parse_mode="HTML", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith('cr_'))
def handle_category_region_selected(call):
    parts = call.data.split('_')
    cat_id = int(parts[1])
    reg_code = parts[2]

    bot.answer_callback_query(call.id)

    if reg_code == 'all':
        text, markup = build_masters_catalog(cat_id, 'all', 'all', call.message.chat.id, page=1)
        try:
            bot.edit_message_text(text, chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="HTML", reply_markup=markup)
        except Exception:
            bot.send_message(call.message.chat.id, text, parse_mode="HTML", reply_markup=markup)
        return

    reg_idx = int(reg_code)
    reg_name = UZBEKISTAN_REGIONS[reg_idx]
    markup = get_category_districts_markup(cat_id, reg_idx, call.message.chat.id)
    prompt = t(call.message.chat.id, 'prompt_district', reg=reg_name)

    try:
        bot.edit_message_text(prompt, chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="HTML", reply_markup=markup)
    except Exception:
        bot.send_message(call.message.chat.id, prompt, parse_mode="HTML", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith('cd_'))
def handle_category_district_selected(call):
    parts = call.data.split('_')
    cat_id = int(parts[1])
    reg_code = parts[2]
    dist_code = parts[3]

    bot.answer_callback_query(call.id)
    text, markup = build_masters_catalog(cat_id, reg_code, dist_code, call.message.chat.id, page=1)

    try:
        bot.edit_message_text(text, chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="HTML", reply_markup=markup)
    except Exception:
        bot.send_message(call.message.chat.id, text, parse_mode="HTML", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith('cp_'))
def handle_category_pagination(call):
    parts = call.data.split('_')
    cat_id = int(parts[1])
    reg_code = parts[2]
    dist_code = parts[3]
    page = int(parts[4])

    bot.answer_callback_query(call.id)
    text, markup = build_masters_catalog(cat_id, reg_code, dist_code, call.message.chat.id, page=page)

    try:
        bot.edit_message_text(text, chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="HTML", reply_markup=markup)
    except Exception:
        pass


@bot.callback_query_handler(func=lambda call: call.data.startswith('vm_'))
def handle_view_master_from_catalog(call):
    parts = call.data.split('_')
    master_id = int(parts[1])
    cat_id = int(parts[2])
    reg_code = parts[3]
    dist_code = parts[4]
    page = int(parts[5])

    master = Master.objects.filter(id=master_id).select_related('user', 'category').first()
    if not master:
        bot.answer_callback_query(call.id, "Usta topilmadi.")
        return

    bot.answer_callback_query(call.id)
    back_cb = f"cp_{cat_id}_{reg_code}_{dist_code}_{page}"
    text, markup = get_detailed_master_card(master, call.message.chat.id, back_callback=back_cb)

    try:
        bot.edit_message_text(text, chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="HTML", reply_markup=markup)
    except Exception:
        bot.send_message(call.message.chat.id, text, parse_mode="HTML", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data == "noop")
def handle_noop(call):
    bot.answer_callback_query(call.id)


@bot.message_handler(func=lambda msg: is_btn(msg.text, 'btn_top'))
def handle_top_masters(message):
    register_subscriber(message.chat.id)
    top_masters = Master.objects.filter(status='active').select_related('user', 'category').order_by('-average_rating', '-ratings_count')[:5]

    if not top_masters.exists():
        bot.send_message(message.chat.id, "Hozircha faol ustalar topilmadi.")
        return

    bot.send_message(
        message.chat.id,
        f"🏆 <b>{t(message.chat.id, 'btn_top')} (Top-5):</b>",
        parse_mode="HTML"
    )
    for master in top_masters:
        text, markup = get_detailed_master_card(master, message.chat.id)
        bot.send_message(message.chat.id, text, parse_mode="HTML", reply_markup=markup)


# ==========================================
# 👷‍♂️ USTA BO'LIB RO'YXATDAN O'TISH
# ==========================================
@bot.message_handler(func=lambda msg: is_btn(msg.text, 'btn_reg_master'))
def handle_start_master_registration(message):
    register_subscriber(message.chat.id)
    user = get_or_create_tg_user(message.from_user)

    if hasattr(user, 'master_profile'):
        save_master_tg_id(user.id, message.chat.id)
        bot.send_message(message.chat.id, t(message.chat.id, 'master_already_reg'), parse_mode="HTML")
        return

    user_states[message.chat.id] = {
        'action': 'reg_master_name',
        'data': {}
    }

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(types.KeyboardButton(t(message.chat.id, 'btn_cancel')))

    bot.send_message(
        message.chat.id,
        t(message.chat.id, 'reg_step_name'),
        parse_mode="HTML",
        reply_markup=markup
    )


# ==========================================
# PROFIL VA MA'LUMOT
# ==========================================
@bot.message_handler(func=lambda msg: is_btn(msg.text, 'btn_profile'))
def handle_profile(message):
    register_subscriber(message.chat.id)
    user = get_or_create_tg_user(message.from_user)

    role_name = "Usta 👷‍♂️" if user.role == 'master' else "Mijoz 👤"
    phone_display = user.phone or "Bog'lanmagan ❌"

    profile_text = (
        f"👤 <b>Shaxsiy Profil:</b>\n\n"
        f"• Ism: <b>{user.full_name}</b>\n"
        f"• Rol: <b>{role_name}</b>\n"
        f"• Telefon: <code>{phone_display}</code>\n"
        f"• Telegram ID: <code>{message.chat.id}</code>\n"
        f"• Til: <b>{get_user_lang(message.chat.id).upper()}</b>\n"
    )

    inline_markup = None
    if user.role == 'master' and hasattr(user, 'master_profile'):
        m = user.master_profile
        save_master_tg_id(user.id, message.chat.id)
        status_txt = "🟢 Hozir bo'sh (Buyurtma olyapti)" if m.status == 'active' else "🔴 Hozir band (Yangi ish olmayapti)"
        works_count = m.portfolio.count()
        coords_txt = f"{m.latitude:.4f}, {m.longitude:.4f}" if (m.latitude and m.longitude) else "Belgilanmagan"

        profile_text += (
            f"\n──────── USTA MA'LUMOTLARI ────────\n"
            f"🛠 Mutaxassislik: <b>{m.category.name}</b>\n"
            f"📍 Hudud: <b>{m.region}, {m.district}</b>\n"
            f"📡 GPS koordinatalari: <code>{coords_txt}</code>\n"
            f"⭐️ Reyting: <b>{m.average_rating} ⭐</b> ({m.ratings_count} ta baho)\n"
            f"💰 Boshlang'ich narx: <b>{m.price:,} so'm</b>\n"
            f"📸 Portfolio namunalari: <b>{works_count} ta</b>\n"
            f"🚦 Holatingiz: <b>{status_txt}</b>\n"
        )
        inline_markup = types.InlineKeyboardMarkup(row_width=1)
        inline_markup.add(types.InlineKeyboardButton("📊 Mening Biznes Statistikam", callback_data="master_business_stats"))
        status_toggle_label = "🔴 Band holatga o'tish" if m.status == 'active' else "🟢 Bo'sh holatga o'tish"
        inline_markup.add(types.InlineKeyboardButton(status_toggle_label, callback_data="toggle_my_status"))
        inline_markup.add(types.InlineKeyboardButton("➕ Yangi ish namunasi (rasm) qo'shish", callback_data="prep_add_portfolio"))
        if works_count > 0:
            inline_markup.add(types.InlineKeyboardButton(f"📸 Mening portfoliom ({works_count} ta)", callback_data=f"m_port_{m.id}"))
        inline_markup.add(types.InlineKeyboardButton("📍 Lokatsiyamni saqlash (GPS)", callback_data="prep_update_my_loc"))

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    btn_phone = types.KeyboardButton(t(message.chat.id, 'btn_update_phone'), request_contact=True)
    btn_back = types.KeyboardButton(t(message.chat.id, 'btn_back'))
    markup.add(btn_phone)
    markup.add(btn_back)

    bot.send_message(message.chat.id, profile_text, parse_mode="HTML", reply_markup=markup)
    if inline_markup:
        bot.send_message(message.chat.id, "⚙️ <b>Usta boshqaruvi:</b>", parse_mode="HTML", reply_markup=inline_markup)


# ==========================================
# 📊 USTA BIZNES STATISTIKASI (Feature 5)
# ==========================================
@bot.callback_query_handler(func=lambda call: call.data == "master_business_stats")
def handle_master_business_stats(call):
    user = get_or_create_tg_user(call.from_user)
    if not (user.role == 'master' and hasattr(user, 'master_profile')):
        bot.answer_callback_query(call.id, "Siz usta emassiz.")
        return

    m = user.master_profile
    my_tenders = [o for o in active_tenders.values() if o.get('accepted_by') == call.from_user.id]
    completed_tenders = [o for o in my_tenders if o.get('status') == 'completed']
    unique_clients = len(set(o.get('client_chat_id') for o in my_tenders if o.get('client_chat_id')))

    total_completed = len(completed_tenders)
    total_accepted = len(my_tenders)

    five_stars = m.ratings.filter(score=5).count()
    satisfaction = int((five_stars / m.ratings_count * 100)) if m.ratings_count > 0 else 100
    estimated_earnings = total_completed * (m.price or 50000)

    status_icon = "🟢 Bo'sh (Buyurtmalar qabul qilinmoqda)" if m.status == 'active' else "🔴 Band (Yangi ish olinmayapti)"

    text = (
        f"📊 <b>MENING BIZNES STATISTIKAM</b>\n"
        f"────────────────────────\n"
        f"👷‍♂️ <b>Usta:</b> {html.escape(m.full_name)}\n"
        f"🛠 <b>Soha:</b> {html.escape(m.category.name)}\n"
        f"🚦 <b>Holat:</b> {status_icon}\n\n"
        f"📈 <b>Ish ko'rsatkichlari:</b>\n"
        f"• Bajarilgan buyurtmalar: <b>{total_completed} ta</b>\n"
        f"• Qabul qilingan barcha buyurtmalar: <b>{total_accepted} ta</b>\n"
        f"• Xizmat ko'rsatilgan mijozlar: <b>{unique_clients} nafar</b>\n"
        f"• Mijozlar mamnuniyati: <b>{satisfaction}%</b>\n"
        f"• O'rtacha reyting: <b>{m.average_rating} ⭐</b> ({m.ratings_count} ta baho)\n"
        f"• Portfolio namunalari: <b>{m.portfolio.count()} ta</b>\n\n"
        f"💰 <b>Taxminiy umumiy tushum:</b> <b>{estimated_earnings:,} so'm</b>\n"
        f"────────────────────────\n"
        f"💡 <i>Tavsiya: Reytingingiz qancha yuqori bo'lsa va ishlarni sifatli yakunlasangiz, yangi buyurtmalarni birinchi bo'lib olasiz!</i>"
    )

    markup = types.InlineKeyboardMarkup(row_width=1)
    status_toggle_label = "🔴 Band holatga o'tish" if m.status == 'active' else "🟢 Bo'sh holatga o'tish"
    markup.add(types.InlineKeyboardButton(status_toggle_label, callback_data="toggle_my_status"))
    markup.add(types.InlineKeyboardButton("➕ Yangi ish namunasi qo'shish", callback_data="prep_add_portfolio"))
    markup.add(types.InlineKeyboardButton("📍 Lokatsiyamni yangilash (GPS)", callback_data="prep_update_my_loc"))

    bot.answer_callback_query(call.id)
    try:
        bot.edit_message_text(text, chat_id=call.message.chat.id, message_id=call.message.message_id, parse_mode="HTML", reply_markup=markup)
    except Exception:
        bot.send_message(call.message.chat.id, text, parse_mode="HTML", reply_markup=markup)


@bot.message_handler(content_types=['contact'])
def handle_contact(message):
    register_subscriber(message.chat.id)
    contact = message.contact
    clean_phone = normalize_phone_number(contact.phone_number)

    state = user_states.get(message.chat.id)
    if state and state.get('action') == 'reg_master_phone':
        state['data']['phone'] = clean_phone
        state['action'] = 'reg_master_category'
        proceed_to_master_category(message.chat.id)
        return

    if state and state.get('action') == 'order_phone':
        state['data']['phone'] = clean_phone
        user = get_or_create_tg_user(message.from_user)
        user.phone = clean_phone
        user.save(update_fields=['phone'])
        broadcast_quick_order(message.chat.id, state['data'])
        user_states.pop(message.chat.id, None)
        return

    user = get_or_create_tg_user(message.from_user)
    user.phone = clean_phone
    if contact.first_name:
        user.first_name = contact.first_name
    if contact.last_name:
        user.last_name = contact.last_name
    user.save()

    bot.send_message(
        message.chat.id,
        f"✅ Telefon raqamingiz muvaffaqiyatli saqlandi: <b>{user.phone}</b>",
        parse_mode="HTML",
        reply_markup=get_main_keyboard(message.chat.id)
    )


@bot.message_handler(func=lambda msg: is_btn(msg.text, 'btn_help'))
def handle_info(message):
    register_subscriber(message.chat.id)
    total_categories = Category.objects.filter(is_active=True).count()
    total_masters = Master.objects.filter(status='active').count()

    info_text = (
        "<b>'Ustasi' xizmat ko'rsatish platformasi</b>\n\n"
        f"📊 <b>Statistika:</b>\n"
        f"• Faol kategoriyalar: {total_categories} ta\n"
        f"• Ro'yxatdan o'tgan ustalar: {total_masters} ta\n\n"
        "Sayt va Telegram bot yagona bazaga ulangan.\n"
        "Siz istalgan vaqtda veb-platformamizdan ham to'liq foydalanishingiz mumkin."
    )
    markup = types.InlineKeyboardMarkup()
    try:
        markup.add(types.InlineKeyboardButton("🌐 Ustasi Mini App", web_app=types.WebAppInfo(url=WEBAPP_URL)))
    except Exception:
        pass
    markup.add(types.InlineKeyboardButton("🌐 Rasmiy veb-sayt", url=WEBAPP_URL))

    bot.send_message(message.chat.id, info_text, parse_mode="HTML", reply_markup=markup)


@bot.message_handler(func=lambda msg: is_btn(msg.text, 'btn_back') or is_btn(msg.text, 'btn_cancel'))
def handle_back_menu(message):
    user_states.pop(message.chat.id, None)
    bot.send_message(message.chat.id, "Asosiy menyu / Главное меню / Main Menu:", reply_markup=get_main_keyboard(message.chat.id))


# ==========================================
# 📍 GEOLOKATSIYA VA GPS QIDIRUV (Phase 2)
# ==========================================
@bot.message_handler(func=lambda msg: is_btn(msg.text, 'btn_gps'))
def handle_gps_request(message):
    register_subscriber(message.chat.id)
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    btn_loc = types.KeyboardButton(t(message.chat.id, 'btn_send_loc'), request_location=True)
    btn_cancel = types.KeyboardButton(t(message.chat.id, 'btn_back'))
    markup.add(btn_loc)
    markup.add(btn_cancel)

    # GPS o'chiq bo'lsa yoki kompyuterda bo'lsa, zaxira tuman tanlash tugmalari
    inline_markup = types.InlineKeyboardMarkup(row_width=2)
    districts = [
        "Chilonzor tumani", "Yunusobod tumani",
        "Mirzo Ulug'bek tumani", "Shayxontohur tumani",
        "Yakkasaroy tumani", "Mirobod tumani",
        "Sergeli tumani", "Olmazor tumani",
        "Uchtepa tumani", "Yashnobod tumani"
    ]
    buttons = [types.InlineKeyboardButton(f"🏙 {d.replace(' tumani', '')}", callback_data=f"gps_dist_{d}") for d in districts]
    inline_markup.add(*buttons)

    bot.send_message(
        message.chat.id,
        t(message.chat.id, 'gps_prompt'),
        parse_mode="HTML",
        reply_markup=markup
    )
    bot.send_message(
        message.chat.id,
        "🏙 <b>GPS o'chiq bo'lsa, tumaningizni tanlang:</b>",
        parse_mode="HTML",
        reply_markup=inline_markup
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith('gps_dist_'))
def handle_gps_by_district(call):
    dist_name = call.data.replace('gps_dist_', '')
    coords = DISTRICT_COORDS.get(dist_name) or (41.2995, 69.2401)
    u_lat, u_lon = coords
    bot.answer_callback_query(call.id, f"{dist_name} markazi tanlandi!")

    all_masters = list(Master.objects.filter(status__in=['active', 'busy']).select_related('user', 'category'))
    if not all_masters:
        bot.send_message(call.message.chat.id, t(call.message.chat.id, 'no_gps_masters'), reply_markup=get_main_keyboard(call.message.chat.id))
        return

    master_dists = []
    for m in all_masters:
        m_lat, m_lon = get_master_coords(m)
        dist = haversine_km(u_lat, u_lon, m_lat, m_lon)
        master_dists.append((dist, m))

    master_dists.sort(key=lambda x: (0 if x[1].status == 'active' else 1, x[0]))
    top_nearby = master_dists[:5]

    bot.send_message(
        call.message.chat.id,
        f"📍 <b>{dist_name} markazi bo'yicha eng yaqin ustalar:</b>\n────────────────────────",
        parse_mode="HTML",
        reply_markup=get_main_keyboard(call.message.chat.id)
    )

    for dist, m in top_nearby:
        try:
            text, markup = get_detailed_master_card(m, call.message.chat.id, distance_km=dist)
            bot.send_message(call.message.chat.id, text, parse_mode="HTML", reply_markup=markup)
        except Exception as err:
            print(f"Error sending nearby master card by district: {err}")


@bot.callback_query_handler(func=lambda call: call.data.startswith('show_map_'))
def handle_show_master_on_map(call):
    master_id = int(call.data.split('_')[2])
    master = Master.objects.filter(id=master_id).first()
    if not master:
        bot.answer_callback_query(call.id, "Usta topilmadi.")
        return

    m_lat, m_lon = get_master_coords(master)
    bot.answer_callback_query(call.id, f"{master.full_name} lokatsiyasi!")

    cat_name = master.category.name if master.category else "Usta"
    dist_name = master.district or master.region or "Toshkent"
    try:
        bot.send_venue(
            call.message.chat.id,
            latitude=m_lat,
            longitude=m_lon,
            title=f"👷‍♂️ {master.full_name} ({cat_name})",
            address=f"📍 {master.region}, {dist_name}"
        )
    except Exception:
        try:
            bot.send_location(call.message.chat.id, latitude=m_lat, longitude=m_lon)
        except Exception:
            pass

    pin_style = get_category_pin_style(cat_name)
    yandex_pin_url = f"https://yandex.uz/maps/?pt={m_lon:.4f},{m_lat:.4f},{pin_style}&z=16"
    yandex_nav_url = f"https://yandex.uz/maps/?rtext=~{m_lat:.5f},{m_lon:.5f}&rtt=auto"
    google_url = f"https://www.google.com/maps/dir/?api=1&destination={m_lat:.5f},{m_lon:.5f}"

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🚗 Yandex Navigator", url=yandex_nav_url),
        types.InlineKeyboardButton("🗺 Yandex Xarita", url=yandex_pin_url)
    )
    markup.add(
        types.InlineKeyboardButton("📍 Google Maps", url=google_url)
    )

    clean_name = html.escape(master.full_name)
    bot.send_message(
        call.message.chat.id,
        f"📍 <b>{clean_name}</b> ({cat_name}) ning aniq xaritadagi joylashuvi ko'rsatildi!\n\n"
        f"Marshrut chizish yoki navigatsiyani yoqish uchun tanlang:",
        parse_mode="HTML",
        reply_markup=markup
    )


@bot.message_handler(func=lambda msg: is_btn(msg.text, 'btn_map') or (msg.text and any(k in msg.text.lower() for k in ["jonli xarita", "xarita", "карта", "живая карта", "live map"])))
def handle_live_map(message):
    register_subscriber(message.chat.id)
    map_data = build_masters_map_data()
    total_count = map_data['total_count']
    tashkent_count = map_data['tashkent_count']
    static_map_url = map_data['static_map_url']
    yandex_tashkent_url = map_data['yandex_tashkent_url']
    yandex_all_url = map_data['yandex_all_url']

    caption_text = (
        "🗺 <b>USTASI.UZ — BARCHA USTALAR JONLI XARITADA</b>\n"
        "────────────────────────\n"
        f"Platformamizda jami <b>{total_count} nafar faol usta</b> ro'yxatdan o'tgan "
        f"(ulardan <b>{tashkent_count} nafari</b> Toshkent shahri bo'ylab joylashgan):\n\n"
        "🔴 <b>Santexniklar</b> (Qizil belgilar)\n"
        "🟡 <b>Elektriklar</b> (Sariq belgilar)\n"
        "🟠 <b>Quruvchilar va Ta'mirchilar</b> (To'q sariq)\n"
        "🔵 <b>Telefon va Maishiy texnika</b> (Ko'k belgilar)\n\n"
        "Xaritada ustalarni ko'rish va navigatsiya qilish uchun quyidagi tugmalardan foydalaning 👇"
    )

    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("🚗 1. Yandex Xaritalarida barcha ustalarni ochish", url=yandex_tashkent_url))
    markup.add(types.InlineKeyboardButton("📍 2. O'zimga eng yaqin ustalarni topish (GPS)", callback_data="map_gps_search"))
    markup.add(types.InlineKeyboardButton("🏙 3. Tumanlar bo'yicha ko'rish", callback_data="gps_prompt_districts"))
    if total_count > tashkent_count:
        markup.add(types.InlineKeyboardButton("🇺🇿 4. Barcha viloyatlar ustalari xaritasi", url=yandex_all_url))

    photo_sent = False
    try:
        req = urllib.request.Request(static_map_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as resp:
            if resp.status == 200:
                img_bytes = resp.read()
                bio = io.BytesIO(img_bytes)
                bio.name = 'masters_map.png'
                bot.send_photo(message.chat.id, photo=bio, caption=caption_text, parse_mode="HTML", reply_markup=markup)
                photo_sent = True
    except Exception as e:
        print(f"Failed to send static map photo: {e}")

    if not photo_sent:
        bot.send_message(message.chat.id, caption_text, parse_mode="HTML", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data == "map_gps_search")
def handle_map_gps_search_callback(call):
    bot.answer_callback_query(call.id)
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    btn_loc = types.KeyboardButton(t(call.message.chat.id, 'btn_send_loc'), request_location=True)
    btn_cancel = types.KeyboardButton(t(call.message.chat.id, 'btn_back'))
    markup.add(btn_loc)
    markup.add(btn_cancel)
    bot.send_message(
        call.message.chat.id,
        "📍 <b>Eng yaqin ustalarni aniqlash uchun pastdagi '📍 Geolokatsiyamni yuborish' tugmasini bosing:</b>",
        parse_mode="HTML",
        reply_markup=markup
    )


@bot.callback_query_handler(func=lambda call: call.data == "gps_prompt_districts")
def handle_map_districts_prompt(call):
    bot.answer_callback_query(call.id)
    inline_markup = types.InlineKeyboardMarkup(row_width=2)
    districts = [
        "Chilonzor tumani", "Yunusobod tumani",
        "Mirzo Ulug'bek tumani", "Shayxontohur tumani",
        "Yakkasaroy tumani", "Mirobod tumani",
        "Sergeli tumani", "Olmazor tumani",
        "Uchtepa tumani", "Yashnobod tumani"
    ]
    buttons = [types.InlineKeyboardButton(f"🏙 {d.replace(' tumani', '')}", callback_data=f"gps_dist_{d}") for d in districts]
    inline_markup.add(*buttons)
    bot.send_message(
        call.message.chat.id,
        "🏙 <b>Qaysi tuman bo'yicha ustalarni ko'rmoqchisiz?</b>\nTumanni tanlang:",
        parse_mode="HTML",
        reply_markup=inline_markup
    )


@bot.message_handler(content_types=['location'])
def handle_location(message):
    register_subscriber(message.chat.id)
    u_lat = message.location.latitude
    u_lon = message.location.longitude

    user = get_or_create_tg_user(message.from_user)
    # Agar foydalanuvchi usta bo'lsa, koordinatalarini profilinga doimiy yangilab qo'yamiz
    if hasattr(user, 'master_profile'):
        m_prof = user.master_profile
        m_prof.latitude = u_lat
        m_prof.longitude = u_lon
        m_prof.save(update_fields=['latitude', 'longitude'])

    state = user_states.get(message.chat.id)
    if state and state.get('action') == 'master_updating_location':
        user_states.pop(message.chat.id, None)
        bot.send_message(
            message.chat.id,
            f"✅ <b>Lokatsiyangiz profilingizga muvaffaqiyatli saqlandi!</b>\n\n"
            f"📍 Koordinatalar: <code>{u_lat:.5f}, {u_lon:.5f}</code>\n"
            f"Endi yaqin-atrofdagi mijozlar sizni GPS qidiruvida eng yuqori o'rinlarda ko'rishadi.",
            parse_mode="HTML",
            reply_markup=get_main_keyboard(message.chat.id)
        )
        return

    all_masters = list(Master.objects.filter(status__in=['active', 'busy']).select_related('user', 'category'))
    if not all_masters:
        bot.send_message(message.chat.id, t(message.chat.id, 'no_gps_masters'), reply_markup=get_main_keyboard(message.chat.id))
        return

    master_dists = []
    for m in all_masters:
        m_lat, m_lon = get_master_coords(m)
        dist = haversine_km(u_lat, u_lon, m_lat, m_lon)
        master_dists.append((dist, m))

    master_dists.sort(key=lambda x: (0 if x[1].status == 'active' else 1, x[0]))
    top_nearby = master_dists[:5]

    bot.send_message(
        message.chat.id,
        f"{t(message.chat.id, 'gps_found')}\n<i>(Koordinatangiz: {u_lat:.4f}, {u_lon:.4f})</i>",
        parse_mode="HTML",
        reply_markup=get_main_keyboard(message.chat.id)
    )

    for dist, m in top_nearby:
        try:
            text, markup = get_detailed_master_card(m, message.chat.id, distance_km=dist)
            bot.send_message(message.chat.id, text, parse_mode="HTML", reply_markup=markup)
        except Exception as err:
            print(f"Error sending nearby master card by location: {err}")


# ==========================================
# ⚡️ TEZKOR BUYURTMA / TENDER (Phase 4)
# ==========================================
@bot.message_handler(func=lambda msg: is_btn(msg.text, 'btn_order') or (msg.text and any(k in msg.text.lower() for k in ["tezkor", "ovozli", "быстрый", "quick"])))
def handle_start_quick_order(message):
    register_subscriber(message.chat.id)
    user_states[message.chat.id] = {'action': 'waiting_ai_voice_or_text'}

    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("📋 Qo'lda soha va tuman tanlash", callback_data="dvo_show_all_cats"))
    markup.add(types.InlineKeyboardButton(t(message.chat.id, 'btn_cancel'), callback_data="dvo_cancel"))

    prompt_text = (
        "🎙 <b>TEZKOR AI OVOZLI BUYURTMA:</b>\n"
        "────────────────────────\n"
        "Soha va tumanlarni qidirib vaqt yo'qotishingiz shart emas!\n\n"
        "👇 <b>Quyidagi mikrofon tugmasini bosib turing va vazifangizni ovozda ayting:</b>\n"
        "<i>(Masalan: «Chilonzorda santexnik kerak, krantdan suv oqyapti» yoki «Yunusobodda rozetka ishlamayapti»)</i>\n\n"
        "🤖 <b>AI tizimi nutqingizni tahlil qilib:</b>\n"
        "• Kerakli usta mutaxassisligini aniqlaydi\n"
        "• Qaysi tuman yoki manzilda ekanligingizni belgilaydi\n"
        "• Buyurtmangizni 1 ta bosishda ushbu hududdagi barcha ustalarga yetkazadi!\n\n"
        "✍️ <i>Yoki muammoingizni pastdagi satrga oddiy matn ko'rinishida ham yozib yuborishingiz mumkin.</i>"
    )
    bot.send_message(
        message.chat.id,
        prompt_text,
        parse_mode="HTML",
        reply_markup=markup
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith('ordcat_'))
def handle_order_category_selected(call):
    cat_id = int(call.data.split('_')[1])
    cat = Category.objects.filter(id=cat_id).first()
    if not cat:
        bot.answer_callback_query(call.id, "Kategoriya topilmadi.")
        return

    bot.answer_callback_query(call.id)
    user_states[call.message.chat.id] = {
        'action': 'order_district',
        'data': {'cat_id': cat_id, 'cat_name': cat.name}
    }

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2, one_time_keyboard=True)
    for d in ["Yunusobod tumani", "Chilonzor tumani", "Mirzo Ulug'bek", "Shayxontohur", "Yakkasaroy", "Sergeli"]:
        markup.add(types.KeyboardButton(d))
    markup.add(types.KeyboardButton(t(call.message.chat.id, 'btn_cancel')))

    bot.send_message(
        call.message.chat.id,
        f"🛠 Tanlangan soha: <b>{cat.name}</b>\n\n{t(call.message.chat.id, 'order_step_dist')}",
        parse_mode="HTML",
        reply_markup=markup
    )


def save_telegram_voice_to_media(file_id):
    if not file_id:
        return None
    try:
        file_info = bot.get_file(file_id)
        downloaded = bot.download_file(file_info.file_path)
        ext = "mp3" if file_info.file_path.endswith(".mp3") else "ogg"
        voice_dir = Path(settings.MEDIA_ROOT) / "voice_orders"
        voice_dir.mkdir(parents=True, exist_ok=True)
        filename = f"voice_{int(time.time())}_{file_id[:8]}.{ext}"
        filepath = voice_dir / filename
        with open(filepath, "wb") as f:
            f.write(downloaded)
        return f"/media/voice_orders/{filename}"
    except Exception as e:
        print(f"Error saving telegram voice to media: {e}")
        return None


def broadcast_quick_order(client_chat_id, data):
    cat_id = data['cat_id']
    cat_name = data['cat_name']
    district = data['district']
    desc = data['desc']
    phone = data['phone']
    voice_file_id = data.get('voice_file_id')
    is_audio = data.get('is_audio', False)

    order_id = f"ord_{int(time.time())}_{client_chat_id}"
    active_tenders[order_id] = {
        'client_chat_id': client_chat_id,
        'cat_name': cat_name,
        'district': district,
        'desc': desc,
        'phone': phone,
        'voice_file_id': voice_file_id,
        'is_audio': is_audio,
        'accepted_by': None,
        'sent_notifications': [],
        'created_at': time.strftime("%Y-%m-%d %H:%M:%S")
    }

    matching_masters = list(Master.objects.filter(category_id=cat_id, status='active').select_related('user'))
    notified_count = 0

    markup = types.InlineKeyboardMarkup()
    btn_accept = types.InlineKeyboardButton("✋ Buyurtmani qabul qilish", callback_data=f"accept_tender_{order_id}")
    markup.add(btn_accept)

    esc_desc = html.escape(str(desc))
    esc_dist = html.escape(str(district))
    esc_cat = html.escape(str(cat_name))

    if voice_file_id:
        desc_info = "🎙 <i>Mijoz vazifani ovozli xabarda qoldirgan.</i>\n🔒 <i>Xavfsizlik: Ovozli xabar va kontaktlar faqat birinchi qabul qilgan ustaga beriladi.</i>"
    else:
        desc_info = f"<i>\"{esc_desc}\"</i>"

    tender_msg = (
        f"⚡️ <b>YANGI TEZKOR BUYURTMA!</b>\n"
        f"────────────────────────\n"
        f"🛠 <b>Soha:</b> {esc_cat}\n"
        f"📍 <b>Manzil / Tuman:</b> {esc_dist}\n"
        f"📝 <b>Vazifa:</b> {desc_info}\n"
        f"👤 <b>Mijoz:</b> [Faqat qabul qilingach ochiladi]\n"
        f"────────────────────────\n"
        f"⚡️ <i>Buyurtmani birinchi bo'lib olish uchun quyidagi tugmani bosing:</i>"
    )

    sent_notifications = []
    for m in matching_masters:
        m_chat_id = master_tg_map.get(str(m.user.id))
        if m_chat_id:
            try:
                # Ovozli xabar hammani bezovta qilmasligi va telefon sizib chiqmasligi uchun
                # hammaga faqat matnli tender yuboriladi, ovoz faqat qabul qilganga beriladi!
                msg = bot.send_message(m_chat_id, tender_msg, parse_mode="HTML", reply_markup=markup)
                sent_notifications.append((m_chat_id, msg.message_id))
                notified_count += 1
            except Exception:
                pass

    active_tenders[order_id]['sent_notifications'] = sent_notifications
    save_json_dict(TENDERS_FILE, active_tenders)

    success_msg = t(client_chat_id, 'order_broadcast_success', count=max(notified_count, 1))
    bot.send_message(
        client_chat_id,
        success_msg,
        parse_mode="HTML",
        reply_markup=get_main_keyboard(client_chat_id)
    )

    # 📢 ADMINGA REAL-VAQTDA MONITORING HISOBOTI VA OVOZ NUSXASI
    client_obj = User.objects.filter(email=f"tg_{client_chat_id}@ustasi.uz").first()
    client_name = client_obj.full_name if client_obj else f"TG: {client_chat_id}"
    admin_report = (
        f"👑 <b>[ADMIN MONITORING] YANGI TEZKOR BUYURTMA!</b>\n"
        f"────────────────────────\n"
        f"👤 <b>Mijoz:</b> {html.escape(client_name)} (ID: <code>{client_chat_id}</code>)\n"
        f"📞 <b>Aloqa:</b> <code>{phone}</code>\n"
        f"🛠 <b>Soha:</b> {esc_cat}\n"
        f"📍 <b>Hudud:</b> {esc_dist}\n"
        f"📝 <b>Vazifa:</b> <i>\"{esc_desc}\"</i>\n"
        f"📡 <b>Yetkazilgan ustalar soni:</b> <b>{notified_count} nafar faol usta</b>\n"
        f"────────────────────────\n"
        f"⚡️ <i>Biror usta qabul qilishi bilan sizga darhol hisobot keladi.</i>"
    )

    for a_id in list(admin_ids):
        try:
            if voice_file_id:
                if is_audio:
                    bot.send_audio(a_id, audio=voice_file_id, caption=admin_report, parse_mode="HTML")
                else:
                    bot.send_voice(a_id, voice=voice_file_id, caption=admin_report, parse_mode="HTML")
            else:
                bot.send_message(a_id, admin_report, parse_mode="HTML")
        except Exception:
            pass


@bot.callback_query_handler(func=lambda call: call.data.startswith('accept_tender_'))
def handle_accept_tender(call):
    order_id = call.data.replace('accept_tender_', '')
    order = active_tenders.get(order_id)
    if not order:
        bot.answer_callback_query(call.id, "Ushbu buyurtma muddati o'tgan yoki bekor qilingan.", show_alert=True)
        return

    if order['accepted_by'] is not None:
        bot.answer_callback_query(call.id, "⚠️ Kechirasiz, ushbu buyurtmani boshqa usta qabul qildi!", show_alert=True)
        return

    master_user = get_or_create_tg_user(call.from_user)
    master_obj = Master.objects.filter(user=master_user).first()
    master_name = master_obj.full_name if master_obj else call.from_user.full_name
    master_phone = master_user.phone or "Ko'rsatilmagan"

    order['accepted_by'] = call.from_user.id
    order['accepted_at'] = time.strftime("%Y-%m-%d %H:%M:%S")
    save_json_dict(TENDERS_FILE, active_tenders)

    bot.answer_callback_query(call.id, "✅ Siz buyurtmani muvaffaqiyatli qabul qildingiz!", show_alert=True)

    esc_desc = html.escape(str(order['desc']))
    esc_dist = html.escape(str(order['district']))
    esc_cat = html.escape(str(order['cat_name']))
    esc_phone = html.escape(str(order['phone']))

    contact_hint = f"📞 <b>Mijoz telefoni:</b> <code>{esc_phone}</code>\n"
    if "Ovozli" in order['phone'] or "Ovozda" in order['phone']:
        contact_hint = f"📞 <b>Mijoz kontakti:</b> <i>Ovozli xabarda aytilgan (pastdagi ovozni eshiting) yoki Telegramdan yozing</i>\n"

    accept_text = (
        f"✅ <b>Siz ushbu buyurtmani qabul qildingiz!</b>\n\n"
        f"🛠 <b>Soha:</b> {esc_cat}\n"
        f"📍 <b>Manzil:</b> {esc_dist}\n"
        f"📝 <b>Vazifa:</b> <i>\"{esc_desc}\"</i>\n"
        f"{contact_hint}\n"
        f"<i>Mijoz bilan darhol bog'laning!</i>"
    )

    accept_markup = types.InlineKeyboardMarkup()
    accept_markup.add(types.InlineKeyboardButton("✍️ Mijozga Telegramdan yozish", callback_data=f"reply_to_client_{order['client_chat_id']}"))
    accept_markup.add(types.InlineKeyboardButton("✅ Ishni yakunladim", callback_data=f"finish_order_{order_id}"))

    try:
        bot.edit_message_text(
            accept_text,
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            parse_mode="HTML",
            reply_markup=accept_markup
        )
    except Exception:
        pass

    # Agar ovozli xabar bo'lsa, uni FAQAT shu qabul qilgan ustaga shaxsan yuboramiz!
    if order.get('voice_file_id'):
        try:
            if order.get('is_audio'):
                bot.send_audio(
                    call.message.chat.id,
                    audio=order['voice_file_id'],
                    caption="🎙 <b>Mijozning audio xabari:</b>\n(Mijoz vazifani ushbu yozuvda tushuntirgan)",
                    parse_mode="HTML"
                )
            else:
                bot.send_voice(
                    call.message.chat.id,
                    voice=order['voice_file_id'],
                    caption="🎙 <b>Mijozning ovozli xabari:</b>\n(Mijoz vazifani ushbu ovozda tushuntirgan)",
                    parse_mode="HTML"
                )
        except Exception:
            pass

    # 📢 Saytdagi platforma kabineti (Chat / Xabarlar) ga ham yozib qo'yamiz:
    try:
        c_chat_id = order.get('client_chat_id')
        client_user = User.objects.filter(email=f"tg_{c_chat_id}@ustasi.uz").first()
        if not client_user and order.get('phone'):
            client_user = User.objects.filter(phone=order.get('phone')).first()
        if not client_user:
            client_user, _ = User.objects.get_or_create(
                email=f"tg_{c_chat_id}@ustasi.uz",
                defaults={'first_name': 'Mijoz', 'role': 'client'}
            )

        media_url = None
        if order.get('voice_file_id'):
            media_url = save_telegram_voice_to_media(order['voice_file_id'])

        audio_hint = f"\n🎧 Ovozli xabar fayli: {media_url}" if media_url else ""
        chat_text = (
            f"⚡️ [TEZKOR BUYURTMA QABUL QILINDI]\n"
            f"🛠 Soha: {order['cat_name']}\n"
            f"📍 Manzil: {order['district']}\n"
            f"📝 Vazifa: {order['desc']}\n"
            f"📞 Mijoz telefoni: {order['phone']}"
            f"{audio_hint}"
        )
        Message.objects.create(
            sender=client_user,
            receiver=master_user,
            text=chat_text,
            is_read=False
        )
    except Exception as err:
        print(f"Platforma kabinetiga xabar yozishda xatolik: {err}")

    # QOLGAN BARCHA USTALARDA XABARNI AVTOMATIK YOPISH:
    closed_text = (
        f"🔒 <b>BUYURTMA YOPILDI (QABUL QILINDI)</b>\n\n"
        f"🛠 <b>Soha:</b> {esc_cat} ({esc_dist})\n\n"
        f"Ushbu buyurtmani <b>boshqa usta qabul qildi</b> va mijoz tomon yo'lga chiqdi.\n"
        f"Mijozning kontaktlari va ovozli yozuvi faqat qabul qilgan ustaga taqdim etildi."
    )
    for other_chat_id, other_msg_id in order.get('sent_notifications', []):
        if other_chat_id != call.message.chat.id:
            try:
                bot.edit_message_text(closed_text, chat_id=other_chat_id, message_id=other_msg_id, parse_mode="HTML", reply_markup=None)
            except Exception:
                pass

    # Mijozga usta qabul qilganini xabar qilish
    client_chat_id = order['client_chat_id']
    client_markup = types.InlineKeyboardMarkup()
    if master_obj:
        client_markup.add(types.InlineKeyboardButton("👤 Usta profilini ko'rish", callback_data=f"vm_{master_obj.id}_all_all_all_1"))
        client_markup.add(types.InlineKeyboardButton("💬 Ustaga yozish", callback_data=f"msg_to_{master_obj.user.id}"))

    try:
        bot.send_message(
            client_chat_id,
            f"🎉 <b>BUYURTMANGIZ QABUL QILINDI!</b>\n\n"
            f"Usta <b>{master_name}</b> sizning buyurtmangizni qabul qildi va tez orada bog'lanadi!\n\n"
            f"👷‍♂️ <b>Usta:</b> {master_name}\n"
            f"📞 <b>Telefon:</b> <code>{master_phone}</code>\n"
            f"🛠 <b>Soha:</b> {order['cat_name']}\n\n"
            f"<i>Boshqa ustalarga buyurtma yopildi deb ko'rsatildi, sizga faqat shu usta bog'lanadi.</i>",
            parse_mode="HTML",
            reply_markup=client_markup
        )
    except Exception:
        pass

    # 📢 ADMINGA QABUL QILINGANLIK HISOBOTI
    admin_accepted_report = (
        f"✅ <b>[ADMIN MONITORING] BUYURTMA QABUL QILINDI!</b>\n"
        f"────────────────────────\n"
        f"🛠 <b>Soha:</b> {esc_cat} ({esc_dist})\n"
        f"👷‍♂️ <b>Qabul qilgan usta:</b> <b>{master_name}</b>\n"
        f"📞 <b>Usta telefoni:</b> <code>{master_phone}</code>\n"
        f"👤 <b>Mijoz ID:</b> <code>{order['client_chat_id']}</code>\n"
        f"📞 <b>Mijoz kontakti:</b> <code>{order['phone']}</code>\n"
        f"────────────────────────\n"
        f"<i>Usta mijoz bilan bog'lanish uchun buyurtmani oldi.</i>"
    )
    for a_id in list(admin_ids):
        try:
            bot.send_message(a_id, admin_accepted_report, parse_mode="HTML")
        except Exception:
            pass


# ==========================================
# 🏁 BUYURTMANI YAKUNLASH VA REJTING (Feature 4)
# ==========================================
@bot.callback_query_handler(func=lambda call: call.data.startswith('finish_order_'))
def handle_finish_order(call):
    order_id = call.data.replace('finish_order_', '')
    order = active_tenders.get(order_id)
    if not order:
        bot.answer_callback_query(call.id, "Buyurtma topilmadi.")
        return

    order['status'] = 'completed'
    order['completed_at'] = time.strftime("%Y-%m-%d %H:%M:%S")
    save_json_dict(TENDERS_FILE, active_tenders)

    bot.answer_callback_query(call.id, "✅ Ish yakunlangani qayd etildi!")
    try:
        bot.edit_message_text(
            f"✅ <b>BUYURTMA YAKUNLANDI!</b>\n\n"
            f"🛠 <b>Soha:</b> {order['cat_name']} ({order['district']})\n\n"
            f"Mijozga xizmatni qabul qilish va sizga baho berish so'rovi yuborildi.\n"
            f"Muvaffaqiyatli xizmat uchun tashakkur!",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            parse_mode="HTML"
        )
    except Exception:
        pass

    # Mijozga baholash oynasi
    master_user = get_or_create_tg_user(call.from_user)
    master_obj = Master.objects.filter(user=master_user).first()
    master_name = master_obj.full_name if master_obj else call.from_user.full_name

    markup = types.InlineKeyboardMarkup(row_width=5)
    stars = [types.InlineKeyboardButton(f"{i} ⭐", callback_data=f"tenderrate_{order_id}_{i}") for i in range(1, 6)]
    markup.add(*stars)

    try:
        bot.send_message(
            order['client_chat_id'],
            f"🏁 <b>BUYURTMA YAKUNLANDI!</b>\n\n"
            f"Usta <b>{html.escape(master_name)}</b> sizning buyurtmangizni muvaffaqiyatli yakunlaganini bildirdi.\n\n"
            f"⭐️ <b>Xizmat sifati sizga ma'qul keldimi?</b>\n"
            f"Iltimos, ustanining ishini baholang (1 dan 5 gacha yulduz):",
            parse_mode="HTML",
            reply_markup=markup
        )
    except Exception:
        pass


@bot.callback_query_handler(func=lambda call: call.data.startswith('tenderrate_'))
def handle_tender_rating(call):
    parts = call.data.split('_')
    order_id = parts[1]
    score = int(parts[2])

    order = active_tenders.get(order_id)
    bot.answer_callback_query(call.id, f"Siz {score} ⭐ baho berdingiz!", show_alert=True)

    if order:
        order['rating'] = score
        save_json_dict(TENDERS_FILE, active_tenders)

        accepted_by_tg_id = order.get('accepted_by')
        master_id_in_db = None
        for u_id_str, tg_id in master_tg_map.items():
            if str(tg_id) == str(accepted_by_tg_id):
                master_id_in_db = int(u_id_str)
                break

        master_user = User.objects.filter(id=master_id_in_db).first() if master_id_in_db else None
        client_user = get_or_create_tg_user(call.from_user)

        if master_user and hasattr(master_user, 'master_profile'):
            m_obj = master_user.master_profile
            Rating.objects.update_or_create(
                user=client_user,
                master=m_obj,
                defaults={'score': score, 'comment': f"Tezkor buyurtma ({order['cat_name']}) orqali baholandi"}
            )
            m_obj.update_rating_stats()

            # Ustaga g'alaba bildirishnomasi
            if accepted_by_tg_id:
                try:
                    bot.send_message(
                        accepted_by_tg_id,
                        f"🎉 <b>YANGI BAHO!</b>\n\n"
                        f"Mijoz sizga <b>{score} ⭐</b> baho berdi!\n"
                        f"Yangi umumiy reytingingiz: <b>{m_obj.average_rating} ⭐</b> ({m_obj.ratings_count} ta baho).\n"
                        f"Ajoyib xizmat uchun tashakkur!",
                        parse_mode="HTML"
                    )
                except Exception:
                    pass

    try:
        bot.edit_message_text(
            f"✅ <b>Rahmat! Siz {score} ⭐ baho berdingiz.</b>\n\n"
            f"Sizning bahoingiz usta profilida va saytda aks etdi.\n"
            f"Ustasi platformasidan foydalanganingiz uchun tashakkur!",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            parse_mode="HTML"
        )
    except Exception:
        pass


# ==========================================
# 📸 PORTFOLIO VA ISH NAMUNALARI (Phase 3)
# ==========================================
@bot.callback_query_handler(func=lambda call: call.data.startswith('m_port_'))
def handle_view_portfolio(call):
    master_id = int(call.data.split('_')[2])
    master = Master.objects.filter(id=master_id).first()
    if not master:
        bot.answer_callback_query(call.id, "Usta topilmadi.")
        return

    works = list(PortfolioWork.objects.filter(master=master).order_by('-created_at')[:6])
    if not works:
        bot.answer_callback_query(call.id, t(call.message.chat.id, 'portfolio_empty'), show_alert=True)
        return

    bot.answer_callback_query(call.id)
    header = t(call.message.chat.id, 'portfolio_title', name=master.full_name, count=len(works))
    bot.send_message(call.message.chat.id, header, parse_mode="HTML")

    for w in works:
        caption = f"🖼 <b>{w.title}</b>"
        if w.description:
            caption += f"\n\n<i>\"{w.description}\"</i>"

        sent = False
        if w.image:
            img_path = Path(settings.MEDIA_ROOT) / str(w.image)
            if img_path.exists():
                try:
                    with open(img_path, 'rb') as pf:
                        bot.send_photo(call.message.chat.id, pf, caption=caption, parse_mode="HTML")
                        sent = True
                except Exception:
                    pass

        if not sent:
            bot.send_message(call.message.chat.id, caption, parse_mode="HTML")


@bot.callback_query_handler(func=lambda call: call.data == "toggle_my_status")
def handle_toggle_my_status(call):
    user = get_or_create_tg_user(call.from_user)
    if not (user.role == 'master' and hasattr(user, 'master_profile')):
        bot.answer_callback_query(call.id, "Siz usta emassiz.")
        return

    m = user.master_profile
    if m.status == 'active':
        m.status = 'busy'
        new_status_text = "🔴 Band"
    else:
        m.status = 'active'
        new_status_text = "🟢 Bo'sh"

    m.save(update_fields=['status'])
    bot.answer_callback_query(call.id, f"Holatingiz '{new_status_text}' deb belgilandi!", show_alert=True)

    status_toggle_label = "🔴 Band holatga o'tish" if m.status == 'active' else "🟢 Bo'sh holatga o'tish"
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton(status_toggle_label, callback_data="toggle_my_status"))
    markup.add(types.InlineKeyboardButton("➕ Yangi ish namunasi (rasm) qo'shish", callback_data="prep_add_portfolio"))
    works_count = m.portfolio.count()
    if works_count > 0:
        markup.add(types.InlineKeyboardButton(f"📸 Mening portfoliom ({works_count} ta)", callback_data=f"m_port_{m.id}"))
    markup.add(types.InlineKeyboardButton("📍 Lokatsiyamni saqlash (GPS)", callback_data="prep_update_my_loc"))

    try:
        bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup)
    except Exception:
        pass


@bot.callback_query_handler(func=lambda call: call.data == "prep_add_portfolio")
def handle_prep_add_portfolio(call):
    user = get_or_create_tg_user(call.from_user)
    if not (user.role == 'master' and hasattr(user, 'master_profile')):
        bot.answer_callback_query(call.id, "Faqat ustalar ish namunasi qo'shishi mumkin.")
        return

    bot.answer_callback_query(call.id)
    user_states[call.message.chat.id] = {
        'action': 'waiting_portfolio_photo',
        'data': {'master_id': user.master_profile.id}
    }
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(types.KeyboardButton(t(call.message.chat.id, 'btn_cancel')))
    bot.send_message(
        call.message.chat.id,
        "📸 <b>Bajargan ishingizning fotosuratini yuboring:</b>\n\n(Telegram orqali rasm yuboring. Chiroyli va sifatli suratlar mijozlar ishonchini oshiradi)",
        parse_mode="HTML",
        reply_markup=markup
    )


@bot.callback_query_handler(func=lambda call: call.data == "prep_update_my_loc")
def handle_prep_update_my_loc(call):
    bot.answer_callback_query(call.id)
    user_states[call.message.chat.id] = {'action': 'master_updating_location'}
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(types.KeyboardButton(t(call.message.chat.id, 'btn_send_loc'), request_location=True))
    markup.add(types.KeyboardButton(t(call.message.chat.id, 'btn_cancel')))
    bot.send_message(
        call.message.chat.id,
        "📍 <b>Hozirgi turgan joyingizni yuboring:</b>\n\nPastdagi <b>'📍 Geolokatsiyamni yuborish'</b> tugmasini bosing:",
        parse_mode="HTML",
        reply_markup=markup
    )


@bot.message_handler(content_types=['photo'])
def handle_photo_upload(message):
    state = user_states.get(message.chat.id)
    if state and state.get('action') == 'waiting_portfolio_photo':
        photo = message.photo[-1]
        file_info = bot.get_file(photo.file_id)
        downloaded = bot.download_file(file_info.file_path)

        portfolio_dir = Path(settings.MEDIA_ROOT) / "portfolio"
        portfolio_dir.mkdir(parents=True, exist_ok=True)

        filename = f"port_{message.chat.id}_{int(time.time())}.jpg"
        filepath = portfolio_dir / filename
        with open(filepath, 'wb') as f:
            f.write(downloaded)

        state['data']['image_rel'] = f"portfolio/{filename}"
        state['action'] = 'waiting_portfolio_title'
        bot.send_message(
            message.chat.id,
            "✅ Rasm qabul qilindi!\n\nEndi ushbu <b>ish nomini</b> kiriting:\n(Masalan: <i>Evro-remont oshxona santexnikasi</i>)",
            parse_mode="HTML"
        )


@bot.message_handler(content_types=['voice', 'audio'])
def handle_voice_message(message):
    register_subscriber(message.chat.id)

    is_audio = False
    if message.voice:
        voice_id = message.voice.file_id
        duration = getattr(message.voice, 'duration', 0)
    elif message.audio:
        voice_id = message.audio.file_id
        duration = getattr(message.audio, 'duration', 0)
        is_audio = True
    else:
        return

    state = user_states.get(message.chat.id)
    action = state.get('action') if state else None
    if action == 'waiting_ai_voice_or_text':
        user_states.pop(message.chat.id, None)
        action = None

    # 1. Tezkor buyurtma (Tender) tavsifi ovozli xabar bo'lganda
    if action == 'order_desc':
        bot.send_chat_action(message.chat.id, 'typing')
        transcribed_text, media_url = transcribe_voice_file(voice_id)
        desc_text = f"🎤 Ovozli: \"{transcribed_text}\"" if transcribed_text else f"🎤 Ovozli xabar ({duration} soniya)"
        state['data']['voice_file_id'] = voice_id
        state['data']['is_audio'] = is_audio
        state['data']['desc'] = desc_text
        if media_url:
            state['data']['media_url'] = media_url
        user = get_or_create_tg_user(message.from_user)

        # Telefon bor bo'lsa raqam, bo'lmasa Telegram kontakti
        if user.phone:
            state['data']['phone'] = user.phone
        else:
            tg_nick = f"@{message.from_user.username}" if message.from_user.username else f"ID: {message.from_user.id}"
            state['data']['phone'] = f"Ovozda aytilgan (Telegram: {tg_nick})"

        # HECH QANDAY KUTISHSIZ: OVOZ TUSHISHI BILANOQ AVTOMATIK USTALARGA YUBORILADI!
        broadcast_quick_order(message.chat.id, state['data'])
        user_states.pop(message.chat.id, None)

        bot.send_message(
            message.chat.id,
            f"⚡️ <b>Ovozli xabaringiz ({duration} soniya) qabul qilindi va darhol barcha ustalarga yetkazildi!</b>\n"
            f"{f'📝 <i>\"{html.escape(transcribed_text)}\"</i>\n\n' if transcribed_text else '\n'}"
            f"Birinchi bo'lib qabul qilgan usta siz bilan tez orada bog'lanadi.",
            parse_mode="HTML",
            reply_markup=get_main_keyboard(message.chat.id)
        )
        return

    # 2. Mijozdan ustaga yuborilgan ovozli xabar (1-on-1 Chat)
    elif action == 'waiting_for_message':
        user_states.pop(message.chat.id, None)
        target_user_id = state['target_user_id']
        target_user = User.objects.filter(id=target_user_id).first()
        if not target_user:
            bot.send_message(message.chat.id, "Xatolik: Usta topilmadi.")
            return

        sender_user = get_or_create_tg_user(message.from_user)
        media_url = save_telegram_voice_to_media(voice_id)
        audio_hint = f"\n🎧 Ovozli xabar fayli: {media_url}" if media_url else ""
        Message.objects.create(
            sender=sender_user,
            receiver=target_user,
            text=f"[Telegram ovozli xabar: {duration} soniya]{audio_hint}",
            is_read=False
        )

        master_chat_id = master_tg_map.get(str(target_user.id))
        if master_chat_id:
            try:
                reply_markup = types.InlineKeyboardMarkup()
                btn_reply = types.InlineKeyboardButton("✍️ Mijozga javob yozish", callback_data=f"reply_to_client_{message.chat.id}")
                reply_markup.add(btn_reply)

                client_phone = sender_user.phone or "Kiritilmagan"
                tg_username = f"@{message.from_user.username}" if message.from_user.username else "Mavjud emas"

                caption = (
                    f"🔔 <b>MIJOZDAN OVOZLI XABAR KELDI!</b>\n\n"
                    f"👤 <b>Mijoz:</b> {message.from_user.full_name}\n"
                    f"📱 <b>Telegram:</b> {tg_username}\n"
                    f"📞 <b>Telefon:</b> <code>{client_phone}</code>\n"
                    f"⏱ Davomiyligi: <b>{duration} soniya</b>\n\n"
                    f"⚡️ <i>Quyidagi tugma orqali mijozga javob yozishingiz mumkin:</i>"
                )
                if is_audio:
                    bot.send_audio(master_chat_id, voice_id, caption=caption, parse_mode="HTML", reply_markup=reply_markup)
                else:
                    bot.send_voice(master_chat_id, voice_id, caption=caption, parse_mode="HTML", reply_markup=reply_markup)
            except Exception:
                pass

        bot.send_message(
            message.chat.id,
            f"✅ Ovozli xabaringiz <b>{target_user.full_name}</b> ga yetkazildi! Usta tez orada javob yozadi.",
            reply_markup=get_main_keyboard(message.chat.id)
        )
        return

    # 3. Ustadan mijozga yuborilgan ovozli javob
    elif action == 'master_replying_to_client':
        user_states.pop(message.chat.id, None)
        client_chat_id = state['client_chat_id']
        master_user = get_or_create_tg_user(message.from_user)
        master_obj = Master.objects.filter(user=master_user).first()
        master_name = master_obj.full_name if master_obj else message.from_user.full_name
        master_phone = master_user.phone or "Ko'rsatilmagan"

        try:
            caption = (
                f"📩 <b>Usta {master_name} dan ovozli javob:</b>\n"
                f"⏱ Davomiyligi: <b>{duration} soniya</b>\n"
                f"📞 <b>Aloqa:</b> <code>{master_phone}</code>"
            )
            if is_audio:
                bot.send_audio(client_chat_id, voice_id, caption=caption, parse_mode="HTML")
            else:
                bot.send_voice(client_chat_id, voice_id, caption=caption, parse_mode="HTML")
            bot.send_message(message.chat.id, "✅ Ovozli javobingiz mijozga yetkazildi!", reply_markup=get_main_keyboard(message.chat.id))
        except Exception:
            bot.send_message(message.chat.id, "⚠️ Mijozga ovozli xabar yetkazishda xatolik yuz berdi.", reply_markup=get_main_keyboard(message.chat.id))
        return

    # 4. TO'G'RIDAN-TO'G'RI YUBORILGAN OVOZLI XABAR (AI TEZKOR TAHLIL)
    bot.send_chat_action(message.chat.id, 'record_voice')
    transcribed_text, media_url = transcribe_voice_file(voice_id)

    user = get_or_create_tg_user(message.from_user)
    user_name = message.from_user.full_name or "Foydalanuvchi"
    user_nick = f"@{message.from_user.username}" if message.from_user.username else f"ID: {message.from_user.id}"
    phone = user.phone or f"Telegram: {user_nick}"

    # A) DARHOL ADMINGA MONITORING VA AUDIO NUSXANI YUBORISH:
    admin_direct_alert = (
        f"👑 <b>[ADMIN MONITORING] TO'G'RIDAN-TO'G'RI OVOZLI MUROJAAT!</b>\n"
        f"────────────────────────\n"
        f"👤 <b>Mijoz:</b> {html.escape(user_name)} ({user_nick}, ID: <code>{message.chat.id}</code>)\n"
        f"⏱ <b>Davomiyligi:</b> {duration} soniya\n"
        f"📞 <b>Aloqa:</b> <code>{phone}</code>\n"
        f"{f'📝 <b>Tahlil qilingan matn:</b> <i>\"{html.escape(transcribed_text)}\"</i>\n' if transcribed_text else ''}"
        f"────────────────────────\n"
        f"🎧 <i>Ovozli murojaat nusxasi:</i>"
    )
    for a_id in list(admin_ids):
        try:
            if is_audio:
                bot.send_audio(a_id, audio=voice_id, caption=admin_direct_alert, parse_mode="HTML")
            else:
                bot.send_voice(a_id, voice=voice_id, caption=admin_direct_alert, parse_mode="HTML")
        except Exception as err:
            print(f"Admin direct voice monitoring alert error: {err}")

    # B) AI ORQALI SOHA VA TUMANNI ANIQLASH:
    detected_cat, detected_dist = detect_intent_and_district(transcribed_text) if transcribed_text else (None, None)

    if detected_cat:
        cat = Category.objects.filter(is_active=True).filter(
            Q(name__icontains=detected_cat) | Q(slug__icontains=detected_cat)
        ).first()
        if not cat:
            cat = Category.objects.filter(is_active=True).filter(
                Q(name__icontains=detected_cat[:4]) | Q(slug__icontains=detected_cat[:4])
            ).first()

        if cat:
            final_dist = detected_dist or "Toshkent shahri"
            desc_val = f"🎤 Ovozli: \"{transcribed_text}\"" if transcribed_text else f"🎤 Ovozli xabar ({duration} soniya)"
            user_states[message.chat.id] = {
                'action': 'ai_detected_order',
                'data': {
                    'cat_id': cat.id,
                    'cat_name': cat.name,
                    'district': final_dist,
                    'desc': desc_val,
                    'phone': phone,
                    'voice_file_id': voice_id,
                    'is_audio': is_audio,
                    'media_url': media_url
                }
            }

            esc_text = html.escape(transcribed_text)

            if detected_dist:
                # 1. Tuman ovozdan aniq topilgan holat
                markup = types.InlineKeyboardMarkup(row_width=1)
                markup.add(types.InlineKeyboardButton(f"⚡️ {cat.name} ustalarga yuborish ({detected_dist})", callback_data="ai_confirm_order"))
                markup.add(types.InlineKeyboardButton("📍 Hududni o'zgartirish", callback_data="ai_change_dist"))
                markup.add(types.InlineKeyboardButton("🔄 Boshqa soha tanlash", callback_data="dvo_show_all_cats"))
                markup.add(types.InlineKeyboardButton("❌ Bekor qilish", callback_data="dvo_cancel"))

                bot.send_message(
                    message.chat.id,
                    f"🤖 <b>AI OVOZLI TEZKOR TAHLILI:</b>\n"
                    f"────────────────────────\n"
                    f"🎙 <b>Tinglangan matn:</b> <i>\"{esc_text}\"</i>\n"
                    f"⏱ <b>Davomiyligi:</b> {duration} soniya\n\n"
                    f"🛠 <b>Aniqlangan soha:</b> <b>{cat.name}</b>\n"
                    f"📍 <b>Aniqlangan hudud:</b> <b>{detected_dist}</b>\n"
                    f"────────────────────────\n"
                    f"⚡️ <i>Ovozli murojaatingiz va vazifa ushbu sohadagi barcha ustalarga darhol yetkazilsinmi?</i>",
                    parse_mode="HTML",
                    reply_markup=markup
                )
            else:
                # 2. Tuman ovozda eshitilmagan holat: 1 ta bosishda tuman tanlash tugmalari
                markup = types.InlineKeyboardMarkup(row_width=2)
                popular_districts = [
                    "Chilonzor tumani", "Yunusobod tumani",
                    "Mirzo Ulug'bek tumani", "Shayxontohur tumani",
                    "Yakkasaroy tumani", "Mirobod tumani",
                    "Sergeli tumani", "Olmazor tumani",
                    "Uchtepa tumani", "Yashnobod tumani"
                ]
                for d in popular_districts:
                    markup.add(types.InlineKeyboardButton(f"📍 {d.replace(' tumani', '')}", callback_data=f"ai_pick_dist_{d}"))
                markup.add(types.InlineKeyboardButton("🌐 Butun Toshkent bo'yicha yuborish", callback_data="ai_confirm_order"))
                markup.add(types.InlineKeyboardButton("🔄 Boshqa soha tanlash", callback_data="dvo_show_all_cats"))
                markup.add(types.InlineKeyboardButton("❌ Bekor qilish", callback_data="dvo_cancel"))

                bot.send_message(
                    message.chat.id,
                    f"🤖 <b>AI OVOZLI TEZKOR TAHLILI:</b>\n"
                    f"────────────────────────\n"
                    f"🎙 <b>Tinglangan matn:</b> <i>\"{esc_text}\"</i>\n"
                    f"⏱ <b>Davomiyligi:</b> {duration} soniya\n\n"
                    f"🛠 <b>Aniqlangan soha:</b> <b>{cat.name}</b>\n"
                    f"📍 <b>Hudud:</b> <i>Ovozda aytilmadi. Qaysi tumandasiz?</i>\n"
                    f"────────────────────────\n"
                    f"⚡️ <i>Tumaningizni 1 ta bosishda tanlang yoki butun shahar bo'yicha yuboring:</i>",
                    parse_mode="HTML",
                    reply_markup=markup
                )
            return

    # C) Foydalanuvchi holatini saqlash (Soha avtomatik aniqlanmagan taqdirda)
    user_states[message.chat.id] = {
        'action': 'dvo_category',
        'data': {
            'voice_file_id': voice_id,
            'is_audio': is_audio,
            'duration': duration,
            'desc': f"🎤 Ovozli: \"{transcribed_text}\"" if transcribed_text else f"🎤 Ovozli xabar ({duration} soniya)",
            'phone': phone,
            'user_name': user_name,
            'media_url': media_url
        }
    }

    # D) Foydalanuvchiga kategoriyalar tugmasini chiqarish
    cats = Category.objects.filter(is_active=True)
    if not cats.exists():
        bot.send_message(message.chat.id, "Hozircha xizmatlar mavjud emas.")
        return

    markup = types.InlineKeyboardMarkup(row_width=2)
    for c in cats:
        markup.add(types.InlineKeyboardButton(f"{c.name}", callback_data=f"dvocat_{c.id}"))
    markup.add(types.InlineKeyboardButton(t(message.chat.id, 'btn_cancel'), callback_data="dvo_cancel"))

    bot.send_message(
        message.chat.id,
        f"🎙 <b>Ovozli xabaringiz qabul qilindi ({duration} soniya)!</b>\n"
        f"{f'📝 <i>\"{html.escape(transcribed_text)}\"</i>\n\n' if transcribed_text else '\n'}"
        f"Vazifangizni kerakli ustalarga yo'llashimiz uchun, iltimos, <b>xizmat sohasini (mutaxassislik)</b> tanlang:",
        parse_mode="HTML",
        reply_markup=markup
    )


# ==========================================
# TO'G'RIDAN-TO'G'RI OVOZLI BUYURTMA CALLBACKS
# ==========================================
@bot.callback_query_handler(func=lambda call: call.data.startswith('dvocat_'))
def handle_dvo_category_selected(call):
    cat_id = int(call.data.split('_')[1])
    cat = Category.objects.filter(id=cat_id).first()
    if not cat:
        bot.answer_callback_query(call.id, "Kategoriya topilmadi.")
        return

    bot.answer_callback_query(call.id)
    state = user_states.get(call.message.chat.id)
    if not state or 'data' not in state:
        user = get_or_create_tg_user(call.from_user)
        user_nick = f"@{call.from_user.username}" if call.from_user.username else f"ID: {call.from_user.id}"
        phone = user.phone or f"Ovozda aytilgan ({user_nick})"
        state = {
            'action': 'dvo_district',
            'data': {
                'cat_id': cat_id,
                'cat_name': cat.name,
                'desc': '🎤 Ovozli xabar',
                'phone': phone,
                'voice_file_id': None,
                'is_audio': False
            }
        }
        user_states[call.message.chat.id] = state
    else:
        state['data']['cat_id'] = cat_id
        state['data']['cat_name'] = cat.name
        state['action'] = 'dvo_district'

    markup = types.InlineKeyboardMarkup(row_width=2)
    popular_districts = [
        "Yunusobod tumani", "Chilonzor tumani", "Mirzo Ulug'bek", 
        "Shayxontohur tumani", "Yakkasaroy tumani", "Sergeli tumani", 
        "Olmazor tumani", "Uchtepa tumani", "Yashnobod tumani"
    ]
    for d in popular_districts:
        markup.add(types.InlineKeyboardButton(f"📍 {d}", callback_data=f"dvodist_{cat_id}_{d[:15]}"))
    markup.add(types.InlineKeyboardButton("🌐 Barcha tumanlar (Toshkent)", callback_data=f"dvodist_{cat_id}_Toshkent"))
    markup.add(types.InlineKeyboardButton(t(call.message.chat.id, 'btn_cancel'), callback_data="dvo_cancel"))

    try:
        bot.edit_message_text(
            f"🛠 <b>Soha:</b> {cat.name}\n\n"
            f"📍 <b>Qaysi tumanda joylashgansiz?</b> Quyidagilardan tanlang:",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            parse_mode="HTML",
            reply_markup=markup
        )
    except Exception:
        bot.send_message(
            call.message.chat.id,
            f"🛠 <b>Soha:</b> {cat.name}\n\n📍 <b>Qaysi tumanda joylashgansiz?</b>",
            parse_mode="HTML",
            reply_markup=markup
        )


@bot.callback_query_handler(func=lambda call: call.data.startswith('dvodist_'))
def handle_dvo_district_selected(call):
    parts = call.data.split('_', 2)
    cat_id = int(parts[1])
    district = parts[2]
    bot.answer_callback_query(call.id, "Buyurtma yuborilmoqda...")

    state = user_states.get(call.message.chat.id)
    if not state or 'data' not in state:
        cat = Category.objects.filter(id=cat_id).first()
        cat_name = cat.name if cat else "Mutaxassis"
        user = get_or_create_tg_user(call.from_user)
        user_nick = f"@{call.from_user.username}" if call.from_user.username else f"ID: {call.from_user.id}"
        phone = user.phone or f"Ovozda aytilgan ({user_nick})"
        data = {
            'cat_id': cat_id,
            'cat_name': cat_name,
            'district': district,
            'desc': '🎤 Ovozli xabar',
            'phone': phone,
            'voice_file_id': None,
            'is_audio': False
        }
    else:
        data = state['data']
        data['district'] = district

    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass

    user_states.pop(call.message.chat.id, None)
    broadcast_quick_order(call.message.chat.id, data)


@bot.callback_query_handler(func=lambda call: call.data == "dvo_cancel")
def handle_dvo_cancel(call):
    bot.answer_callback_query(call.id, "Bekor qilindi.")
    user_states.pop(call.message.chat.id, None)
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass
    bot.send_message(call.message.chat.id, "Amal bekor qilindi.", reply_markup=get_main_keyboard(call.message.chat.id))


# ==========================================
# BAHOLASH TIZIMI (RATING)
# ==========================================
@bot.callback_query_handler(func=lambda call: call.data.startswith('rate_prep_'))
def handle_rate_prep(call):
    register_subscriber(call.message.chat.id)
    master_id = int(call.data.split('_')[2])
    master = Master.objects.filter(id=master_id).first()
    if not master:
        bot.answer_callback_query(call.id, "Usta topilmadi.")
        return

    bot.answer_callback_query(call.id)
    markup = types.InlineKeyboardMarkup(row_width=5)
    stars_buttons = [
        types.InlineKeyboardButton("1 ⭐", callback_data=f"set_rate_{master.id}_1"),
        types.InlineKeyboardButton("2 ⭐", callback_data=f"set_rate_{master.id}_2"),
        types.InlineKeyboardButton("3 ⭐", callback_data=f"set_rate_{master.id}_3"),
        types.InlineKeyboardButton("4 ⭐", callback_data=f"set_rate_{master.id}_4"),
        types.InlineKeyboardButton("5 ⭐", callback_data=f"set_rate_{master.id}_5"),
    ]
    markup.add(*stars_buttons)
    btn_cancel = types.InlineKeyboardButton(t(call.message.chat.id, 'btn_cancel'), callback_data=f"back_master_{master.id}")
    markup.add(btn_cancel)

    prompt = t(call.message.chat.id, 'rate_master_prompt', name=master.full_name)
    bot.send_message(call.message.chat.id, prompt, parse_mode="HTML", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith('set_rate_'))
def handle_set_rate(call):
    parts = call.data.split('_')
    master_id = int(parts[2])
    score = int(parts[3])

    master = Master.objects.filter(id=master_id).first()
    if not master:
        bot.answer_callback_query(call.id, "Usta topilmadi.")
        return

    user = get_or_create_tg_user(call.from_user)

    if master.user_id == user.id:
        bot.answer_callback_query(call.id, "Usta o'ziga baho bera olmaydi!", show_alert=True)
        return

    Rating.objects.update_or_create(
        user=user,
        master=master,
        defaults={'score': score}
    )
    master.refresh_from_db()

    master_chat_id = master_tg_map.get(str(master.user.id))
    if master_chat_id:
        try:
            bot.send_message(
                master_chat_id,
                f"⭐️ <b>Sizning profilingiz baholandi!</b>\n\n"
                f"👤 Baholagan: <b>{call.from_user.full_name}</b>\n"
                f"⭐️ Baho: <b>{score} yulduz</b>\n"
                f"📈 Yangi reytingingiz: <b>{master.average_rating} ⭐</b> ({master.ratings_count} ta baho)",
                parse_mode="HTML"
            )
        except Exception:
            pass

    bot.answer_callback_query(call.id, f"Siz {score} ⭐ baho berdingiz!", show_alert=True)
    success_text = t(call.message.chat.id, 'rating_success', name=master.full_name, score=score, avg=master.average_rating, count=master.ratings_count)

    try:
        bot.edit_message_text(
            success_text,
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            parse_mode="HTML"
        )
    except Exception:
        pass


@bot.callback_query_handler(func=lambda call: call.data.startswith('back_master_'))
def handle_back_master(call):
    master_id = int(call.data.split('_')[2])
    master = Master.objects.filter(id=master_id).first()
    bot.answer_callback_query(call.id)
    if master:
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception:
            pass


# ==========================================
# XABAR ALMASHISH (CHAT)
# ==========================================
@bot.callback_query_handler(func=lambda call: call.data.startswith('msg_to_'))
def handle_message_to_master(call):
    target_user_id = int(call.data.split('_')[2])
    target_user = User.objects.filter(id=target_user_id).first()

    if not target_user:
        bot.answer_callback_query(call.id, "Usta topilmadi.")
        return

    bot.answer_callback_query(call.id)
    user_states[call.message.chat.id] = {
        'action': 'waiting_for_message',
        'target_user_id': target_user_id,
        'target_name': target_user.full_name
    }

    prompt = t(call.message.chat.id, 'msg_prompt', name=target_user.full_name)
    bot.send_message(call.message.chat.id, prompt, parse_mode="HTML")


@bot.callback_query_handler(func=lambda call: call.data.startswith('reply_to_client_'))
def handle_reply_to_client_callback(call):
    client_chat_id = int(call.data.split('_')[3])
    bot.answer_callback_query(call.id)

    user_states[call.message.chat.id] = {
        'action': 'master_replying_to_client',
        'client_chat_id': client_chat_id
    }

    bot.send_message(
        call.message.chat.id,
        "✍️ <b>Mijozga javob xabaringizni yozing:</b>\n(Ushbu javob to'g'ridan-to'g'ri mijozning Telegramiga yuboriladi)",
        parse_mode="HTML"
    )


# ==========================================
# USTA ANKETASINING BOSQICHLARI
# ==========================================
def proceed_to_master_category(chat_id):
    markup = get_categories_markup()
    bot.send_message(
        chat_id,
        t(chat_id, 'reg_step_cat'),
        parse_mode="HTML",
        reply_markup=markup
    )


# ==========================================
# MATNLI XABARLAR VA STATE HANDLER
# ==========================================
@bot.message_handler(func=lambda msg: msg.chat.id in user_states)
def handle_user_states(message):
    state = user_states.get(message.chat.id)
    if not state:
        return

    action = state.get('action')

    # --- ADMIN USTA MA'LUMOTLARINI TAHRIRLASH ---
    if action == 'admin_saving_master_edit':
        user_states.pop(message.chat.id, None)
        master_id = state['master_id']
        field = state['field']
        master = Master.objects.filter(id=master_id).first()

        if not master:
            bot.send_message(message.chat.id, "Xatolik: Usta topilmadi.")
            return

        new_val = message.text.strip()

        if field == 'price':
            try:
                price = int(new_val.replace(" ", "").replace(",", ""))
                master.price = price
                master.save(update_fields=['price'])
                resp_text = f"✅ Usta narxi muvaffaqiyatli <b>{price:,} so'm</b> qilib o'zgartirildi!"
            except ValueError:
                resp_text = "❌ Xatolik: Narx faqat son bo'lishi kerak."

        elif field == 'phone':
            clean_phone = normalize_phone_number(new_val)
            master.user.phone = clean_phone
            master.user.save(update_fields=['phone'])
            resp_text = f"✅ Usta telefon raqami muvaffaqiyatli <b>{clean_phone}</b> ga yangilandi!"

        elif field == 'name':
            parts = new_val.split(maxsplit=1)
            master.user.first_name = parts[0]
            master.user.last_name = parts[1] if len(parts) > 1 else ""
            master.user.save(update_fields=['first_name', 'last_name'])
            resp_text = f"✅ Usta ismi muvaffaqiyatli <b>{master.full_name}</b> ga o'zgartirildi!"

        elif field == 'exp':
            try:
                exp = int(new_val)
                master.experience = exp
                master.save(update_fields=['experience'])
                resp_text = f"✅ Ish tajribasi muvaffaqiyatli <b>{exp} yil</b> qilib yangilandi!"
            except ValueError:
                resp_text = "❌ Xatolik: Tajriba faqat butun son bo'lishi kerak."

        elif field == 'desc':
            master.description = new_val
            master.save(update_fields=['description'])
            resp_text = f"✅ Usta xizmat tavsifi muvaffaqiyatli yangilandi!"

        bot.send_message(
            message.chat.id,
            f"{resp_text}\n\n<i>Ushbu o'zgarish darhol saytda va botda aks etdi.</i>",
            parse_mode="HTML",
            reply_markup=get_main_keyboard(message.chat.id)
        )
        text, markup = get_detailed_master_card(master, message.chat.id)
        bot.send_message(message.chat.id, text, parse_mode="HTML", reply_markup=markup)

    # --- ADMIN QIDIRUV ---
    elif action == 'admin_waiting_search_query':
        user_states.pop(message.chat.id, None)
        q = message.text.strip()
        users = User.objects.filter(
            Q(first_name__icontains=q) | Q(last_name__icontains=q) | Q(phone__icontains=q) | Q(email__icontains=q)
        )[:5]

        if not users.exists():
            bot.send_message(message.chat.id, f"🔍 '<b>{q}</b>' bo'yicha hech kim topilmadi.", parse_mode="HTML")
            return

        bot.send_message(message.chat.id, f"🔍 '<b>{q}</b>' bo'yicha qidiruv natijalari:", parse_mode="HTML")
        for u in users:
            role_txt = "Usta 👷‍♂️" if u.role == 'master' else "Mijoz 👤"
            txt = (
                f"👤 <b>{u.full_name}</b> (Rol: {role_txt})\n"
                f"📞 Tel: <code>{u.phone or 'Mavjud emas'}</code>\n"
                f"✉️ Email: <code>{u.email or 'Mavjud emas'}</code>"
            )
            markup = types.InlineKeyboardMarkup()
            if u.role == 'master' and hasattr(u, 'master_profile'):
                m = u.master_profile
                btn_del = types.InlineKeyboardButton("🗑 Ustani o'chirish", callback_data=f"adm_del_m_confirm_{m.id}")
            else:
                btn_del = types.InlineKeyboardButton("🗑 Mijozni o'chirish", callback_data=f"adm_del_u_confirm_{u.id}")
            markup.add(btn_del)
            bot.send_message(message.chat.id, txt, parse_mode="HTML", reply_markup=markup)

    # --- USTA RO'YXATDAN O'TISH BOSQICHLARI ---
    elif action == 'reg_master_name':
        names = message.text.strip().split(maxsplit=1)
        first_name = names[0]
        last_name = names[1] if len(names) > 1 else ""
        state['data']['first_name'] = first_name
        state['data']['last_name'] = last_name

        state['action'] = 'reg_master_phone'
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        btn_phone = types.KeyboardButton(t(message.chat.id, 'btn_share_phone'), request_contact=True)
        btn_cancel = types.KeyboardButton(t(message.chat.id, 'btn_cancel'))
        markup.add(btn_phone)
        markup.add(btn_cancel)

        bot.send_message(
            message.chat.id,
            t(message.chat.id, 'reg_step_phone', name=first_name),
            parse_mode="HTML",
            reply_markup=markup
        )

    elif action == 'reg_master_phone':
        raw_phone = message.text.strip()
        clean_phone = normalize_phone_number(raw_phone)
        if len(clean_phone) < 9:
            bot.send_message(message.chat.id, "Iltimos, to'g'ri telefon raqam kiriting (masalan: +998901234567):")
            return
        state['data']['phone'] = clean_phone
        state['action'] = 'reg_master_category'
        proceed_to_master_category(message.chat.id)

    elif action == 'reg_master_region':
        selected_reg = message.text.strip()
        state['data']['region'] = selected_reg

        districts = REGION_DISTRICTS.get(selected_reg)
        if districts:
            state['action'] = 'reg_master_district'
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2, one_time_keyboard=True)
            for d in districts:
                markup.add(types.KeyboardButton(d))
            markup.add(types.KeyboardButton("Markaziy hudud"))
            markup.add(types.KeyboardButton(t(message.chat.id, 'btn_cancel')))

            bot.send_message(
                message.chat.id,
                t(message.chat.id, 'reg_step_dist'),
                parse_mode="HTML",
                reply_markup=markup
            )
        else:
            state['data']['district'] = 'Markaz'
            state['action'] = 'reg_master_experience'
            bot.send_message(
                message.chat.id,
                t(message.chat.id, 'reg_step_exp'),
                parse_mode="HTML",
                reply_markup=types.ReplyKeyboardRemove()
            )

    elif action == 'reg_master_district':
        state['data']['district'] = message.text.strip()
        state['action'] = 'reg_master_experience'
        bot.send_message(
            message.chat.id,
            t(message.chat.id, 'reg_step_exp'),
            parse_mode="HTML",
            reply_markup=types.ReplyKeyboardRemove()
        )

    elif action == 'reg_master_experience':
        try:
            exp = int(message.text.strip())
        except ValueError:
            exp = 1
        state['data']['experience'] = exp
        state['action'] = 'reg_master_price'
        bot.send_message(
            message.chat.id,
            t(message.chat.id, 'reg_step_price'),
            parse_mode="HTML"
        )

    elif action == 'reg_master_price':
        try:
            price = int(message.text.strip().replace(" ", "").replace(",", ""))
        except ValueError:
            price = 50000
        state['data']['price'] = price
        state['action'] = 'reg_master_description'
        bot.send_message(
            message.chat.id,
            t(message.chat.id, 'reg_step_desc'),
            parse_mode="HTML"
        )

    elif action == 'reg_master_description':
        desc = message.text.strip()
        data = state['data']
        user_states.pop(message.chat.id, None)

        try:
            category = Category.objects.get(id=data['category_id'])
        except Category.DoesNotExist:
            category = Category.objects.first()

        user = get_or_create_tg_user(message.from_user, phone=data.get('phone'))
        user.first_name = data.get('first_name') or user.first_name
        user.last_name = data.get('last_name') or user.last_name
        if data.get('phone'):
            user.phone = data.get('phone')
        user.role = 'master'
        user.save()

        master, created = Master.objects.update_or_create(
            user=user,
            defaults={
                'category': category,
                'description': desc,
                'experience': data.get('experience', 1),
                'price': data.get('price', 50000),
                'region': data.get('region', 'Toshkent shahri'),
                'district': data.get('district', 'Markaz'),
                'status': 'active'
            }
        )

        save_master_tg_id(user.id, message.chat.id)

        bot.send_message(
            message.chat.id,
            t(message.chat.id, 'reg_success'),
            parse_mode="HTML",
            reply_markup=get_main_keyboard(message.chat.id)
        )
        text, markup = get_detailed_master_card(master, message.chat.id)
        bot.send_message(message.chat.id, text, parse_mode="HTML", reply_markup=markup)

    # --- USTANING MIJOZGA JAVOB YOZISHI ---
    elif action == 'master_replying_to_client':
        user_states.pop(message.chat.id, None)
        client_chat_id = state['client_chat_id']

        master_user = get_or_create_tg_user(message.from_user)
        master_obj = Master.objects.filter(user=master_user).first()
        master_name = master_obj.full_name if master_obj else message.from_user.full_name
        master_phone = master_user.phone or "Ko'rsatilmagan"

        try:
            bot.send_message(
                client_chat_id,
                f"📩 <b>Usta {master_name} javobi:</b>\n\n"
                f"💬 <i>\"{message.text}\"</i>\n\n"
                f"📞 <b>Aloqa:</b> <code>{master_phone}</code>",
                parse_mode="HTML"
            )
            bot.send_message(message.chat.id, "✅ Javobingiz mijozga yetkazildi!", reply_markup=get_main_keyboard(message.chat.id))
        except Exception:
            bot.send_message(message.chat.id, "⚠️ Mijozga xabar yetkazishda xatolik yuz berdi.", reply_markup=get_main_keyboard(message.chat.id))

    # --- MIJOZNING USTAGA XABAR YUBORISHI ---
    elif action == 'waiting_for_message':
        user_states.pop(message.chat.id, None)
        target_user_id = state['target_user_id']
        target_user = User.objects.filter(id=target_user_id).first()
        if not target_user:
            bot.send_message(message.chat.id, "Xatolik: Usta topilmadi.")
            return

        sender_user = get_or_create_tg_user(message.from_user)

        Message.objects.create(
            sender=sender_user,
            receiver=target_user,
            text=f"[Telegramdan: @{message.from_user.username or message.from_user.first_name}]: {message.text}",
            is_read=False
        )

        master_chat_id = master_tg_map.get(str(target_user.id))

        if master_chat_id:
            try:
                reply_markup = types.InlineKeyboardMarkup()
                btn_reply = types.InlineKeyboardButton("✍️ Mijozga javob yozish", callback_data=f"reply_to_client_{message.chat.id}")
                reply_markup.add(btn_reply)

                client_phone = sender_user.phone or "Kiritilmagan"
                tg_username = f"@{message.from_user.username}" if message.from_user.username else "Mavjud emas"

                bot.send_message(
                    master_chat_id,
                    f"🔔 <b>YANGI MIJOZDAN XABAR KELDI!</b>\n\n"
                    f"👤 <b>Mijoz:</b> {message.from_user.full_name}\n"
                    f"📱 <b>Telegram:</b> {tg_username}\n"
                    f"📞 <b>Telefon:</b> <code>{client_phone}</code>\n\n"
                    f"💬 <b>Xabar matni:</b>\n<i>\"{message.text}\"</i>\n\n"
                    "⚡️ <i>Quyidagi tugma orqali mijozga darhol javob yozishingiz mumkin:</i>",
                    parse_mode="HTML",
                    reply_markup=reply_markup
                )
            except Exception:
                pass

        bot.send_message(
            message.chat.id,
            t(message.chat.id, 'msg_sent', name=target_user.full_name),
            parse_mode="HTML",
            reply_markup=get_main_keyboard(message.chat.id)
        )

    # --- RASSILKA ---
    elif action == 'waiting_for_broadcast':
        user_states.pop(message.chat.id, None)
        sent_count = 0
        fail_count = 0
        bot.send_message(message.chat.id, "⏳ Xabar barcha foydalanuvchilarga yuborilmoqda...")

        for sub_id in list(subscribers):
            try:
                bot.copy_message(chat_id=sub_id, from_chat_id=message.chat.id, message_id=message.message_id)
                sent_count += 1
            except Exception:
                fail_count += 1

        bot.send_message(
            message.chat.id,
            f"✅ <b>Xabar tarqatish yakunlandi!</b>\n\n"
            f"• Yetib bordi: <b>{sent_count} ta</b>\n"
            f"• Yetib bormadi (bloklaganlar): <b>{fail_count} ta</b>",
            parse_mode="HTML",
            reply_markup=get_main_keyboard(message.chat.id)
        )

    # --- TEZKOR AI OVOZLI YOKI MATNLI BUYURTMA ---
    elif action == 'waiting_ai_voice_or_text':
        user_states.pop(message.chat.id, None)
        handle_fallback_text(message)
        return

    # --- PORTFOLIO NOMI VA TAVSIFI ---
    elif action == 'waiting_portfolio_title':
        title = message.text.strip()
        state['data']['title'] = title
        state['action'] = 'waiting_portfolio_desc'
        bot.send_message(
            message.chat.id,
            f"✅ Ish nomi: <b>{title}</b>\n\nEndi ushbu ish haqida <b>qisqacha tavsif</b> kiriting:\n(Masalan: <i>Barcha sanitariya quvurlari yangilandi, kafolat berildi</i>)",
            parse_mode="HTML"
        )

    elif action == 'waiting_portfolio_desc':
        desc = message.text.strip()
        master_id = state['data']['master_id']
        title = state['data']['title']
        image_rel = state['data'].get('image_rel')
        user_states.pop(message.chat.id, None)

        master = Master.objects.filter(id=master_id).first()
        if master:
            PortfolioWork.objects.create(
                master=master,
                title=title,
                description=desc,
                image=image_rel
            )
            bot.send_message(
                message.chat.id,
                f"🎉 <b>Yangi ish namunasi muvaffaqiyatli saqlandi!</b>\n\n"
                f"🖼 <b>{title}</b>\n\n"
                f"U darhol profilingizda, portfoliongizda va veb-saytda aks etdi.",
                parse_mode="HTML",
                reply_markup=get_main_keyboard(message.chat.id)
            )
        else:
            bot.send_message(message.chat.id, "Xatolik: Usta topilmadi.", reply_markup=get_main_keyboard(message.chat.id))

    # --- TEZKOR BUYURTMA (TENDER) BOSQICHLARI ---
    elif action == 'order_district':
        dist = message.text.strip()
        state['data']['district'] = dist
        state['action'] = 'order_desc'
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add(types.KeyboardButton(t(message.chat.id, 'btn_cancel')))
        bot.send_message(
            message.chat.id,
            t(message.chat.id, 'order_step_desc'),
            parse_mode="HTML",
            reply_markup=markup
        )

    elif action == 'order_desc':
        desc = message.text.strip()
        state['data']['desc'] = desc
        user = get_or_create_tg_user(message.from_user)

        if user.phone:
            state['data']['phone'] = user.phone
            broadcast_quick_order(message.chat.id, state['data'])
            user_states.pop(message.chat.id, None)
        else:
            state['action'] = 'order_phone'
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
            markup.add(types.KeyboardButton(t(message.chat.id, 'btn_share_phone'), request_contact=True))
            markup.add(types.KeyboardButton(t(message.chat.id, 'btn_cancel')))
            bot.send_message(
                message.chat.id,
                t(message.chat.id, 'order_step_phone'),
                parse_mode="HTML",
                reply_markup=markup
            )

    elif action == 'order_phone':
        raw_phone = message.text.strip()
        if "Ovozda" in raw_phone or "O'tkazish" in raw_phone or "Skip" in raw_phone or "Пропустить" in raw_phone:
            tg_nick = f"@{message.from_user.username}" if message.from_user.username else f"ID: {message.from_user.id}"
            state['data']['phone'] = f"Ovozda aytilgan ({tg_nick})"
            broadcast_quick_order(message.chat.id, state['data'])
            user_states.pop(message.chat.id, None)
            return

        clean_phone = normalize_phone_number(raw_phone)
        if len(clean_phone) < 9:
            bot.send_message(message.chat.id, "Iltimos, to'g'ri telefon raqam kiriting (masalan: +998901234567):")
            return
        state['data']['phone'] = clean_phone
        user = get_or_create_tg_user(message.from_user)
        user.phone = clean_phone
        user.save(update_fields=['phone'])
        broadcast_quick_order(message.chat.id, state['data'])
        user_states.pop(message.chat.id, None)

    # --- YANGI KATEGORIYA QO'SHISH ---
    elif action == 'waiting_for_category_name':
        user_states.pop(message.chat.id, None)
        cat_name = message.text.strip()
        slug = slugify(cat_name) or f"cat-{Category.objects.count() + 1}"

        category, created = Category.objects.get_or_create(
            slug=slug,
            defaults={'name': cat_name, 'is_active': True}
        )
        if created:
            bot.send_message(
                message.chat.id,
                f"✅ Yangi kategoriya muvaffaqiyatli qo'shildi: <b>{category.name}</b>\n"
                "U darhol saytda va botda paydo bo'ldi!",
                parse_mode="HTML",
                reply_markup=get_main_keyboard(message.chat.id)
            )
        else:
            bot.send_message(message.chat.id, f"⚠️ Ushbu kategoriya allaqachon mavjud: {category.name}")


@bot.message_handler(func=lambda msg: True, content_types=['text'])
def handle_fallback_text(message):
    register_subscriber(message.chat.id)
    user_text = message.text.strip()

    # 1. 🤖 AI INTELLEKTUAL TAHLILI (Soha va Tuman)
    detected_cat, detected_dist = detect_intent_and_district(user_text)
    if detected_cat:
        cat = Category.objects.filter(is_active=True).filter(
            Q(name__icontains=detected_cat) | Q(slug__icontains=detected_cat)
        ).first()
        if not cat:
            cat = Category.objects.filter(is_active=True).filter(
                Q(name__icontains=detected_cat[:4]) | Q(slug__icontains=detected_cat[:4])
            ).first()
        if cat:
            user = get_or_create_tg_user(message.from_user)
            user_nick = f"@{message.from_user.username}" if message.from_user.username else f"ID: {message.from_user.id}"
            phone = user.phone or f"Telegram: {user_nick}"
            final_dist = detected_dist or "Toshkent shahri"

            user_states[message.chat.id] = {
                'action': 'ai_detected_order',
                'data': {
                    'cat_id': cat.id,
                    'cat_name': cat.name,
                    'district': final_dist,
                    'desc': user_text,
                    'phone': phone
                }
            }

            esc_text = html.escape(user_text)

            if detected_dist:
                markup = types.InlineKeyboardMarkup(row_width=1)
                markup.add(types.InlineKeyboardButton(f"⚡️ {cat.name} ustalarga yuborish ({detected_dist})", callback_data="ai_confirm_order"))
                markup.add(types.InlineKeyboardButton("📍 Hududni o'zgartirish", callback_data="ai_change_dist"))
                markup.add(types.InlineKeyboardButton("🔄 Boshqa soha tanlash", callback_data="dvo_show_all_cats"))
                markup.add(types.InlineKeyboardButton("❌ Bekor qilish", callback_data="dvo_cancel"))

                bot.send_message(
                    message.chat.id,
                    f"🤖 <b>AI TEZKOR TAHLILI:</b>\n"
                    f"────────────────────────\n"
                    f"Sizning murojaatingiz tahlil qilindi va quyidagi xizmat turi aniqlandi:\n\n"
                    f"🛠 <b>Kerakli soha:</b> <b>{cat.name}</b>\n"
                    f"📍 <b>Aniqlangan hudud:</b> <b>{detected_dist}</b>\n"
                    f"📝 <b>Vazifa:</b> <i>\"{esc_text}\"</i>\n"
                    f"────────────────────────\n"
                    f"⚡️ <i>Ushbu buyurtmani zudlik bilan barcha faol ustalarga tarqatishni tasdiqlaysizmi?</i>",
                    parse_mode="HTML",
                    reply_markup=markup
                )
            else:
                markup = types.InlineKeyboardMarkup(row_width=2)
                popular_districts = [
                    "Chilonzor tumani", "Yunusobod tumani",
                    "Mirzo Ulug'bek tumani", "Shayxontohur tumani",
                    "Yakkasaroy tumani", "Mirobod tumani",
                    "Sergeli tumani", "Olmazor tumani",
                    "Uchtepa tumani", "Yashnobod tumani"
                ]
                for d in popular_districts:
                    markup.add(types.InlineKeyboardButton(f"📍 {d.replace(' tumani', '')}", callback_data=f"ai_pick_dist_{d}"))
                markup.add(types.InlineKeyboardButton("🌐 Butun Toshkent bo'yicha yuborish", callback_data="ai_confirm_order"))
                markup.add(types.InlineKeyboardButton("🔄 Boshqa soha tanlash", callback_data="dvo_show_all_cats"))
                markup.add(types.InlineKeyboardButton("❌ Bekor qilish", callback_data="dvo_cancel"))

                bot.send_message(
                    message.chat.id,
                    f"🤖 <b>AI TEZKOR TAHLILI:</b>\n"
                    f"────────────────────────\n"
                    f"Sizning murojaatingiz tahlil qilindi:\n\n"
                    f"🛠 <b>Kerakli soha:</b> <b>{cat.name}</b>\n"
                    f"📍 <b>Hudud:</b> <i>Xabarda aytilmadi. Qaysi tumandasiz?</i>\n"
                    f"📝 <b>Vazifa:</b> <i>\"{esc_text}\"</i>\n"
                    f"────────────────────────\n"
                    f"⚡️ <i>Tumaningizni 1 ta bosishda tanlang yoki butun shahar bo'yicha yuboring:</i>",
                    parse_mode="HTML",
                    reply_markup=markup
                )
            return

    # Agar maxsus soha aniqlanmasa, do'stona menyu chiqadi
    bot.send_message(
        message.chat.id,
        "Assalomu alaykum! Bot xizmatlaridan foydalanish uchun quyidagi menyulardan birini tanlang yoki <b>⚡️ Tezkor buyurtma</b> berish uchun mikrofonni bosib ovozli xabar qoldiring:",
        parse_mode="HTML",
        reply_markup=get_main_keyboard(message.chat.id)
    )


@bot.callback_query_handler(func=lambda call: call.data == "ai_confirm_order")
def handle_ai_confirm_order(call):
    state = user_states.get(call.message.chat.id)
    if not state or state.get('action') != 'ai_detected_order':
        bot.answer_callback_query(call.id, "Buyurtma muddati o'tgan yoki bekor qilingan.")
        return

    data = state['data']
    user_states.pop(call.message.chat.id, None)
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass

    bot.answer_callback_query(call.id, "Buyurtmangiz barcha ustalarga yuborilmoqda!")
    broadcast_quick_order(call.message.chat.id, data)


@bot.callback_query_handler(func=lambda call: call.data.startswith('ai_pick_dist_'))
def handle_ai_pick_dist(call):
    dist_name = call.data.replace('ai_pick_dist_', '')
    state = user_states.get(call.message.chat.id)
    if not state or state.get('action') != 'ai_detected_order':
        bot.answer_callback_query(call.id, "Buyurtma muddati o'tgan yoki bekor qilingan.", show_alert=True)
        return

    state['data']['district'] = dist_name
    data = state['data']
    user_states.pop(call.message.chat.id, None)

    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass

    bot.answer_callback_query(call.id, f"📍 {dist_name} tanlandi!")
    broadcast_quick_order(call.message.chat.id, data)


@bot.callback_query_handler(func=lambda call: call.data == "ai_change_dist")
def handle_ai_change_dist(call):
    bot.answer_callback_query(call.id)
    state = user_states.get(call.message.chat.id)
    if not state or state.get('action') != 'ai_detected_order':
        bot.send_message(call.message.chat.id, "Iltimos, qaytadan buyurtma bering.")
        return

    markup = types.InlineKeyboardMarkup(row_width=2)
    districts = [
        "Chilonzor tumani", "Yunusobod tumani",
        "Mirzo Ulug'bek tumani", "Shayxontohur tumani",
        "Yakkasaroy tumani", "Mirobod tumani",
        "Sergeli tumani", "Olmazor tumani",
        "Uchtepa tumani", "Yashnobod tumani"
    ]
    for d in districts:
        markup.add(types.InlineKeyboardButton(f"📍 {d.replace(' tumani', '')}", callback_data=f"ai_pick_dist_{d}"))
    markup.add(types.InlineKeyboardButton("🌐 Butun Toshkent bo'yicha yuborish", callback_data="ai_confirm_order"))
    markup.add(types.InlineKeyboardButton(t(call.message.chat.id, 'btn_cancel'), callback_data="dvo_cancel"))

    try:
        bot.edit_message_text(
            "📍 <b>O'zingiz joylashgan tumanni tanlang:</b>\n\n"
            "Tugmani bosishingiz bilan buyurtma darhol shu tuman ustalariga yetkaziladi:",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            parse_mode="HTML",
            reply_markup=markup
        )
    except Exception:
        pass


@bot.callback_query_handler(func=lambda call: call.data == "dvo_show_all_cats")
def handle_dvo_show_all_cats(call):
    bot.answer_callback_query(call.id)
    cats = Category.objects.filter(is_active=True)
    markup = types.InlineKeyboardMarkup(row_width=2)
    for c in cats:
        markup.add(types.InlineKeyboardButton(f"{c.name}", callback_data=f"dvocat_{c.id}"))
    markup.add(types.InlineKeyboardButton(t(call.message.chat.id, 'btn_cancel'), callback_data="dvo_cancel"))

    try:
        bot.edit_message_text(
            f"🛠 <b>Xizmat sohasini tanlang:</b>\n\nQaysi mutaxassislik bo'yicha usta kerak?",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            parse_mode="HTML",
            reply_markup=markup
        )
    except Exception:
        pass


if __name__ == '__main__':
    print("=" * 50, flush=True)
    print("Ustasi Telegram Bot (3 Tilda: UZ / RU / EN) ishga tushdi!", flush=True)
    print(f"Kategoriyalar soni: {Category.objects.count()}", flush=True)
    print(f"Ustalar soni: {Master.objects.count()}", flush=True)
    print("=" * 50, flush=True)

    # Telegram Menu Button ni sozlash
    try:
        bot.set_chat_menu_button(menu_button=types.MenuButtonDefault())
    except Exception as e:
        pass

    bot.infinity_polling(timeout=15, long_polling_timeout=10, skip_pending=True)
