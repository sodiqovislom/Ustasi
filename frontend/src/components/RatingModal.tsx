import React, { useState } from 'react';
import { Star, X, Loader2, CheckCircle2, AlertCircle } from 'lucide-react';
import { Master } from '../types';
import { api } from '../api/client';

interface RatingModalProps {
  master: Master;
  onClose: () => void;
  onSuccess: (updatedAvg: number, count: number) => void;
}

export const RatingModal: React.FC<RatingModalProps> = ({ master, onClose, onSuccess }) => {
  const [score, setScore] = useState<number>(5);
  const [hoverScore, setHoverScore] = useState<number>(0);
  const [comment, setComment] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isSuccess, setIsSuccess] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);
    setIsSubmitting(true);

    try {
      const res = await api.rateMaster(master.id, score, comment);
      setIsSuccess(true);
      setTimeout(() => {
        onSuccess(res.average_rating, res.ratings_count);
        onClose();
      }, 1400);
    } catch (err: any) {
      setErrorMessage(err.message || "Baho yuborishda xatolik yuz berdi.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const getScoreLabel = (val: number) => {
    switch (val) {
      case 5: return "Ajoyib! Juda mamnunman";
      case 4: return "Yaxshi, tavsiya qilaman";
      case 3: return "Qoniqarli, o'rtacha";
      case 2: return "Yomon, kamchiliklari bor";
      case 1: return "Juda yomon, noroziman";
      default: return "";
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-in fade-in">
      <div className="bg-white rounded-3xl max-w-md w-full p-6 shadow-2xl border border-slate-100 relative animate-in zoom-in-95">
        
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-2 text-slate-400 hover:text-slate-600 rounded-full hover:bg-slate-100 transition"
        >
          <X className="w-5 h-5" />
        </button>

        {isSuccess ? (
          <div className="text-center py-8">
            <CheckCircle2 className="w-16 h-16 text-emerald-500 mx-auto mb-3 animate-bounce" />
            <h3 className="text-xl font-bold text-slate-900">Rahmat!</h3>
            <p className="text-sm text-slate-500 mt-1">
              Bahoyingiz muvaffaqiyatli saqlandi va ustaning umumiy reytingida hisobga olindi.
            </p>
          </div>
        ) : (
          <div>
            <div className="text-center mb-6">
              <h3 className="text-lg font-bold text-slate-900">
                Ustaga baho berish
              </h3>
              <p className="text-xs text-slate-500 mt-1">
                {master.full_name} ({master.category.name})
              </p>
            </div>

            {errorMessage && (
              <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-2xl flex items-center gap-2.5 text-xs text-red-700">
                <AlertCircle className="w-4 h-4 shrink-0 text-red-500" />
                <span>{errorMessage}</span>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-5">
              {/* Star Rating Selector */}
              <div className="flex flex-col items-center gap-2">
                <div className="flex items-center gap-1.5">
                  {[1, 2, 3, 4, 5].map((star) => {
                    const active = (hoverScore || score) >= star;
                    return (
                      <button
                        key={star}
                        type="button"
                        onClick={() => setScore(star)}
                        onMouseEnter={() => setHoverScore(star)}
                        onMouseLeave={() => setHoverScore(0)}
                        className="p-1 focus:outline-none transition transform hover:scale-110"
                      >
                        <Star
                          className={`w-9 h-9 ${
                            active
                              ? 'text-amber-400 fill-amber-400'
                              : 'text-slate-200 hover:text-amber-200'
                          } transition-colors`}
                        />
                      </button>
                    );
                  })}
                </div>
                <span className="text-xs font-bold text-amber-600 h-4">
                  {getScoreLabel(hoverScore || score)}
                </span>
              </div>

              {/* Comment text */}
              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1.5">
                  Fikringiz yoki sharhingiz (ixtiyoriy)
                </label>
                <textarea
                  value={comment}
                  onChange={(e) => setComment(e.target.value)}
                  placeholder="Usta haqida taassurotingizni yozing..."
                  rows={3}
                  className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-2xl text-xs sm:text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600 transition resize-none"
                />
              </div>

              {/* Action buttons */}
              <div className="flex items-center gap-3">
                <button
                  type="button"
                  onClick={onClose}
                  className="flex-1 py-3 px-4 bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold rounded-2xl text-xs transition"
                >
                  Bekor qilish
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="flex-1 py-3 px-4 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded-2xl text-xs shadow-md shadow-blue-600/20 flex items-center justify-center gap-2 transition disabled:opacity-50"
                >
                  {isSubmitting ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Yuborilmoqda...
                    </>
                  ) : (
                    "Bahoni saqlash"
                  )}
                </button>
              </div>

            </form>
          </div>
        )}

      </div>
    </div>
  );
};
