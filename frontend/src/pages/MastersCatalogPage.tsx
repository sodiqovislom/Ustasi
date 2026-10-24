import React, { useState, useEffect } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import {
  Filter, SlidersHorizontal, Star, MapPin, X, RotateCcw,
  Smartphone, Zap, Hammer, Wrench, ChevronDown, Check, Loader2
} from 'lucide-react';
import { api } from '../api/client';
import { Master, Category, LocationRegion } from '../types';
import { MasterCard } from '../components/MasterCard';
import { SearchAutocomplete } from '../components/SearchAutocomplete';
import { useAuth } from '../context/AuthContext';

export const MastersCatalogPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const { userCoords, requestUserLocation } = useAuth();

  const [masters, setMasters] = useState<Master[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [categories, setCategories] = useState<Category[]>([]);
  const [locations, setLocations] = useState<LocationRegion[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Mobile Filter Drawer State
  const [isMobileFilterOpen, setIsMobileFilterOpen] = useState(false);

  // Current Filter values extracted from URL search params
  const categoryParam = searchParams.get('category') || '';
  const searchParam = searchParams.get('search') || '';
  const regionParam = searchParams.get('region') || '';
  const districtParam = searchParams.get('district') || '';
  const distanceParam = searchParams.get('distance') || '';
  const minPriceParam = searchParams.get('min_price') || '';
  const maxPriceParam = searchParams.get('max_price') || '';
  const minRatingParam = searchParams.get('min_rating') || '';
  const orderingParam = searchParams.get('ordering') || '-average_rating';

  // Local filter states for immediate user interaction inside the Filter panel
  const [filterRegion, setFilterRegion] = useState(regionParam);
  const [filterDistrict, setFilterDistrict] = useState(districtParam);
  const [filterDistance, setFilterDistance] = useState(distanceParam);
  const [filterMinPrice, setFilterMinPrice] = useState(minPriceParam);
  const [filterMaxPrice, setFilterMaxPrice] = useState(maxPriceParam);
  const [filterMinRating, setFilterMinRating] = useState(minRatingParam);
  const [districtsList, setDistrictsList] = useState<string[]>([]);

  // Load Categories & Locations once
  useEffect(() => {
    const fetchMetadata = async () => {
      try {
        const [cats, locs] = await Promise.all([
          api.getCategories(),
          api.getLocations()
        ]);
        setCategories(Array.isArray(cats) ? cats : (cats as any)?.results || []);
        setLocations(Array.isArray(locs) ? locs : []);
      } catch (err) {
        console.error("Metadatalarni yuklashda xatolik:", err);
      }
    };
    fetchMetadata();
  }, []);

  // Update district options when region changes
  useEffect(() => {
    if (filterRegion && locations.length > 0) {
      const found = locations.find(l => l.region.toLowerCase().includes(filterRegion.toLowerCase()));
      if (found) {
        setDistrictsList(found.districts);
      } else {
        setDistrictsList([]);
      }
    } else {
      setDistrictsList([]);
    }
  }, [filterRegion, locations]);

  // Sync local filter state with URL query params
  useEffect(() => {
    setFilterRegion(regionParam);
    setFilterDistrict(districtParam);
    setFilterDistance(distanceParam);
    setFilterMinPrice(minPriceParam);
    setFilterMaxPrice(maxPriceParam);
    setFilterMinRating(minRatingParam);
  }, [regionParam, districtParam, distanceParam, minPriceParam, maxPriceParam, minRatingParam]);

  // Fetch masters on query params change
  useEffect(() => {
    const fetchMasters = async () => {
      setIsLoading(true);
      try {
        const res = await api.getMasters({
          category: categoryParam || undefined,
          search: searchParam || undefined,
          region: regionParam || undefined,
          district: districtParam || undefined,
          distance: distanceParam ? Number(distanceParam) : undefined,
          min_price: minPriceParam ? Number(minPriceParam) : undefined,
          max_price: maxPriceParam ? Number(maxPriceParam) : undefined,
          min_rating: minRatingParam ? Number(minRatingParam) : undefined,
          ordering: orderingParam,
          lat: userCoords?.lat,
          lng: userCoords?.lng,
        });
        setMasters(res.results || []);
        setTotalCount(res.count || 0);
      } catch (err) {
        console.error("Ustalarni yuklashda xatolik:", err);
      } finally {
        setIsLoading(false);
      }
    };

    fetchMasters();
  }, [
    categoryParam, searchParam, regionParam, districtParam,
    distanceParam, minPriceParam, maxPriceParam, minRatingParam,
    orderingParam, userCoords
  ]);

  const applyFilters = () => {
    const nextParams = new URLSearchParams(searchParams);
    if (filterRegion) nextParams.set('region', filterRegion); else nextParams.delete('region');
    if (filterDistrict) nextParams.set('district', filterDistrict); else nextParams.delete('district');
    if (filterDistance) nextParams.set('distance', filterDistance); else nextParams.delete('distance');
    if (filterMinPrice) nextParams.set('min_price', filterMinPrice); else nextParams.delete('min_price');
    if (filterMaxPrice) nextParams.set('max_price', filterMaxPrice); else nextParams.delete('max_price');
    if (filterMinRating) nextParams.set('min_rating', filterMinRating); else nextParams.delete('min_rating');
    setSearchParams(nextParams);
    setIsMobileFilterOpen(false);
  };

  const handleResetFilters = () => {
    setFilterRegion('');
    setFilterDistrict('');
    setFilterDistance('');
    setFilterMinPrice('');
    setFilterMaxPrice('');
    setFilterMinRating('');
    
    const nextParams = new URLSearchParams();
    if (categoryParam) nextParams.set('category', categoryParam);
    if (searchParam) nextParams.set('search', searchParam);
    if (orderingParam) nextParams.set('ordering', orderingParam);
    setSearchParams(nextParams);
    setIsMobileFilterOpen(false);
  };

  const handleCategorySelect = (slug: string) => {
    const nextParams = new URLSearchParams(searchParams);
    if (slug) {
      nextParams.set('category', slug);
    } else {
      nextParams.delete('category');
    }
    setSearchParams(nextParams);
  };

  const handleSortChange = (newOrdering: string) => {
    const nextParams = new URLSearchParams(searchParams);
    nextParams.set('ordering', newOrdering);
    setSearchParams(nextParams);
  };

  const hasActiveFilters = Boolean(
    regionParam || districtParam || distanceParam || minPriceParam || maxPriceParam || minRatingParam
  );

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
      
      {/* Top Header & Search Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-black text-slate-900 tracking-tight">
            Ustalar katalogi
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            {isLoading ? "Qidirilmoqda..." : `${totalCount} nafar usta topildi`}
          </p>
        </div>

        {/* Search input with autocomplete */}
        <div className="w-full md:w-96">
          <SearchAutocomplete
            initialValue={searchParam}
            placeholder="Usta yoki xizmat nomi..."
            onSearch={(val) => {
              const nextParams = new URLSearchParams(searchParams);
              if (val) nextParams.set('search', val);
              else nextParams.delete('search');
              setSearchParams(nextParams);
            }}
          />
        </div>
      </div>

      {/* Category Pills Bar */}
      <div className="flex items-center gap-2 overflow-x-auto pb-2 scrollbar-none">
        <button
          onClick={() => handleCategorySelect('')}
          className={`px-4 py-2 rounded-2xl text-xs font-bold shrink-0 transition ${
            !categoryParam
              ? 'bg-blue-600 text-white shadow-md shadow-blue-500/20'
              : 'bg-white border border-slate-200 text-slate-700 hover:border-slate-300'
          }`}
        >
          Barchasi
        </button>
        {categories.map((cat) => {
          const isSelected = categoryParam === cat.slug;
          return (
            <button
              key={cat.id}
              onClick={() => handleCategorySelect(cat.slug)}
              className={`px-4 py-2 rounded-2xl text-xs font-bold shrink-0 transition flex items-center gap-1.5 ${
                isSelected
                  ? 'bg-blue-600 text-white shadow-md shadow-blue-500/20'
                  : 'bg-white border border-slate-200 text-slate-700 hover:border-slate-300'
              }`}
            >
              {cat.slug === 'phone-repair' && <Smartphone className="w-3.5 h-3.5" />}
              {cat.slug === 'electrician' && <Zap className="w-3.5 h-3.5" />}
              {cat.slug === 'builder' && <Hammer className="w-3.5 h-3.5" />}
              <span>{cat.name}</span>
            </button>
          );
        })}
      </div>

      {/* Main Content Layout (Desktop Sidebar Filter + Masters Grid) */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 items-start">
        
        {/* DESKTOP FILTER SIDEBAR */}
        <aside className="hidden lg:block lg:col-span-1 bg-white p-5 rounded-3xl border border-slate-200/90 shadow-sm sticky top-20">
          <div className="flex items-center justify-between pb-3 border-b border-slate-100 mb-4">
            <div className="flex items-center gap-2">
              <Filter className="w-4 h-4 text-blue-600" />
              <h2 className="text-sm font-black text-slate-900 tracking-tight">Filtr</h2>
            </div>
            {hasActiveFilters && (
              <button
                onClick={handleResetFilters}
                className="text-[11px] font-bold text-slate-400 hover:text-red-500 flex items-center gap-1"
              >
                <RotateCcw className="w-3 h-3" />
                Tozalash
              </button>
            )}
          </div>

          <div className="space-y-5 text-xs">
            {/* 1. Hudud */}
            <div>
              <label className="text-[11px] font-extrabold uppercase tracking-wider text-slate-400 block mb-1.5">
                Hudud
              </label>
              <select
                value={filterRegion}
                onChange={(e) => {
                  setFilterRegion(e.target.value);
                  setFilterDistrict('');
                }}
                className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-xs font-semibold text-slate-700 focus:outline-none focus:border-blue-600 focus:bg-white"
              >
                <option value="">Barcha viloyatlar</option>
                {locations.map((l) => (
                  <option key={l.region} value={l.region}>{l.region}</option>
                ))}
              </select>

              {districtsList.length > 0 && (
                <div className="mt-2">
                  <select
                    value={filterDistrict}
                    onChange={(e) => setFilterDistrict(e.target.value)}
                    className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-xs font-semibold text-slate-700 focus:outline-none focus:border-blue-600 focus:bg-white"
                  >
                    <option value="">Barcha tumanlar</option>
                    {districtsList.map((d) => (
                      <option key={d} value={d}>{d}</option>
                    ))}
                  </select>
                </div>
              )}
            </div>

            {/* 2. Masofa */}
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="text-[11px] font-extrabold uppercase tracking-wider text-slate-400 block">
                  Masofa
                </label>
                {!userCoords && (
                  <button
                    type="button"
                    onClick={requestUserLocation}
                    className="text-[10px] font-bold text-blue-600 hover:underline"
                  >
                    GPS ni yoqish
                  </button>
                )}
              </div>
              <div className="grid grid-cols-2 gap-1.5">
                {[
                  { label: "1 km", val: "1" },
                  { label: "5 km", val: "5" },
                  { label: "10 km", val: "10" },
                  { label: "25 km", val: "25" },
                  { label: "50 km+", val: "50" },
                ].map((item) => {
                  const isChecked = filterDistance === item.val;
                  return (
                    <button
                      key={item.val}
                      type="button"
                      onClick={() => setFilterDistance(isChecked ? '' : item.val)}
                      className={`py-1.5 px-2 rounded-xl text-xs font-semibold border transition ${
                        isChecked
                          ? 'border-blue-600 bg-blue-50 text-blue-700 font-bold'
                          : 'border-slate-200 bg-slate-50 text-slate-600 hover:border-slate-300'
                      }`}
                    >
                      {item.label}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* 3. Xizmat qiymati (Narx oralig'i) */}
            <div>
              <label className="text-[11px] font-extrabold uppercase tracking-wider text-slate-400 block mb-1.5">
                Xizmat qiymati (so‘m)
              </label>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <input
                    type="number"
                    placeholder="Min narx"
                    value={filterMinPrice}
                    onChange={(e) => setFilterMinPrice(e.target.value)}
                    className="w-full bg-slate-50 border border-slate-200 rounded-xl px-2.5 py-1.5 text-xs text-slate-700 focus:outline-none focus:border-blue-600 focus:bg-white"
                  />
                </div>
                <div>
                  <input
                    type="number"
                    placeholder="Maks narx"
                    value={filterMaxPrice}
                    onChange={(e) => setFilterMaxPrice(e.target.value)}
                    className="w-full bg-slate-50 border border-slate-200 rounded-xl px-2.5 py-1.5 text-xs text-slate-700 focus:outline-none focus:border-blue-600 focus:bg-white"
                  />
                </div>
              </div>
            </div>

            {/* 4. Reyting */}
            <div>
              <label className="text-[11px] font-extrabold uppercase tracking-wider text-slate-400 block mb-1.5">
                Reyting
              </label>
              <div className="space-y-1">
                {[
                  { label: "4.5 va undan yuqori", val: "4.5" },
                  { label: "4.0 va undan yuqori", val: "4.0" },
                  { label: "3.5 va undan yuqori", val: "3.5" },
                ].map((item) => {
                  const isChecked = filterMinRating === item.val;
                  return (
                    <button
                      key={item.val}
                      type="button"
                      onClick={() => setFilterMinRating(isChecked ? '' : item.val)}
                      className={`w-full py-1.5 px-3 rounded-xl text-left border flex items-center justify-between transition ${
                        isChecked
                          ? 'border-amber-400 bg-amber-50 text-amber-900 font-bold'
                          : 'border-slate-200 text-slate-600 hover:border-slate-300'
                      }`}
                    >
                      <span className="flex items-center gap-1.5">
                        <Star className="w-3.5 h-3.5 fill-amber-400 text-amber-400" />
                        {item.label}
                      </span>
                      {isChecked && <Check className="w-3.5 h-3.5 text-amber-600" />}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Apply button */}
            <button
              onClick={applyFilters}
              className="w-full py-2.5 px-4 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded-xl text-xs shadow-md shadow-blue-500/20 transition active:scale-98"
            >
              Filtrni qo‘llash
            </button>
          </div>
        </aside>

        {/* MASTERS GRID CONTAINER */}
        <div className="lg:col-span-3 space-y-4">
          
          {/* Controls Bar: Mobile Filter Button & Sorting */}
          <div className="flex items-center justify-between bg-white p-3 rounded-2xl border border-slate-200/80">
            {/* Mobile Filter Toggle */}
            <button
              onClick={() => setIsMobileFilterOpen(true)}
              className="lg:hidden inline-flex items-center gap-1.5 px-3 py-1.5 bg-slate-100 hover:bg-slate-200 rounded-xl text-xs font-bold text-slate-800 transition"
            >
              <SlidersHorizontal className="w-3.5 h-3.5 text-blue-600" />
              <span>Filtr</span>
              {hasActiveFilters && (
                <span className="w-2 h-2 rounded-full bg-blue-600 inline-block" />
              )}
            </button>

            <span className="hidden sm:inline text-xs text-slate-400 font-medium">
              Ko‘rsatilmoqda: <strong>{masters.length}</strong> ta usta
            </span>

            {/* Sorting Dropdown */}
            <div className="flex items-center gap-2 ml-auto">
              <span className="text-xs text-slate-400 font-medium hidden sm:inline">Saralash:</span>
              <select
                value={orderingParam}
                onChange={(e) => handleSortChange(e.target.value)}
                className="bg-slate-50 border border-slate-200 rounded-xl px-3 py-1.5 text-xs font-bold text-slate-700 focus:outline-none focus:border-blue-600 focus:bg-white"
              >
                <option value="-average_rating">Reyting bo‘yicha</option>
                <option value="price">Arzonroq narx</option>
                <option value="-price">Qimmatroq narx</option>
                <option value="-experience">Ish tajribasi</option>
                <option value="-created_at">Eng yangi</option>
              </select>
            </div>
          </div>

          {/* Cards Grid */}
          {isLoading ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
              {[1, 2, 3, 4, 5, 6].map((n) => (
                <div key={n} className="h-60 bg-slate-100 animate-pulse rounded-3xl" />
              ))}
            </div>
          ) : masters.length > 0 ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
              {masters.map((master) => (
                <MasterCard key={master.id} master={master} />
              ))}
            </div>
          ) : (
            /* Empty State */
            <div className="bg-white rounded-3xl p-12 text-center border border-slate-200/80 space-y-4">
              <div className="w-16 h-16 bg-slate-100 text-slate-400 rounded-2xl flex items-center justify-center mx-auto">
                <Wrench className="w-8 h-8" />
              </div>
              <div className="max-w-sm mx-auto">
                <h3 className="text-lg font-bold text-slate-900">
                  Mos usta topilmadi
                </h3>
                <p className="text-xs text-slate-500 mt-1 leading-relaxed">
                  Siz tanlagan shartlar yoki qidiruv so‘rovi bo‘yicha hech qanday usta topilmadi. Filtr parametrlarini o‘zgartirib ko‘ring.
                </p>
              </div>
              {hasActiveFilters && (
                <button
                  onClick={handleResetFilters}
                  className="inline-flex items-center gap-1.5 px-4 py-2 bg-blue-50 text-blue-600 hover:bg-blue-100 font-bold rounded-xl text-xs transition"
                >
                  <RotateCcw className="w-3.5 h-3.5" />
                  Filtrlarni tozalash
                </button>
              )}
            </div>
          )}

        </div>
      </div>

      {/* MOBILE FILTER DRAWER (BOTTOM-SHEET) */}
      {isMobileFilterOpen && (
        <div className="fixed inset-0 z-50 flex flex-col justify-end lg:hidden bg-slate-900/60 backdrop-blur-sm animate-in fade-in">
          <div className="bg-white rounded-t-3xl max-h-[85vh] overflow-y-auto p-6 space-y-5 shadow-2xl animate-in slide-in-from-bottom">
            
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div className="flex items-center gap-2">
                <Filter className="w-5 h-5 text-blue-600" />
                <h3 className="text-base font-bold text-slate-900">Filtr</h3>
              </div>
              <button
                onClick={() => setIsMobileFilterOpen(false)}
                className="p-2 text-slate-400 hover:text-slate-600 rounded-full hover:bg-slate-100"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Hudud */}
            <div>
              <label className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block mb-1">
                Hudud
              </label>
              <select
                value={filterRegion}
                onChange={(e) => {
                  setFilterRegion(e.target.value);
                  setFilterDistrict('');
                }}
                className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-xs font-semibold text-slate-700"
              >
                <option value="">Barcha viloyatlar</option>
                {locations.map((l) => (
                  <option key={l.region} value={l.region}>{l.region}</option>
                ))}
              </select>

              {districtsList.length > 0 && (
                <select
                  value={filterDistrict}
                  onChange={(e) => setFilterDistrict(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-xs font-semibold text-slate-700 mt-2"
                >
                  <option value="">Barcha tumanlar</option>
                  {districtsList.map((d) => (
                    <option key={d} value={d}>{d}</option>
                  ))}
                </select>
              )}
            </div>

            {/* Masofa */}
            <div>
              <label className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block mb-1">
                Masofa
              </label>
              <div className="grid grid-cols-3 gap-2">
                {[
                  { label: "1 km", val: "1" },
                  { label: "5 km", val: "5" },
                  { label: "10 km", val: "10" },
                  { label: "25 km", val: "25" },
                  { label: "50 km+", val: "50" },
                ].map((item) => (
                  <button
                    key={item.val}
                    type="button"
                    onClick={() => setFilterDistance(filterDistance === item.val ? '' : item.val)}
                    className={`py-2 rounded-xl text-xs font-bold border transition ${
                      filterDistance === item.val
                        ? 'border-blue-600 bg-blue-50 text-blue-700'
                        : 'border-slate-200 text-slate-600'
                    }`}
                  >
                    {item.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Xizmat narxi */}
            <div>
              <label className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block mb-1">
                Xizmat qiymati (so‘m)
              </label>
              <div className="grid grid-cols-2 gap-2">
                <input
                  type="number"
                  placeholder="Min narx"
                  value={filterMinPrice}
                  onChange={(e) => setFilterMinPrice(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-xs"
                />
                <input
                  type="number"
                  placeholder="Maks narx"
                  value={filterMaxPrice}
                  onChange={(e) => setFilterMaxPrice(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-xs"
                />
              </div>
            </div>

            {/* Reyting */}
            <div>
              <label className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block mb-1">
                Reyting
              </label>
              <div className="grid grid-cols-1 gap-1.5">
                {[
                  { label: "4.5 va undan yuqori", val: "4.5" },
                  { label: "4.0 va undan yuqori", val: "4.0" },
                  { label: "3.5 va undan yuqori", val: "3.5" },
                ].map((item) => (
                  <button
                    key={item.val}
                    type="button"
                    onClick={() => setFilterMinRating(filterMinRating === item.val ? '' : item.val)}
                    className={`w-full py-2 px-3 rounded-xl text-left border flex items-center justify-between text-xs transition ${
                      filterMinRating === item.val
                        ? 'border-amber-400 bg-amber-50 text-amber-900 font-bold'
                        : 'border-slate-200 text-slate-600'
                    }`}
                  >
                    <span className="flex items-center gap-1.5">
                      <Star className="w-3.5 h-3.5 fill-amber-400 text-amber-400" />
                      {item.label}
                    </span>
                    {filterMinRating === item.val && <Check className="w-3.5 h-3.5 text-amber-600" />}
                  </button>
                ))}
              </div>
            </div>

            {/* Drawer Actions */}
            <div className="pt-2 flex gap-3">
              <button
                type="button"
                onClick={handleResetFilters}
                className="flex-1 py-3 bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold rounded-2xl text-xs transition"
              >
                Tozalash
              </button>
              <button
                type="button"
                onClick={applyFilters}
                className="flex-1 py-3 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded-2xl text-xs shadow-md shadow-blue-500/20 transition"
              >
                Qo‘llash
              </button>
            </div>

          </div>
        </div>
      )}

    </div>
  );
};
