import React, { useState } from 'react';
import { X, Phone, Mail, Lock, User, AlertCircle, Loader2, Wrench, CheckCircle } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export const AuthModal: React.FC = () => {
  const { isAuthModalOpen, authModalActionReason, authModalMode, closeAuthModal, login, register } = useAuth();
  
  const [mode, setMode] = useState<'login' | 'register'>(authModalMode || 'login');
  const [role, setRole] = useState<'client' | 'master'>('client');
  const [authMethod, setAuthMethod] = useState<'phone' | 'email'>('phone');

  // Form states
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [phone, setPhone] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [passwordConfirm, setPasswordConfirm] = useState('');

  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Sync mode when modal opens with specified mode
  React.useEffect(() => {
    if (authModalMode) {
      setMode(authModalMode);
    }
    setErrorMessage(null);
  }, [authModalMode, isAuthModalOpen]);

  if (!isAuthModalOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);
    setIsLoading(true);

    try {
      if (mode === 'login') {
        const loginIdentifier = authMethod === 'phone' ? phone.trim() : email.trim();
        if (!loginIdentifier || !password) {
          setErrorMessage("Login va parolni to‘liq kiriting.");
          setIsLoading(false);
          return;
        }
        await login({ login: loginIdentifier, password });
      } else {
        // Registration
        if (!firstName.trim()) {
          setErrorMessage("Ismingizni kiriting.");
          setIsLoading(false);
          return;
        }
        if (authMethod === 'phone' && !phone.trim()) {
          setErrorMessage("Telefon raqamingizni kiriting.");
          setIsLoading(false);
          return;
        }
        if (authMethod === 'email' && !email.trim()) {
          setErrorMessage("Elektron pochtangizni kiriting.");
          setIsLoading(false);
          return;
        }
        if (password.length < 6) {
          setErrorMessage("Parol kamida 6 ta belgidan iborat bo‘lishi kerak.");
          setIsLoading(false);
          return;
        }
        if (password !== passwordConfirm) {
          setErrorMessage("Kiritilgan parollar bir-biriga mos kelmadi.");
          setIsLoading(false);
          return;
        }

        await register({
          first_name: firstName.trim(),
          last_name: lastName.trim(),
          phone: authMethod === 'phone' ? phone.trim() : undefined,
          email: authMethod === 'email' ? email.trim() : undefined,
          password,
          role,
        });
      }
    } catch (err: any) {
      setErrorMessage(err.message || "Xatolik yuz berdi. Iltimos, ma'lumotlarni tekshiring.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-in fade-in">
      <div className="bg-white rounded-3xl max-w-md w-full p-6 shadow-2xl border border-slate-100 relative max-h-[92vh] overflow-y-auto">
        
        {/* Close Button */}
        <button
          onClick={closeAuthModal}
          className="absolute top-4 right-4 p-2 text-slate-400 hover:text-slate-600 rounded-full hover:bg-slate-100 transition"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Modal Header */}
        <div className="text-center pt-1 pb-4">
          <div className="w-12 h-12 bg-blue-50 text-blue-600 rounded-2xl flex items-center justify-center mx-auto mb-3 shadow-inner">
            <Wrench className="w-6 h-6" />
          </div>
          <h3 className="text-xl font-extrabold text-slate-900">
            {mode === 'login' ? "Tizimga kirish" : "Ro‘yxatdan o‘tish"}
          </h3>
          {authModalActionReason ? (
            <p className="text-xs text-amber-600 font-semibold bg-amber-50 rounded-xl py-1 px-3 mt-2 inline-block">
              {authModalActionReason}
            </p>
          ) : (
            <p className="text-xs text-slate-500 mt-1">
              Ustasi platformasi imkoniyatlaridan to‘liq foydalaning
            </p>
          )}
        </div>

        {/* Switch Mode Tabs (Kirish / Ro'yxatdan o'tish) */}
        <div className="flex bg-slate-100 p-1 rounded-2xl mb-4 text-xs font-bold">
          <button
            type="button"
            onClick={() => { setMode('login'); setErrorMessage(null); }}
            className={`flex-1 py-2 rounded-xl transition ${
              mode === 'login' ? 'bg-white text-blue-600 shadow-sm' : 'text-slate-500 hover:text-slate-900'
            }`}
          >
            Kirish
          </button>
          <button
            type="button"
            onClick={() => { setMode('register'); setErrorMessage(null); }}
            className={`flex-1 py-2 rounded-xl transition ${
              mode === 'register' ? 'bg-white text-blue-600 shadow-sm' : 'text-slate-500 hover:text-slate-900'
            }`}
          >
            Ro‘yxatdan o‘tish
          </button>
        </div>

        {/* Register Role Selector (Siz kimsiz?) */}
        {mode === 'register' && (
          <div className="mb-4">
            <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block mb-1.5">
              Siz kimsiz?
            </span>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => setRole('client')}
                className={`py-2 px-3 rounded-xl border text-xs font-bold text-left transition flex items-center justify-between ${
                  role === 'client'
                    ? 'border-blue-600 bg-blue-50/50 text-blue-700 shadow-sm'
                    : 'border-slate-200 text-slate-600 hover:border-slate-300'
                }`}
              >
                <span>Foydalanuvchi</span>
                {role === 'client' && <CheckCircle className="w-3.5 h-3.5 text-blue-600" />}
              </button>
              <button
                type="button"
                onClick={() => setRole('master')}
                className={`py-2 px-3 rounded-xl border text-xs font-bold text-left transition flex items-center justify-between ${
                  role === 'master'
                    ? 'border-blue-600 bg-blue-50/50 text-blue-700 shadow-sm'
                    : 'border-slate-200 text-slate-600 hover:border-slate-300'
                }`}
              >
                <span>Usta</span>
                {role === 'master' && <CheckCircle className="w-3.5 h-3.5 text-blue-600" />}
              </button>
            </div>
          </div>
        )}

        {/* Input Method Selector (Telefon / Email) */}
        <div className="flex items-center gap-3 mb-4 text-xs font-semibold text-slate-500">
          <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">Usul:</span>
          <button
            type="button"
            onClick={() => { setAuthMethod('phone'); setErrorMessage(null); }}
            className={`flex items-center gap-1.5 px-3 py-1 rounded-lg transition ${
              authMethod === 'phone' ? 'bg-slate-200 text-slate-900 font-bold' : 'hover:bg-slate-100 text-slate-500'
            }`}
          >
            <Phone className="w-3.5 h-3.5" />
            Telefon orqali
          </button>
          <button
            type="button"
            onClick={() => { setAuthMethod('email'); setErrorMessage(null); }}
            className={`flex items-center gap-1.5 px-3 py-1 rounded-lg transition ${
              authMethod === 'email' ? 'bg-slate-200 text-slate-900 font-bold' : 'hover:bg-slate-100 text-slate-500'
            }`}
          >
            <Mail className="w-3.5 h-3.5" />
            Elektron pochta
          </button>
        </div>

        {/* Error message notification */}
        {errorMessage && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-2xl flex items-center gap-2.5 text-xs text-red-700 animate-in fade-in">
            <AlertCircle className="w-4 h-4 shrink-0 text-red-500" />
            <span>{errorMessage}</span>
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-3.5">
          {mode === 'register' && (
            <div className="grid grid-cols-2 gap-2.5">
              <div>
                <label className="text-[11px] font-bold text-slate-600 block mb-1">
                  Ism *
                </label>
                <div className="relative">
                  <User className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                  <input
                    type="text"
                    required
                    value={firstName}
                    onChange={(e) => setFirstName(e.target.value)}
                    placeholder="Ali"
                    className="w-full pl-9 pr-3 py-2 text-xs bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:border-blue-600 focus:bg-white transition"
                  />
                </div>
              </div>
              <div>
                <label className="text-[11px] font-bold text-slate-600 block mb-1">
                  Familiya
                </label>
                <input
                  type="text"
                  value={lastName}
                  onChange={(e) => setLastName(e.target.value)}
                  placeholder="Valiyev"
                  className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:border-blue-600 focus:bg-white transition"
                />
              </div>
            </div>
          )}

          {authMethod === 'phone' ? (
            <div>
              <label className="text-[11px] font-bold text-slate-600 block mb-1">
                Telefon raqami *
              </label>
              <div className="relative">
                <Phone className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="tel"
                  required
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  placeholder="+998 90 123 45 67"
                  className="w-full pl-9 pr-3 py-2.5 text-xs bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:border-blue-600 focus:bg-white transition font-mono"
                />
              </div>
            </div>
          ) : (
            <div>
              <label className="text-[11px] font-bold text-slate-600 block mb-1">
                Elektron pochta *
              </label>
              <div className="relative">
                <Mail className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="misol@ustasi.uz"
                  className="w-full pl-9 pr-3 py-2.5 text-xs bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:border-blue-600 focus:bg-white transition"
                />
              </div>
            </div>
          )}

          <div>
            <label className="text-[11px] font-bold text-slate-600 block mb-1">
              Parol *
            </label>
            <div className="relative">
              <Lock className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="password"
                required
                minLength={6}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Kamida 6 ta belgi"
                className="w-full pl-9 pr-3 py-2.5 text-xs bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:border-blue-600 focus:bg-white transition"
              />
            </div>
          </div>

          {mode === 'register' && (
            <div>
              <label className="text-[11px] font-bold text-slate-600 block mb-1">
                Parolni qaytaring *
              </label>
              <div className="relative">
                <Lock className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="password"
                  required
                  value={passwordConfirm}
                  onChange={(e) => setPasswordConfirm(e.target.value)}
                  placeholder="Parolni qayta tering"
                  className="w-full pl-9 pr-3 py-2.5 text-xs bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:border-blue-600 focus:bg-white transition"
                />
              </div>
            </div>
          )}

          <button
            type="submit"
            disabled={isLoading}
            className="w-full py-3 px-4 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded-2xl shadow-md shadow-blue-500/25 flex items-center justify-center gap-2 transition active:scale-98 disabled:opacity-50 mt-4 text-xs"
          >
            {isLoading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : mode === 'login' ? (
              "Kirish"
            ) : (
              "Ro‘yxatdan o‘tish"
            )}
          </button>
        </form>

        <p className="text-[11px] text-center text-slate-400 mt-4">
          {mode === 'login' ? (
            <>
              Hisobingiz yo‘qmi?{' '}
              <button
                type="button"
                onClick={() => { setMode('register'); setErrorMessage(null); }}
                className="text-blue-600 font-bold hover:underline"
              >
                Ro‘yxatdan o‘ting
              </button>
            </>
          ) : (
            <>
              Akkauntingiz bormi?{' '}
              <button
                type="button"
                onClick={() => { setMode('login'); setErrorMessage(null); }}
                className="text-blue-600 font-bold hover:underline"
              >
                Tizimga kiring
              </button>
            </>
          )}
        </p>

      </div>
    </div>
  );
};
