export type UserRole = 'client' | 'master' | 'admin';

export interface User {
  id: number;
  first_name: string;
  last_name: string;
  full_name: string;
  phone: string | null;
  email: string | null;
  role: UserRole;
  avatar: string | null;
  avatar_url: string | null;
  created_at: string;
}

export interface Category {
  id: number;
  name: string;
  slug: string;
  icon: string;
  description: string;
  order: number;
  masters_count: number;
}

export interface ServiceItem {
  id?: number;
  name: string;
  price: number;
}

export interface RatingItem {
  id: number;
  user: number;
  user_name: string;
  user_avatar: string | null;
  master: number;
  score: number;
  comment: string;
  created_at: string;
}

export interface PortfolioItem {
  id: number;
  title: string;
  description: string;
  image?: string | null;
  image_url?: string | null;
  created_at: string;
}

export interface Master {
  id: number;
  user_id: number;
  full_name: string;
  avatar_url: string | null;
  phone: string | null;
  category: Category;
  description: string;
  experience: number;
  price: number;
  region: string;
  district: string;
  address?: string;
  latitude: number | null;
  longitude: number | null;
  working_hours: string;
  status: 'active' | 'busy' | 'inactive';
  average_rating: string | number;
  ratings_count: number;
  is_favorite: boolean;
  distance_km: number | null;
  services: ServiceItem[];
  ratings?: RatingItem[];
  portfolio?: PortfolioItem[];
  user_rated?: boolean;
  user_rating?: { id: number; score: number; comment: string } | null;
}

export interface MessageItem {
  id: number;
  sender: number;
  sender_name: string;
  sender_avatar: string | null;
  receiver: number;
  receiver_name: string;
  receiver_avatar: string | null;
  text: string;
  is_read: boolean;
  created_at: string;
  is_me: boolean;
}

export interface ConversationItem {
  partner: {
    id: number;
    full_name: string;
    avatar_url: string | null;
    role: UserRole;
    master_id?: number | null;
    master_category?: string | null;
  };
  last_message: {
    text: string;
    created_at: string | null;
    is_me: boolean;
  } | null;
  unread_count: number;
}

export interface SearchSuggestion {
  type: 'category' | 'master' | 'service' | 'location';
  label: string;
  subtext: string;
  category_id?: number;
  slug?: string;
  master_id?: number;
  region?: string;
  district?: string;
}

export interface LocationRegion {
  region: string;
  lat: number;
  lng: number;
  districts: string[];
}
