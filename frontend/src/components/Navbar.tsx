import React, { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import {
  Wrench, MessageSquare, User as UserIcon, LogOut,
  Menu, X, Briefcase, PlusCircle, Bookmark, Star
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { TelegramAvatar } from './TelegramAvatar';

export const Navbar: React.FC = () => {
  const { user, isAuthenticated, isMaster, logout, openAuthModal } = useAuth();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();

  const handleLogout = () => {
    logout();
    setIsUserMenuOpen(false);
    setIsMobileMenuOpen(false);
    navigate('/');
  };

  const isActive = (path: string) => location.pathname === path;

  return (
    <header className="sticky top-0 z-40 bg-white/95 backdrop-blur-md border-b border-slate-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          
          {/* Logo */}
          <Link to="/" className="flex items-center gap-2.5 group">
            <div className="w-10 h-10 rounded-xl bg-blue-600 flex items-center justify-center text-white shadow-md shadow-blue-500/20 group-hover:bg-blue-700 transition">
              <Wrench className="w-5 h-5 transition-transform group-hover:rotate-12" />
            </div>
            <div className="flex flex-col">
              <span className="text-xl font-extrabold tracking-tight text-slate-900 leading-none">
                Ustasi<span className="text-blue-600">.uz</span>
              </span>
              <span className="text-[11px] font-medium text-slate-400 leading-tight">
                Xizmatlar platformasi
              </span>
            </div>
          </Link>

          {/* Desktop Navigation */}
          <nav className="hidden md:flex items-center gap-6">
            <Link
              to="/masters"
              className={`text-sm font-semibold transition ${
                isActive('/masters') ? 'text-blue-600' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              Ustalarni qidirish
            </Link>

            {/* If not a master, show "Usta bo'lish" */}
            {!isMaster && (
              <Link
                to="/become-master"
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-blue-700 bg-blue-50 hover:bg-blue-100 rounded-lg border border-blue-200/60 transition"
              >
                <PlusCircle className="w-3.5 h-3.5" />
                Usta bo‘lish
              </Link>
            )}

            {isMaster && (
              <Link
                to="/master/dashboard"
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-emerald-700 bg-emerald-50 hover:bg-emerald-100 rounded-lg border border-emerald-200/60 transition"
              >
                <Briefcase className="w-3.5 h-3.5" />
                Usta kabineti
              </Link>
            )}
          </nav>

          {/* Right Action buttons */}
          <div className="hidden md:flex items-center gap-3">
            {isAuthenticated ? (
              <div className="flex items-center gap-3">
                {/* Chat button */}
                <Link
                  to="/chat"
                  className="relative p-2 text-slate-600 hover:text-blue-600 hover:bg-slate-100 rounded-xl transition"
                  title="Xabarlar"
                >
                  <MessageSquare className="w-5 h-5" />
                </Link>

                {/* User menu dropdown */}
                <div className="relative">
                  <button
                    onClick={() => setIsUserMenuOpen(!isUserMenuOpen)}
                    className="flex items-center gap-2 pl-1.5 pr-3 py-1 rounded-full border border-slate-200 hover:border-slate-300 hover:bg-slate-50 transition"
                  >
                    <TelegramAvatar
                      src={user?.avatar_url}
                      name={user?.full_name || 'U'}
                      size="xs"
                      clickable={false}
                    />
                    <span className="text-xs font-semibold text-slate-700 max-w-[100px] truncate">
                      {user?.first_name}
                    </span>
                  </button>

                  {/* Dropdown popup */}
                  {isUserMenuOpen && (
                    <div className="absolute right-0 mt-2 w-60 bg-white rounded-2xl shadow-xl border border-slate-100 py-2 z-50 animate-in fade-in slide-in-from-top-2">
                      <div className="px-4 py-3 border-b border-slate-100 flex items-center gap-3">
                        <TelegramAvatar
                          src={user?.avatar_url}
                          name={user?.full_name || 'U'}
                          size="sm"
                          clickable={false}
                        />
                        <div className="min-w-0">
                          <p className="text-sm font-bold text-slate-800 truncate">{user?.full_name}</p>
                          <p className="text-[11px] text-slate-400 truncate">{user?.phone || user?.email}</p>
                          <span className="inline-block mt-0.5 px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider rounded bg-slate-100 text-slate-600">
                            {user?.role === 'master' ? 'Usta' : 'Foydalanuvchi'}
                          </span>
                        </div>
                      </div>

                      <div className="py-1">
                        <Link
                          to="/cabinet"
                          onClick={() => setIsUserMenuOpen(false)}
                          className="flex items-center gap-2 px-4 py-2 text-xs font-medium text-slate-700 hover:bg-slate-50 hover:text-blue-600 transition"
                        >
                          <UserIcon className="w-4 h-4 text-slate-400" />
                          Mening profilim
                        </Link>

                        <Link
                          to="/cabinet?tab=saved"
                          onClick={() => setIsUserMenuOpen(false)}
                          className="flex items-center gap-2 px-4 py-2 text-xs font-medium text-slate-700 hover:bg-slate-50 hover:text-blue-600 transition"
                        >
                          <Bookmark className="w-4 h-4 text-slate-400" />
                          Saqlangan ustalar
                        </Link>

                        <Link
                          to="/cabinet?tab=ratings"
                          onClick={() => setIsUserMenuOpen(false)}
                          className="flex items-center gap-2 px-4 py-2 text-xs font-medium text-slate-700 hover:bg-slate-50 hover:text-blue-600 transition"
                        >
                          <Star className="w-4 h-4 text-slate-400" />
                          Baholagan ustalarim
                        </Link>

                        {isMaster && (
                          <Link
                            to="/master/dashboard"
                            onClick={() => setIsUserMenuOpen(false)}
                            className="flex items-center gap-2 px-4 py-2 text-xs font-semibold text-emerald-700 hover:bg-emerald-50 transition"
                          >
                            <Briefcase className="w-4 h-4 text-emerald-600" />
                            Usta kabineti
                          </Link>
                        )}
                      </div>

                      <div className="pt-1 border-t border-slate-100">
                        <button
                          onClick={handleLogout}
                          className="flex items-center gap-2 w-full px-4 py-2 text-xs font-medium text-red-600 hover:bg-red-50 transition"
                        >
                          <LogOut className="w-4 h-4" />
                          Chiqish
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <button
                  onClick={() => openAuthModal("Xizmatlardan to'liq foydalanish uchun kiring", "login")}
                  className="px-3.5 py-2 text-xs font-semibold text-slate-700 hover:text-blue-600 hover:bg-slate-100 rounded-xl transition"
                >
                  Kirish
                </button>
                <button
                  onClick={() => openAuthModal("Ro'yxatdan o'ting va usta toping", "register")}
                  className="px-4 py-2 text-xs font-bold text-white bg-blue-600 hover:bg-blue-700 rounded-xl shadow-sm transition active:scale-95"
                >
                  Ro‘yxatdan o‘tish
                </button>
              </div>
            )}
          </div>

          {/* Mobile hamburger */}
          <div className="flex items-center gap-2 md:hidden">
            {isAuthenticated && (
              <Link
                to="/chat"
                className="p-2 text-slate-600 hover:text-blue-600 rounded-lg"
              >
                <MessageSquare className="w-5 h-5" />
              </Link>
            )}
            <button
              onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
              className="p-2 text-slate-600 hover:text-slate-900 rounded-lg"
            >
              {isMobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile Drawer Menu */}
      {isMobileMenuOpen && (
        <div className="md:hidden border-t border-slate-200 bg-white px-4 pt-3 pb-6 space-y-3">
          <Link
            to="/masters"
            onClick={() => setIsMobileMenuOpen(false)}
            className="block px-3 py-2 rounded-xl text-base font-medium text-slate-800 hover:bg-slate-50"
          >
            Ustalarni qidirish
          </Link>

          {!isMaster && (
            <Link
              to="/become-master"
              onClick={() => setIsMobileMenuOpen(false)}
              className="block px-3 py-2 rounded-xl text-base font-semibold text-blue-600 bg-blue-50"
            >
              Usta bo‘lish
            </Link>
          )}

          {isMaster && (
            <Link
              to="/master/dashboard"
              onClick={() => setIsMobileMenuOpen(false)}
              className="block px-3 py-2 rounded-xl text-base font-semibold text-emerald-600 bg-emerald-50"
            >
              Usta kabineti
            </Link>
          )}

          {isAuthenticated ? (
            <div className="pt-3 border-t border-slate-100 space-y-2">
              <div className="px-3 py-2 bg-slate-50 rounded-xl">
                <p className="font-bold text-sm text-slate-800">{user?.full_name}</p>
                <p className="text-xs text-slate-400">{user?.phone || user?.email}</p>
              </div>
              <Link
                to="/cabinet"
                onClick={() => setIsMobileMenuOpen(false)}
                className="block px-3 py-2 text-sm text-slate-700 hover:bg-slate-50 rounded-lg"
              >
                Mening profilim
              </Link>
              <Link
                to="/cabinet?tab=saved"
                onClick={() => setIsMobileMenuOpen(false)}
                className="block px-3 py-2 text-sm text-slate-700 hover:bg-slate-50 rounded-lg"
              >
                Saqlangan ustalar
              </Link>
              <button
                onClick={handleLogout}
                className="w-full text-left px-3 py-2 text-sm font-semibold text-red-600 hover:bg-red-50 rounded-lg"
              >
                Chiqish
              </button>
            </div>
          ) : (
            <div className="pt-3 border-t border-slate-100 flex flex-col gap-2">
              <button
                onClick={() => {
                  setIsMobileMenuOpen(false);
                  openAuthModal("Kirish", "login");
                }}
                className="w-full py-2.5 text-center font-semibold text-sm text-slate-700 bg-slate-100 rounded-xl"
              >
                Kirish
              </button>
              <button
                onClick={() => {
                  setIsMobileMenuOpen(false);
                  openAuthModal("Ro‘yxatdan o‘tish", "register");
                }}
                className="w-full py-2.5 text-center font-bold text-sm text-white bg-blue-600 rounded-xl"
              >
                Ro‘yxatdan o‘tish
              </button>
            </div>
          )}
        </div>
      )}
    </header>
  );
};
