-- ============================================================================
-- MEDIZY / SANTÉ DZ — Migration 002 : Table structures (Annuaire National)
-- ============================================================================
-- Table dédiée aux 41 421 entrées du fichier CSV maître
-- Annuaire_Sanitaire_National_Algerie_58_Wilayas_Parfait.csv
-- Colonnes calquées exactement sur la structure CSV ; index couvrant toutes
-- les requêtes de filtrage / tri / géolocalisation prévues dans l'API.
-- ============================================================================

-- Extensions (idempotent : CREATE IF NOT EXISTS)
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS unaccent;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- ===========================================================================
-- 1. TABLE PRINCIPALE : structures
-- ===========================================================================
CREATE TABLE IF NOT EXISTS structures (
    id                       BIGSERIAL PRIMARY KEY,

    -- Colonnes administratives / géographiques
    code_wilaya              VARCHAR(3)   NOT NULL CHECK (code_wilaya ~ '^\d{2}$'),
    nom_wilaya               VARCHAR(100) NOT NULL,
    nom_daira                VARCHAR(100),
    nom_commune              VARCHAR(100),

    -- Classification sanitaire
    categorie                VARCHAR(120) NOT NULL,          -- ex: Établissement Public, Pharmacie d'Officine…
    discipline_specialite    VARCHAR(200),                   -- ex: Cardiologie, Chirurgien-Dentiste…

    -- Identité de l'établissement ou praticien
    nom_etablissement_praticien VARCHAR(300) NOT NULL,

    -- Coordonnées
    adresse                  TEXT,
    telephone                VARCHAR(80),

    -- Disponibilité / horaires
    horaires                 VARCHAR(100),                   -- ex: "Urgences 24h/24", "Lun–Ven 08h–17h"

    -- Géolocalisation PostGIS (nullable : certains établissements sans GPS)
    latitude                 DOUBLE PRECISION,
    longitude                DOUBLE PRECISION,
    coordonnees_gps          VARCHAR(80),                    -- champ texte original du CSV
    geom                     GEOMETRY(Point, 4326),          -- colonne spatiale générée à l'import

    -- Informations complémentaires
    statut_remarques         TEXT,                           -- missions, équipements clés
    source_csv               VARCHAR(200),                   -- organisme d'agrément ou source officielle

    -- Traçabilité
    is_verified              BOOLEAN NOT NULL DEFAULT FALSE,
    imported_at              TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at               TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE structures IS
    'Référentiel national complet (41 421 entrées) des structures de santé et praticiens algériens '
    'issu de l''Annuaire_Sanitaire_National_Algerie_58_Wilayas_Parfait.csv.';

COMMENT ON COLUMN structures.geom IS
    'Point PostGIS EPSG:4326 (longitude, latitude) généré automatiquement à partir des colonnes '
    'latitude/longitude lors de l''import CSV.';

COMMENT ON COLUMN structures.code_wilaya IS
    'Code numérique de la wilaya sur 2 chiffres (01 à 58), ex : ''16'' pour Alger.';

-- ===========================================================================
-- 2. TRIGGER : Mise à jour automatique du champ updated_at
-- ===========================================================================
CREATE OR REPLACE FUNCTION fn_structures_set_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_structures_updated_at ON structures;
CREATE TRIGGER trg_structures_updated_at
    BEFORE UPDATE ON structures
    FOR EACH ROW EXECUTE FUNCTION fn_structures_set_updated_at();

-- ===========================================================================
-- 3. INDEXATION HAUTE PERFORMANCE
-- ===========================================================================

-- 3.1 Index spatial GiST (ST_DWithin / KNN / viewport BBox)
CREATE INDEX IF NOT EXISTS idx_structures_geom
    ON structures USING GIST (geom)
    WHERE geom IS NOT NULL;

-- 3.2 Index B-Tree sur les colonnes de filtrage fréquentes
CREATE INDEX IF NOT EXISTS idx_structures_code_wilaya   ON structures (code_wilaya);
CREATE INDEX IF NOT EXISTS idx_structures_nom_wilaya    ON structures (nom_wilaya);
CREATE INDEX IF NOT EXISTS idx_structures_nom_commune   ON structures (nom_commune);
CREATE INDEX IF NOT EXISTS idx_structures_categorie     ON structures (categorie);
CREATE INDEX IF NOT EXISTS idx_structures_discipline    ON structures (discipline_specialite);

-- 3.3 Index composite wilaya + catégorie (filtre le plus fréquent en production)
CREATE INDEX IF NOT EXISTS idx_structures_wilaya_categorie
    ON structures (code_wilaya, categorie);

-- 3.4 Index composite wilaya + commune (navigation géographique descendante)
CREATE INDEX IF NOT EXISTS idx_structures_wilaya_commune
    ON structures (code_wilaya, nom_commune);

-- 3.5 Recherche textuelle trigramme (pg_trgm) — insensible aux accents et fautes de frappe
CREATE INDEX IF NOT EXISTS idx_structures_nom_trgm
    ON structures USING GIN (unaccent(nom_etablissement_praticien) gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_structures_categorie_trgm
    ON structures USING GIN (categorie gin_trgm_ops);

CREATE INDEX IF NOT EXISTS idx_structures_discipline_trgm
    ON structures USING GIN (unaccent(discipline_specialite) gin_trgm_ops);

-- 3.6 Index partiel sur les structures géocodées (accélère les requêtes ST_DWithin)
CREATE INDEX IF NOT EXISTS idx_structures_has_geom
    ON structures (id)
    WHERE geom IS NOT NULL;

-- ===========================================================================
-- 4. VUES MATÉRIALISÉES UTILITAIRES
-- ===========================================================================

-- Vue agrégée par wilaya (tableau de bord et statistiques nationales)
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_structures_par_wilaya AS
    SELECT
        code_wilaya,
        nom_wilaya,
        COUNT(*)                                  AS total,
        COUNT(*) FILTER (WHERE geom IS NOT NULL)  AS avec_gps,
        COUNT(DISTINCT categorie)                 AS nb_categories,
        COUNT(DISTINCT nom_commune)               AS nb_communes
    FROM structures
    GROUP BY code_wilaya, nom_wilaya
    ORDER BY code_wilaya;

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_wilaya_pk
    ON mv_structures_par_wilaya (code_wilaya);

-- Vue agrégée par catégorie (filtre rapide de la liste déroulante UI)
CREATE MATERIALIZED VIEW IF NOT EXISTS mv_structures_par_categorie AS
    SELECT
        categorie,
        COUNT(*)             AS total,
        array_agg(DISTINCT code_wilaya ORDER BY code_wilaya) AS wilayas
    FROM structures
    GROUP BY categorie
    ORDER BY total DESC;

CREATE UNIQUE INDEX IF NOT EXISTS idx_mv_categorie_pk
    ON mv_structures_par_categorie (categorie);

-- ===========================================================================
-- 5. FONCTION DE RECHERCHE SPATIALE RAPIDE
-- ===========================================================================
CREATE OR REPLACE FUNCTION fn_structures_nearby(
    p_lat          DOUBLE PRECISION,
    p_lon          DOUBLE PRECISION,
    p_radius_km    DOUBLE PRECISION DEFAULT 5.0,
    p_categorie    VARCHAR          DEFAULT NULL,
    p_wilaya       VARCHAR          DEFAULT NULL,
    p_discipline   VARCHAR          DEFAULT NULL,
    p_limit        INT              DEFAULT 20,
    p_offset       INT              DEFAULT 0
)
RETURNS TABLE (
    id                          BIGINT,
    nom_etablissement_praticien VARCHAR,
    categorie                   VARCHAR,
    discipline_specialite       VARCHAR,
    nom_wilaya                  VARCHAR,
    nom_commune                 VARCHAR,
    adresse                     TEXT,
    telephone                   VARCHAR,
    horaires                    VARCHAR,
    latitude                    DOUBLE PRECISION,
    longitude                   DOUBLE PRECISION,
    statut_remarques            TEXT,
    is_verified                 BOOLEAN,
    distance_meters             DOUBLE PRECISION
) LANGUAGE SQL STABLE AS $$
    SELECT
        s.id,
        s.nom_etablissement_praticien,
        s.categorie,
        s.discipline_specialite,
        s.nom_wilaya,
        s.nom_commune,
        s.adresse,
        s.telephone,
        s.horaires,
        s.latitude,
        s.longitude,
        s.statut_remarques,
        s.is_verified,
        ST_Distance(
            s.geom::geography,
            ST_SetSRID(ST_MakePoint(p_lon, p_lat), 4326)::geography
        ) AS distance_meters
    FROM structures s
    WHERE
        s.geom IS NOT NULL
        AND ST_DWithin(
            s.geom::geography,
            ST_SetSRID(ST_MakePoint(p_lon, p_lat), 4326)::geography,
            p_radius_km * 1000.0
        )
        AND (p_categorie    IS NULL OR s.categorie            ILIKE '%' || p_categorie  || '%')
        AND (p_wilaya       IS NULL OR s.nom_wilaya           ILIKE '%' || p_wilaya     || '%'
                                    OR s.code_wilaya          = p_wilaya)
        AND (p_discipline   IS NULL OR s.discipline_specialite ILIKE '%' || p_discipline || '%')
    ORDER BY distance_meters
    LIMIT  p_limit
    OFFSET p_offset;
$$;

COMMENT ON FUNCTION fn_structures_nearby IS
    'Recherche spatiale optimisée ST_DWithin avec filtres optionnels. '
    'Retour trié par distance croissante. Rayon en km.';

-- ===========================================================================
-- 6. RAFRAÎCHISSEMENT DES VUES MATÉRIALISÉES (à exécuter après import)
-- ===========================================================================
-- REFRESH MATERIALIZED VIEW CONCURRENTLY mv_structures_par_wilaya;
-- REFRESH MATERIALIZED VIEW CONCURRENTLY mv_structures_par_categorie;
