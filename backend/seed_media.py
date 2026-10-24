import os
import django
import urllib.request
from django.core.files.base import ContentFile

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ustasi_core.settings')
django.setup()

from django.contrib.auth import get_user_model
from apps.masters.models import Master, PortfolioWork

User = get_user_model()

# Curated high-quality, professional portraits & work photos
AVATAR_BY_PHONE = {
    # 1. Jasur Mirzayev - Phone repairer
    "+998903330001": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=500&auto=format&fit=crop&q=80",
    # 2. Sardor Aliyev - Phone technician
    "+998903330002": "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=500&auto=format&fit=crop&q=80",
    # 3. Sanjar Sobirov - Phone technician Samarqand
    "+998903330003": "https://images.unsplash.com/photo-1492562080023-ab3db95bfbce?w=500&auto=format&fit=crop&q=80",
    # 4. Otabek G'ofurov - Senior Electrician
    "+998903330004": "https://images.unsplash.com/photo-1621905251189-08b45d6a269e?w=500&auto=format&fit=crop&q=80",
    # 5. Sherzod Toshmatov - Electrician
    "+998903330005": "https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=500&auto=format&fit=crop&q=80",
    # 6. Farrux Qosimov - Electrician Farg'ona
    "+998903330006": "https://images.unsplash.com/photo-1519085360753-af0119f7cbe7?w=500&auto=format&fit=crop&q=80",
    # 7. Bahodir Ergashev - Builder / Brigadier
    "+998903330007": "https://images.unsplash.com/photo-1560250097-0b93528c311a?w=500&auto=format&fit=crop&q=80",
    # 8. Nodir Kamolov - Builder Samarqand
    "+998903330008": "https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?w=500&auto=format&fit=crop&q=80",
    # 9. Custom Master Jasur
    "+998993256897": "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=500&auto=format&fit=crop&q=80",
}

PORTFOLIO_IMAGE_MAP = {
    # Phone repair works
    "iPhone 13 Pro original OLED ekran almashtirish": "https://images.unsplash.com/photo-1588508065123-287b28e013da?w=800&auto=format&fit=crop&q=80",
    "Samsung Galaxy S22 Ultra quvvat zanjirini tiklash": "https://images.unsplash.com/photo-1581092160607-ee22621dd758?w=800&auto=format&fit=crop&q=80",
    "Xiaomi 12 Pro Type-C zaryadlash platasini almashtirish": "https://images.unsplash.com/photo-1597740985671-2a8a3b80532e?w=800&auto=format&fit=crop&q=80",
    "iPhone 12 Pro Max periskop kamera modulini ta'mirlash": "https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?w=800&auto=format&fit=crop&q=80",
    # Electrician works
    "Yangi kvartira uchun to'liq elektr shitini yig'ish (Schneider Electric)": "https://images.unsplash.com/photo-1558494949-ef010cbdcc31?w=800&auto=format&fit=crop&q=80",
    "Kottej yashirin LED va trekoviy yoritish tizimi": "https://images.unsplash.com/photo-1565814636199-ae8133055c1c?w=800&auto=format&fit=crop&q=80",
    "Xonadon kabel trassasi va rozetkalar montaji": "https://images.unsplash.com/photo-1621905252507-b35492cc74b4?w=800&auto=format&fit=crop&q=80",
    # Builder works
    "Vanna xonasi kafel va santexnika montaji": "https://images.unsplash.com/photo-1584622650111-993a426fbf0a?w=800&auto=format&fit=crop&q=80",
    "2 qavatli shaxsiy uy g'isht terish va to'liq qurilish": "https://images.unsplash.com/photo-1541888946425-d0fbb186156f?w=800&auto=format&fit=crop&q=80",
    "Suvoqli pol va sifatli issiq pol yotqizish": "https://images.unsplash.com/photo-1503387762-592deb58ef4e?w=800&auto=format&fit=crop&q=80",
}

def download_and_assign():
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    print("1. Ustalar uchun profil rasmlari yuklanmoqda...")
    for phone, img_url in AVATAR_BY_PHONE.items():
        try:
            user = User.objects.filter(phone=phone).first()
            if user:
                req = urllib.request.Request(img_url, headers=headers)
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = resp.read()
                    ext = "jpg"
                    file_name = f"avatar_{user.id}_{user.first_name.lower()}.{ext}"
                    user.avatar.save(file_name, ContentFile(data), save=True)
                    print(f" [OK] Avatar saqlandi: {user.full_name} -> {user.avatar.url}")
        except Exception as e:
            print(f" [XATO] Avatar yuklashda ({phone}): {e}")

    print("\n2. Bajarilgan ishlar (Portfolio) uchun fotosuratlar yuklanmoqda...")
    portfolio_images_keywords = [
        ("kafel", "https://images.unsplash.com/photo-1584622650111-993a426fbf0a?w=800&auto=format&fit=crop&q=80"),
        ("hovli", "https://images.unsplash.com/photo-1503387762-592deb58ef4e?w=800&auto=format&fit=crop&q=80"),
        ("qurilish", "https://images.unsplash.com/photo-1503387762-592deb58ef4e?w=800&auto=format&fit=crop&q=80"),
        ("elektr", "https://images.unsplash.com/photo-1558494949-ef010cbdcc31?w=800&auto=format&fit=crop&q=80"),
        ("generator", "https://images.unsplash.com/photo-1565814636199-ae8133055c1c?w=800&auto=format&fit=crop&q=80"),
        ("shit", "https://images.unsplash.com/photo-1558494949-ef010cbdcc31?w=800&auto=format&fit=crop&q=80"),
        ("oled", "https://images.unsplash.com/photo-1588508065123-287b28e013da?w=800&auto=format&fit=crop&q=80"),
        ("samsung", "https://images.unsplash.com/photo-1581092160607-ee22621dd758?w=800&auto=format&fit=crop&q=80"),
        ("ekran", "https://images.unsplash.com/photo-1588508065123-287b28e013da?w=800&auto=format&fit=crop&q=80"),
    ]

    for work in PortfolioWork.objects.all():
        img_to_use = None
        for kw, img_url in portfolio_images_keywords:
            if kw in work.title.lower() or kw in work.description.lower():
                img_to_use = img_url
                break
        if not img_to_use:
            img_to_use = "https://images.unsplash.com/photo-1581092160607-ee22621dd758?w=800&auto=format&fit=crop&q=80"
        
        try:
            req = urllib.request.Request(img_to_use, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = resp.read()
                file_name = f"portfolio_{work.id}.jpg"
                work.image.save(file_name, ContentFile(data), save=True)
                print(f" [OK] Portfolio saqlandi: '{work.title}' -> {work.image.url}")
        except Exception as e:
            print(f" [XATO] Portfolio ({work.title}): {e}")

    print("\nBarcha rasmlar muvaffaqiyatli yuklandi va bazaga biriktirildi!")

if __name__ == '__main__':
    download_and_assign()
