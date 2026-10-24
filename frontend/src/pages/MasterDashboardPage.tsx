import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  Wrench, Star, Phone, MapPin, DollarSign, Clock, MessageSquare,
  CheckCircle2, AlertCircle, Save, Plus, Trash2, Eye, ShieldCheck, Loader2,
  Camera, Upload, Image as ImageIcon, Briefcase
} from 'lucide-react';
import { api, resolveMediaUrl } from '../api/client';
import { Master, ServiceItem, LocationRegion, PortfolioItem } from '../types';
import { useAuth } from '../context/AuthContext';
import { TelegramAvatar } from '../components/TelegramAvatar';

export const MasterDashboardPage: React.FC = () => {
  const navigate = useNavigate();
  const { user, isAuthenticated, isMaster, refreshUser } = useAuth();

  const [master, setMaster] = useState<Master | null>(null);
  const [locations, setLocations] = useState<LocationRegion[]>([]);
  const [districtsList, setDistrictsList] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [isUploadingAvatar, setIsUploadingAvatar] = useState(false);
  const [feedbackMessage, setFeedbackMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Tabs: 'profile' | 'portfolio' | 'services' | 'ratings'
  const [activeTab, setActiveTab] = useState<'profile' | 'portfolio' | 'services' | 'ratings'>('profile');

  // Form Edit State
  const [status, setStatus] = useState<'active' | 'busy' | 'inactive'>('active');
  const [phone, setPhone] = useState('');
  const [address, setAddress] = useState('');
  const [price, setPrice] = useState<number>(50000);
  const [experience, setExperience] = useState<number>(1);
  const [description, setDescription] = useState('');
  const [workingHours, setWorkingHours] = useState('');
  const [region, setRegion] = useState('');
  const [district, setDistrict] = useState('');
  const [services, setServices] = useState<ServiceItem[]>([]);
  const [newServiceName, setNewServiceName] = useState('');
  const [newServicePrice, setNewServicePrice] = useState<number>(50000);

  // Portfolio State
  const [portfolio, setPortfolio] = useState<PortfolioItem[]>([]);
  const [newWorkTitle, setNewWorkTitle] = useState('');
  const [newWorkDesc, setNewWorkDesc] = useState('');
  const [newWorkImage, setNewWorkImage] = useState<string | null>(null);
  const [isAddingWork, setIsAddingWork] = useState(false);
  const [isDeletingWorkId, setIsDeletingWorkId] = useState<number | null>(null);

  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/login');
      return;
    }

    const loadData = async () => {
      setIsLoading(true);
      try {
        const [masterData, locs, portData] = await Promise.all([
          api.getMyMasterProfile(),
          api.getLocations(),
          api.getMyPortfolio().catch(() => []),
        ]);
        setMaster(masterData);
        setLocations(locs);
        setPortfolio(Array.isArray(portData) ? portData : (masterData.portfolio || []));

        // Populate fields
        setStatus(masterData.status);
        setPhone(masterData.phone || '');
        setAddress(masterData.address || '');
        setPrice(masterData.price);
        setExperience(masterData.experience);
        setDescription(masterData.description);
        setWorkingHours(masterData.working_hours);
        setRegion(masterData.region);
        setDistrict(masterData.district);
        setServices(masterData.services || []);
      } catch (err: any) {
        if (err.status === 404) {
          // No master profile yet
          navigate('/become-master');
        } else {
          setFeedbackMessage({ type: 'error', text: err.message || "Xatolik yuz berdi" });
        }
      } finally {
        setIsLoading(false);
      }
    };

    loadData();
  }, [isAuthenticated, navigate]);

  // Update district options when region changes
  useEffect(() => {
    if (region && locations.length > 0) {
      const found = locations.find((l) => l.region.toLowerCase().includes(region.toLowerCase()));
      if (found) {
        setDistrictsList(found.districts);
      }
    }
  }, [region, locations]);

  const handleStatusChange = async (newStatus: 'active' | 'busy' | 'inactive') => {
    setStatus(newStatus);
    try {
      await api.updateMasterProfile({ status: newStatus });
      setFeedbackMessage({ type: 'success', text: "Profil holati yangilandi." });
      setTimeout(() => setFeedbackMessage(null), 3000);
    } catch (err: any) {
      setFeedbackMessage({ type: 'error', text: err.message || "Xatolik yuz berdi." });
    }
  };

  const handleAvatarUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!file.type.startsWith('image/')) {
      setFeedbackMessage({ type: 'error', text: "Faqat rasm fayllarini yuklash mumkin." });
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      setFeedbackMessage({ type: 'error', text: "Rasm hajmi 5MB dan oshmasligi kerak." });
      return;
    }

    setIsUploadingAvatar(true);
    const reader = new FileReader();
    reader.onload = async () => {
      const base64 = reader.result as string;
      try {
        await api.updateMe({ avatar: base64 });
        await refreshUser();
        const updatedMaster = await api.getMyMasterProfile();
        setMaster(updatedMaster);
        setFeedbackMessage({ type: 'success', text: "Profil rasmi muvaffaqiyatli yangilandi!" });
        setTimeout(() => setFeedbackMessage(null), 3000);
      } catch (err: any) {
        setFeedbackMessage({ type: 'error', text: err.message || "Rasm yuklashda xatolik yuz berdi." });
      } finally {
        setIsUploadingAvatar(false);
      }
    };
    reader.readAsDataURL(file);
  };

  const handleSaveProfile = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSaving(true);
    setFeedbackMessage(null);

    try {
      const updated = await api.updateMasterProfile({
        phone,
        address,
        price,
        experience,
        description,
        working_hours: workingHours,
        region,
        district,
        services,
      });
      setMaster(updated);
      setFeedbackMessage({ type: 'success', text: "O‘zgarishlar muvaffaqiyatli saqlandi!" });
      setTimeout(() => setFeedbackMessage(null), 3000);
    } catch (err: any) {
      setFeedbackMessage({ type: 'error', text: err.message || "Saqlashda xatolik yuz berdi." });
    } finally {
      setIsSaving(false);
    }
  };

  const handleWorkImageSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!file.type.startsWith('image/')) {
      setFeedbackMessage({ type: 'error', text: "Faqat rasm fayllarini yuklash mumkin." });
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      setFeedbackMessage({ type: 'error', text: "Rasm hajmi 5MB dan oshmasligi kerak." });
      return;
    }
    const reader = new FileReader();
    reader.onload = () => {
      setNewWorkImage(reader.result as string);
    };
    reader.readAsDataURL(file);
  };

  const handleAddWork = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newWorkTitle.trim()) {
      setFeedbackMessage({ type: 'error', text: "Iltimos, ish nomini kiriting." });
      return;
    }

    setIsAddingWork(true);
    try {
      const created = await api.addPortfolioWork({
        title: newWorkTitle.trim(),
        description: newWorkDesc.trim(),
        image: newWorkImage || undefined,
      });
      setPortfolio([created, ...portfolio]);
      setNewWorkTitle('');
      setNewWorkDesc('');
      setNewWorkImage(null);
      setFeedbackMessage({ type: 'success', text: "Yangi bajarilgan ish muvaffaqiyatli qo‘shildi!" });
      setTimeout(() => setFeedbackMessage(null), 3000);
    } catch (err: any) {
      setFeedbackMessage({ type: 'error', text: err.message || "Ishni qo‘shishda xatolik yuz berdi." });
    } finally {
      setIsAddingWork(false);
    }
  };

  const handleDeleteWork = async (id: number) => {
    if (!confirm("Haqiqatan ham ushbu ishni o‘chirmoqchimisiz?")) return;
    setIsDeletingWorkId(id);
    try {
      await api.deletePortfolioWork(id);
      setPortfolio(portfolio.filter(w => w.id !== id));
      setFeedbackMessage({ type: 'success', text: "Bajarilgan ish o‘chirildi." });
      setTimeout(() => setFeedbackMessage(null), 3000);
    } catch (err: any) {
      setFeedbackMessage({ type: 'error', text: err.message || "O‘chirishda xatolik yuz berdi." });
    } finally {
      setIsDeletingWorkId(null);
    }
  };

  const handleAddService = () => {
    if (!newServiceName.trim()) return;
    setServices([
      ...services,
      { name: newServiceName.trim(), price: newServicePrice }
    ]);
    setNewServiceName('');
    setNewServicePrice(50000);
  };

  const handleRemoveService = (index: number) => {
    setServices(services.filter((_, idx) => idx !== index));
  };

  if (isLoading) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-16 text-center">
        <Loader2 className="w-8 h-8 animate-spin mx-auto text-blue-600 mb-2" />
        <p className="text-xs text-slate-500">Kabinet yuklanmoqda...</p>
      </div>
    );
  }

  if (!master) return null;

  const avgRating = Number(master.average_rating) || 0;

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      
      {/* Dashboard Top Header */}
      <div className="bg-white rounded-3xl p-6 border border-slate-200/80 shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div className="flex items-center gap-4">
          <div className="relative group shrink-0">
            <TelegramAvatar
              src={master.avatar_url || user?.avatar_url}
              name={master.full_name}
              size="lg"
              status={master.status}
              showStatus={true}
              hasStoryRing={true}
              clickable={false}
            />
            <label
              htmlFor="master-header-avatar-upload"
              className="absolute inset-0 bg-black/50 text-white rounded-full opacity-0 group-hover:opacity-100 flex flex-col items-center justify-center cursor-pointer transition shadow-md"
              title="Profil rasmini almashtirish"
            >
              <Camera className="w-5 h-5 text-white" />
            </label>
            <input
              id="master-header-avatar-upload"
              type="file"
              accept="image/*"
              onChange={handleAvatarUpload}
              className="hidden"
            />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold text-slate-900">{master.full_name}</h1>
              <span className="text-xs font-bold text-blue-600 bg-blue-50 px-2 py-0.5 rounded-md">
                {master.category.name}
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-0.5 flex items-center gap-1.5 flex-wrap">
              <MapPin className="w-3.5 h-3.5 text-blue-600 shrink-0" />
              <span>
                {master.address ? `${master.address} (${master.district}, ${master.region})` : `${master.district}, ${master.region}`}
              </span>
            </p>
          </div>
        </div>

        {/* Status Switcher & Preview Profile */}
        <div className="flex items-center gap-3">
          <div className="flex bg-slate-100 p-1 rounded-2xl text-xs font-bold">
            <button
              onClick={() => handleStatusChange('active')}
              className={`px-3 py-1.5 rounded-xl transition ${
                status === 'active'
                  ? 'bg-emerald-600 text-white shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Faol
            </button>
            <button
              onClick={() => handleStatusChange('busy')}
              className={`px-3 py-1.5 rounded-xl transition ${
                status === 'busy'
                  ? 'bg-amber-500 text-white shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Band
            </button>
          </div>

          <Link
            to={`/masters/${master.id}`}
            className="inline-flex items-center gap-1.5 px-3 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold rounded-2xl text-xs transition"
          >
            <Eye className="w-4 h-4 text-slate-500" />
            <span>Profilni ko‘rish</span>
          </Link>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="bg-white p-4 sm:p-5 rounded-3xl border border-slate-200/80 shadow-sm flex items-center gap-3 sm:gap-4">
          <div className="w-11 h-11 rounded-2xl bg-amber-50 text-amber-600 flex items-center justify-center shrink-0">
            <Star className="w-5 h-5 fill-amber-400 text-amber-400" />
          </div>
          <div>
            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
              Umumiy reyting
            </span>
            <span className="text-lg sm:text-xl font-black text-slate-900 font-mono">
              {avgRating > 0 ? avgRating.toFixed(1) : "—"} / 5.0
            </span>
          </div>
        </div>

        <div className="bg-white p-4 sm:p-5 rounded-3xl border border-slate-200/80 shadow-sm flex items-center gap-3 sm:gap-4">
          <div className="w-11 h-11 rounded-2xl bg-blue-50 text-blue-600 flex items-center justify-center shrink-0">
            <ShieldCheck className="w-5 h-5" />
          </div>
          <div>
            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
              Mijozlar baholari
            </span>
            <span className="text-lg sm:text-xl font-black text-slate-900 font-mono">
              {master.ratings_count} ta baho
            </span>
          </div>
        </div>

        <div className="bg-white p-4 sm:p-5 rounded-3xl border border-slate-200/80 shadow-sm flex items-center gap-3 sm:gap-4">
          <div className="w-11 h-11 rounded-2xl bg-indigo-50 text-indigo-600 flex items-center justify-center shrink-0">
            <Briefcase className="w-5 h-5" />
          </div>
          <div>
            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
              Bajarilgan ishlar
            </span>
            <span className="text-lg sm:text-xl font-black text-slate-900 font-mono">
              {portfolio.length} ta
            </span>
          </div>
        </div>

        <div className="bg-white p-4 sm:p-5 rounded-3xl border border-slate-200/80 shadow-sm flex items-center gap-3 sm:gap-4">
          <div className="w-11 h-11 rounded-2xl bg-emerald-50 text-emerald-600 flex items-center justify-center shrink-0">
            <Wrench className="w-5 h-5" />
          </div>
          <div>
            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">
              Xizmatlar soni
            </span>
            <span className="text-lg sm:text-xl font-black text-slate-900 font-mono">
              {services.length} ta
            </span>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-slate-200 gap-4 sm:gap-6 text-xs font-bold overflow-x-auto">
        <button
          onClick={() => setActiveTab('profile')}
          className={`pb-3 border-b-2 whitespace-nowrap transition ${
            activeTab === 'profile'
              ? 'border-blue-600 text-blue-600'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          Profilni tahrirlash
        </button>
        <button
          onClick={() => setActiveTab('portfolio')}
          className={`pb-3 border-b-2 whitespace-nowrap transition flex items-center gap-1.5 ${
            activeTab === 'portfolio'
              ? 'border-blue-600 text-blue-600'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <span>Bajarilgan ishlar (Portfolio)</span>
          <span className="bg-slate-100 text-slate-600 px-1.5 py-0.2 rounded-full text-[10px]">
            {portfolio.length}
          </span>
        </button>
        <button
          onClick={() => setActiveTab('services')}
          className={`pb-3 border-b-2 whitespace-nowrap transition ${
            activeTab === 'services'
              ? 'border-blue-600 text-blue-600'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          Xizmatlar ({services.length})
        </button>
        <button
          onClick={() => setActiveTab('ratings')}
          className={`pb-3 border-b-2 whitespace-nowrap transition ${
            activeTab === 'ratings'
              ? 'border-blue-600 text-blue-600'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          Mening baholarim ({master.ratings_count})
        </button>
      </div>

      {feedbackMessage && (
        <div className={`p-4 rounded-2xl flex items-center gap-2 text-xs animate-in fade-in ${
          feedbackMessage.type === 'success'
            ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
            : 'bg-red-50 text-red-800 border border-red-200'
        }`}>
          {feedbackMessage.type === 'success' ? (
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
          ) : (
            <AlertCircle className="w-4 h-4 text-red-600 shrink-0" />
          )}
          <span>{feedbackMessage.text}</span>
        </div>
      )}

      {/* TAB 1: Edit Profile */}
      {activeTab === 'profile' && (
        <form onSubmit={handleSaveProfile} className="bg-white rounded-3xl p-6 sm:p-8 border border-slate-200/80 shadow-sm space-y-6">
          {/* Avatar Upload Card */}
          <div className="flex items-center gap-4 p-4 bg-slate-50 border border-slate-200/80 rounded-2xl">
            <TelegramAvatar
              src={master.avatar_url || user?.avatar_url}
              name={master.full_name}
              size="lg"
              status={master.status}
              showStatus={true}
              clickable={false}
            />
            <div className="space-y-1">
              <span className="text-xs font-bold text-slate-800 block">Profil fotosi</span>
              <p className="text-[11px] text-slate-500">
                Usta profilingiz va qidiruv kartangizda ko‘rinadigan rasmingizni yangilang (PNG, JPG, maks. 5MB)
              </p>
              <label
                htmlFor="master-tab-avatar-upload"
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
                id="master-tab-avatar-upload"
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
                Boshlang‘ich xizmat narxi (so‘m)
              </label>
              <input
                type="number"
                step={5000}
                value={price}
                onChange={(e) => setPrice(Number(e.target.value))}
                className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-xs font-mono focus:outline-none focus:border-blue-600 focus:bg-white"
              />
            </div>

            <div>
              <label className="text-xs font-bold text-slate-700 block mb-1">
                Ish tajribasi (yil)
              </label>
              <input
                type="number"
                value={experience}
                onChange={(e) => setExperience(Number(e.target.value))}
                className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-xs focus:outline-none focus:border-blue-600 focus:bg-white"
              />
            </div>

            <div>
              <label className="text-xs font-bold text-slate-700 block mb-1">
                Ish vaqti
              </label>
              <input
                type="text"
                value={workingHours}
                onChange={(e) => setWorkingHours(e.target.value)}
                className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-xs focus:outline-none focus:border-blue-600 focus:bg-white"
              />
            </div>

            <div>
              <label className="text-xs font-bold text-slate-700 block mb-1">
                Viloyat / Shahar
              </label>
              <select
                value={region}
                onChange={(e) => setRegion(e.target.value)}
                className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-xs focus:outline-none focus:border-blue-600 focus:bg-white"
              >
                {locations.map((l) => (
                  <option key={l.region} value={l.region}>{l.region}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="text-xs font-bold text-slate-700 block mb-1">
                Tuman
              </label>
              <select
                value={district}
                onChange={(e) => setDistrict(e.target.value)}
                className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-xs focus:outline-none focus:border-blue-600 focus:bg-white"
              >
                {districtsList.map((d) => (
                  <option key={d} value={d}>{d}</option>
                ))}
              </select>
            </div>

            <div className="sm:col-span-2">
              <label className="text-xs font-bold text-slate-700 block mb-1">
                Aniq ish joyi manzili / Mo‘ljal
              </label>
              <input
                type="text"
                value={address}
                onChange={(e) => setAddress(e.target.value)}
                placeholder="Masalan: Yunusobod 4-mavze, 12-uy yoki Megaplanet savdo markazi yonida"
                className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-xs focus:outline-none focus:border-blue-600 focus:bg-white"
              />
              <span className="text-[11px] text-slate-400 mt-1 block">
                Ushbu manzil mijozlar uchun xaritada va profilingizda aniq ko‘rinadi (koordinatalar o‘rniga).
              </span>
            </div>

            <div className="sm:col-span-2">
              <label className="text-xs font-bold text-slate-700 block mb-1">
                Xizmat haqida batafsil ma’lumot
              </label>
              <textarea
                rows={4}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                className="w-full bg-slate-50 border border-slate-200 rounded-xl p-3 text-xs focus:outline-none focus:border-blue-600 focus:bg-white"
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
              <span>O‘zgarishlarni saqlash</span>
            </button>
          </div>
        </form>
      )}

      {/* TAB: Portfolio / Bajarilgan ishlar */}
      {activeTab === 'portfolio' && (
        <div className="space-y-6">
          {/* Add New Portfolio Work Form */}
          <div className="bg-white rounded-3xl p-6 sm:p-8 border border-slate-200/80 shadow-sm space-y-5">
            <div>
              <h3 className="text-base font-bold text-slate-900">
                Yangi bajarilgan ish qo‘shish
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">
                Mijozlar ishonchini oshirish uchun avval bajargan ishlaringiz fotosuratlari va tavsifini yuklang
              </p>
            </div>

            <form onSubmit={handleAddWork} className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="text-xs font-bold text-slate-700 block mb-1">
                    Ish nomi / Qilingan ish *
                  </label>
                  <input
                    type="text"
                    required
                    value={newWorkTitle}
                    onChange={(e) => setNewWorkTitle(e.target.value)}
                    placeholder="Masalan: iPhone 13 Pro ekran va batareya almashtirish"
                    className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-xs focus:outline-none focus:border-blue-600 focus:bg-white"
                  />
                </div>

                <div>
                  <label className="text-xs font-bold text-slate-700 block mb-1">
                    Ish fotosurati
                  </label>
                  <div className="flex items-center gap-3">
                    <label
                      htmlFor="portfolio-image-input"
                      className="flex-1 flex items-center justify-center gap-2 px-3 py-2 bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded-xl text-xs font-bold text-slate-700 cursor-pointer transition truncate"
                    >
                      <Upload className="w-4 h-4 text-blue-600 shrink-0" />
                      <span className="truncate">
                        {newWorkImage ? "Rasm tanlandi (o‘zgartirish)" : "Rasm tanlash (PNG, JPG)"}
                      </span>
                    </label>
                    <input
                      id="portfolio-image-input"
                      type="file"
                      accept="image/*"
                      onChange={handleWorkImageSelect}
                      className="hidden"
                    />
                    {newWorkImage && (
                      <div className="w-10 h-10 rounded-xl overflow-hidden border border-slate-200 shrink-0 relative group">
                        <img src={newWorkImage} alt="Preview" className="w-full h-full object-cover" />
                        <button
                          type="button"
                          onClick={() => setNewWorkImage(null)}
                          className="absolute inset-0 bg-red-600/80 text-white flex items-center justify-center opacity-0 group-hover:opacity-100 text-[10px] font-bold transition"
                          title="Bekor qilish"
                        >
                          ✕
                        </button>
                      </div>
                    )}
                  </div>
                </div>

                <div className="sm:col-span-2">
                  <label className="text-xs font-bold text-slate-700 block mb-1">
                    Batafsil tavsif (nimalar bajarildi, qanday kafolat berildi)
                  </label>
                  <textarea
                    rows={2}
                    value={newWorkDesc}
                    onChange={(e) => setNewWorkDesc(e.target.value)}
                    placeholder="Qisqacha jarayon, ishlatilgan ehtiyot qismlar va berilgan kafolat..."
                    className="w-full bg-slate-50 border border-slate-200 rounded-xl p-3 text-xs focus:outline-none focus:border-blue-600 focus:bg-white"
                  />
                </div>
              </div>

              <div className="flex justify-end pt-1">
                <button
                  type="submit"
                  disabled={isAddingWork}
                  className="px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded-xl text-xs flex items-center gap-1.5 shadow-md shadow-blue-500/20 transition disabled:opacity-50"
                >
                  {isAddingWork ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
                  <span>Ishni qo‘shish</span>
                </button>
              </div>
            </form>
          </div>

          {/* Portfolio Items List */}
          <div className="bg-white rounded-3xl p-6 sm:p-8 border border-slate-200/80 shadow-sm space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-base font-bold text-slate-900">
                  Mening barcha ishlarim ({portfolio.length})
                </h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  Profilingizda mijozlarga ko‘rinadigan namunalar
                </p>
              </div>
            </div>

            {portfolio.length > 0 ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4 pt-2">
                {portfolio.map((item) => (
                  <div
                    key={item.id}
                    className="group border border-slate-100 bg-slate-50/50 hover:bg-white rounded-2xl overflow-hidden shadow-xs hover:shadow-md transition flex flex-col justify-between"
                  >
                    <div>
                      {item.image_url ? (
                        <div className="h-44 w-full bg-slate-100 overflow-hidden relative">
                          <img
                            src={resolveMediaUrl(item.image_url)}
                            alt={item.title}
                            className="w-full h-full object-cover group-hover:scale-105 transition duration-300"
                          />
                        </div>
                      ) : (
                        <div className="h-28 w-full bg-gradient-to-br from-blue-50 to-indigo-50 flex items-center justify-center text-blue-500">
                          <Briefcase className="w-8 h-8 opacity-40" />
                        </div>
                      )}
                      <div className="p-4 space-y-1">
                        <h4 className="text-xs font-bold text-slate-900 group-hover:text-blue-600 transition line-clamp-1">
                          {item.title}
                        </h4>
                        {item.description && (
                          <p className="text-[11px] text-slate-500 line-clamp-2 leading-relaxed">
                            {item.description}
                          </p>
                        )}
                        <span className="text-[10px] text-slate-400 block pt-1">
                          {new Date(item.created_at).toLocaleDateString('uz-UZ')}
                        </span>
                      </div>
                    </div>

                    <div className="px-4 pb-4 pt-1 flex justify-end">
                      <button
                        type="button"
                        onClick={() => handleDeleteWork(item.id)}
                        disabled={isDeletingWorkId === item.id}
                        className="inline-flex items-center gap-1 px-2.5 py-1 text-[11px] font-bold text-red-600 hover:bg-red-50 rounded-lg transition disabled:opacity-50"
                        title="O‘chirish"
                      >
                        {isDeletingWorkId === item.id ? (
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        ) : (
                          <Trash2 className="w-3.5 h-3.5" />
                        )}
                        <span>O‘chirish</span>
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="p-8 text-center border-2 border-dashed border-slate-200 rounded-2xl space-y-2">
                <Briefcase className="w-8 h-8 text-slate-300 mx-auto" />
                <p className="text-xs font-medium text-slate-500">
                  Hozircha birorta ham ish namunasi kiritilmagan.
                </p>
                <p className="text-[11px] text-slate-400 max-w-sm mx-auto">
                  Yuqoridagi forma orqali birinchi bajargan ishingizni qo‘shing. Bu mijozlar sizni tanlashiga yordam beradi!
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 2: Services Management */}
      {activeTab === 'services' && (
        <div className="bg-white rounded-3xl p-6 sm:p-8 border border-slate-200/80 shadow-sm space-y-6">
          <div>
            <h3 className="text-base font-bold text-slate-900">
              Xizmatlar ro‘yxati
            </h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Mijozlar profilingizda ko‘radigan aniq xizmat turlari va ularning narxi
            </p>
          </div>

          {/* Add Service Bar */}
          <div className="p-4 bg-slate-50 rounded-2xl border border-slate-200 flex flex-col sm:flex-row items-center gap-3">
            <input
              type="text"
              placeholder="Xizmat nomi (masalan: Ekran almashtirish)"
              value={newServiceName}
              onChange={(e) => setNewServiceName(e.target.value)}
              className="flex-1 w-full bg-white border border-slate-200 rounded-xl px-3 py-2 text-xs focus:outline-none focus:border-blue-600"
            />
            <input
              type="number"
              step={5000}
              placeholder="Narxi"
              value={newServicePrice}
              onChange={(e) => setNewServicePrice(Number(e.target.value))}
              className="w-full sm:w-36 bg-white border border-slate-200 rounded-xl px-3 py-2 text-xs font-mono focus:outline-none focus:border-blue-600"
            />
            <button
              type="button"
              onClick={handleAddService}
              className="w-full sm:w-auto px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded-xl text-xs flex items-center justify-center gap-1 shrink-0 transition"
            >
              <Plus className="w-4 h-4" />
              <span>Qo‘shish</span>
            </button>
          </div>

          {/* Services list */}
          <div className="divide-y divide-slate-100 border border-slate-100 rounded-2xl overflow-hidden">
            {services.map((srv, idx) => (
              <div key={idx} className="p-3.5 flex items-center justify-between hover:bg-slate-50 transition">
                <span className="text-xs font-bold text-slate-800">{srv.name}</span>
                <div className="flex items-center gap-4">
                  <span className="text-xs font-extrabold text-blue-600 font-mono">
                    {srv.price.toLocaleString('uz-UZ')} so‘m
                  </span>
                  <button
                    type="button"
                    onClick={() => handleRemoveService(idx)}
                    className="p-1.5 text-slate-400 hover:text-red-500 rounded-lg hover:bg-red-50 transition"
                    title="O‘chirish"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>

          <div className="flex justify-end pt-2">
            <button
              type="button"
              onClick={handleSaveProfile}
              disabled={isSaving}
              className="px-6 py-2.5 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded-xl text-xs flex items-center gap-1.5 shadow-md shadow-blue-500/20 transition"
            >
              {isSaving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
              <span>Xizmatlar ro‘yxatini saqlash</span>
            </button>
          </div>
        </div>
      )}

      {/* TAB 3: Ratings and Reviews */}
      {activeTab === 'ratings' && (
        <div className="bg-white rounded-3xl p-6 sm:p-8 border border-slate-200/80 shadow-sm space-y-4">
          <h3 className="text-base font-bold text-slate-900">
            Sizga berilgan barcha baholar
          </h3>

          {master.ratings && master.ratings.length > 0 ? (
            <div className="space-y-3">
              {master.ratings.map((r) => (
                <div key={r.id} className="p-4 rounded-2xl bg-slate-50 border border-slate-100 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-slate-900">{r.user_name}</span>
                    <div className="flex items-center gap-1">
                      {[1, 2, 3, 4, 5].map((st) => (
                        <Star
                          key={st}
                          className={`w-3.5 h-3.5 ${
                            r.score >= st ? 'fill-amber-400 text-amber-400' : 'text-slate-200'
                          }`}
                        />
                      ))}
                    </div>
                  </div>
                  {r.comment && (
                    <p className="text-xs text-slate-600">"{r.comment}"</p>
                  )}
                  <span className="text-[10px] text-slate-400 block">
                    {new Date(r.created_at).toLocaleDateString('uz-UZ')}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-xs text-slate-400 text-center py-8">
              Sizga hali hech kim baho bermagan. Xizmatlaringizdan so‘ng mijozlardan platformada baho qoldirishlarini so‘rang!
            </p>
          )}
        </div>
      )}

    </div>
  );
};
