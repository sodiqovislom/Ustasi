import React from 'react';
import { Link } from 'react-router-dom';
import { Wrench, Phone, ShieldCheck, Heart } from 'lucide-react';

export const Footer: React.FC = () => {
  return (
    <footer className="bg-white border-t border-slate-200 mt-20 pt-12 pb-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8 pb-10 border-b border-slate-100">
          
          {/* Brand Info */}
          <div className="md:col-span-1 space-y-3">
            <div className="flex items-center gap-2 group">
              <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center text-white">
                <Wrench className="w-4 h-4" />
              </div>
              <span className="text-lg font-extrabold text-slate-900">
                Ustasi<span className="text-blue-600">.uz</span>
              </span>
            </div>
            <p className="text-xs text-slate-500 leading-relaxed">
              O‘zbekistonda usta topishning eng sodda va ishonchli xizmati. Kerakli mutaxassisni bir necha soniyada toping.
            </p>
          </div>

          {/* Categories */}
          <div>
            <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider mb-3">
              Asosiy xizmatlar
            </h4>
            <ul className="space-y-2 text-xs text-slate-600">
              <li>
                <Link to="/masters?category=phone-repair" className="hover:text-blue-600 transition">
                  Telefon ustasi
                </Link>
              </li>
              <li>
                <Link to="/masters?category=electrician" className="hover:text-blue-600 transition">
                  Elektrik
                </Link>
              </li>
              <li>
                <Link to="/masters?category=builder" className="hover:text-blue-600 transition">
                  Quruvchi
                </Link>
              </li>
            </ul>
          </div>

          {/* Hududlar */}
          <div>
            <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider mb-3">
              Katta hududlar
            </h4>
            <ul className="space-y-2 text-xs text-slate-600">
              <li>
                <Link to="/masters?region=Toshkent" className="hover:text-blue-600 transition">
                  Toshkent shahri
                </Link>
              </li>
              <li>
                <Link to="/masters?region=Samarqand" className="hover:text-blue-600 transition">
                  Samarqand viloyati
                </Link>
              </li>
              <li>
                <Link to="/masters?region=Farg'ona" className="hover:text-blue-600 transition">
                  Farg'ona vodiysi
                </Link>
              </li>
              <li>
                <Link to="/masters?region=Buxoro" className="hover:text-blue-600 transition">
                  Buxoro viloyati
                </Link>
              </li>
            </ul>
          </div>

          {/* Ustalar uchun */}
          <div>
            <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider mb-3">
              Ustalar uchun
            </h4>
            <p className="text-xs text-slate-500 mb-3">
              O‘z xizmatingizni bepul joylang va hududingizdagi yangi mijozlar bilan bog‘laning.
            </p>
            <Link
              to="/become-master"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold text-blue-600 bg-blue-50 hover:bg-blue-100 rounded-lg transition"
            >
              Usta sifatida ro‘yxatdan o‘tish
            </Link>
          </div>

        </div>

        {/* Bottom copyright */}
        <div className="pt-6 flex flex-col sm:flex-row items-center justify-between text-xs text-slate-400 gap-2">
          <p>© {new Date().getFullYear()} Ustasi. Barcha huquqlar himoyalangan.</p>
          <p className="flex items-center gap-1">
            <ShieldCheck className="w-4 h-4 text-emerald-500" />
            Xavfsiz va tekshirilgan ustalar
          </p>
        </div>
      </div>
    </footer>
  );
};
