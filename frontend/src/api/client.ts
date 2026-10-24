import {
  User, Category, Master, SearchSuggestion,
  LocationRegion, ConversationItem, MessageItem
} from '../types';

const API_BASE = '/api/v1';

class ApiClient {
  private getAccessToken(): string | null {
    return localStorage.getItem('ustasi_access_token');
  }

  private getRefreshToken(): string | null {
    return localStorage.getItem('ustasi_refresh_token');
  }

  public setTokens(access: string, refresh: string) {
    localStorage.setItem('ustasi_access_token', access);
    localStorage.setItem('ustasi_refresh_token', refresh);
  }

  public clearTokens() {
    localStorage.removeItem('ustasi_access_token');
    localStorage.removeItem('ustasi_refresh_token');
    localStorage.removeItem('ustasi_user');
  }

  public async request<T = any>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = endpoint.startsWith('http') ? endpoint : `${API_BASE}${endpoint}`;
    const headers = new Headers(options.headers || {});

    if (!headers.has('Content-Type') && !(options.body instanceof FormData)) {
      headers.set('Content-Type', 'application/json');
    }

    const token = this.getAccessToken();
    if (token) {
      headers.set('Authorization', `Bearer ${token}`);
    }

    let response = await fetch(url, {
      ...options,
      headers,
    });

    // Handle 401 Unauthorized -> Attempt refresh token
    if (response.status === 401 && this.getRefreshToken() && !endpoint.includes('/token/refresh/')) {
      const refreshed = await this.refreshAccessToken();
      if (refreshed) {
        headers.set('Authorization', `Bearer ${this.getAccessToken()}`);
        response = await fetch(url, {
          ...options,
          headers,
        });
      } else {
        this.clearTokens();
        window.dispatchEvent(new Event('ustasi:auth_expired'));
      }
    }

    if (!response.ok) {
      let errorData: any = {};
      try {
        errorData = await response.json();
      } catch {
        errorData = { detail: `Serverda xatolik yuz berdi (${response.status})` };
      }

      // Extract user-friendly error message
      let message = "Xatolik yuz berdi.";
      if (typeof errorData === 'string') {
        message = errorData;
      } else if (errorData.detail) {
        message = errorData.detail;
      } else if (errorData.phone) {
        message = Array.isArray(errorData.phone) ? errorData.phone[0] : errorData.phone;
      } else if (errorData.email) {
        message = Array.isArray(errorData.email) ? errorData.email[0] : errorData.email;
      } else if (errorData.non_field_errors) {
        message = Array.isArray(errorData.non_field_errors) ? errorData.non_field_errors[0] : errorData.non_field_errors;
      } else if (errorData.score) {
        message = Array.isArray(errorData.score) ? errorData.score[0] : errorData.score;
      } else if (errorData.password) {
        message = Array.isArray(errorData.password) ? errorData.password[0] : errorData.password;
      } else {
        const firstKey = Object.keys(errorData)[0];
        if (firstKey) {
          const val = errorData[firstKey];
          message = Array.isArray(val) ? val[0] : String(val);
        }
      }

      const err = new Error(message) as any;
      err.data = errorData;
      err.status = response.status;
      throw err;
    }

    if (response.status === 204) {
      return null as any;
    }

    return response.json();
  }

  private async refreshAccessToken(): Promise<boolean> {
    const refreshToken = this.getRefreshToken();
    if (!refreshToken) return false;

    try {
      const res = await fetch(`${API_BASE}/auth/token/refresh/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh: refreshToken }),
      });
      if (!res.ok) return false;
      const data = await res.json();
      if (data.access) {
        localStorage.setItem('ustasi_access_token', data.access);
        return true;
      }
      return false;
    } catch {
      return false;
    }
  }

  // Auth methods
  async register(data: {
    first_name: string;
    last_name?: string;
    phone?: string;
    email?: string;
    password: string;
    role?: 'client' | 'master';
  }) {
    return this.request<{
      message: string;
      user: User;
      tokens: { access: string; refresh: string };
    }>('/auth/register/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async login(data: { login: string; password: string }) {
    return this.request<{
      message: string;
      user: User;
      tokens: { access: string; refresh: string };
    }>('/auth/login/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getMe() {
    return this.request<User & { master_profile?: Master | null }>('/auth/me/');
  }

  async updateMe(data: Partial<User>) {
    return this.request<User>('/auth/me/', {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  }

  // Categories
  async getCategories(): Promise<Category[]> {
    const res = await this.request<any>('/categories/');
    return Array.isArray(res) ? res : (res?.results || []);
  }

  // Masters
  async getMasters(params: {
    category?: string;
    region?: string;
    district?: string;
    min_price?: number;
    max_price?: number;
    min_rating?: number;
    search?: string;
    distance?: number;
    lat?: number;
    lng?: number;
    ordering?: string;
    page?: number;
  }) {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== '') {
        query.append(k, String(v));
      }
    });
    return this.request<{
      count: number;
      next: string | null;
      previous: string | null;
      results: Master[];
    }>(`/masters/?${query.toString()}`);
  }

  async getMasterDetail(id: number, coords?: { lat: number; lng: number }) {
    const query = coords ? `?lat=${coords.lat}&lng=${coords.lng}` : '';
    return this.request<Master>(`/masters/${id}/${query}`);
  }

  async rateMaster(masterId: number, score: number, comment: string = '') {
    return this.request<{
      message: string;
      average_rating: number;
      ratings_count: number;
    }>(`/masters/${masterId}/rate/`, {
      method: 'POST',
      body: JSON.stringify({ score, comment }),
    });
  }

  async getMyMasterProfile() {
    return this.request<Master>('/masters/me/');
  }

  async createMasterProfile(data: any) {
    return this.request<Master>('/masters/me/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateMasterProfile(data: any) {
    return this.request<Master>('/masters/me/', {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  }

  // Portfolio works
  async getMyPortfolio() {
    return this.request<any[]>('/masters/me/portfolio/');
  }

  async addPortfolioWork(data: { title: string; description?: string; image?: string }) {
    return this.request<any>('/masters/me/portfolio/', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async deletePortfolioWork(id: number) {
    return this.request<void>(`/masters/me/portfolio/${id}/`, {
      method: 'DELETE',
    });
  }

  // Autocomplete suggestions
  async getSearchSuggestions(query: string) {
    if (query.trim().length < 2) {
      return { query, suggestions: [] };
    }
    return this.request<{
      query: string;
      suggestions: SearchSuggestion[];
    }>(`/search/suggestions/?q=${encodeURIComponent(query.trim())}`);
  }

  // Locations
  async getLocations() {
    return this.request<LocationRegion[]>('/locations/');
  }

  // Favorites
  async getFavorites() {
    return this.request<{ results: Master[] }>('/favorites/');
  }

  async toggleFavorite(masterId: number) {
    return this.request<{ is_favorite: boolean; message: string }>(
      `/favorites/toggle/${masterId}/`,
      { method: 'POST' }
    );
  }

  // My ratings
  async getMyRatings() {
    return this.request<any[]>('/ratings/my/');
  }

  // Chat / Messages
  async getConversations() {
    return this.request<ConversationItem[]>('/messages/conversations/');
  }

  async getMessages(userId: number) {
    return this.request<{
      partner: {
        id: number;
        full_name: string;
        avatar_url: string | null;
        role: string;
        phone: string | null;
        master_id: number | null;
        master_category: string | null;
      };
      messages: MessageItem[];
    }>(`/messages/?user_id=${userId}`);
  }

  async sendMessage(receiverId: number, text: string) {
    return this.request<MessageItem>('/messages/', {
      method: 'POST',
      body: JSON.stringify({ receiver_id: receiverId, text }),
    });
  }
}

export const api = new ApiClient();
