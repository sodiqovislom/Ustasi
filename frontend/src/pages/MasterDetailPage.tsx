import React, { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import {
  Star, MapPin, Phone, MessageSquare, Heart, ShieldCheck,
  Clock, Award, Wrench, ChevronLeft, Calendar, User, CheckCircle2,
  ExternalLink, Smartphone, Zap, Hammer, Briefcase, Camera, Eye
} from 'lucide-react';
import { api } from '../api/client';
import { Master, RatingItem } from '../types';
import { useAuth } from '../context/AuthContext';
import { CallModal } from '../components/CallModal';
import { RatingModal } from '../components/RatingModal';
import { TelegramAvatar } from '../components/TelegramAvatar';
import { PhotoViewerModal } from '../components/PhotoViewerModal';

export const MasterDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { isAuthenticated, user, openAuthModal, userCoords } = useAuth();

  const [master, setMaster] = useState<Master | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Modals
  const [isCallModalOpen, setIsCallModalOpen] = useState(false);
  const [isRatingModalOpen, setIsRatingModalOpen] = useState(false);
  const [isFavorite, setIsFavorite] = useState(false);
  const [selectedPortfolioItem, setSelectedPortfolioItem] = useState<{ url: string; title: string; desc?: string } | null>(null);

  useEffect(() => {
    const fetchMaster = async () => {
      if (!id) return;
      setIsLoading(true);
      setError(null);
      try {
        const data = await api.getMasterDetail(Number(id), userCoords || undefined);
        setMaster(data);
        setIsFavorite(data.is_favorite || false);
      } catch (err: any) {
        setError(err.message || "Ustani yuklashda xatolik yuz berdi.");
      } finally {
        setIsLoading(false);
      }
    };

    fetchMaster();
  }, [id, userCoords]);

  const handleFavoriteToggle = async () => {
    if (!master) return;
    if (!isAuthenticated) {
      openAuthModal("Ustalarni saqlab qo‘yish uchun tizimga kiring");
      return;
    }
    try {
      const nextFav = !isFavorite;
      setIsFavorite(nextFav);
      const res = await api.toggleFavorite(master.id);
      setIsFavorite(res.is_favorite);
    } catch (err) {
      console.error(err);
      setIsFavorite(isFavorite);
    }
  };

  const handleCallClick = () => {
    if (!isAuthenticated) {
      openAuthModal("Ustaga qo‘ng‘iroq qilish uchun tizimga kiring");
      return;
    }
    setIsCallModalOpen(true);
  };

  const handleChatClick = () => {
    if (!isAuthenticated) {
      openAuthModal("Usta bilan yozishish uchun tizimga kiring");
      return;
    }
    if (master) {
      navigate(`/chat?user_id=${master.user_id}`);
    }
  };

  const handleRateClick = () => {
    if (!isAuthenticated) {
      openAuthModal("Ustaga baho berish uchun tizimga kiring");
      return;
    }
    setIsRatingModalOpen(true);
  };

  const handleRatingSuccess = (updatedAvg: number, count: number) => {
    if (master) {
      setMaster({
        ...master,
        average_rating: updatedAvg,
        ratings_count: count,
        user_rated: true,
      });
    }
  };

  const getYandexMapUrl = () => {
    if (master?.latitude && master?.longitude) {
      return `https://yandex.uz/map-widget/v1/?ll=${master.longitude}%2C${master.latitude}&z=15&pt=${master.longitude}%2C${master.latitude},pm2rdm`;
    }
    const query = `${master?.address ? master.address + ', ' : ''}${master?.district || ''} ${master?.region || 'Toshkent'}`.trim();
    return `https://yandex.uz/map-widget/v1/?text=${encodeURIComponent(query)}&z=14`;
  };

  const getYandexExternalUrl = () => {
    if (master?.latitude && master?.longitude) {
      return `https://yandex.uz/maps/?pt=${master.longitude},${master.latitude}&z=15&l=map`;
    }
    const query = `${master?.address ? master.address + ', ' : ''}${master?.district || ''} ${master?.region || 'Toshkent'}`.trim();
    return `https://yandex.uz/maps/?text=${encodeURIComponent(query)}`;
  };

  if (isLoading) {
    return (
      <div className="max-w-5xl mx-auto px-4 py-12">
        <div className="animate-pulse space-y-6">
          <div className="h-48 bg-slate-200 rounded-3xl" />
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="md:col-span-2 h-64 bg-slate-100 rounded-3xl" />
            <div className="h-64 bg-slate-100 rounded-3xl" />
          </div>
        </div>
      </div>
    );
  }

  if (error || !master) {
    return (
      <div className="max-w-md mx-auto px-4 py-20 text-center space-y-4">
        <div className="w-16 h-16 bg-red-50 text-red-500 rounded-2xl flex items-center justify-center mx-auto">
          <Wrench className="w-8 h-8" />
        </div>
        <h2 className="text-xl font-bold text-slate-900">Usta topilmadi</h2>
        <p className="text-xs text-slate-500">{error || "Bunday usta mavjud emas yoki o‘chirilgan."}</p>
        <Link
          to="/masters"
          className="inline-flex items-center gap-1.5 px-4 py-2 bg-blue-600 text-white font-bold text-xs rounded-xl"
        >
          <ChevronLeft className="w-4 h-4" />
          Katalogga qaytish
        </Link>
      </div>
    );
  }

  const avgRating = Number(master.average_rating) || 0;
  const isSelf = user?.id === master.user_id;

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      
      {/* Breadcrumb Navigation */}
      <div className="flex items-center gap-2 text-xs text-slate-500">
        <Link to="/" className="hover:text-blue-600 transition">Bosh sahifa</Link>
        <span>/</span>
        <Link to="/masters" className="hover:text-blue-600 transition">Ustalar</Link>
        <span>/</span>
        <span className="text-slate-900 font-semibold truncate max-w-[200px]">{master.full_name}</span>
      </div>

      {/* HEADER BANNER / PROFILE OVERVIEW */}
      <div className="bg-white rounded-3xl p-6 sm:p-8 border border-slate-200/80 shadow-sm relative overflow-hidden">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
          
          <div className="flex flex-col sm:flex-row items-start sm:items-center gap-5">
            {/* Telegram-style Circular Avatar with Story Ring and Status */}
            <div className="relative shrink-0">
              <TelegramAvatar
                src={master.avatar_url}
                name={master.full_name}
                size="2xl"
                status={master.status}
                showStatus={true}
                hasStoryRing={true}
                clickable={true}
                subtitle={`${master.category.name} • ${master.district ? master.district + ', ' : ''}${master.region}`}
              />
            </div>

            {/* Basic Identity */}
            <div className="space-y-1.5">
              <div className="flex items-center gap-2 flex-wrap">
                <h1 className="text-2xl sm:text-3xl font-black text-slate-900 tracking-tight">
                  {master.full_name}
                </h1>
                {master.ratings_count >= 1 && (
                  <span title="Tasdiqlangan mutaxassis">
                    <ShieldCheck className="w-6 h-6 text-emerald-500" />
                  </span>
                )}
                <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold ${
                  master.status === 'active'
                    ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                    : 'bg-amber-50 text-amber-700 border border-amber-200'
                }`}>
                  {master.status === 'active' ? 'Buyurtmaga tayyor' : 'Band'}
                </span>
              </div>

              <div className="flex items-center gap-3 text-xs text-slate-600 flex-wrap">
                <span className="font-bold text-blue-600 bg-blue-50 px-2.5 py-1 rounded-lg">
                  {master.category.name}
                </span>
                <span className="flex items-center gap-1 font-medium text-slate-500">
                  <Award className="w-4 h-4 text-slate-400" />
                  {master.experience} yil ish tajribasi
                </span>
                <span className="flex items-center gap-1 font-medium text-slate-500">
                  <MapPin className="w-4 h-4 text-slate-400" />
                  {master.district ? `${master.district}, ` : ''}{master.region}
                </span>
              </div>
            </div>
          </div>

          {/* Quick Header Actions: Favorite & Rating overview */}
          <div className="flex items-center gap-3 self-end md:self-center">
            <button
              onClick={handleFavoriteToggle}
              className={`p-3 rounded-2xl border transition ${
                isFavorite
                  ? 'border-rose-200 bg-rose-50 text-rose-500'
                  : 'border-slate-200 bg-white text-slate-400 hover:text-rose-500 hover:bg-slate-50'
              }`}
              title="Saqlab qo‘yish"
            >
              <Heart className={`w-5 h-5 ${isFavorite ? 'fill-rose-500 text-rose-500' : ''}`} />
            </button>

            <div className="bg-amber-50 border border-amber-200/80 px-4 py-2.5 rounded-2xl text-center">
              <div className="flex items-center justify-center gap-1 font-black text-base text-amber-900">
                <Star className="w-4 h-4 fill-amber-400 text-amber-400" />
                <span>{avgRating > 0 ? avgRating.toFixed(1) : "Yangi"}</span>
              </div>
              <span className="text-[10px] text-amber-700 font-semibold block">
                {master.ratings_count} ta baho
              </span>
            </div>
          </div>

        </div>
      </div>

      {/* TWO-COLUMN DETAILS LAYOUT */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* LEFT COLUMN: Main details (Asosiy ma'lumot, Xizmatlar, Lokatsiya, Sharhlar) */}
        <div className="lg:col-span-2 space-y-6">
          
          {/* 1. ASOSIY MA'LUMOT */}
          <section className="bg-white rounded-3xl p-6 border border-slate-200/80 shadow-sm space-y-4">
            <h2 className="text-base font-black text-slate-900 tracking-tight flex items-center gap-2">
              <User className="w-4 h-4 text-blue-600" />
              Asosiy ma’lumot
            </h2>
            <p className="text-xs sm:text-sm text-slate-700 leading-relaxed whitespace-pre-line">
              {master.description}
            </p>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2 border-t border-slate-100">
              <div className="bg-slate-50 p-3 rounded-2xl">
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
                  Ish vaqti
                </span>
                <span className="text-xs font-bold text-slate-800 flex items-center gap-1.5 mt-0.5">
                  <Clock className="w-3.5 h-3.5 text-blue-600" />
                  {master.working_hours}
                </span>
              </div>
              <div className="bg-slate-50 p-3 rounded-2xl">
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
                  Boshlang‘ich xizmat qiymati
                </span>
                <span className="text-xs font-bold text-slate-800 flex items-center gap-1 mt-0.5">
                  {master.price.toLocaleString('uz-UZ')} so‘mdan
                </span>
              </div>
            </div>
          </section>

          {/* 2. XIZMATLAR VA NARXLAR */}
          <section className="bg-white rounded-3xl p-6 border border-slate-200/80 shadow-sm space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-base font-black text-slate-900 tracking-tight flex items-center gap-2">
                <Wrench className="w-4 h-4 text-blue-600" />
                Xizmatlar va narxlar
              </h2>
              <span className="text-xs font-semibold text-slate-400">
                {master.services.length} ta xizmat turi
              </span>
            </div>

            {master.services.length > 0 ? (
              <div className="divide-y divide-slate-100 border border-slate-100 rounded-2xl overflow-hidden">
                {master.services.map((srv, idx) => (
                  <div key={srv.id || idx} className="p-3.5 flex items-center justify-between hover:bg-slate-50 transition">
                    <span className="text-xs font-bold text-slate-800">
                      {srv.name}
                    </span>
                    <span className="text-xs font-extrabold text-blue-600 font-mono">
                      {srv.price.toLocaleString('uz-UZ')} so‘m
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-slate-500 py-3 text-center">
                Qo‘shimcha xizmatlar ro‘yxati kiritilmagan. Boshlang‘ich xizmat: {master.price.toLocaleString('uz-UZ')} so‘m.
              </p>
            )}
          </section>

          {/* 3. LOKATSIYA VA YANDEX KARTA */}
          <section className="bg-white rounded-3xl p-6 border border-slate-200/80 shadow-sm space-y-4">
            <div className="flex items-center justify-between flex-wrap gap-2">
              <h2 className="text-base font-black text-slate-900 tracking-tight flex items-center gap-2">
                <MapPin className="w-4 h-4 text-blue-600" />
                Lokatsiya va xizmat ko‘rsatish hududi
              </h2>
              <a
                href={getYandexExternalUrl()}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-red-50 hover:bg-red-100 text-red-600 text-xs font-bold rounded-xl border border-red-200/70 transition"
              >
                <span>Yandex Kartada ochish</span>
                <ExternalLink className="w-3.5 h-3.5" />
              </a>
            </div>

            <div className="p-4 bg-slate-50 rounded-2xl border border-slate-200/60 flex items-start gap-3">
              <div className="w-10 h-10 rounded-xl bg-blue-100 text-blue-700 flex items-center justify-center shrink-0">
                <MapPin className="w-5 h-5" />
              </div>
              <div className="flex-1">
                <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider">
                  {master.district ? `${master.district}, ` : ''}{master.region}
                </h4>
                <div className="mt-1">
                  <span className="inline-flex items-center gap-1.5 text-xs text-slate-800 bg-white px-3 py-1.5 rounded-xl border border-slate-200/90 font-semibold shadow-xs">
                    📍 Aniq manzil: <strong className="text-blue-600 font-bold">{master.address || `${master.district ? `${master.district}, ` : ''}${master.region}`}</strong>
                  </span>
                </div>
                <p className="text-[11px] text-slate-500 mt-2">
                  Usta asosan ushbu hudud va unga yondosh tumanlar bo‘ylab buyurtmalarni qabul qiladi.
                </p>
              </div>
            </div>

            {/* Yandex Xarita (Interactive Map Widget) */}
            <div className="rounded-2xl overflow-hidden border border-slate-200 shadow-inner relative w-full h-[280px] sm:h-[350px] bg-slate-100">
              <iframe
                title="Yandex Xarita — Usta lokatsiyasi"
                src={getYandexMapUrl()}
                width="100%"
                height="100%"
                frameBorder="0"
                allowFullScreen={true}
                className="w-full h-full"
                loading="lazy"
              />
              <div className="absolute bottom-3 left-3 pointer-events-none bg-white/95 backdrop-blur-xs px-3.5 py-2 rounded-xl text-xs font-bold text-slate-800 shadow-md border border-slate-200/80 flex items-center gap-2 max-w-[90%]">
                <span className="w-2.5 h-2.5 rounded-full bg-red-500 animate-pulse shrink-0" />
                <span className="truncate">{master.address || `${master.district ? `${master.district}, ` : ''}${master.region}`}</span>
              </div>
            </div>
          </section>

          {/* BAJARILGAN ISHLAR (PORTFOLIO) */}
          {master.portfolio && master.portfolio.length > 0 && (
            <section className="bg-white rounded-3xl p-6 border border-slate-200/80 shadow-sm space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-base font-black text-slate-900 tracking-tight flex items-center gap-2">
                  <Briefcase className="w-4 h-4 text-blue-600" />
                  Bajarilgan ishlar (Portfolio)
                </h2>
                <span className="text-xs font-semibold text-slate-400">
                  {master.portfolio.length} ta amalga oshirilgan ish
                </span>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {master.portfolio.map((item) => (
                  <div
                    key={item.id}
                    onClick={() => {
                      if (item.image_url) {
                        setSelectedPortfolioItem({
                          url: item.image_url,
                          title: item.title,
                          desc: item.description,
                        });
                      }
                    }}
                    className={`bg-slate-50 hover:bg-white rounded-3xl p-4 border border-slate-200/70 space-y-3 hover:shadow-xl hover:border-blue-200 transition-all duration-200 flex flex-col justify-between group ${
                      item.image_url ? 'cursor-pointer' : ''
                    }`}
                  >
                    <div>
                      {item.image_url ? (
                        <div className="w-full h-44 rounded-2xl overflow-hidden bg-slate-200 mb-2.5 relative shadow-xs">
                          <img
                            src={item.image_url}
                            alt={item.title}
                            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                          />
                          <div className="absolute inset-0 bg-black/35 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                            <span className="px-3.5 py-1.5 bg-white/95 backdrop-blur-xs text-slate-900 rounded-full text-xs font-bold flex items-center gap-1.5 shadow-md">
                              <Eye className="w-3.5 h-3.5 text-blue-600" />
                              Kattalashtirish
                            </span>
                          </div>
                        </div>
                      ) : (
                        <div className="w-full h-24 rounded-2xl bg-blue-50/60 border border-blue-100 flex items-center justify-center text-blue-500 mb-2.5">
                          <Briefcase className="w-8 h-8 opacity-40" />
                        </div>
                      )}
                      <h4 className="text-sm font-bold text-slate-900 group-hover:text-blue-600 transition">
                        {item.title}
                      </h4>
                      {item.description && (
                        <p className="text-xs text-slate-600 leading-relaxed mt-1">
                          {item.description}
                        </p>
                      )}
                    </div>
                    <span className="text-[10px] text-slate-400 block pt-1 border-t border-slate-200/50">
                      Bajarilgan sana: {new Date(item.created_at).toLocaleDateString('uz-UZ')}
                    </span>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* 4. REYTING VA MIJOZLAR FIKRLARI */}
          <section className="bg-white rounded-3xl p-6 border border-slate-200/80 shadow-sm space-y-5">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-base font-black text-slate-900 tracking-tight flex items-center gap-2">
                  <Star className="w-4 h-4 text-amber-400 fill-amber-400" />
                  Reyting va baholar
                </h2>
                <p className="text-xs text-slate-500 mt-0.5">
                  Haqiqiy mijozlar tomonidan qoldirilgan fikrlar
                </p>
              </div>

              {/* Baholash button */}
              {!isSelf && (
                <div>
                  {master.user_rated ? (
                    <span className="inline-flex items-center gap-1 text-xs font-bold text-emerald-700 bg-emerald-50 px-3 py-1.5 rounded-xl border border-emerald-200">
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      Baholagansiz
                    </span>
                  ) : (
                    <button
                      onClick={handleRateClick}
                      className="px-4 py-2 bg-amber-500 hover:bg-amber-600 text-white font-bold text-xs rounded-xl shadow-md shadow-amber-500/20 transition active:scale-98"
                    >
                      Baho berish
                    </button>
                  )}
                </div>
              )}
            </div>

            {/* Rating summary cards */}
            <div className="bg-slate-50 p-4 rounded-2xl flex items-center gap-6">
              <div className="text-center shrink-0 pr-4 border-r border-slate-200">
                <span className="text-3xl font-black text-slate-900 font-mono block">
                  {avgRating > 0 ? avgRating.toFixed(1) : "—"}
                </span>
                <div className="flex items-center justify-center gap-0.5 my-1">
                  {[1, 2, 3, 4, 5].map((s) => (
                    <Star
                      key={s}
                      className={`w-3.5 h-3.5 ${
                        avgRating >= s ? 'fill-amber-400 text-amber-400' : 'text-slate-300'
                      }`}
                    />
                  ))}
                </div>
                <span className="text-[10px] text-slate-400 font-medium">
                  {master.ratings_count} ta umumiy baho
                </span>
              </div>

              <div className="text-xs text-slate-600 space-y-1">
                <p className="font-semibold text-slate-800">
                  Shaffof baholash tizimi:
                </p>
                <p className="text-[11px] text-slate-500 leading-relaxed">
                  Har bir foydalanuvchi faqat 1 marta baho bera oladi. Usta o‘ziga baho qo‘ya olmaydi.
                </p>
              </div>
            </div>

            {/* Individual Reviews list */}
            {master.ratings && master.ratings.length > 0 ? (
              <div className="space-y-3 pt-2">
                {master.ratings.map((rev) => (
                  <div key={rev.id} className="p-4 rounded-2xl bg-white border border-slate-100 shadow-sm space-y-2">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2.5">
                        <TelegramAvatar
                          src={rev.user_avatar}
                          name={rev.user_name}
                          size="sm"
                          clickable={Boolean(rev.user_avatar)}
                        />
                        <span className="text-xs font-bold text-slate-900">{rev.user_name}</span>
                      </div>
                      <div className="flex items-center gap-1">
                        {[1, 2, 3, 4, 5].map((st) => (
                          <Star
                            key={st}
                            className={`w-3 h-3 ${
                              rev.score >= st ? 'fill-amber-400 text-amber-400' : 'text-slate-200'
                            }`}
                          />
                        ))}
                      </div>
                    </div>
                    {rev.comment && (
                      <p className="text-xs text-slate-600 leading-relaxed">
                        "{rev.comment}"
                      </p>
                    )}
                    <span className="text-[10px] text-slate-400 block">
                      {new Date(rev.created_at).toLocaleDateString('uz-UZ')}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-slate-400 text-center py-4">
                Hozircha sharhlar mavjud emas. Birinchi bo‘lib o‘z bahoingizni qoldiring!
              </p>
            )}

          </section>

        </div>

        {/* RIGHT COLUMN: Sticky Contact & Booking Sidebar */}
        <div className="lg:col-span-1">
          <div className="bg-white rounded-3xl p-6 border border-slate-200/90 shadow-lg sticky top-20 space-y-5">
            
            <div className="border-b border-slate-100 pb-4">
              <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block mb-1">
                Boshlang‘ich xizmat qiymati
              </span>
              <div className="flex items-baseline gap-1">
                <span className="text-2xl font-black text-slate-900 font-mono">
                  {master.price.toLocaleString('uz-UZ')}
                </span>
                <span className="text-xs font-bold text-slate-500">so‘m</span>
              </div>
            </div>

            {/* Fast Action Buttons */}
            <div className="space-y-2.5">
              <button
                onClick={handleCallClick}
                className="w-full py-3.5 px-4 bg-emerald-600 hover:bg-emerald-700 text-white font-bold rounded-2xl shadow-lg shadow-emerald-600/20 flex items-center justify-center gap-2 text-xs transition active:scale-98"
              >
                <Phone className="w-4 h-4" />
                <span>Telefon qilish</span>
              </button>

              <button
                onClick={handleChatClick}
                className="w-full py-3.5 px-4 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded-2xl shadow-lg shadow-blue-500/20 flex items-center justify-center gap-2 text-xs transition active:scale-98"
              >
                <MessageSquare className="w-4 h-4" />
                <span>Usta bilan yozishish (Chat)</span>
              </button>
            </div>

            <div className="p-3.5 bg-slate-50 rounded-2xl border border-slate-100 text-[11px] text-slate-500 space-y-1">
              <div className="flex items-center gap-1.5 font-bold text-slate-700">
                <Clock className="w-3.5 h-3.5 text-blue-600" />
                <span>Ish vaqti: {master.working_hours}</span>
              </div>
              <p>Murojaat qilishdan oldin ish vaqti bilan tanishib chiqing.</p>
            </div>

          </div>
        </div>

      </div>

      {/* Modals */}
      {isCallModalOpen && (
        <CallModal master={master} onClose={() => setIsCallModalOpen(false)} />
      )}

      {isRatingModalOpen && (
        <RatingModal
          master={master}
          onClose={() => setIsRatingModalOpen(false)}
          onSuccess={handleRatingSuccess}
        />
      )}

      {/* Telegram-style Portfolio Photo Viewer Modal */}
      {selectedPortfolioItem && (
        <PhotoViewerModal
          isOpen={Boolean(selectedPortfolioItem)}
          onClose={() => setSelectedPortfolioItem(null)}
          imageUrl={selectedPortfolioItem.url}
          title={selectedPortfolioItem.title}
          subtitle={selectedPortfolioItem.desc}
          isAvatar={false}
        />
      )}

    </div>
  );
};
