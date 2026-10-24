import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  User as UserIcon, Bookmark, Star, MessageSquare, Save,
  CheckCircle2, AlertCircle, Phone, ChevronRight, Loader2, Heart, Camera, Upload
} from 'lucide-react';
import { api } from '../api/client';
import { Master } from '../types';
import { useAuth } from '../context/AuthContext';
import { MasterCard } from '../components/MasterCard';
import { TelegramAvatar } from '../components/TelegramAvatar';

export const UserDashboardPage: React.FC = () => {
  const navigate = useNavigate();
  const { user, isAuthenticated, updateProfile } = useAuth();

  const [activeTab, setActiveTab] = useState<'profile' | 'favorites' | 'ratings'>('profile');
  const [favorites, setFavorites] = useState<Master[]>([]);
  const [myRatings, setMyRatings] = useState<any[]>([]);
  const [isLoadingData, setIsLoadingData] = useState(false);

  // Profile Edit fields
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [phone, setPhone] = useState('');
  const [email, setEmail] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  const [isUploadingAvatar, setIsUploadingAvatar] = useState(false);
  const [statusMessage, setStatusMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/login');
      return;
    }

    if (user) {
      setFirstName(user.first_name || '');
      setLastName(user.last_name || '');
      setPhone(user.phone || '');
      setEmail(user.email || '');
    }
  }, [user, isAuthenticated, navigate]);

  useEffect(() => {
    const fetchUserData = async () => {
      if (!isAuthenticated) return;
      setIsLoadingData(true);
      try {
        if (activeTab === 'favorites') {
          const favs = await api.getFavorites();
          setFavorites(favs.results || []);
        } else if (activeTab === 'ratings') {
          const ratings = await api.getMyRatings();
          setMyRatings(ratings || []);
        }
      } catch (err) {
        console.error(err);
      } finally {
        setIsLoadingData(false);
      }
    };

    fetchUserData();
  }, [activeTab, isAuthenticated]);

  const handleAvatarUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!file.type.startsWith('image/')) {
      setStatusMessage({ type: 'error', text: "Faqat rasm fayllarini yuklash mumkin." });
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      setStatusMessage({ type: 'error', text: "Rasm hajmi 5MB dan oshmasligi kerak." });
      return;
    }

    setIsUploadingAvatar(true);
    const reader = new FileReader();
    reader.onload = async () => {
      const base64 = reader.result as string;
      try {
        await updateProfile({ avatar: base64 });
        setStatusMessage({ type: 'success', text: "Profil rasmi muvaffaqiyatli yuklandi!" });
        setTimeout(() => setStatusMessage(null), 3000);
      } catch (err: any) {
        setStatusMessage({ type: 'error', text: err.message || "Rasm yuklashda xatolik yuz berdi." });
      } finally {
        setIsUploadingAvatar(false);
      }
    };
    reader.readAsDataURL(file);
  };

  const handleSaveProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSaving(true);
    setStatusMessage(null);

    try {
      await updateProfile({
        first_name: firstName.trim(),
        last_name: lastName.trim(),
        phone: phone.trim() || null,
        email: email.trim() || null,
      });
      setStatusMessage({ type: 'success', text: "Profil ma'lumotlari muvaffaqiyatli saqlandi!" });
      setTimeout(() => setStatusMessage(null), 3000);
    } catch (err: any) {
      setStatusMessage({ type: 'error', text: err.message || "Saqlashda xatolik yuz berdi." });
    } finally {
      setIsSaving(false);
    }
  };

  const handleFavoriteRemoved = (masterId: number) => {
    setFavorites(favorites.filter(f => f.id !== masterId));
  };

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      
      {/* Top Banner */}
      <div className="bg-white rounded-3xl p-6 border border-slate-200/80 shadow-sm flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <div className="relative group shrink-0">
            <TelegramAvatar
              src={user?.avatar_url}
              name={user?.full_name || 'F'}
              size="lg"
              hasStoryRing={true}
              clickable={false}
            />
            <label
              htmlFor="user-avatar-upload"
              className="absolute inset-0 bg-black/50 text-white rounded-full opacity-0 group-hover:opacity-100 flex flex-col items-center justify-center cursor-pointer transition shadow-md"
              title="Profil rasmini yuklash"
            >
              <Camera className="w-5 h-5 text-white" />
            </label>
            <input
              id="user-avatar-upload"
              type="file"
              accept="image/*"
              onChange={handleAvatarUpload}
              className="hidden"
            />
          </div>
          <div>
            <h1 className="text-xl font-bold text-slate-900">
              {user?.full_name || "Foydalanuvchi kabineti"}
            </h1>
            <p className="text-xs text-slate-500 mt-0.5">
              {user?.phone || user?.email || "Shaxsiy kabinet"}
            </p>
          </div>
        </div>

        <Link
          to="/chat"
          className="inline-flex items-center gap-2 px-4 py-2 bg-blue-50 text-blue-700 hover:bg-blue-100 font-bold rounded-2xl text-xs transition"
        >
          <MessageSquare className="w-4 h-4" />
          <span>Mening xabarlarim</span>
        </Link>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-slate-200 gap-6 text-xs font-bold">
        <button
          onClick={() => setActiveTab('profile')}
          className={`pb-3 border-b-2 transition flex items-center gap-1.5 ${
            activeTab === 'profile'
              ? 'border-blue-600 text-blue-600'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <UserIcon className="w-4 h-4" />
          <span>Mening ma’lumotlarim</span>
        </button>

        <button
          onClick={() => setActiveTab('favorites')}
          className={`pb-3 border-b-2 transition flex items-center gap-1.5 ${
            activeTab === 'favorites'
              ? 'border-blue-600 text-blue-600'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <Bookmark className="w-4 h-4" />
          <span>Saqlangan ustalar</span>
        </button>

        <button
          onClick={() => setActiveTab('ratings')}
          className={`pb-3 border-b-2 transition flex items-center gap-1.5 ${
            activeTab === 'ratings'
              ? 'border-blue-600 text-blue-600'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <Star className="w-4 h-4" />
          <span>Baholangan ustalar</span>
        </button>
      </div>

      {/* Status Feedback */}
      {statusMessage && (
        <div className={`p-4 rounded-2xl flex items-center gap-2 text-xs animate-in fade-in ${
          statusMessage.type === 'success'
            ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
            : 'bg-red-50 text-red-800 border border-red-200'
        }`}>
          {statusMessage.type === 'success' ? (
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
          ) : (
            <AlertCircle className="w-4 h-4 text-red-600 shrink-0" />
          )}
          <span>{statusMessage.text}</span>
        </div>
      )}

      {/* TAB 1: Profile Edit */}
      {activeTab === 'profile' && (
        <form onSubmit={handleSaveProfile} className="bg-white rounded-3xl p-6 sm:p-8 border border-slate-200/80 shadow-sm space-y-6 max-w-2xl">
          {/* Avatar Upload Card */}
          <div className="flex items-center gap-4 p-4 bg-slate-50 border border-slate-200/80 rounded-2xl">
            <TelegramAvatar
              src={user?.avatar_url}
              name={user?.full_name || 'F'}
              size="lg"
              clickable={false}
            />
            <div className="space-y-1">
              <span className="text-xs font-bold text-slate-800 block">Profil fotosi</span>
              <p className="text-[11px] text-slate-500">
                O‘zingizning real rasmingizni yuklang (PNG, JPG, maks. 5MB)
              </p>
              <label
                htmlFor="user-avatar-upload-btn"
                className={`inline-flex items-center gap-1.5 px-3 py-1.5 bg-white border border-slate-200 hover:border-blue-600 text-slate-700 hover:text-blue-600 text-xs font-bold rounded-xl cursor-pointer shadow-sm transition ${
                  isUploadingAvatar ? 'opacity-50 pointer-events-none' : ''
                }`}
              >
                {isUploadingAvatar ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin text-blue-600" />
                ) : (
                  <Upload className="w-3.5 h-3.5 text-slate-500" />
                )}
                <span>{isUploadingAvatar ? "Yuklanmoqda..." : "Rasmni almashtirish"}</span>
              </label>
              <input
                id="user-avatar-upload-btn"
                type="file"
                accept="image/*"
                onChange={handleAvatarUpload}
                className="hidden"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="text-xs font-bold text-slate-700 block mb-1">
                Ism
              </label>
              <input
                type="text"
                required
                value={firstName}
                onChange={(e) => setFirstName(e.target.value)}
                className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-xs focus:outline-none focus:border-blue-600 focus:bg-white"
              />
            </div>

            <div>
              <label className="text-xs font-bold text-slate-700 block mb-1">
                Familiya
              </label>
              <input
                type="text"
                value={lastName}
                onChange={(e) => setLastName(e.target.value)}
                className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-xs focus:outline-none focus:border-blue-600 focus:bg-white"
              />
            </div>

            <div>
              <label className="text-xs font-bold text-slate-700 block mb-1">
                Telefon raqami
              </label>
              <input
                type="tel"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-xs font-mono focus:outline-none focus:border-blue-600 focus:bg-white"
              />
            </div>

            <div>
              <label className="text-xs font-bold text-slate-700 block mb-1">
                Elektron pochta
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-xs focus:outline-none focus:border-blue-600 focus:bg-white"
              />
            </div>
          </div>

          <div className="pt-2 flex justify-end">
            <button
              type="submit"
              disabled={isSaving}
              className="px-6 py-2.5 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded-xl text-xs flex items-center gap-1.5 shadow-md shadow-blue-500/20 transition disabled:opacity-50"
            >
              {isSaving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
              <span>Saqlash</span>
            </button>
          </div>
        </form>
      )}

      {/* TAB 2: Favorites */}
      {activeTab === 'favorites' && (
        <div>
          {isLoadingData ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {[1, 2, 3].map(n => <div key={n} className="h-60 bg-slate-100 animate-pulse rounded-3xl" />)}
            </div>
          ) : favorites.length > 0 ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {favorites.map(m => (
                <MasterCard
                  key={m.id}
                  master={m}
                  onFavoriteChange={(id, isFav) => {
                    if (!isFav) handleFavoriteRemoved(id);
                  }}
                />
              ))}
            </div>
          ) : (
            <div className="bg-white rounded-3xl p-10 text-center border border-slate-200/80 space-y-3">
              <Heart className="w-10 h-10 text-slate-300 mx-auto" />
              <h3 className="text-sm font-bold text-slate-700">Hozircha saqlangan ustalar yo‘q</h3>
              <p className="text-xs text-slate-400">
                Katalogdan yoqqan ustalarni yurakcha tugmasi orqali bu yerga saqlab qo‘yishingiz mumkin.
              </p>
              <Link
                to="/masters"
                className="inline-block px-4 py-2 bg-blue-600 text-white font-bold text-xs rounded-xl mt-2"
              >
                Ustalarni ko‘rish
              </Link>
            </div>
          )}
        </div>
      )}

      {/* TAB 3: Rated Masters */}
      {activeTab === 'ratings' && (
        <div>
          {isLoadingData ? (
            <div className="space-y-3">
              {[1, 2].map(n => <div key={n} className="h-24 bg-slate-100 animate-pulse rounded-2xl" />)}
            </div>
          ) : myRatings.length > 0 ? (
            <div className="space-y-3">
              {myRatings.map((r) => (
                <div key={r.id} className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-sm flex items-center justify-between">
                  <div className="space-y-1">
                    <Link
                      to={`/masters/${r.master.id}`}
                      className="text-sm font-bold text-slate-900 hover:text-blue-600 transition"
                    >
                      {r.master.full_name}
                    </Link>
                    <p className="text-xs text-slate-400">
                      {r.master.category} • {r.master.region}
                    </p>
                    {r.comment && (
                      <p className="text-xs text-slate-600 pt-1 italic">
                        "{r.comment}"
                      </p>
                    )}
                  </div>

                  <div className="text-right shrink-0">
                    <div className="flex items-center gap-1 justify-end font-bold text-amber-500 text-sm">
                      <Star className="w-4 h-4 fill-amber-400 text-amber-400" />
                      <span>{r.score}</span>
                    </div>
                    <span className="text-[10px] text-slate-400 block mt-1">
                      {new Date(r.created_at).toLocaleDateString('uz-UZ')}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="bg-white rounded-3xl p-10 text-center border border-slate-200/80 space-y-3">
              <Star className="w-10 h-10 text-slate-300 mx-auto" />
              <h3 className="text-sm font-bold text-slate-700">Hozircha hech qaysi ustaga baho bermagansiz</h3>
              <p className="text-xs text-slate-400">
                Foydalangan xizmatlaringizdan so‘ng ustalarga baho qoldiring, bu boshqalarga to‘g‘ri tanlov qilishda yordam beradi.
              </p>
            </div>
          )}
        </div>
      )}

    </div>
  );
};
