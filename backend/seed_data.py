import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ustasi_core.settings')
django.setup()

from django.contrib.auth import get_user_model
from apps.masters.models import Category, Master, Service, Rating, PortfolioWork
from apps.chat.models import Message

User = get_user_model()

def seed():
    print("Baza tozalanmoqda va boshlang'ich ma'lumotlar yuklanmoqda...")

    # 1. Categories
    categories_data = [
        {
            "name": "Telefon ustasi",
            "slug": "phone-repair",
            "icon": "Smartphone",
            "description": "Smartfon, planshet, iPhone va Android telefonlarni ta'mirlash, ekran, plata va akkumulyator almashtirish xizmatlari.",
            "order": 1
        },
        {
            "name": "Elektrik",
            "slug": "electrician",
            "icon": "Zap",
            "description": "Xonadon, ofis va korxonalar uchun barcha turdagi elektr montaj, qisqa tutashuvlarni tuzatish va shit o'rnatish.",
            "order": 2
        },
        {
            "name": "Quruvchi",
            "slug": "builder",
            "icon": "Hammer",
            "description": "Qurilish, g'isht terish, suvoq, santexnika, kafelli va sifatli poydevor quyish ishlari.",
            "order": 3
        },
    ]

    cats = {}
    for c_data in categories_data:
        cat, _ = Category.objects.update_or_create(slug=c_data['slug'], defaults=c_data)
        cats[cat.slug] = cat
        print(f"Kategoriya: {cat.name}")

    # 1.5. Superuser (Admin)
    admin_user, _ = User.objects.update_or_create(
        phone="+998900000000",
        defaults={
            "first_name": "Admin",
            "last_name": "Ustasi",
            "email": "admin@ustasi.uz",
            "role": "admin",
            "is_staff": True,
            "is_superuser": True
        }
    )
    admin_user.set_password("admin123")
    admin_user.is_staff = True
    admin_user.is_superuser = True
    admin_user.save()
    print("Admin yaratildi: admin@ustasi.uz / admin123")

    # 2. Test Client Users
    client1, _ = User.objects.update_or_create(
        phone="+998901111111",
        defaults={
            "first_name": "Azizbek",
            "last_name": "Karimov",
            "email": "aziz@ustasi.uz",
            "role": "client"
        }
    )
    client1.set_password("password123")
    client1.save()

    client2, _ = User.objects.update_or_create(
        phone="+998902222222",
        defaults={
            "first_name": "Madina",
            "last_name": "Rahimova",
            "email": "madina@ustasi.uz",
            "role": "client"
        }
    )
    client2.set_password("password123")
    client2.save()

    # 3. Masters Data
    masters_info = [
        # --- Telefon ustalari ---
        {
            "phone": "+998903330001",
            "email": "jasur.phone@ustasi.uz",
            "first_name": "Jasur",
            "last_name": "Mirzayev",
            "category": cats["phone-repair"],
            "description": "10 yillik tajribaga ega sertifikatlangan iPhone va Samsung ustasi. Ekran, shleyf, plata chipi va batareyani 30 daqiqada almashtirib beraman. Kafolat 6 oy.",
            "experience": 10,
            "price": 50000,
            "region": "Toshkent shahri",
            "district": "Yunusobod tumani",
            "address": "Amir Temur shoh ko'chasi, 108-uy (Malika savdo majmuasi, A-15 do'kon)",
            "latitude": 41.3650,
            "longitude": 69.2880,
            "working_hours": "09:00 - 20:00 (Har kuni)",
            "services": [
                {"name": "Diagnostika qilish", "price": 30000},
                {"name": "Ekran (display) almashtirish", "price": 120000},
                {"name": "Original batareya o'rnatish", "price": 80000},
                {"name": "Plata payvandlash va mikrosxema", "price": 180000},
            ],
            "portfolio": [
                {"title": "iPhone 13 Pro original OLED ekran almashtirish", "description": "Siniq displey ehtiyotkorlik bilan olinib, TrueTone va FaceID funksiyalari to'liq saqlangan holda yangi original modul o'rnatildi."},
                {"title": "Samsung Galaxy S22 Ultra quvvat zanjirini tiklash", "description": "Suv tushishi oqibatida qisqa tutashgan mikrosxema mikroskop ostida qayta lehimlandi va batareya tekshirildi."}
            ],
            "reviews": [
                {"user": client1, "score": 5, "comment": "Ekranini juda sifatli va tez almashtirib berdi, tavsiya qilaman!"},
                {"user": client2, "score": 5, "comment": "Original batareya qo'ydi, kafolat berdi. Rahmat usta."}
            ]
        },
        {
            "phone": "+998903330002",
            "email": "sardor.fix@ustasi.uz",
            "first_name": "Sardor",
            "last_name": "Aliyev",
            "category": cats["phone-repair"],
            "description": "Xiaomi, Honor, Realme va barcha Android modellarni tezkor dasturiy va texnik tuzatish. Suv tushgan telefonlarni tozalash.",
            "experience": 6,
            "price": 40000,
            "region": "Toshkent shahri",
            "district": "Chilonzor tumani",
            "latitude": 41.2780,
            "longitude": 69.2050,
            "working_hours": "10:00 - 19:00 (Dush - Shan)",
            "services": [
                {"name": "Dasturiy proshivka (ROM)", "price": 50000},
                {"name": "Dinamik va mikrofon almashtirish", "price": 45000},
                {"name": "Zaryadlash uyasi (Type-C) ta'mirlash", "price": 60000},
            ],
            "reviews": [
                {"user": client1, "score": 4, "comment": "Yaxshi tuzatdi, ozgina kutdim lekin sifatli."}
            ]
        },
        {
            "phone": "+998903330003",
            "email": "sanjar.phone@ustasi.uz",
            "first_name": "Sanjar",
            "last_name": "Sobirov",
            "category": cats["phone-repair"],
            "description": "Samarqand shahrida eng ilg'or uskunalar bilan ta'minlangan telefon ustaxonasi. Har qanday murakkab nosozliklar.",
            "experience": 8,
            "price": 45000,
            "region": "Samarqand viloyati",
            "district": "Samarqand shahri",
            "latitude": 39.6542,
            "longitude": 66.9597,
            "working_hours": "08:30 - 19:00",
            "services": [
                {"name": "Smartfon to'liq tekshiruvi", "price": 25000},
                {"name": "Orqa qopqoq va oyna almashtirish", "price": 70000},
                {"name": "Kamera moduli ta'mirlash", "price": 90000},
            ],
            "reviews": [
                {"user": client2, "score": 5, "comment": "Samarqandda 1-raqamli telefon ustasi, qo'li yengil."}
            ]
        },

        # --- Elektriklar ---
        {
            "phone": "+998903330004",
            "email": "otabek.elektrik@ustasi.uz",
            "first_name": "Otabek",
            "last_name": "G'ofurov",
            "category": cats["electrician"],
            "description": "Yuqori toifali elektrik usta. Xonadon, novostroyka va kottejlarda noldan elektr montaji, shit yig'ish, stabilizator va generator ulash.",
            "experience": 12,
            "price": 80000,
            "region": "Toshkent shahri",
            "district": "Mirzo Ulug'bek tumani",
            "address": "Buyuk Ipak Yo'li ko'chasi, 45-uy (Maksim Gorkiy metro yaqinida)",
            "latitude": 41.3280,
            "longitude": 69.3350,
            "working_hours": "08:00 - 21:00 (Dam olishsiz)",
            "services": [
                {"name": "Chaqiruv va nosozlikni aniqlash", "price": 50000},
                {"name": "Elektr shitini yig'ish (avtomatlar)", "price": 150000},
                {"name": "Rozetka va viklyuchatel o'rnatish", "price": 25000},
                {"name": "Lyustra va LED chiroqlar montaji", "price": 70000},
                {"name": "To'liq xonadon elektr o'tkazish (1 xona)", "price": 600000}
            ],
            "portfolio": [
                {"title": "Yangi 4 xonali xonadonda to'liq elektr montaji", "description": "16 ta Schneider avtomatli zamonaviy xavfsiz elektr shiti yig'ildi va yashirin liniyalar tortildi."},
                {"title": "Katta ofis binosi uchun zaxira generator ulash", "description": "Elektr o'chganda avtomatik ishga tushadigan ATS bloki va kuchlanish stabilizatori o'rnatildi."}
            ],
            "reviews": [
                {"user": client1, "score": 5, "comment": "Uyimizdagi qisqa tutashuvni tezda topib hal qildi. Haqiqiy professional!"},
                {"user": client2, "score": 5, "comment": "Shitni tartibli qilib yig'ib berdi, materiallarni ham arzon topishga yordam berdi."}
            ]
        },
        {
            "phone": "+998903330005",
            "email": "sherzod.volt@ustasi.uz",
            "first_name": "Sherzod",
            "last_name": "Toshmatov",
            "category": cats["electrician"],
            "description": "Tezkor chaqiruvga boraman. Chilonzor, Uchtepa va Shayxontohur tumanlarida 30 daqiqada yetib borish imkoniyati.",
            "experience": 7,
            "price": 60000,
            "region": "Toshkent shahri",
            "district": "Shayxontohur tumani",
            "latitude": 41.3190,
            "longitude": 69.2300,
            "working_hours": "24/7 Shoshilinch xizmat",
            "services": [
                {"name": "Shoshilinch chaqiruv", "price": 60000},
                {"name": "Kabel trassasini tortish (metr)", "price": 10000},
                {"name": "Uchinchi faza ulash", "price": 120000},
            ],
            "reviews": [
                {"user": client1, "score": 4, "comment": "Kechasi kelib svetni yoqib berdi, rahmat!"}
            ]
        },
        {
            "phone": "+998903330006",
            "email": "farrux.elektrik@ustasi.uz",
            "first_name": "Farrux",
            "last_name": "Qosimov",
            "category": cats["electrician"],
            "description": "Farg'ona vodiysi bo'ylab sifatli elektr ishlari. Sanoat va xususiy sektorlar uchun xavfsiz elektr tizimlari.",
            "experience": 9,
            "price": 50000,
            "region": "Farg'ona viloyati",
            "district": "Farg'ona shahri",
            "latitude": 40.3842,
            "longitude": 71.7843,
            "working_hours": "09:00 - 18:00",
            "services": [
                {"name": "Shit o'rnatish", "price": 100000},
                {"name": "Kabel o'tkazish", "price": 15000},
            ],
            "reviews": []
        },

        # --- Quruvchilar ---
        {
            "phone": "+998903330007",
            "email": "bahodir.quruvchi@ustasi.uz",
            "first_name": "Bahodir",
            "last_name": "Ergashev",
            "category": cats["builder"],
            "description": "Brigada boshlig'i. 15 yillik tajribaga ega usta. Xususiy uylar, kottejlar, to'liq evrota'mirlash, kafel, shpaklyovka va gipsokarton ishlari.",
            "experience": 15,
            "price": 100000,
            "region": "Toshkent shahri",
            "district": "Yakkasaroy tumani",
            "address": "Shota Rustaveli ko'chasi, 64-uy",
            "latitude": 41.2850,
            "longitude": 69.2450,
            "working_hours": "08:00 - 19:00",
            "services": [
                {"name": "Kafel terish (kv.m)", "price": 80000},
                {"name": "Devor suvoq va shpaklyovka (kv.m)", "price": 35000},
                {"name": "G'isht terish (dona)", "price": 1500},
                {"name": "Laminat yotqizish (kv.m)", "price": 25000},
                {"name": "Noldan kottej qurish (kelishuv)", "price": 5000000}
            ],
            "portfolio": [
                {"title": "2 qavatli hovli uchun monolit poydevor va pishiq g'isht terish", "description": "M300 markali beton quyildi, 1-qavat pishiq g'ishtdan mustahkam qilib terib topshirildi."},
                {"title": "Kvartira hammomi va koridoriga 60x120 sm kafel yotqizish", "description": "Lazerli sath tekislagich yordamida sifatli granit plitkalar o'rnatildi."}
            ],
            "reviews": [
                {"user": client1, "score": 5, "comment": "Kafellarni tekis va ajoyib terdi. Ishiga javob beradigan usta."},
                {"user": client2, "score": 5, "comment": "Brigadasi intizomli, o'z vaqtida topshirdi."}
            ]
        },
        {
            "phone": "+998903330008",
            "email": "nodir.stroy@ustasi.uz",
            "first_name": "Nodir",
            "last_name": "Kamolov",
            "category": cats["builder"],
            "description": "Buxoro va Samarqandda sifatli santexnika va qurilish ta'mirlash xizmatlari. Sifat va kafolat.",
            "experience": 11,
            "price": 70000,
            "region": "Buxoro viloyati",
            "district": "Buxoro shahri",
            "latitude": 39.7747,
            "longitude": 64.4286,
            "working_hours": "08:30 - 18:30",
            "services": [
                {"name": "Issiq pol (tyopliy pol) montaji (kv.m)", "price": 60000},
                {"name": "Suvoq va kafel ishlari", "price": 70000},
            ],
            "reviews": [
                {"user": client1, "score": 5, "comment": "Buxoroda eng yaxshi quruvchi usta!"}
            ]
        }
    ]

    for m_info in masters_info:
        u, _ = User.objects.update_or_create(
            phone=m_info["phone"],
            defaults={
                "first_name": m_info["first_name"],
                "last_name": m_info["last_name"],
                "email": m_info["email"],
                "role": "master"
            }
        )
        u.set_password("password123")
        u.save()

        m, _ = Master.objects.update_or_create(
            user=u,
            defaults={
                "category": m_info["category"],
                "description": m_info["description"],
                "experience": m_info["experience"],
                "price": m_info["price"],
                "region": m_info["region"],
                "district": m_info["district"],
                "address": m_info.get("address", f"{m_info['district']}, Markaziy ko'cha 10-uy"),
                "latitude": m_info["latitude"],
                "longitude": m_info["longitude"],
                "working_hours": m_info["working_hours"],
                "status": "active"
            }
        )

        # Services
        m.services.all().delete()
        for s in m_info["services"]:
            Service.objects.create(master=m, name=s["name"], price=s["price"])

        # Portfolio (Bajarilgan ishlar)
        m.portfolio.all().delete()
        for p in m_info.get("portfolio", []):
            PortfolioWork.objects.create(
                master=m,
                title=p["title"],
                description=p.get("description", "")
            )

        # Reviews
        for r in m_info["reviews"]:
            Rating.objects.update_or_create(
                user=r["user"],
                master=m,
                defaults={"score": r["score"], "comment": r["comment"]}
            )
        m.update_rating_stats()
        print(f"Usta: {m.user.full_name} | {m.category.name} | Reyting: {m.average_rating} ({m.ratings_count} ta baho)")

    # 4. Sample messages
    master_jasur = Master.objects.filter(user__phone="+998903330001").first()
    if master_jasur:
        Message.objects.get_or_create(
            sender=client1,
            receiver=master_jasur.user,
            text="Assalomu alaykum Jasur aka! iPhone 13 ekranini almashtirish qancha vaqt oladi?",
            defaults={"is_read": True}
        )
        Message.objects.get_or_create(
            sender=master_jasur.user,
            receiver=client1,
            text="Va alaykum assalom! Taxminan 30-40 daqiqa vaqt oladi. Hozir ustaxonadaman, bemalol kelavering.",
            defaults={"is_read": True}
        )

    try:
        from seed_media import download_and_assign
        download_and_assign()
    except Exception as e:
        print("Media yuklashda xatolik:", e)

    print("Boshlang'ich ma'lumotlar muvaffaqiyatli saqlandi!")

if __name__ == '__main__':
    seed()
