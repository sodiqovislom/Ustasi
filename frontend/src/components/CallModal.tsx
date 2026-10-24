import React, { useState } from 'react';
import { Phone, Copy, Check, X, Clock, ShieldCheck } from 'lucide-react';
import { Master } from '../types';

interface CallModalProps {
  master: Master;
  onClose: () => void;
}

export const CallModal: React.FC<CallModalProps> = ({ master, onClose }) => {
  const [copied, setCopied] = useState(false);

  const phone = master.phone || "+998 90 000 00 00";

  const handleCopy = () => {
    navigator.clipboard.writeText(phone);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-in fade-in">
      <div className="bg-white rounded-3xl max-w-sm w-full p-6 shadow-2xl border border-slate-100 relative animate-in zoom-in-95">
        
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-2 text-slate-400 hover:text-slate-600 rounded-full hover:bg-slate-100 transition"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="text-center pt-2 pb-4">
          <div className="w-14 h-14 bg-emerald-100 text-emerald-600 rounded-2xl flex items-center justify-center mx-auto mb-3 shadow-inner">
            <Phone className="w-7 h-7" />
          </div>

          <h3 className="text-lg font-bold text-slate-900">
            {master.full_name}
          </h3>
          <p className="text-xs text-blue-600 font-semibold mb-1">
            {master.category.name}
          </p>
          <p className="text-xs text-slate-500 flex items-center justify-center gap-1">
            <Clock className="w-3.5 h-3.5 text-slate-400" />
            {master.working_hours}
          </p>
        </div>

        {/* Big Phone Number Box */}
        <div className="bg-slate-50 border border-slate-200/80 rounded-2xl p-4 text-center my-2">
          <span className="text-xs text-slate-400 font-medium block mb-1">Usta telefon raqami:</span>
          <span className="text-xl sm:text-2xl font-black text-slate-900 tracking-wide select-all font-mono">
            {phone}
          </span>
        </div>

        {/* Action Buttons */}
        <div className="space-y-2 mt-4">
          <a
            href={`tel:${phone.replace(/\s+/g, '')}`}
            className="w-full py-3 px-4 bg-emerald-600 hover:bg-emerald-700 text-white font-bold rounded-2xl shadow-md shadow-emerald-600/20 flex items-center justify-center gap-2 transition active:scale-98"
          >
            <Phone className="w-4 h-4" />
            Qo‘ng‘iroq qilish
          </a>

          <button
            onClick={handleCopy}
            className="w-full py-3 px-4 bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold rounded-2xl flex items-center justify-center gap-2 transition"
          >
            {copied ? (
              <>
                <Check className="w-4 h-4 text-emerald-600" />
                <span className="text-emerald-700 font-bold">Nusxa olindi!</span>
              </>
            ) : (
              <>
                <Copy className="w-4 h-4 text-slate-500" />
                Raqamdan nusxa olish
              </>
            )}
          </button>
        </div>

        <p className="text-[11px] text-center text-slate-400 mt-4 flex items-center justify-center gap-1">
          <ShieldCheck className="w-3.5 h-3.5 text-emerald-500" />
          Qo‘ng‘iroq paytida o‘zingizni "Ustasi" orqali topganingizni ayting
        </p>

      </div>
    </div>
  );
};
