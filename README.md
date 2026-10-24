# Ustasi - Ustalar va Mijozlar Platformasi

Ustasi — turli sohadagi malakali ustalarni topish, ularning xizmatlaridan foydalanish va to'g'ridan-to'g'ri bog'lanish uchun mo'ljallangan zamonaviy platforma.

## 🚀 Texnologiyalar

### Backend
- **Python 3.12+**
- **Django & Django REST Framework**
- **Simple JWT** (autentifikatsiya)
- **Django Filter & CORS Headers**
- **SQLite / PostgreSQL**

### Frontend
- **React 18**
- **TypeScript**
- **Vite**
- **Tailwind CSS**
- **Lucide React** (ikonkalar)

## 📁 Loyiha Strukturasi

```
Ustasi/
├── backend/            # Django REST API serveri
│   ├── apps/           # Loyiha ilovalari (users, masters, chat)
│   ├── ustasi_core/    # Django asosiy sozlamalari
│   ├── manage.py
│   └── requirements.txt
├── frontend/           # React + Vite frontend ilovasi
│   ├── src/
│   ├── package.json
│   └── vite.config.ts
└── README.md
```

## 🛠 O'rnatish va Ishga Tushirish

### 1. Backend sozlash
```bash
cd backend
python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
python manage.py migrate
python seed_data.py   # Test ma'lumotlarini yuklash
python manage.py runserver
```

### 2. Frontend sozlash
```bash
cd frontend
npm install
npm run dev
```

---
Ishlab chiqilgan: Ustasi jamoasi
