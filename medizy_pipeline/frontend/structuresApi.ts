/**
 * MEDIZY / SANTÉ DZ — Client API pour l'Annuaire Sanitaire National (/api/structures)
 * Compatible avec l'URL de base définie dans api_constants.dart et la constante API_BASE_URL.
 */

import type {
  CategorieStats,
  Structure,
  StructureListResponse,
  StructureSearchParams,
  WilayaStats,
} from "./structuresTypes";

// ─── Configuration ───────────────────────────────────────────────────────────

/** URL de base de l'API MEDIZY — surcharger via variable d'environnement */
const API_BASE_URL =
  (typeof process !== "undefined" && process.env?.REACT_APP_API_URL) ||
  (typeof import.meta !== "undefined" && (import.meta as any).env?.VITE_API_URL) ||
  "http://10.188.170.227:8000";

const STRUCTURES_BASE = `${API_BASE_URL}/api/structures`;

const DEFAULT_TIMEOUT_MS = 8000;

// ─── Helpers ─────────────────────────────────────────────────────────────────

function buildQueryString(params: Record<string, string | number | boolean | undefined | null>): string {
  const parts: string[] = [];
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== "") {
      parts.push(`${encodeURIComponent(key)}=${encodeURIComponent(String(value))}`);
    }
  }
  return parts.length > 0 ? `?${parts.join("&")}` : "";
}

async function fetchWithTimeout(url: string, timeoutMs = DEFAULT_TIMEOUT_MS): Promise<Response> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const resp = await fetch(url, { signal: controller.signal });
    if (!resp.ok) {
      throw new Error(`HTTP ${resp.status} : ${resp.statusText} — ${url}`);
    }
    return resp;
  } finally {
    clearTimeout(timer);
  }
}

// ─── API Functions ────────────────────────────────────────────────────────────

/**
 * Recherche dynamique dans l'Annuaire Sanitaire National.
 * @param params Filtres optionnels : wilaya, commune, catégorie, spécialité, GPS, recherche libre.
 */
export async function searchStructures(
  params: StructureSearchParams = {}
): Promise<StructureListResponse> {
  const qs = buildQueryString({
    q: params.q,
    code_wilaya: params.code_wilaya,
    nom_wilaya: params.nom_wilaya,
    nom_commune: params.nom_commune,
    categorie: params.categorie,
    discipline: params.discipline,
    lat: params.lat,
    lon: params.lon,
    radius_km: params.radius_km,
    limit: params.limit ?? 20,
    offset: params.offset ?? 0,
  });
  const resp = await fetchWithTimeout(`${STRUCTURES_BASE}/${qs}`);
  return resp.json() as Promise<StructureListResponse>;
}

/**
 * Structures les plus proches d'une position GPS.
 * @param lat Latitude (18.0–38.5)
 * @param lon Longitude (−9.5–13.0)
 * @param radius_km Rayon en km (défaut 5 km)
 * @param options Filtres optionnels
 */
export async function getNearbyStructures(
  lat: number,
  lon: number,
  radius_km = 5.0,
  options: { categorie?: string; discipline?: string; limit?: number } = {}
): Promise<StructureListResponse> {
  const qs = buildQueryString({
    lat,
    lon,
    radius_km,
    categorie: options.categorie,
    discipline: options.discipline,
    limit: options.limit ?? 15,
  });
  const resp = await fetchWithTimeout(`${STRUCTURES_BASE}/nearby${qs}`);
  return resp.json() as Promise<StructureListResponse>;
}

/**
 * Fiche détaillée d'une structure par son identifiant.
 */
export async function getStructureById(id: number): Promise<Structure> {
  const resp = await fetchWithTimeout(`${STRUCTURES_BASE}/${id}`);
  return resp.json() as Promise<Structure>;
}

/**
 * Statistiques par wilaya (pour la carte de couverture nationale).
 */
export async function getWilayasStats(): Promise<WilayaStats[]> {
  const resp = await fetchWithTimeout(`${STRUCTURES_BASE}/meta/wilayas`);
  return resp.json() as Promise<WilayaStats[]>;
}

/**
 * Liste des catégories disponibles avec comptage (pour les filtres déroulants).
 */
export async function getCategoriesStats(): Promise<CategorieStats[]> {
  const resp = await fetchWithTimeout(`${STRUCTURES_BASE}/meta/categories`);
  return resp.json() as Promise<CategorieStats[]>;
}
