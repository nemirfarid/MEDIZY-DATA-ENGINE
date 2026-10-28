-- ============================================================================
-- MEDIZY / SANTÉ DZ - Schéma PostgreSQL & PostGIS pour les Établissements de Santé
-- ============================================================================
-- Description:
--   Migration complète définissant la table `facilities`, l'indexation spatiale
--   GIST, la table de modération des suggestions citoyennes `facility_suggestions`,
--   les fonctions de recherche de proximité et la procédure de validation modérateur.
-- ============================================================================

-- 1. EXTENSIONS REQUISES
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS unaccent;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- 2. TABLE PRINCIPALE: FACILITIES (Établissements de Santé)
CREATE TABLE IF NOT EXISTS facilities (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(50) NOT NULL CHECK (
        type IN (
            'CHU',
            'EPH',
            'EPSP',
            'EHS',
            'Hôpital',
            'Clinique',
            'Polyclinique',
            'Urgences',
            'Centre de Santé',
            'Dispensaire',
            'Cabinet Médical'
        )
    ),
    wilaya VARCHAR(100) NOT NULL,
    wilaya_code VARCHAR(5),
    commune VARCHAR(100),
    address TEXT,
    phone VARCHAR(50),
    phone_normalized VARCHAR(50),
    
    -- Colonne spatiale PostGIS (WGS84 - EPSG:4326)
    geom GEOMETRY(Point, 4326) NOT NULL,
    
    -- Flags d'état et propriété de la fiche
    is_claimed BOOLEAN NOT NULL DEFAULT FALSE,
    is_verified BOOLEAN NOT NULL DEFAULT FALSE,
    
    -- Traçabilité et provenance des données
    source VARCHAR(50) NOT NULL DEFAULT 'manual' CHECK (
        source IN ('google_places', 'openstreetmap', 'dsp', 'manual', 'community_suggestion')
    ),
    google_place_id VARCHAR(255) UNIQUE,
    osm_id VARCHAR(100) UNIQUE,
    
    -- Données complémentaires (horaires, équipements, spécialités)
    metadata JSONB DEFAULT '{}'::jsonb,
    
    -- Audit & Horodatage
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Commentaires descriptifs sur la table et les colonnes
COMMENT ON TABLE facilities IS 'Référentiel géospatial national des structures de santé publiques et privées en Algérie.';
COMMENT ON COLUMN facilities.geom IS 'Coordonnées GPS projetées en EPSG:4326 (Point longitude, latitude).';
COMMENT ON COLUMN facilities.is_claimed IS 'Faux si l''établissement est une fiche publique informative non encore revendiquée par un praticien/administrateur.';
COMMENT ON COLUMN facilities.is_verified IS 'Vrai si les informations ont été contrôlées par un administrateur MEDIZY ou issues d''une source officielle (DSP/Ministère).';

-- 3. INDEXATION HAUTE PERFORMANCE
-- Index spatial GiST pour requêtes ST_DWithin / KNN ultra-rapides
CREATE INDEX IF NOT EXISTS idx_facilities_geom ON facilities USING GIST (geom);

-- Index composites pour les filtres fréquents
CREATE INDEX IF NOT EXISTS idx_facilities_wilaya_type ON facilities (wilaya, type);
CREATE INDEX IF NOT EXISTS idx_facilities_commune ON facilities (commune);
CREATE INDEX IF NOT EXISTS idx_facilities_is_claimed ON facilities (is_claimed);
CREATE INDEX IF NOT EXISTS idx_facilities_is_verified ON facilities (is_verified);
CREATE INDEX IF NOT EXISTS idx_facilities_source ON facilities (source);

-- Index trigramme (pg_trgm) pour la recherche textuelle insensible aux fautes de frappe et accents
CREATE INDEX IF NOT EXISTS idx_facilities_name_trgm ON facilities USING GIN (name gin_trgm_ops);

-- Index partiels sur les identifiants externes
CREATE INDEX IF NOT EXISTS idx_facilities_google_place_id ON facilities (google_place_id) WHERE google_place_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_facilities_osm_id ON facilities (osm_id) WHERE osm_id IS NOT NULL;


-- 4. TABLE DE MODÉRATION: FACILITY_SUGGESTIONS (Contributions communautaires)
CREATE TABLE IF NOT EXISTS facility_suggestions (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    type VARCHAR(50) CHECK (
        type IS NULL OR type IN (
            'CHU', 'EPH', 'EPSP', 'EHS', 'Hôpital', 'Clinique',
            'Polyclinique', 'Urgences', 'Centre de Santé', 'Dispensaire', 'Cabinet Médical'
        )
    ),
    wilaya VARCHAR(100) NOT NULL,
    commune VARCHAR(100),
    address TEXT,
    phone VARCHAR(50),
    
    -- Coordonnées proposées
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    geom GEOMETRY(Point, 4326),
    
    -- Lien Google Maps fourni par le contributeur
    google_maps_url TEXT,
    
    -- Informations sur le contributeur
    submitter_name VARCHAR(150),
    submitter_email VARCHAR(150),
    submitter_phone VARCHAR(50),
    submitter_notes TEXT,
    
    -- Statut du cycle de modération
    status VARCHAR(30) NOT NULL DEFAULT 'PENDING' CHECK (
        status IN ('PENDING', 'APPROVED', 'REJECTED', 'DUPLICATE')
    ),
    matched_facility_id BIGINT REFERENCES facilities(id) ON DELETE SET NULL,
    
    -- Traçabilité de la décision
    moderated_by VARCHAR(150),
    moderated_at TIMESTAMPTZ,
    moderation_comment TEXT,
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE facility_suggestions IS 'File d''attente de modération pour les établissements de santé suggérés par les utilisateurs et professionnels.';

-- Index pour la table de modération
CREATE INDEX IF NOT EXISTS idx_suggestions_status ON facility_suggestions (status);
CREATE INDEX IF NOT EXISTS idx_suggestions_geom ON facility_suggestions USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_suggestions_created ON facility_suggestions (created_at DESC);


-- 5. TRIGGERS POUR MISE À JOUR AUTOMATIQUE DE UPDATED_AT
CREATE OR REPLACE FUNCTION fn_update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_facilities_timestamp ON facilities;
CREATE TRIGGER trg_facilities_timestamp
BEFORE UPDATE ON facilities
FOR EACH ROW
EXECUTE FUNCTION fn_update_timestamp();

DROP TRIGGER IF EXISTS trg_suggestions_timestamp ON facility_suggestions;
CREATE TRIGGER trg_suggestions_timestamp
BEFORE UPDATE ON facility_suggestions
FOR EACH ROW
EXECUTE FUNCTION fn_update_timestamp();


-- 6. TRIGGER POUR SYNCHRONISATION AUTOMATIQUE DE GEOM DANS FACILITY_SUGGESTIONS
CREATE OR REPLACE FUNCTION fn_sync_suggestion_geom()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.latitude IS NOT NULL AND NEW.longitude IS NOT NULL THEN
        -- Validation des coordonnées en Algérie (Latitude [18.0, 38.0], Longitude [-9.0, 13.0])
        IF NEW.latitude BETWEEN 18.0 AND 38.5 AND NEW.longitude BETWEEN -9.5 AND 13.0 THEN
            NEW.geom = ST_SetSRID(ST_MakePoint(NEW.longitude, NEW.latitude), 4326);
        END IF;
    ELSIF NEW.geom IS NOT NULL THEN
        NEW.longitude = ST_X(NEW.geom);
        NEW.latitude = ST_Y(NEW.geom);
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_suggestions_geom ON facility_suggestions;
CREATE TRIGGER trg_suggestions_geom
BEFORE INSERT OR UPDATE ON facility_suggestions
FOR EACH ROW
EXECUTE FUNCTION fn_sync_suggestion_geom();


-- 7. FONCTION DE PROCÉDURE MÉTIER: APPROBATION D'UNE SUGGESTION VERS FACILITIES
CREATE OR REPLACE FUNCTION fn_approve_facility_suggestion(
    p_suggestion_id BIGINT,
    p_moderator VARCHAR,
    p_comment TEXT DEFAULT NULL
)
RETURNS BIGINT AS $$
DECLARE
    v_sug RECORD;
    v_new_facility_id BIGINT;
    v_type VARCHAR(50);
BEGIN
    -- Récupération de la suggestion
    SELECT * INTO v_sug FROM facility_suggestions WHERE id = p_suggestion_id FOR UPDATE;
    
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Suggestion ID % introuvable', p_suggestion_id;
    END IF;
    
    IF v_sug.status != 'PENDING' THEN
        RAISE EXCEPTION 'La suggestion ID % n''est plus en attente (statut: %)', p_suggestion_id, v_sug.status;
    END IF;
    
    IF v_sug.geom IS NULL THEN
        RAISE EXCEPTION 'Impossible d''approuver: coordonnées GPS manquantes pour la suggestion ID %', p_suggestion_id;
    END IF;
    
    v_type := COALESCE(v_sug.type, 'Clinique');

    -- Insertion dans le référentiel officiel
    INSERT INTO facilities (
        name,
        type,
        wilaya,
        commune,
        address,
        phone,
        geom,
        is_claimed,
        is_verified,
        source,
        metadata
    ) VALUES (
        v_sug.name,
        v_type,
        v_sug.wilaya,
        v_sug.commune,
        v_sug.address,
        v_sug.phone,
        v_sug.geom,
        FALSE,          -- is_claimed: reste non revendiqué
        TRUE,           -- is_verified: validé par le modérateur
        'community_suggestion',
        jsonb_build_object(
            'approved_by', p_moderator,
            'approved_at', CURRENT_TIMESTAMP,
            'google_maps_url', v_sug.google_maps_url,
            'suggestion_id', v_sug.id,
            'submitter_notes', v_sug.submitter_notes
        )
    )
    RETURNING id INTO v_new_facility_id;

    -- Mise à jour du statut de la suggestion
    UPDATE facility_suggestions
    SET status = 'APPROVED',
        moderated_by = p_moderator,
        moderated_at = CURRENT_TIMESTAMP,
        moderation_comment = p_comment,
        matched_facility_id = v_new_facility_id
    WHERE id = p_suggestion_id;

    RETURN v_new_facility_id;
END;
$$ LANGUAGE plpgsql;


-- 8. VUE APPLICATIVE OPTIMISÉE POUR L'API ET L'AFFICHAGE CARTO
CREATE OR REPLACE VIEW v_facilities_public AS
SELECT
    f.id,
    f.name,
    f.type,
    f.wilaya,
    f.wilaya_code,
    f.commune,
    f.address,
    f.phone,
    ST_Y(f.geom) AS latitude,
    ST_X(f.geom) AS longitude,
    f.is_claimed,
    f.is_verified,
    f.source,
    f.google_place_id,
    f.metadata,
    CASE 
        WHEN f.is_claimed THEN 'Établissement revendiqué et vérifié'
        ELSE 'Fiche informative publique'
    END AS badge_label,
    CASE 
        WHEN f.is_claimed THEN 'claimed'
        ELSE 'unclaimed_public'
    END AS badge_status
FROM facilities f;
