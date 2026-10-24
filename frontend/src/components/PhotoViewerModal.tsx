import React, { useEffect } from 'react';
import { X, ExternalLink, Download } from 'lucide-react';

interface PhotoViewerModalProps {
  isOpen: boolean;
  onClose: () => void;
  imageUrl: string;
  title: string;
  subtitle?: string;
  isAvatar?: boolean;
}

export const PhotoViewerModal: React.FC<PhotoViewerModalProps> = ({
  isOpen,
  onClose,
  imageUrl,
  title,
  subtitle,
  isAvatar = false,
}) => {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    if (isOpen) {
      document.body.style.overflow = 'hidden';
      window.addEventListener('keydown', handleKeyDown);
    }
    return () => {
      document.body.style.overflow = '';
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [isOpen, onClose]);

  if (!isOpen || !imageUrl) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex flex-col justify-between bg-black/90 backdrop-blur-md animate-in fade-in duration-200 select-none"
      onClick={onClose}
    >
      {/* Top Telegram Header Bar */}
      <div
        className="w-full flex items-center justify-between px-4 sm:px-8 py-4 bg-gradient-to-b from-black/80 to-transparent z-10"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center gap-3 min-w-0">
          <div className="min-w-0">
            <h3 className="text-white text-sm sm:text-base font-bold truncate">
              {title}
            </h3>
            {subtitle && (
              <p className="text-slate-400 text-xs truncate">
                {subtitle}
              </p>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2">
          <a
            href={imageUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="p-2 rounded-full text-slate-300 hover:text-white hover:bg-white/10 transition"
            title="Asl nusxada ochish"
          >
            <ExternalLink className="w-5 h-5" />
          </a>
          <button
            onClick={onClose}
            className="p-2 rounded-full text-slate-300 hover:text-white hover:bg-white/10 transition"
            title="Yopish (Esc)"
          >
            <X className="w-6 h-6" />
          </button>
        </div>
      </div>

      {/* Main Image Center View */}
      <div
        className="flex-1 flex items-center justify-center p-4 sm:p-8"
        onClick={onClose}
      >
        <div
          className={`relative max-w-full max-h-[80vh] flex items-center justify-center animate-in zoom-in-95 duration-200 ${
            isAvatar ? 'rounded-full overflow-hidden shadow-2xl ring-4 ring-white/20' : 'rounded-3xl overflow-hidden shadow-2xl'
          }`}
          onClick={(e) => e.stopPropagation()}
        >
          <img
            src={imageUrl}
            alt={title}
            className={`${
              isAvatar
                ? 'w-72 h-72 sm:w-96 sm:h-96 object-cover bg-slate-900'
                : 'max-h-[75vh] max-w-[90vw] sm:max-w-3xl object-contain rounded-2xl bg-black/40'
            }`}
          />
        </div>
      </div>

      {/* Bottom info caption (if portfolio or subtitle) */}
      <div
        className="w-full text-center px-4 py-4 bg-gradient-to-t from-black/80 to-transparent z-10"
        onClick={(e) => e.stopPropagation()}
      >
        <p className="text-slate-400 text-xs">
          Rasmdan chiqish uchun istalgan joyni yoki <kbd className="px-1.5 py-0.5 bg-white/10 rounded text-[11px] text-white">Esc</kbd> tugmasini bosing
        </p>
      </div>
    </div>
  );
};
