import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Wrench, Smartphone, Zap, Hammer, CheckCircle2, ChevronRight,
  ChevronLeft, MapPin, DollarSign, Clock, User, AlertCircle, Loader2, ShieldCheck
} from 'lucide-react';
import { api } from '../api/client';
import { Category, LocationRegion } from '../types';
import { useAuth } from '../context/AuthContext';

export const BecomeMasterPage: React.FC = () => {
  const navigate = useNavigate();
  const { user, isAuthenticated, isMaster, register, refreshUser } = useAuth();

  const [currentStep, setCurrentStep] = useState(1);
  const [categories, setCategories] = useState<Category[]>([]);
  const [locations, setLocations] = useState<LocationRegion[]>([]);
  const [districtsList, setDistrictsList] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Form State
  // Step 1: Category
  const [selectedCategoryId, setSelectedCategoryId] = useState<number | null>(null);

  // Step 2: Basic Info
  const [firstName, setFirstName] = useState(user?.first_name || '');
  const [lastName, setLastName] = useState(user?.last_name || '');
  const [phone, setPhone] = useState(user?.phone || '');
  const [email, setEmail] = useState(user?.email || '');
  const [password, setPassword] = useState('');
  const [experience, setExperience] = useState<number>(3);

  // Step 3: Service & Price
  const [serviceName, setServiceName] = useState('');
  const [description, setDescription] = useState('');
  const [price, setPrice] = useState<number>(50000);
  const [workingHours, setWorkingHours] = useState('09:00 - 18:00');

  // Step 4: Location
  const [region, setRegion] = useState('Toshkent shahri');
  const [district, setDistrict] = useState('Yunusobod tumani');
  const [address, setAddress] = useState('');
  const [latitude, setLatitude] = useState<number | null>(41.2995);
  const [longitude, setLongitude] = useState<number | null>(69.2401);

  // If already master, redirect to dashboard
  useEffect(() => {
    if (isMaster) {
      navigate('/master/dashboard');
    }
  }, [isMaster, navigate]);

  // Load Categories & Locations
  useEffect(() => {
    const loadData = async () => {
      try {
        const [cats, locs] = await Promise.all([
          api.getCategories(),
          api.getLocations(),
        ]);
        const safeCats = Array.isArray(cats) ? cats : (cats as any)?.results || [];
        setCategories(safeCats);
        setLocations(Array.isArray(locs) ? locs : []);
        if (safeCats.length > 0) {
          setSelectedCategoryId(safeCats[0].id);
        }
      } catch (err) {
        console.error(err);
      }
    };
    loadData();
  }, []);

  // Update district options when region changes
  useEffect(() => {
    if (region && locations.length > 0) {
      const found = locations.find((l) => l.region.toLowerCase().includes(region.toLowerCase()));
      if (found) {
        setDistrictsList(found.districts);
        if (found.districts.length > 0) {
          setDistrict(found.districts[0]);
        }
        if (found.lat && found.lng) {
          setLatitude(found.lat);
          setLongitude(found.lng);
        }
      }
    }
  }, [region, locations]);

  // Sync user info if logged in
  useEffect(() => {
    if (user) {
      setFirstName(user.first_name || '');
      setLastName(user.last_name || '');
      if (user.phone) setPhone(user.phone);
      if (user.email) setEmail(user.email);
    }
  }, [user]);

  // Step validations
  const handleNext = () => {
    setErrorMessage(null);

    if (currentStep === 1) {
      if (!selectedCategoryId) {
        setErrorMessage("Iltimos, o‘z usta yo‘nalishingizni tanlang.");
        return;
      }
    } else if (currentStep === 2) {
      if (!firstName.trim()) {
        setErrorMessage("Ismingizni kiriting.");
        return;
      }
      if (!phone.trim()) {
        setErrorMessage("Telefon raqamingizni kiriting.");
        return;
      }
      if (!isAuthenticated && (!password || password.length < 6)) {
        setErrorMessage("Kabinetga kirish uchun kamida 6 ta belgidan iborat parol kiriting.");
        return;
      }
    } else if (currentStep === 3) {
      if (!description.trim()) {
        setErrorMessage("Xizmatingiz haqida qisqa ma’lumot kiriting.");
        return;
      }
      if (!price || price < 1000) {
        setErrorMessage("Boshlang‘ich xizmat narxini to‘g‘ri kiriting.");
        return;
      }
    } else if (currentStep === 4) {
      if (!region || !district) {
        setErrorMessage("Ishlaydigan hududingiz va tumanni tanlang.");
        return;
      }
    }

    setCurrentStep((prev) => Math.min(prev + 1, 5));
  };

  const handleBack = () => {
    setErrorMessage(null);
    setCurrentStep((prev) => Math.max(prev - 1, 1));
  };

  const handleFinish = async () => {
    setIsLoading(true);
    setErrorMessage(null);

    try {
      // 1. If not authenticated, register as master first
      if (!isAuthenticated) {
        await register({
          first_name: firstName.trim(),
          last_name: lastName.trim(),
          phone: phone.trim(),
          email: email.trim() || undefined,
          password,
          role: 'master',
        });
      }

      // 2. Create Master Profile
      const services = [];
      if (serviceName.trim()) {
        services.push({ name: serviceName.trim(), price });
      }

      await api.createMasterProfile({
        category_id: selectedCategoryId,
        description: description.trim(),
        experience,
        price,
        region,
        district,
        address: address.trim(),
        latitude,
        longitude,
        working_hours: workingHours,
        services,
      });

      await refreshUser();
      navigate('/master/dashboard');
    } catch (err: any) {
      setErrorMessage(err.message || "Profilni saqlashda xatolik yuz berdi. Iltimos qaytadan urinib ko‘ring.");
    } finally {
      setIsLoading(false);
    }
  };

  const selectedCategoryObj = categories.find((c) => c.id === selectedCategoryId);

  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 py-10">
      
      {/* Step Indicator Header */}
      <div className="mb-8 text-center space-y-2">
        <h1 className="text-2xl sm:text-3xl font-black text-slate-900 tracking-tight">
          Usta sifatida ro‘yxatdan o‘tish
        </h1>
        <p className="text-xs text-slate-500">
          Atigi 5 ta sodda bosqichda profilingizni yarating va yangi mijozlarga ega bo‘ling
        </p>

        {/* 5-Step Visual Progress Bar */}
        <div className="flex items-center justify-between max-w-md mx-auto pt-4 relative">
          <div className="absolute top-1/2 left-0 right-0 h-1 bg-slate-200 -translate-y-1/2 z-0" />
          <div
            className="absolute top-1/2 left-0 h-1 bg-blue-600 -translate-y-1/2 z-0 transition-all duration-300"
            style={{ width: `${((currentStep - 1) / 4) * 100}%` }}
          />

          {[1, 2, 3, 4, 5].map((s) => (
            <div
              key={s}
              className={`w-8 h-8 rounded-full font-bold text-xs flex items-center justify-center relative z-10 transition ${
                s < currentStep
                  ? 'bg-blue-600 text-white'
                  : s === currentStep
                  ? 'bg-blue-600 text-white ring-4 ring-blue-100'
                  : 'bg-white border-2 border-slate-300 text-slate-400'
              }`}
            >
              {s < currentStep ? <CheckCircle2 className="w-4 h-4" /> : s}
            </div>
          ))}
        </div>
      </div>

      {/* Main Form Container */}
      <div className="bg-white rounded-3xl p-6 sm:p-8 border border-slate-200/90 shadow-xl space-y-6">
        
        {errorMessage && (
          <div className="p-3.5 bg-red-50 border border-red-200 rounded-2xl flex items-center gap-2.5 text-xs text-red-700 animate-in fade-in">
            <AlertCircle className="w-4 h-4 shrink-0 text-red-500" />
            <span>{errorMessage}</span>
          </div>
        )}

        {/* STEP 1: Kimligingiz? (Kategoriya) */}
        {currentStep === 1 && (
          <div className="space-y-4">
            <div>
              <h2 className="text-base font-bold text-slate-900">
                1-bosqich: Kimligingiz?
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">
                O‘z mutaxassislik yo‘nalishingizni tanlang
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2">
              {categories.map((c) => {
                const isSelected = selectedCategoryId === c.id;
                return (
                  <button
                    key={c.id}
                    type="button"
                    onClick={() => setSelectedCategoryId(c.id)}
                    className={`p-5 rounded-2xl border text-left transition flex flex-col justify-between gap-3 ${
                      isSelected
                        ? 'border-blue-600 bg-blue-50/60 ring-2 ring-blue-500/20'
                        : 'border-slate-200 hover:border-slate-300 bg-slate-50/50'
                    }`}
                  >
                    <div className="w-12 h-12 rounded-xl bg-white shadow-sm flex items-center justify-center">
                      {c.slug === 'phone-repair' && <Smartphone className="w-6 h-6 text-blue-600" />}
                      {c.slug === 'electrician' && <Zap className="w-6 h-6 text-amber-500" />}
                      {c.slug === 'builder' && <Hammer className="w-6 h-6 text-emerald-600" />}
                    </div>

                    <div>
                      <h3 className="text-sm font-bold text-slate-900">{c.name}</h3>
                      <p className="text-[11px] text-slate-500 mt-1 line-clamp-2">{c.description}</p>
                    </div>

                    {isSelected && (
                      <span className="text-xs font-bold text-blue-600 flex items-center gap-1">
                        <CheckCircle2 className="w-3.5 h-3.5" /> Tanlandi
                      </span>
                    )}
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {/* STEP 2: Asosiy ma'lumotlar */}
        {currentStep === 2 && (
          <div className="space-y-4">
            <div>
              <h2 className="text-base font-bold text-slate-900">
                2-bosqich: Asosiy ma’lumotlar
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">
                Ism, familiya va bog‘lanish ma’lumotlaringiz
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="text-xs font-bold text-slate-700 block mb-1">
                  Ism *
                </label>
                <input
                  type="text"
                  required
                  value={firstName}
                  onChange={(e) => setFirstName(e.target.value)}
                  placeholder="Jasur"
                  className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3 py-2.5 text-xs text-slate-900 focus:outline-none focus:border-blue-600 focus:bg-white"
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
                  placeholder="Mirzayev"
                  className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3 py-2.5 text-xs text-slate-900 focus:outline-none focus:border-blue-600 focus:bg-white"
                />
              </div>

              <div>
                <label className="text-xs font-bold text-slate-700 block mb-1">
                  Telefon raqami *
                </label>
                <input
                  type="tel"
                  required
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  placeholder="+998 90 123 45 67"
                  className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3 py-2.5 text-xs text-slate-900 font-mono focus:outline-none focus:border-blue-600 focus:bg-white"
                />
              </div>

              <div>
                <label className="text-xs font-bold text-slate-700 block mb-1">
                  Ish tajribasi (yil)
                </label>
                <input
                  type="number"
                  min={1}
                  max={50}
                  value={experience}
                  onChange={(e) => setExperience(Number(e.target.value))}
                  className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3 py-2.5 text-xs text-slate-900 focus:outline-none focus:border-blue-600 focus:bg-white"
                />
              </div>

              {/* Password if not logged in */}
              {!isAuthenticated && (
                <div className="sm:col-span-2">
                  <label className="text-xs font-bold text-slate-700 block mb-1">
                    Kabinet paroli *
                  </label>
                  <input
                    type="password"
                    required
                    minLength={6}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Kelajakda tizimga kirish uchun parol o‘ylab toping"
                    className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3 py-2.5 text-xs text-slate-900 focus:outline-none focus:border-blue-600 focus:bg-white"
                  />
                  <span className="text-[11px] text-slate-400 mt-1 block">
                    Kamida 6 ta belgidan iborat bo‘lishi kerak
                  </span>
                </div>
              )}
            </div>
          </div>
        )}

        {/* STEP 3: Xizmat va narx */}
        {currentStep === 3 && (
          <div className="space-y-4">
            <div>
              <h2 className="text-base font-bold text-slate-900">
                3-bosqich: Xizmat va narx
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">
                Mijozlarga taklif qiladigan asosiy xizmat va boshlang‘ich narx
              </p>
            </div>

            <div className="space-y-3.5">
              <div>
                <label className="text-xs font-bold text-slate-700 block mb-1">
                  Asosiy xizmat nomi
                </label>
                <input
                  type="text"
                  value={serviceName}
                  onChange={(e) => setServiceName(e.target.value)}
                  placeholder="Masalan: Ekran va plata ta'mirlash"
                  className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3 py-2.5 text-xs text-slate-900 focus:outline-none focus:border-blue-600 focus:bg-white"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="text-xs font-bold text-slate-700 block mb-1">
                    Boshlang‘ich xizmat narxi (so‘m) *
                  </label>
                  <input
                    type="number"
                    step={10000}
                    value={price}
                    onChange={(e) => setPrice(Number(e.target.value))}
                    className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3 py-2.5 text-xs text-slate-900 font-mono focus:outline-none focus:border-blue-600 focus:bg-white"
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
                    placeholder="09:00 - 18:00 (Dush-Shan)"
                    className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3 py-2.5 text-xs text-slate-900 focus:outline-none focus:border-blue-600 focus:bg-white"
                  />
                </div>
              </div>

              <div>
                <label className="text-xs font-bold text-slate-700 block mb-1">
                  Xizmat haqida qisqa ma’lumot *
                </label>
                <textarea
                  rows={3}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Qanday ishlarni bajarasiz, qanday kafolat berasiz, qanday tajribaga egasiz..."
                  className="w-full bg-slate-50 border border-slate-200 rounded-xl p-3 text-xs text-slate-900 focus:outline-none focus:border-blue-600 focus:bg-white"
                />
              </div>
            </div>
          </div>
        )}

        {/* STEP 4: Lokatsiya */}
        {currentStep === 4 && (
          <div className="space-y-4">
            <div>
              <h2 className="text-base font-bold text-slate-900">
                4-bosqich: Ish joyi lokatsiyasi
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">
                Xizmat ko‘rsatadigan asosiy hududingizni belgilang
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="text-xs font-bold text-slate-700 block mb-1">
                  Viloyat / Shahar *
                </label>
                <select
                  value={region}
                  onChange={(e) => setRegion(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3 py-2.5 text-xs text-slate-900 focus:outline-none focus:border-blue-600 focus:bg-white"
                >
                  {locations.map((l) => (
                    <option key={l.region} value={l.region}>{l.region}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="text-xs font-bold text-slate-700 block mb-1">
                  Tuman / Shahar *
                </label>
                <select
                  value={district}
                  onChange={(e) => setDistrict(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3 py-2.5 text-xs text-slate-900 focus:outline-none focus:border-blue-600 focus:bg-white"
                >
                  {districtsList.map((d) => (
                    <option key={d} value={d}>{d}</option>
                  ))}
                </select>
              </div>
            </div>

            <div>
              <label className="text-xs font-bold text-slate-700 block mb-1">
                Aniq ish joyi manzili / Mo‘ljal
              </label>
              <input
                type="text"
                value={address}
                onChange={(e) => setAddress(e.target.value)}
                placeholder="Masalan: Yunusobod 4-mavze, 12-uy yoki Megaplanet savdo markazi yonida"
                className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3 py-2.5 text-xs text-slate-900 focus:outline-none focus:border-blue-600 focus:bg-white"
              />
              <span className="text-[11px] text-slate-400 mt-1 block">
                Ushbu manzil mijozlar uchun xaritada va profilingizda aniq ko‘rsatiladi.
              </span>
            </div>

            {/* Location preview badge */}
            <div className="p-4 bg-slate-50 border border-slate-200 rounded-2xl flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-blue-100 text-blue-700 flex items-center justify-center shrink-0">
                <MapPin className="w-5 h-5" />
              </div>
              <div>
                <span className="text-xs font-bold text-slate-900 block">
                  {address ? `${address} (${district}, ${region})` : `${district}, ${region}`}
                </span>
                <span className="text-[11px] text-slate-500">
                  Ushbu tuman va unga yaqin hududlardagi mijozlar sizni qidiruvda topa oladi.
                </span>
              </div>
            </div>
          </div>
        )}

        {/* STEP 5: Profilni tasdiqlash */}
        {currentStep === 5 && (
          <div className="space-y-4">
            <div>
              <h2 className="text-base font-bold text-slate-900">
                5-bosqich: Profilni tasdiqlash
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">
                Kiritilgan barcha ma’lumotlarni ko‘rib chiqing va faollashtiring
              </p>
            </div>

            <div className="bg-slate-50 rounded-2xl p-4 border border-slate-200 space-y-3 text-xs">
              <div className="flex justify-between py-1 border-b border-slate-200/60">
                <span className="text-slate-500">Mutaxassislik:</span>
                <span className="font-bold text-blue-600">{selectedCategoryObj?.name}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-200/60">
                <span className="text-slate-500">F.I.Sh:</span>
                <span className="font-bold text-slate-900">{firstName} {lastName}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-200/60">
                <span className="text-slate-500">Telefon:</span>
                <span className="font-bold font-mono text-slate-900">{phone}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-200/60">
                <span className="text-slate-500">Ish tajribasi:</span>
                <span className="font-bold text-slate-900">{experience} yil</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-200/60">
                <span className="text-slate-500">Boshlang‘ich narx:</span>
                <span className="font-bold text-emerald-700">{price.toLocaleString('uz-UZ')} so‘m</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-200/60">
                <span className="text-slate-500">Ish vaqti:</span>
                <span className="font-bold text-slate-900">{workingHours}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-slate-200/60">
                <span className="text-slate-500">Hudud:</span>
                <span className="font-bold text-slate-900">{district}, {region}</span>
              </div>
              {address && (
                <div className="flex justify-between py-1">
                  <span className="text-slate-500">Aniq manzil:</span>
                  <span className="font-bold text-slate-900">{address}</span>
                </div>
              )}
            </div>

            <div className="p-3 bg-blue-50 border border-blue-200 rounded-2xl flex items-center gap-2 text-[11px] text-blue-700">
              <ShieldCheck className="w-4 h-4 text-blue-600 shrink-0" />
              <span>Profilingiz tasdiqlangach, darhol qidiruv tizimida paydo bo‘ladi.</span>
            </div>
          </div>
        )}

        {/* Action Controls (Orqaga / Keyingisi / Faollashtirish) */}
        <div className="pt-4 flex items-center justify-between border-t border-slate-100">
          {currentStep > 1 ? (
            <button
              type="button"
              onClick={handleBack}
              disabled={isLoading}
              className="px-4 py-2.5 bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold rounded-xl text-xs transition flex items-center gap-1.5"
            >
              <ChevronLeft className="w-4 h-4" />
              <span>Orqaga</span>
            </button>
          ) : <div />}

          {currentStep < 5 ? (
            <button
              type="button"
              onClick={handleNext}
              className="px-6 py-2.5 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded-xl text-xs shadow-md shadow-blue-500/20 transition flex items-center gap-1.5 active:scale-98"
            >
              <span>Keyingi bosqich</span>
              <ChevronRight className="w-4 h-4" />
            </button>
          ) : (
            <button
              type="button"
              onClick={handleFinish}
              disabled={isLoading}
              className="px-6 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white font-bold rounded-xl text-xs shadow-md shadow-emerald-600/20 transition flex items-center gap-1.5 active:scale-98 disabled:opacity-50"
            >
              {isLoading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <CheckCircle2 className="w-4 h-4" />
              )}
              <span>Profilni faollashtirish</span>
            </button>
          )}
        </div>

      </div>
    </div>
  );
};
