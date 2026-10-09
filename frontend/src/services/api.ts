/**
 * Central API Client for OffSet Mobile Application.
 * Handles JWT attachment, base URL resolution, 401 expiration intercepting,
 * and clear errors for network unavailability.
 */

export interface UserSession {
  token: string;
  username: string;
  vpa: string;
  type?: string;
}

export interface ApiError {
  message: string;
  status?: number;
}

const TOKEN_KEY = 'offset_auth_token';
const USER_KEY = 'offset_user_session';

// Auth Token Helpers
export const getStoredToken = (): string | null => {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
};

export const getStoredUser = (): UserSession | null => {
  try {
    const raw = localStorage.getItem(USER_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
};

export const saveAuthSession = (session: UserSession) => {
  try {
    localStorage.setItem(TOKEN_KEY, session.token);
    localStorage.setItem(USER_KEY, JSON.stringify(session));
  } catch (err) {
    console.error('Failed to persist auth session:', err);
  }
};

export const clearAuthSession = () => {
  try {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  } catch (err) {
    console.error('Failed to clear auth session:', err);
  }
};

// Global event listener for token expiration / 401
type UnauthorizedCallback = () => void;
let onUnauthorizedCb: UnauthorizedCallback | null = null;

export const setOnUnauthorizedListener = (cb: UnauthorizedCallback) => {
  onUnauthorizedCb = cb;
};

// Base HTTP Request Wrapper
export async function apiRequest<T = any>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getStoredToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  // Ensure leading slash
  const url = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;

  let response: Response;
  try {
    response = await fetch(url, {
      ...options,
      headers,
    });
  } catch (networkErr: any) {
    throw {
      message: 'Backend unavailable. Ensure the Spring Boot server is running on http://localhost:8080.',
      status: 0,
    } as ApiError;
  }

  if (response.status === 401) {
    clearAuthSession();
    if (onUnauthorizedCb) {
      onUnauthorizedCb();
    }
    const errBody = await response.json().catch(() => ({}));
    throw {
      message: errBody.message || errBody.error || 'Session expired. Please log in again.',
      status: 401,
    } as ApiError;
  }

  if (!response.ok) {
    const errBody = await response.json().catch(() => ({}));
    throw {
      message: errBody.error || errBody.message || `Request failed with status ${response.status}`,
      status: response.status,
    } as ApiError;
  }

  return response.json();
}

// Concrete Service APIs
export const AuthService = {
  login: async (username: string, password: string): Promise<UserSession> => {
    const res = await apiRequest<UserSession>('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    });
    saveAuthSession(res);
    return res;
  },

  register: async (data: { username: string; password: string; fullName?: string; vpa?: string }): Promise<UserSession> => {
    const res = await apiRequest<UserSession>('/api/auth/register', {
      method: 'POST',
      body: JSON.stringify(data),
    });
    saveAuthSession(res);
    return res;
  },

  logout: () => {
    clearAuthSession();
  },
};

export const WalletService = {
  getWallet: async () => {
    return apiRequest('/api/wallet');
  },
  getLimits: async () => {
    return apiRequest('/api/wallet/limits');
  },
  fund: async (amount: number) => {
    return apiRequest('/api/wallet/fund', {
      method: 'POST',
      body: JSON.stringify({ amount }),
    });
  },
};

export const TransactionService = {
  list: async () => {
    return apiRequest<any[]>('/api/transactions');
  },
};
