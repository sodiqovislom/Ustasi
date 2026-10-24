import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import {
  Wrench, Phone, Mail, Lock, User, AlertCircle, Loader2, CheckCircle, ShieldCheck
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export const AuthPage: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { isAuthenticated, login, register } = useAuth();

  const isRegisterRoute = location.pathname.includes('/register');
  const [mode, setMode] = useState<'login' | 'register'>(isRegisterRoute ? 'register' : 'login');
  const [role, setRole] = useState<'client' | 'master'>('client');
  const [authMethod, setAuthMethod] = useState<'phone' | 'email'>('phone');

  // Form State
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [phone, setPhone] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [passwordConfirm, setPasswordConfirm] = useState('');

  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    if (isAuthenticated) {
      navigate('/');
    }
  }, [isAuthenticated, navigate]);

  useEffect(() => {
    setMode(location.pathname.includes('/register') ? 'register' : 'login');
    setErrorMessage(null);
  }, [location.pathname]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);
    setIsLoading(true);

    try {
      if (mode === 'login') {
        const loginIdentifier = authMethod === 'phone' ? phone.trim() : email.trim();
        if (!loginIdentifier || !password) {
          setErrorMessage("Login va parolni kiriting.");
          setIsLoading(false);
          return;
        }
        await login({ login: loginIdentifier, password });
        navigate('/');
      } else {
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

        if (role === 'master') {
          navigate('/become-master');
        } else {
          navigate('/');
        }
      }
    } catch (err: any) {
      setErrorMessage(err.message || "Xatolik yuz berdi. Iltimos tekshirib qaytadan urinib ko‘ring.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-[75vh] flex items-center justify-center px-4 py-12">
      <div className="bg-white rounded-3xl p-8 max-w-md w-full border border-slate-200/90 shadow-xl space-y-6">
        
        {/* Brand Logo & Header */}
        <div className="text-center space-y-2">
          <Link to="/" className="inline-flex items-center gap-2 group">
            <div className="w-10 h-10 rounded-xl bg-blue-600 flex items-center justify-center text-white shadow-md shadow-blue-500/20">
              <Wrench className="w-5 h-5" />
            </div>
            <span className="text-xl font-black text-slate-900">
              Ustasi<span className="text-blue-600">.uz</span>
            </span>
          </Link>
          <h2 className="text-lg font-bold text-slate-900">
            {mode === 'login' ? "Tizimga kirish" : "Ro‘yxatdan o‘tish"}
          </h2>
          <p className="text-xs text-slate-500">
            Platformaning barcha imkoniyatlaridan to‘liq foydalaning
          </p>
        </div>

        {/* Mode Selector Tabs */}
        <div className="flex bg-slate-100 p-1 rounded-2xl text-xs font-bold">
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

        {/* If Register: Role selector */}
        {mode === 'register' && (
          <div>
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

        {/* Input Method Selector */}
        <div className="flex items-center gap-3 text-xs font-semibold text-slate-500">
          <span className="text-[11px] font-bold uppercase tracking-wider text-slate-400">Usul:</span>
          <button
            type="button"
            onClick={() => { setAuthMethod('phone'); setErrorMessage(null); }}
            className={`flex items-center gap-1.5 px-3 py-1 rounded-lg transition ${
              authMethod === 'phone' ? 'bg-slate-200 text-slate-900 font-bold' : 'hover:bg-slate-100 text-slate-500'
            }`}
          >
            <Phone className="w-3.5 h-3.5" />
            Telefon
          </button>
          <button
            type="button"
            onClick={() => { setAuthMethod('email'); setErrorMessage(null); }}
            className={`flex items-center gap-1.5 px-3 py-1 rounded-lg transition ${
              authMethod === 'email' ? 'bg-slate-200 text-slate-900 font-bold' : 'hover:bg-slate-100 text-slate-500'
            }`}
          >
            <Mail className="w-3.5 h-3.5" />
            Email
          </button>
        </div>

        {/* Error Notification */}
        {errorMessage && (
          <div className="p-3 bg-red-50 border border-red-200 rounded-2xl flex items-center gap-2.5 text-xs text-red-700 animate-in fade-in">
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
                <input
                  type="text"
                  required
                  value={firstName}
                  onChange={(e) => setFirstName(e.target.value)}
                  placeholder="Ali"
                  className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:border-blue-600 focus:bg-white"
                />
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
                  className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:border-blue-600 focus:bg-white"
                />
              </div>
            </div>
          )}

          {authMethod === 'phone' ? (
            <div>
              <label className="text-[11px] font-bold text-slate-600 block mb-1">
                Telefon raqami *
              </label>
              <input
                type="tel"
                required
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                placeholder="+998 90 123 45 67"
                className="w-full px-3.5 py-2.5 text-xs bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:border-blue-600 focus:bg-white font-mono"
              />
            </div>
          ) : (
            <div>
              <label className="text-[11px] font-bold text-slate-600 block mb-1">
                Elektron pochta *
              </label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="misol@ustasi.uz"
                className="w-full px-3.5 py-2.5 text-xs bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:border-blue-600 focus:bg-white"
              />
            </div>
          )}

          <div>
            <label className="text-[11px] font-bold text-slate-600 block mb-1">
              Parol *
            </label>
            <input
              type="password"
              required
              minLength={6}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Kamida 6 ta belgi"
              className="w-full px-3.5 py-2.5 text-xs bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:border-blue-600 focus:bg-white"
            />
          </div>

          {mode === 'register' && (
            <div>
              <label className="text-[11px] font-bold text-slate-600 block mb-1">
                Parolni qaytaring *
              </label>
              <input
                type="password"
                required
                value={passwordConfirm}
                onChange={(e) => setPasswordConfirm(e.target.value)}
                placeholder="Parolni qayta tering"
                className="w-full px-3.5 py-2.5 text-xs bg-slate-50 border border-slate-200 rounded-xl focus:outline-none focus:border-blue-600 focus:bg-white"
              />
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

      </div>
    </div>
  );
};
