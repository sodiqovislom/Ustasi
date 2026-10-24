import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, X, Smartphone, Zap, Hammer, User, Wrench, MapPin, Loader2 } from 'lucide-react';
import { api } from '../api/client';
import { SearchSuggestion } from '../types';

interface SearchAutocompleteProps {
  initialValue?: string;
  onSearch?: (query: string) => void;
  placeholder?: string;
  className?: string;
}

export const SearchAutocomplete: React.FC<SearchAutocompleteProps> = ({
  initialValue = '',
  onSearch,
  placeholder = "Qanday usta kerak? (Masalan: telefon, elektrik, kafel...)",
  className = '',
}) => {
  const [query, setQuery] = useState(initialValue);
  const [suggestions, setSuggestions] = useState<SearchSuggestion[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();
  const containerRef = useRef<HTMLDivElement>(null);

  // Sync initialValue
  useEffect(() => {
    setQuery(initialValue);
  }, [initialValue]);

  // Debounced suggestion fetcher
  useEffect(() => {
    const trimmed = query.trim();
    if (trimmed.length < 2) {
      setSuggestions([]);
      setIsOpen(false);
      return;
    }

    const timer = setTimeout(async () => {
      setIsLoading(true);
      try {
        const res = await api.getSearchSuggestions(trimmed);
        setSuggestions(res.suggestions || []);
        setIsOpen(res.suggestions && res.suggestions.length > 0);
      } catch (err) {
        console.error("Qidiruv xatoligi:", err);
      } finally {
        setIsLoading(false);
      }
    }, 280);

    return () => clearTimeout(timer);
  }, [query]);

  // Click outside listener
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSelectSuggestion = (s: SearchSuggestion) => {
    setIsOpen(false);
    if (s.type === 'category' && s.slug) {
      navigate(`/masters?category=${s.slug}`);
    } else if (s.type === 'master' && s.master_id) {
      navigate(`/masters/${s.master_id}`);
    } else if (s.type === 'location' && s.region) {
      navigate(`/masters?region=${encodeURIComponent(s.region)}&district=${encodeURIComponent(s.district || '')}`);
    } else {
      setQuery(s.label);
      if (onSearch) {
        onSearch(s.label);
      } else {
        navigate(`/masters?search=${encodeURIComponent(s.label)}`);
      }
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setIsOpen(false);
    const trimmed = query.trim();
    if (onSearch) {
      onSearch(trimmed);
    } else {
      navigate(`/masters?search=${encodeURIComponent(trimmed)}`);
    }
  };

  const getSuggestionIcon = (type: string, label: string) => {
    if (type === 'category') {
      if (label.toLowerCase().includes('telefon')) return <Smartphone className="w-4 h-4 text-blue-500" />;
      if (label.toLowerCase().includes('elektr')) return <Zap className="w-4 h-4 text-amber-500" />;
      return <Hammer className="w-4 h-4 text-emerald-500" />;
    }
    if (type === 'master') return <User className="w-4 h-4 text-indigo-500" />;
    if (type === 'service') return <Wrench className="w-4 h-4 text-slate-500" />;
    return <MapPin className="w-4 h-4 text-red-500" />;
  };

  return (
    <div ref={containerRef} className={`relative w-full ${className}`}>
      <form onSubmit={handleSubmit} className="relative flex items-center">
        <div className="absolute left-4 pointer-events-none text-slate-400">
          {isLoading ? (
            <Loader2 className="w-5 h-5 animate-spin text-blue-600" />
          ) : (
            <Search className="w-5 h-5" />
          )}
        </div>

        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => {
            if (suggestions.length > 0 && query.trim().length >= 2) {
              setIsOpen(true);
            }
          }}
          placeholder={placeholder}
          className="w-full pl-12 pr-12 py-3.5 sm:py-4 bg-white border border-slate-200 rounded-2xl text-slate-900 placeholder:text-slate-400 text-sm sm:text-base font-medium shadow-sm hover:border-slate-300 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-600 transition"
        />

        {query && (
          <button
            type="button"
            onClick={() => {
              setQuery('');
              setSuggestions([]);
              setIsOpen(false);
              if (onSearch) onSearch('');
            }}
            className="absolute right-4 p-1 text-slate-400 hover:text-slate-600 rounded-full transition"
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </form>

      {/* Autocomplete Dropdown */}
      {isOpen && suggestions.length > 0 && (
        <div className="absolute left-0 right-0 mt-2 bg-white rounded-2xl shadow-2xl border border-slate-100 overflow-hidden z-50 animate-in fade-in slide-in-from-top-2">
          <div className="p-2 border-b border-slate-100 bg-slate-50/70 text-[11px] font-semibold text-slate-400 px-3 uppercase tracking-wider">
            Tavsiya etilgan natijalar
          </div>
          <ul className="divide-y divide-slate-50 max-h-80 overflow-y-auto">
            {suggestions.map((s, idx) => (
              <li
                key={idx}
                onClick={() => handleSelectSuggestion(s)}
                className="px-4 py-3 flex items-center justify-between hover:bg-blue-50/70 cursor-pointer transition group"
              >
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-xl bg-slate-100 group-hover:bg-white transition">
                    {getSuggestionIcon(s.type, s.label)}
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-slate-800 group-hover:text-blue-700">
                      {s.label}
                    </p>
                    <p className="text-xs text-slate-400">
                      {s.subtext}
                    </p>
                  </div>
                </div>
                <span className="text-[11px] font-medium text-slate-400 bg-slate-100 px-2 py-0.5 rounded-full group-hover:bg-blue-100 group-hover:text-blue-700">
                  {s.type === 'category' ? 'Kategoriya' : s.type === 'master' ? 'Usta' : s.type === 'service' ? 'Xizmat' : 'Hudud'}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};
