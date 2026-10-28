/**
 * MEDIZY / SANTÉ DZ — Types TypeScript pour l'API et la Cartographie
 */

export type FacilityType =
  | 'CHU'
  | 'EPH'
  | 'EPSP'
  | 'EHS'
  | 'Hôpital'
  | 'Clinique'
  | 'Polyclinique'
  | 'Urgences'
  | 'Centre de Santé'
  | 'Dispensaire'
  | 'Cabinet Médical';

export interface FacilityBadge {
  label: string;
  variant: 'info' | 'success' | 'warning';
  is_claimed: boolean;
  is_verified: boolean;
  can_claim: boolean;
  claim_url?: string | null;
}

export interface Facility {
  id: number;
  name: string;
  type: FacilityType;
  wilaya: string;
  wilaya_code?: string;
  commune?: string;
  address?: string;
  phone?: string;
  latitude: number;
  longitude: number;
  is_claimed: boolean;
  is_verified: boolean;
  source: string;
  google_place_id?: string;
  osm_id?: string;
  distance_meters?: number | null;
  badge: FacilityBadge;
  metadata?: Record<string, any>;
}

export interface MapBounds {
  min_lat: number;
  min_lon: number;
  max_lat: number;
  max_lon: number;
}

export interface FacilitySearchParams {
  lat?: number;
  lon?: number;
  radius_km?: number;
  bounds?: MapBounds;
  type?: FacilityType;
  wilaya?: string;
  commune?: string;
  q?: string;
  is_claimed?: boolean;
  limit?: number;
  offset?: number;
}

export interface SuggestFacilityPayload {
  name: string;
  type?: FacilityType;
  wilaya: string;
  commune?: string;
  address?: string;
  phone?: string;
  latitude?: number;
  longitude?: number;
  google_maps_url?: string;
  submitter_name?: string;
  submitter_email?: string;
  submitter_phone?: string;
  submitter_notes?: string;
}

export interface SuggestFacilityResponse {
  suggestion_id: number;
  status: 'PENDING' | 'APPROVED' | 'REJECTED' | 'DUPLICATE';
  message: string;
  parsed_coordinates?: {
    latitude: number;
    longitude: number;
  } | null;
  possible_duplicate_facility_id?: number | null;
  created_at: string;
}

export type SuggestionStatus = 'PENDING' | 'APPROVED' | 'REJECTED' | 'DUPLICATE';

export interface AdminSuggestion {
  id: number;
  name: string;
  type?: FacilityType;
  wilaya: string;
  commune?: string;
  address?: string;
  phone?: string;
  latitude?: number;
  longitude?: number;
  google_maps_url?: string;
  submitter_name?: string;
  submitter_email?: string;
  submitter_phone?: string;
  submitter_notes?: string;
  status: SuggestionStatus;
  matched_facility_id?: number | null;
  matched_facility?: Facility | null;
  distance_to_matched_meters?: number | null;
  moderated_by?: string | null;
  moderated_at?: string | null;
  moderation_comment?: string | null;
  created_at: string;
  updated_at?: string;
}

export interface AdminLoginCredentials {
  username: string;
  password: string;
}

export interface AdminAuthToken {
  access_token: string;
  token_type: string;
  expires_in: number;
  role: string;
  admin_name: string;
}

export interface ApproveSuggestionPayload {
  moderator_name?: string;
  override_name?: string;
  override_type?: FacilityType;
  moderation_comment?: string;
}

export interface RejectSuggestionPayload {
  reason: string;
  moderator_name?: string;
}

export interface DuplicateComparisonData {
  proposed: {
    id: number;
    name: string;
    type?: string;
    wilaya: string;
    commune?: string;
    address?: string;
    phone?: string;
    latitude: number;
    longitude: number;
    submitter_name?: string;
    submitter_notes?: string;
  };
  existing: {
    id: number;
    name: string;
    type: string;
    wilaya: string;
    commune?: string;
    address?: string;
    phone?: string;
    latitude: number;
    longitude: number;
    source: string;
    is_verified: boolean;
  };
  distance_meters: number;
  is_proximity_duplicate: boolean; // < 100 meters
}
