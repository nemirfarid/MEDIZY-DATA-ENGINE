/**
 * MEDIZY / SANTÉ DZ — Client API TypeScript (Frontend Web & Mobile)
 */

import {
  Facility,
  FacilitySearchParams,
  SuggestFacilityPayload,
  SuggestFacilityResponse,
} from './types';

const API_BASE_URL = process.env.NEXT_PUBLIC_MEDIZY_API_URL || 'http://localhost:8000';

export async function searchFacilities(params: FacilitySearchParams): Promise<{
  total: number;
  data: Facility[];
  execution_time_ms: number;
}> {
  const url = new URL(`${API_BASE_URL}/api/v1/facilities/search`);

  if (params.lat !== undefined && params.lon !== undefined) {
    url.searchParams.set('lat', params.lat.toString());
    url.searchParams.set('lon', params.lon.toString());
    if (params.radius_km) url.searchParams.set('radius_km', params.radius_km.toString());
  }

  if (params.bounds) {
    url.searchParams.set('min_lat', params.bounds.min_lat.toString());
    url.searchParams.set('min_lon', params.bounds.min_lon.toString());
    url.searchParams.set('max_lat', params.bounds.max_lat.toString());
    url.searchParams.set('max_lon', params.bounds.max_lon.toString());
  }

  if (params.type) url.searchParams.set('type', params.type);
  if (params.wilaya) url.searchParams.set('wilaya', params.wilaya);
  if (params.commune) url.searchParams.set('commune', params.commune);
  if (params.q) url.searchParams.set('q', params.q);
  if (params.is_claimed !== undefined) url.searchParams.set('is_claimed', params.is_claimed.toString());
  if (params.limit) url.searchParams.set('limit', params.limit.toString());
  if (params.offset) url.searchParams.set('offset', params.offset.toString());

  const response = await fetch(url.toString(), {
    method: 'GET',
    headers: { 'Accept': 'application/json' },
  });

  if (!response.ok) {
    throw new Error(`Erreur API MEDIZY (${response.status}): ${await response.text()}`);
  }

  return response.json();
}

export async function getFacilityDetail(facilityId: number): Promise<Facility> {
  const response = await fetch(`${API_BASE_URL}/api/v1/facilities/${facilityId}`, {
    method: 'GET',
    headers: { 'Accept': 'application/json' },
  });

  if (!response.ok) {
    throw new Error(`Établissement #${facilityId} introuvable`);
  }

  return response.json();
}

export async function submitFacilitySuggestion(
  payload: SuggestFacilityPayload
): Promise<SuggestFacilityResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/facilities/suggest`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || 'Impossible d\'enregistrer la suggestion.');
  }

  return response.json();
}
