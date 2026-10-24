import React, { useState } from 'react';
import { PhotoViewerModal } from './PhotoViewerModal';
import { resolveMediaUrl } from '../api/client';

// Telegram Signature Color Gradients for initials
const TELEGRAM_GRADIENTS = [
  'from-[#2AABEE] to-[#229ED9]', // Blue
  'from-[#A74BF6] to-[#8E32D9]', // Violet
  'from-[#2DC97C] to-[#20AA64]', // Emerald Green
  'from-[#FE9E41] to-[#F37B1D]', // Orange
  'from-[#FF5E89] to-[#E93B67]', // Coral / Pink
  'from-[#00C9FF] to-[#0081DF]', // Cyan
  'from-[#6C5CE7] to-[#4834D4]', // Indigo
];

function getTelegramGradient(name: string): string {
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash);
  }
  const index = Math.abs(hash) % TELEGRAM_GRADIENTS.length;
  return TELEGRAM_GRADIENTS[index];
}

function getInitials(name: string): string {
  if (!name) return '?';
  const parts = name.trim().split(/\s+/);
  if (parts.length >= 2) {
    return (parts[0][0] + parts[1][0]).toUpperCase();
  }
  return parts[0].slice(0, 1).toUpperCase();
}

export interface TelegramAvatarProps {
  src?: string | null;
  name: string;
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl' | '2xl';
  status?: 'active' | 'busy' | 'inactive';
  showStatus?: boolean;
  hasStoryRing?: boolean;
  clickable?: boolean;
  subtitle?: string;
  onClick?: () => void;
  className?: string;
}

export const TelegramAvatar: React.FC<TelegramAvatarProps> = ({
  src,
  name,
  size = 'md',
  status,
  showStatus = false,
  hasStoryRing = false,
  clickable = true,
  subtitle,
  onClick,
  className = '',
}) => {
  const [imageError, setImageError] = useState(false);
  const [isViewerOpen, setIsViewerOpen] = useState(false);

  // Size dimensions
  const sizeMap = {
    xs: {
      container: 'w-7 h-7 text-[10px]',
      dot: 'w-2 h-2 border-[1.5px]',
      ringPadding: 'p-0.5',
    },
    sm: {
      container: 'w-10 h-10 text-xs font-bold',
      dot: 'w-2.5 h-2.5 border-[1.5px]',
      ringPadding: 'p-0.5',
    },
    md: {
      container: 'w-12 h-12 text-sm font-black',
      dot: 'w-3 h-3 border-2',
      ringPadding: 'p-[2px]',
    },
    lg: {
      container: 'w-16 h-16 text-xl font-black',
      dot: 'w-3.5 h-3.5 border-2',
      ringPadding: 'p-[3px]',
    },
    xl: {
      container: 'w-20 h-20 text-2xl font-black',
      dot: 'w-4 h-4 border-2',
      ringPadding: 'p-1',
    },
    '2xl': {
      container: 'w-24 h-24 sm:w-28 sm:h-28 text-3xl sm:text-4xl font-black',
      dot: 'w-5 h-5 border-[3px]',
      ringPadding: 'p-1',
    },
  };

  const currentSize = sizeMap[size];
  const gradient = getTelegramGradient(name);
  const initials = getInitials(name);
  const resolvedSrc = resolveMediaUrl(src);
  const hasImage = Boolean(resolvedSrc && !imageError);

  const handleClick = (e: React.MouseEvent) => {
    if (onClick) {
      onClick();
    } else if (clickable && hasImage) {
      e.stopPropagation();
      e.preventDefault();
      setIsViewerOpen(true);
    }
  };

  const avatarElement = (
    <div
      onClick={handleClick}
      className={`relative inline-flex items-center justify-center shrink-0 ${
        clickable && hasImage ? 'cursor-pointer group' : ''
      } ${className}`}
    >
      {/* Outer Telegram Story Ring (Optional) */}
      <div
        className={`rounded-full transition-transform duration-200 ${
          hasStoryRing
            ? `bg-gradient-to-tr from-cyan-400 via-blue-500 to-indigo-500 ${currentSize.ringPadding}`
            : ''
        } ${clickable && hasImage ? 'group-hover:scale-105' : ''}`}
      >
        {/* Circular Avatar Body */}
        <div
          className={`${currentSize.container} rounded-full overflow-hidden flex items-center justify-center shadow-xs select-none relative ${
            hasStoryRing ? 'border-2 border-white' : 'border border-slate-200/60'
          } ${
            !hasImage ? `bg-gradient-to-tr ${gradient} text-white shadow-inner` : 'bg-slate-100'
          }`}
        >
          {hasImage ? (
            <img
              src={resolvedSrc!}
              alt={name}
              onError={() => setImageError(true)}
              className="w-full h-full object-cover rounded-full"
              loading="lazy"
            />
          ) : (
            <span className="tracking-tight text-white drop-shadow-xs">
              {initials}
            </span>
          )}

          {/* Telegram-style micro subtle zoom hover overlay */}
          {clickable && hasImage && (
            <div className="absolute inset-0 bg-black/10 opacity-0 group-hover:opacity-100 transition-opacity rounded-full pointer-events-none" />
          )}
        </div>
      </div>

      {/* Telegram Status Badge Dot (Bottom-Right) */}
      {showStatus && status && (
        <span
          className={`absolute bottom-0 right-0 ${currentSize.dot} rounded-full border-white shadow-xs ${
            status === 'active'
              ? 'bg-emerald-500'
              : status === 'busy'
              ? 'bg-amber-500'
              : 'bg-slate-400'
          }`}
          title={status === 'active' ? 'Faol / Onlayn' : status === 'busy' ? 'Band' : 'Oflayn'}
        />
      )}
    </div>
  );

  return (
    <>
      {avatarElement}

      {/* Fullscreen Photo Viewer Modal */}
      {hasImage && isViewerOpen && (
        <PhotoViewerModal
          isOpen={isViewerOpen}
          onClose={() => setIsViewerOpen(false)}
          imageUrl={resolvedSrc!}
          title={name}
          subtitle={subtitle}
          isAvatar={true}
        />
      )}
    </>
  );
};
