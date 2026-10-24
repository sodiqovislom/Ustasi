import React, { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import {
  Search, MapPin, Compass, Star, Smartphone, Zap, Hammer,
  ArrowRight, ShieldCheck, Clock, Users, Wrench, CheckCircle2
} from 'lucide-react';
import { api } from '../api/client';
import { Master, Category, LocationRegion } from '../types';
import { MasterCard } from '../components/MasterCard';
import { SearchAutocomplete } from '../components/SearchAutocomplete';
import { useAuth } from '../context/AuthContext';

export const HomePage: React.FC = () => {
  const navigate = useNavigate();
  const { userCoords, requestUserLocation } = useAuth();

  const [categories, setCategories] = useState<Category[]>([]);
  const [locations, setLocations] = useState<LocationRegion[]>([]);
  const [topMasters, setTopMasters] = useState<Master[]>([]);
  const [isLoadingMasters, setIsLoadingMasters] = useState(true);

  // Hero Quick Filter States
  const [selectedCategory, setSelectedCategory] = useState<string>('');
  const [selectedRegion, setSelectedRegion] = useState<string>('');
  const [selectedDistance, setSelectedDistance] = useState<string>('');

  useEffect(() => {
    // Fetch initial categories & locations
    const loadInitialData = async () => {
      try {
        const [cats, locs, mastersData] = await Promise.all([
          api.getCategories(),
          api.getLocations(),
          api.getMasters({ ordering: '-average_rating', min_rating: 4.0 })
        ]);
        setCategories(Array.isArray(cats) ? cats : (cats as any)?.results || []);
        setLocations(Array.isArray(locs) ? locs : []);
        setTopMasters(mastersData?.results ? mastersData.results.slice(0, 6) : []);
      } catch (err) {
        console.error("Ma'lumotlarni yuklashda xatolik:", err);
      } finally {
        setIsLoadingMasters(false);
      }
    };

    loadInitialData();
  }, []);

  const handleHeroSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const query = new URLSearchParams();
    if (selectedCategory) query.append('category', selectedCategory);
    if (selectedRegion) query.append('region', selectedRegion);
    if (selectedDistance) query.append('distance', selectedDistance);
    if (userCoords && selectedDistance) {
      query.append('lat', String(userCoords.lat));
      query.append('lng', String(userCoords.lng));
    }
    navigate(`/masters?${query.toString()}`);
  };

  const getCategoryIcon = (slug: string) => {
    switch (slug) {
      case 'phone-repair':
        return <Smartphone className="w-6 h-6 text-blue-600" />;
      case 'electrician':
        return <Zap className="w-6 h-6 text-amber-500" />;
      case 'builder':
        return <Hammer className="w-6 h-6 text-emerald-600" />;
      default:
        return <Wrench className="w-6 h-6 text-blue-600" />;
    }
  };

  return (
    <div className="space-y-16 pb-12">
      
      {/* HERO SECTION */}
      <section className="relative overflow-hidden bg-gradient-to-b from-blue-50/70 via-white to-slate-50 pt-10 pb-16 md:py-20 border-b border-slate-200/60">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="max-w-3xl mx-auto text-center space-y-4">
            
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-100/70 text-blue-800 text-xs font-bold tracking-wide animate-in fade-in">
              <ShieldCheck className="w-4 h-4 text-blue-600" />
              Ishonchli va tajribali ustalar platformasi
            </div>

            <h1 className="text-3xl sm:text-5xl font-black text-slate-900 tracking-tight leading-tight">
              Qanday usta kerak?
            </h1>

            <p className="text-sm sm:text-base text-slate-600 max-w-xl mx-auto font-medium">
              Hudud, masofa va xizmat narxiga qarab kerakli mutaxassisni bir necha soniyada toping va to‘g‘ridan-to‘g‘ri bog‘laning.
            </p>

            {/* Main Search Autocomplete */}
            <div className="pt-2 max-w-2xl mx-auto">
              <SearchAutocomplete
                placeholder="Usta, xizmat yoki hududni yozing (masalan: telefon, elektrik, Toshkent)..."
              />
            </div>

            {/* Quick Filter Box */}
            <div className="pt-4 max-w-3xl mx-auto">
              <form
                onSubmit={handleHeroSearchSubmit}
                className="bg-white p-3.5 sm:p-4 rounded-3xl shadow-xl border border-slate-200/80 flex flex-col md:flex-row items-center gap-2.5"
              >
                {/* Category select */}
                <div className="w-full md:flex-1 text-left">
                  <label className="text-[10px] font-extrabold uppercase tracking-wider text-slate-400 block px-2 mb-1">
                    Kategoriya
                  </label>
                  <select
                    value={selectedCategory}
                    onChange={(e) => setSelectedCategory(e.target.value)}
                    className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-xs font-semibold text-slate-700 focus:outline-none focus:border-blue-600 focus:bg-white"
                  >
                    <option value="">Barcha kategoriyalar</option>
                    {categories.map((c) => (
                      <option key={c.id} value={c.slug}>
                        {c.name}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Region select */}
                <div className="w-full md:flex-1 text-left">
                  <label className="text-[10px] font-extrabold uppercase tracking-wider text-slate-400 block px-2 mb-1">
                    Hudud
                  </label>
                  <select
                    value={selectedRegion}
                    onChange={(e) => setSelectedRegion(e.target.value)}
                    className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-xs font-semibold text-slate-700 focus:outline-none focus:border-blue-600 focus:bg-white"
                  >
                    <option value="">Barcha hududlar</option>
                    {locations.map((loc) => (
                      <option key={loc.region} value={loc.region}>
                        {loc.region}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Distance select */}
                <div className="w-full md:flex-1 text-left">
                  <div className="flex items-center justify-between px-2 mb-1">
                    <label className="text-[10px] font-extrabold uppercase tracking-wider text-slate-400 block">
                      Masofa
                    </label>
                    {!userCoords && (
                      <button
                        type="button"
                        onClick={requestUserLocation}
                        className="text-[10px] font-bold text-blue-600 hover:underline"
                        title="GPS lokatsiyani aniqlash"
                      >
                        GPS
                      </button>
                    )}
                  </div>
                  <select
                    value={selectedDistance}
                    onChange={(e) => setSelectedDistance(e.target.value)}
                    className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-xs font-semibold text-slate-700 focus:outline-none focus:border-blue-600 focus:bg-white"
                  >
                    <option value="">Ixtiyoriy masofa</option>
                    <option value="1">1 km radiusda</option>
                    <option value="5">5 km radiusda</option>
                    <option value="10">10 km radiusda</option>
                    <option value="25">25 km radiusda</option>
                    <option value="50">50 km radiusda</option>
                  </select>
                </div>

                {/* Submit button */}
                <div className="w-full md:w-auto self-end pt-1 md:pt-0">
                  <button
                    type="submit"
                    className="w-full md:w-auto h-[42px] px-6 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded-xl text-xs flex items-center justify-center gap-2 shadow-md shadow-blue-500/30 transition active:scale-98"
                  >
                    <Search className="w-4 h-4" />
                    <span>Ustani topish</span>
                  </button>
                </div>
              </form>
            </div>

          </div>
        </div>
      </section>

      {/* CATEGORIES SECTION */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-xl sm:text-2xl font-black text-slate-900 tracking-tight">
              Asosiy xizmat turlari
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              1-bosqichda O‘zbekistonda eng ko‘p talab qilinadigan usta yo‘nalishlari
            </p>
          </div>
          <Link
            to="/masters"
            className="text-xs font-bold text-blue-600 hover:text-blue-700 flex items-center gap-1"
          >
            <span>Barchasi</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {categories.map((cat) => (
            <Link
              key={cat.id}
              to={`/masters?category=${cat.slug}`}
              className="bg-white p-5 rounded-3xl border border-slate-200/80 shadow-sm hover:shadow-md hover:border-blue-400 transition-all group flex items-start gap-4"
            >
              <div className="w-12 h-12 rounded-2xl bg-slate-50 group-hover:bg-blue-50 flex items-center justify-center shrink-0 transition">
                {getCategoryIcon(cat.slug)}
              </div>
              <div className="min-w-0">
                <h3 className="text-base font-bold text-slate-900 group-hover:text-blue-600 transition">
                  {cat.name}
                </h3>
                <p className="text-xs text-slate-500 line-clamp-2 mt-1 leading-relaxed">
                  {cat.description}
                </p>
                <span className="text-[11px] font-bold text-blue-600 mt-2 inline-flex items-center gap-1">
                  Ustalarni ko‘rish <ArrowRight className="w-3 h-3 group-hover:translate-x-1 transition-transform" />
                </span>
              </div>
            </Link>
          ))}
        </div>
      </section>

      {/* TOP RATED MASTERS */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-xl sm:text-2xl font-black text-slate-900 tracking-tight flex items-center gap-2">
              Yuqori reytingli ustalar
              <span className="text-xs font-bold bg-amber-100 text-amber-800 px-2 py-0.5 rounded-full">
                4.5+ ⭐
              </span>
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Mijozlar tomonidan eng yaxshi baholangan haqiqiy mutaxassislar
            </p>
          </div>
          <Link
            to="/masters?min_rating=4.5"
            className="text-xs font-bold text-blue-600 hover:text-blue-700 flex items-center gap-1"
          >
            <span>Katalog</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        {isLoadingMasters ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {[1, 2, 3].map((n) => (
              <div key={n} className="h-64 bg-slate-100 animate-pulse rounded-3xl" />
            ))}
          </div>
        ) : topMasters.length > 0 ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {topMasters.map((master) => (
              <MasterCard key={master.id} master={master} />
            ))}
          </div>
        ) : (
          <div className="text-center py-10 bg-white rounded-3xl border border-slate-200">
            <p className="text-xs text-slate-500">Hozircha ustalar ro‘yxati yangilanmoqda.</p>
          </div>
        )}
      </section>

      {/* HOW IT WORKS (QANDAY ISHLAYDI?) */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="bg-slate-900 text-white rounded-3xl p-8 sm:p-12 relative overflow-hidden">
          <div className="max-w-2xl mb-8">
            <h2 className="text-2xl sm:text-3xl font-black tracking-tight mb-2">
              Qanday ishlaydi?
            </h2>
            <p className="text-xs sm:text-sm text-slate-400">
              Keraksiz vositachilarsiz to‘g‘ridan-to‘g‘ri ustani topishning eng qulay yo‘li:
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="bg-slate-800/80 p-5 rounded-2xl border border-slate-700/60">
              <div className="w-9 h-9 rounded-xl bg-blue-600 text-white font-black text-sm flex items-center justify-center mb-3">
                1
              </div>
              <h3 className="text-sm font-bold text-white mb-1">
                Kategoriya va hududni tanlang
              </h3>
              <p className="text-xs text-slate-400 leading-relaxed">
                Telefon, elektrik yoki quruvchi ustasini o‘zingizga eng yaqin masofadan qidiring.
              </p>
            </div>

            <div className="bg-slate-800/80 p-5 rounded-2xl border border-slate-700/60">
              <div className="w-9 h-9 rounded-xl bg-blue-600 text-white font-black text-sm flex items-center justify-center mb-3">
                2
              </div>
              <h3 className="text-sm font-bold text-white mb-1">
                Profil va narxni ko‘ring
              </h3>
              <p className="text-xs text-slate-400 leading-relaxed">
                Ustaning ish tajribasi, xizmat qiymati va boshqa mijozlar qo‘ygan haqqoniy baholarni o‘rganing.
              </p>
            </div>

            <div className="bg-slate-800/80 p-5 rounded-2xl border border-slate-700/60">
              <div className="w-9 h-9 rounded-xl bg-blue-600 text-white font-black text-sm flex items-center justify-center mb-3">
                3
              </div>
              <h3 className="text-sm font-bold text-white mb-1">
                Telefon qiling yoki yozing
              </h3>
              <p className="text-xs text-slate-400 leading-relaxed">
                Ustaga bevosita telefon qiling yoki sayt ichidagi qulay chat orqali murojaat qiling.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* BECOME A MASTER CTA */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="bg-gradient-to-r from-blue-600 to-indigo-700 rounded-3xl p-8 sm:p-12 text-white flex flex-col md:flex-row items-center justify-between gap-6 shadow-xl shadow-blue-500/10">
          <div className="space-y-2 max-w-xl text-center md:text-left">
            <h2 className="text-2xl sm:text-3xl font-black tracking-tight">
              Siz ham ustamisiz?
            </h2>
            <p className="text-xs sm:text-sm text-blue-100 leading-relaxed">
              O‘z xizmatlaringizni “Ustasi” platformasiga bepul joylang va hududingizdagi yangi buyurtmachilar bilan to‘g‘ridan-to‘g‘ri bog‘laning.
            </p>
          </div>
          <Link
            to="/become-master"
            className="px-6 py-3.5 bg-white hover:bg-slate-50 text-blue-700 font-extrabold text-xs rounded-2xl shadow-lg transition active:scale-98 shrink-0 flex items-center gap-2"
          >
            <span>Usta sifatida qo‘shilish</span>
            <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>

    </div>
  );
};
