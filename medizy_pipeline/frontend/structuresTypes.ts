/**
 * MEDIZY / SANTÉ DZ — Types TypeScript pour l'Annuaire Sanitaire National
 * Correspondance exacte avec les colonnes du CSV et le schéma Pydantic /api/structures
 */

export interface Structure {
  id: number;
  code_wilaya: string;
  nom_wilaya: string;
  nom_daira?: string | null;
  nom_commune?: string | null;
  categorie: string;
  discipline_specialite?: string | null;
  nom_etablissement_praticien: string;
  adresse?: string | null;
  telephone?: string | null;
  horaires?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  statut_remarques?: string | null;
  source_csv?: string | null;
  is_verified: boolean;
  distance_meters?: number | null;
}

export interface StructureListResponse {
  total: number;
  limit: number;
  offset: number;
  execution_time_ms: number;
  data: Structure[];
}

export interface WilayaStats {
  code_wilaya: string;
  nom_wilaya: string;
  total: number;
  avec_gps: number;
  nb_categories: number;
  nb_communes: number;
}

export interface CategorieStats {
  categorie: string;
  total: number;
}

export interface StructureSearchParams {
  q?: string;
  code_wilaya?: string;
  nom_wilaya?: string;
  nom_commune?: string;
  categorie?: string;
  discipline?: string;
  lat?: number;
  lon?: number;
  radius_km?: number;
  limit?: number;
  offset?: number;
}
