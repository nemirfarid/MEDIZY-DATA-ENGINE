/**
 * MEDIZY / SANTÉ DZ — Client API d'Administration et Modération
 * =============================================================
 * Gère l'authentification sécurisée par jeton JWT (Bearer), le stockage
 * en session, la gestion des en-têtes de limitation de débit (Rate Limit)
 * et les opérations de validation/rejet des établissements de santé.
 */

import {
  AdminAuthToken,
  AdminLoginCredentials,
  AdminSuggestion,
  ApproveSuggestionPayload,
  Facility,
  RejectSuggestionPayload,
  SuggestionStatus,
} from './types';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
const TOKEN_STORAGE_KEY = 'medizy_admin_jwt_token';
const ADMIN_INFO_KEY = 'medizy_admin_info';

export interface RateLimitHeaders {
  limit?: string;
  remaining?: string;
  reset?: string;
}

export interface ApiResponse<T> {
  data: T;
  rateLimit: RateLimitHeaders;
}

export class AdminAuthError extends Error {
  constructor(message: string, public status: number) {
    super(message);
    this.name = 'AdminAuthError';
  }
}

/**
 * Récupère le jeton JWT persisté dans le navigateur.
 */
export function getStoredAdminToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(TOKEN_STORAGE_KEY);
}

/**
 * Récupère les données de profil de l'administrateur connecté.
 */
export function getStoredAdminInfo(): Partial<AdminAuthToken> | null {
  if (typeof window === 'undefined') return null;
  const raw = localStorage.getItem(ADMIN_INFO_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

/**
 * Authentifie l'administrateur et conserve le jeton d'accès sécurisé.
 */
export async function loginAdmin(credentials: AdminLoginCredentials): Promise<AdminAuthToken> {
  const response = await fetch(`${API_BASE_URL}/api/v1/admin/auth/login`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(credentials),
  });

  if (!response.ok) {
    let errorDetail = 'Identifiants invalides';
    try {
      const errorJson = await response.json();
      errorDetail = errorJson.detail || errorDetail;
    } catch {}
    throw new AdminAuthError(errorDetail, response.status);
  }

  const tokenData: AdminAuthToken = await response.json();
  localStorage.setItem(TOKEN_STORAGE_KEY, tokenData.access_token);
  localStorage.setItem(
    ADMIN_INFO_KEY,
    JSON.stringify({
      admin_name: tokenData.admin_name,
      role: tokenData.role,
      expires_in: tokenData.expires_in,
    })
  );
  return tokenData;
}

/**
 * Déconnecte l'administrateur et purge les jetons.
 */
export function logoutAdmin(): void {
  if (typeof window !== 'undefined') {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
    localStorage.removeItem(ADMIN_INFO_KEY);
  }
}

/**
 * Génère les en-têtes avec autorisation Bearer.
 */
function getAuthHeaders(): Record<string, string> {
  const token = getStoredAdminToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
}

/**
 * Extrait les métriques de limitation de débit des réponses API.
 */
function extractRateLimitHeaders(response: Response): RateLimitHeaders {
  return {
    limit: response.headers.get('X-RateLimit-Limit') || undefined,
    remaining: response.headers.get('X-RateLimit-Remaining') || undefined,
    reset: response.headers.get('X-RateLimit-Reset') || undefined,
  };
}

/**
 * Récupère les suggestions citoyennes filtrées par statut.
 */
export async function fetchAdminSuggestions(
  status?: SuggestionStatus,
  limit: number = 50,
  offset: number = 0
): Promise<ApiResponse<{ total: number; data: AdminSuggestion[] }>> {
  const params = new URLSearchParams();
  if (status) params.append('status', status);
  params.append('limit', String(limit));
  params.append('offset', String(offset));

  const response = await fetch(`${API_BASE_URL}/api/v1/admin/suggestions?${params.toString()}`, {
    method: 'GET',
    headers: getAuthHeaders(),
  });

  if (response.status === 401) {
    logoutAdmin();
    throw new AdminAuthError('Session expirée ou non autorisée. Veuillez vous reconnecter.', 401);
  }

  if (!response.ok) {
    throw new Error(`Erreur lors du chargement des suggestions (${response.status})`);
  }

  const data = await response.json();
  return {
    data,
    rateLimit: extractRateLimitHeaders(response),
  };
}

/**
 * Valide et approuve une suggestion citoyenne pour publication officielle.
 */
export async function approveSuggestion(
  suggestionId: number,
  payload: ApproveSuggestionPayload
): Promise<ApiResponse<{ message: string; facility: Facility; created_facility_id: number }>> {
  const response = await fetch(`${API_BASE_URL}/api/v1/admin/suggestions/${suggestionId}/approve`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify(payload),
  });

  if (response.status === 401) {
    logoutAdmin();
    throw new AdminAuthError('Session expirée.', 401);
  }

  if (!response.ok) {
    let errorDetail = "Échec de l'approbation";
    try {
      const err = await response.json();
      errorDetail = err.detail || errorDetail;
    } catch {}
    throw new Error(errorDetail);
  }

  const data = await response.json();
  return {
    data,
    rateLimit: extractRateLimitHeaders(response),
  };
}

/**
 * Rejette une suggestion citoyenne avec motif formel.
 */
export async function rejectSuggestion(
  suggestionId: number,
  payload: RejectSuggestionPayload
): Promise<ApiResponse<{ message: string; status: string; reason: string }>> {
  const response = await fetch(`${API_BASE_URL}/api/v1/admin/suggestions/${suggestionId}/reject`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify(payload),
  });

  if (response.status === 401) {
    logoutAdmin();
    throw new AdminAuthError('Session expirée.', 401);
  }

  if (!response.ok) {
    let errorDetail = 'Échec du rejet';
    try {
      const err = await response.json();
      errorDetail = err.detail || errorDetail;
    } catch {}
    throw new Error(errorDetail);
  }

  const data = await response.json();
  return {
    data,
    rateLimit: extractRateLimitHeaders(response),
  };
}

/**
 * Récupère un établissement existant par son ID pour la comparaison de doublons.
 */
export async function fetchFacilityById(id: number): Promise<Facility | null> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/facilities/${id}`);
    if (!response.ok) return null;
    return await response.json();
  } catch {
    return null;
  }
}
