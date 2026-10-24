import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  Star, MapPin, Phone, MessageSquare, Heart,
  Smartphone, Zap, Hammer, Wrench, ShieldCheck, ChevronRight
} from 'lucide-react';
import { Master } from '../types';
import { useAuth } from '../context/AuthContext';
import { api } from '../api/client';
import { CallModal } from './CallModal';
import { TelegramAvatar } from './TelegramAvatar';

interface MasterCardProps {
  master: Master;
  onFavoriteChange?: (masterId: number, isFav: boolean) => void;
}

export const MasterCard: React.FC<MasterCardProps> = ({ master, onFavoriteChange }) => {
  const { isAuthenticated, openAuthModal, user } = useAuth();
  const [isFavorite, setIsFavorite] = useState(master.is_favorite || false);
  const [isCallModalOpen, setIsCallModalOpen] = useState(false);
  const navigate = useNavigate();

  const handleFavoriteClick = async (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (!isAuthenticated) {
      openAuthModal("Ustalarni saqlab qo‘yish uchun tizimga kiring");
      return;
    }

    try {
      const nextFav = !isFavorite;
      setIsFavorite(nextFav);
      const res = await api.toggleFavorite(master.id);
      setIsFavorite(res.is_favorite);
      if (onFavoriteChange) {
        onFavoriteChange(master.id, res.is_favorite);
      }
    } catch (err) {
      console.error(err);
      setIsFavorite(isFavorite);
    }
  };

  const handleCallClick = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (!isAuthenticated) {
      openAuthModal("Ustaga qo‘ng‘iroq qilish uchun tizimga kiring");
      return;
    }
    setIsCallModalOpen(true);
  };

  const handleChatClick = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (!isAuthenticated) {
      openAuthModal("Usta bilan yozishish uchun tizimga kiring");
      return;
    }
    // Navigate to chat with this master's user id
    navigate(`/chat?user_id=${master.user_id}`);
  };

  // Category Icon and badge styles
  const getCategoryBadge = () => {
    const slug = master.category?.slug || '';
    if (slug === 'phone-repair') {
      return {
        bg: 'bg-blue-50 text-blue-700 border-blue-200/60',
        icon: <Smartphone className="w-3 h-3 text-blue-600" />
      };
    }
    if (slug === 'electrician') {
      return {
        bg: 'bg-amber-50 text-amber-700 border-amber-200/60',
        icon: <Zap className="w-3 h-3 text-amber-600" />
      };
    }
    if (slug === 'builder') {
      return {
        bg: 'bg-emerald-50 text-emerald-700 border-emerald-200/60',
        icon: <Hammer className="w-3 h-3 text-emerald-600" />
      };
    }
    return {
      bg: 'bg-slate-50 text-slate-700 border-slate-200',
      icon: <Wrench className="w-3 h-3 text-slate-500" />
    };
  };

  const badge = getCategoryBadge();
  const avgRating = Number(master.average_rating) || 0;

  return (
    <>
      <div className="bg-white rounded-3xl p-5 border border-slate-200/80 shadow-sm hover:shadow-xl hover:border-blue-300 transition-all duration-200 flex flex-col justify-between group relative">
        
        {/* Top Header: Avatar, Name, Category & Favorite Button */}
        <div>
          <div className="flex items-start justify-between gap-3 mb-3">
            <Link to={`/masters/${master.id}`} className="flex items-center gap-3 min-w-0">
              {/* Telegram-style Avatar */}
              <TelegramAvatar
                src={master.avatar_url}
                name={master.full_name}
                size="md"
                status={master.status}
                showStatus={true}
                clickable={false}
              />

              {/* Name & Experience */}
              <div className="min-w-0">
                <h3 className="text-base font-bold text-slate-900 group-hover:text-blue-600 transition truncate flex items-center gap-1.5">
                  {master.full_name}
                  {master.ratings_count >= 2 && (
                    <span title="Tasdiqlangan usta">
                      <ShieldCheck className="w-4 h-4 text-emerald-500 shrink-0" />
                    </span>
                  )}
                </h3>
                <div className="flex items-center gap-2 mt-0.5">
                  <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-bold border ${badge.bg}`}>
                    {badge.icon}
                    {master.category.name}
                  </span>
                  <span className="text-[11px] text-slate-400 font-medium">
                    {master.experience} yil tajriba
                  </span>
                </div>
              </div>
            </Link>

            {/* Favorite button */}
            <button
              onClick={handleFavoriteClick}
              className={`p-2 rounded-xl transition shrink-0 ${
                isFavorite
                  ? 'bg-rose-50 text-rose-500 hover:bg-rose-100'
                  : 'bg-slate-50 text-slate-400 hover:text-rose-500 hover:bg-slate-100'
              }`}
              title="Saqlash"
            >
              <Heart className={`w-4 h-4 ${isFavorite ? 'fill-rose-500 text-rose-500' : ''}`} />
            </button>
          </div>

          {/* Description snippet */}
          <p className="text-xs text-slate-600 line-clamp-2 mb-3 leading-relaxed">
            {master.description}
          </p>

          {/* Location & Distance badge */}
          <div className="flex items-center flex-wrap gap-2 text-xs text-slate-500 mb-3">
            <span className="inline-flex items-center gap-1 text-slate-600 bg-slate-50 px-2 py-1 rounded-lg">
              <MapPin className="w-3.5 h-3.5 text-slate-400 shrink-0" />
              <span className="truncate max-w-[160px]">
                {master.district ? `${master.district}, ` : ''}{master.region}
              </span>
            </span>

            {master.distance_km !== null && master.distance_km !== undefined && (
              <span className="text-[11px] font-bold text-blue-600 bg-blue-50 px-2 py-0.5 rounded-md">
                ~{master.distance_km} km masofada
              </span>
            )}
          </div>
        </div>

        {/* Bottom Section: Rating, Price, Action buttons */}
        <div className="pt-3 border-t border-slate-100 space-y-3">
          <div className="flex items-center justify-between">
            {/* Rating badge */}
            <div className="flex items-center gap-1.5">
              <div className="flex items-center gap-1 bg-amber-50 text-amber-700 px-2 py-0.5 rounded-lg font-bold text-xs">
                <Star className="w-3.5 h-3.5 fill-amber-400 text-amber-400" />
                <span>{avgRating > 0 ? avgRating.toFixed(1) : "Yangi"}</span>
              </div>
              <span className="text-[11px] text-slate-400 font-medium">
                ({master.ratings_count} ta baho)
              </span>
            </div>

            {/* Price */}
            <div className="text-right">
              <span className="text-[10px] text-slate-400 block font-medium">Xizmat narxi</span>
              <span className="text-sm font-extrabold text-slate-900">
                {master.price.toLocaleString('uz-UZ')} <span className="text-xs font-semibold text-slate-500">so‘mdan</span>
              </span>
            </div>
          </div>

          {/* Action buttons: Profilni ko'rish, Telefon, Yozish */}
          <div className="grid grid-cols-3 gap-1.5 pt-1">
            <Link
              to={`/masters/${master.id}`}
              className="col-span-1 py-2 px-2 text-center text-xs font-bold text-slate-700 bg-slate-100 hover:bg-slate-200 rounded-xl transition flex items-center justify-center gap-1"
            >
              <span>Profil</span>
              <ChevronRight className="w-3.5 h-3.5 text-slate-400" />
            </Link>

            <button
              onClick={handleCallClick}
              className="col-span-1 py-2 px-2 text-xs font-bold text-emerald-700 bg-emerald-50 hover:bg-emerald-100 rounded-xl transition flex items-center justify-center gap-1"
            >
              <Phone className="w-3.5 h-3.5 text-emerald-600" />
              <span>Telefon</span>
            </button>

            <button
              onClick={handleChatClick}
              className="col-span-1 py-2 px-2 text-xs font-bold text-blue-700 bg-blue-50 hover:bg-blue-100 rounded-xl transition flex items-center justify-center gap-1"
            >
              <MessageSquare className="w-3.5 h-3.5 text-blue-600" />
              <span>Yozish</span>
            </button>
          </div>
        </div>

      </div>

      {/* Call Modal */}
      {isCallModalOpen && (
        <CallModal master={master} onClose={() => setIsCallModalOpen(false)} />
      )}
    </>
  );
};
