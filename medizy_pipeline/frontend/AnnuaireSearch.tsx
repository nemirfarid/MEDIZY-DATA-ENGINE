/**
 * MEDIZY / SANTÉ DZ — Composant de Recherche de l'Annuaire Sanitaire National
 * ===========================================================================
 * Fonctionnalités :
 *  - Barre de recherche textuelle libre + filtres (wilaya, catégorie, spécialité, commune)
 *  - Bouton "Utiliser ma position GPS" → recherche radiale (radius_km configurable)
 *  - Liste de résultats avec fiches détaillées (téléphone, horaires, adresse, badge GPS)
 *  - Pagination intégrée
 *  - Mode mobile-first (flex wrap, taille de police adaptée)
 *
 * Dépendances : React 18+, aucune autre lib requise (CSS natif inline)
 * Usage :
 *   import AnnuaireSearch from './AnnuaireSearch';
 *   <AnnuaireSearch />
 */

import React, {
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";

import {
  getCategoriesStats,
  getNearbyStructures,
  searchStructures,
} from "./structuresApi";
import type {
  CategorieStats,
  Structure,
  StructureListResponse,
} from "./structuresTypes";

// ─────────────────────────────────────────────────────────────────────────────
// Icônes SVG inline (pas de dépendance externe)
// ─────────────────────────────────────────────────────────────────────────────

const IconSearch = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
    <circle cx="11" cy="11" r="8" /><path d="M21 21l-4.35-4.35" />
  </svg>
);

const IconGPS = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2">
    <path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7z" />
    <circle cx="12" cy="9" r="2.5" fill="currentColor" />
  </svg>
);

const IconPhone = () => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M22 16.92v3a2 2 0 01-2.18 2A19.79 19.79 0 013.09 5.18 2 2 0 015.1 3h3a2 2 0 012 1.72c.127.96.361 1.903.7 2.81a2 2 0 01-.45 2.11L9.09 11a16 16 0 006.91 6.91l1.27-1.27a2 2 0 012.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0122 16.92z" />
  </svg>
);

const IconClock = () => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <circle cx="12" cy="12" r="10" /><polyline points="12 6 12 12 16 14" />
  </svg>
);

const IconLocation = () => (
  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7z" /><circle cx="12" cy="9" r="2.5" />
  </svg>
);

// ─────────────────────────────────────────────────────────────────────────────
// CSS-in-JS (inline styles) pour éviter tout import CSS externe
// ─────────────────────────────────────────────────────────────────────────────

const S = {
  container: {
    fontFamily: "'Segoe UI', 'Roboto', sans-serif",
    maxWidth: "900px",
    margin: "0 auto",
    padding: "16px",
    color: "#1a1a2e",
  } as React.CSSProperties,

  header: {
    marginBottom: "20px",
  } as React.CSSProperties,

  title: {
    fontSize: "22px",
    fontWeight: 700,
    color: "#0f3460",
    margin: "0 0 4px",
  } as React.CSSProperties,

  subtitle: {
    fontSize: "13px",
    color: "#6b7280",
    margin: 0,
  } as React.CSSProperties,

  searchBar: {
    display: "flex",
    gap: "8px",
    marginBottom: "12px",
    flexWrap: "wrap" as const,
  } as React.CSSProperties,

  inputWrapper: {
    flex: 1,
    minWidth: "200px",
    position: "relative" as const,
    display: "flex",
    alignItems: "center",
  } as React.CSSProperties,

  inputIcon: {
    position: "absolute" as const,
    left: "10px",
    color: "#9ca3af",
    pointerEvents: "none" as const,
  } as React.CSSProperties,

  input: {
    width: "100%",
    padding: "10px 12px 10px 36px",
    border: "1.5px solid #d1d5db",
    borderRadius: "10px",
    fontSize: "14px",
    outline: "none",
    boxSizing: "border-box" as const,
    transition: "border-color 0.2s",
  } as React.CSSProperties,

  select: {
    padding: "10px 12px",
    border: "1.5px solid #d1d5db",
    borderRadius: "10px",
    fontSize: "14px",
    outline: "none",
    background: "#fff",
    cursor: "pointer",
    minWidth: "140px",
  } as React.CSSProperties,

  btnGps: {
    display: "flex",
    alignItems: "center",
    gap: "6px",
    padding: "10px 14px",
    background: "#0f3460",
    color: "#fff",
    border: "none",
    borderRadius: "10px",
    fontSize: "13px",
    fontWeight: 600,
    cursor: "pointer",
    whiteSpace: "nowrap" as const,
    transition: "background 0.2s",
  } as React.CSSProperties,

  btnSearch: {
    display: "flex",
    alignItems: "center",
    gap: "6px",
    padding: "10px 16px",
    background: "#16213e",
    color: "#fff",
    border: "none",
    borderRadius: "10px",
    fontSize: "13px",
    fontWeight: 600,
    cursor: "pointer",
    transition: "background 0.2s",
  } as React.CSSProperties,

  filtersRow: {
    display: "flex",
    gap: "8px",
    flexWrap: "wrap" as const,
    marginBottom: "14px",
  } as React.CSSProperties,

  meta: {
    fontSize: "12px",
    color: "#6b7280",
    marginBottom: "10px",
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    flexWrap: "wrap" as const,
    gap: "4px",
  } as React.CSSProperties,

  list: {
    display: "flex",
    flexDirection: "column" as const,
    gap: "10px",
  } as React.CSSProperties,

  card: {
    background: "#fff",
    border: "1px solid #e5e7eb",
    borderRadius: "14px",
    padding: "14px 16px",
    boxShadow: "0 1px 4px rgba(0,0,0,0.06)",
    cursor: "pointer",
    transition: "box-shadow 0.2s, border-color 0.2s",
  } as React.CSSProperties,

  cardTop: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "flex-start",
    marginBottom: "6px",
    flexWrap: "wrap" as const,
    gap: "4px",
  } as React.CSSProperties,

  cardName: {
    fontWeight: 700,
    fontSize: "15px",
    color: "#0f3460",
    flex: 1,
    minWidth: 0,
    wordBreak: "break-word" as const,
  } as React.CSSProperties,

  badgeCategorie: {
    background: "#e8f4fd",
    color: "#0369a1",
    fontSize: "11px",
    fontWeight: 600,
    padding: "3px 9px",
    borderRadius: "20px",
    whiteSpace: "nowrap" as const,
  } as React.CSSProperties,

  badgeVerified: {
    background: "#d1fae5",
    color: "#065f46",
    fontSize: "11px",
    fontWeight: 600,
    padding: "3px 8px",
    borderRadius: "20px",
  } as React.CSSProperties,

  badgeDistance: {
    background: "#fef3c7",
    color: "#92400e",
    fontSize: "11px",
    fontWeight: 600,
    padding: "3px 9px",
    borderRadius: "20px",
  } as React.CSSProperties,

  infoRow: {
    display: "flex",
    alignItems: "center",
    gap: "6px",
    fontSize: "13px",
    color: "#374151",
    marginTop: "4px",
  } as React.CSSProperties,

  discipline: {
    fontSize: "12px",
    color: "#7c3aed",
    fontStyle: "italic",
    marginTop: "2px",
  } as React.CSSProperties,

  pagination: {
    display: "flex",
    justifyContent: "center",
    alignItems: "center",
    gap: "8px",
    marginTop: "20px",
  } as React.CSSProperties,

  pageBtn: (active: boolean, disabled: boolean): React.CSSProperties => ({
    padding: "7px 13px",
    border: active ? "2px solid #0f3460" : "1px solid #d1d5db",
    borderRadius: "8px",
    background: active ? "#0f3460" : "#fff",
    color: active ? "#fff" : disabled ? "#d1d5db" : "#374151",
    fontSize: "13px",
    fontWeight: active ? 700 : 400,
    cursor: disabled ? "not-allowed" : "pointer",
    transition: "all 0.15s",
  }),

  noResults: {
    textAlign: "center" as const,
    padding: "40px 20px",
    color: "#9ca3af",
    fontSize: "15px",
  } as React.CSSProperties,

  loading: {
    textAlign: "center" as const,
    padding: "30px",
    color: "#6b7280",
    fontSize: "14px",
  } as React.CSSProperties,

  error: {
    background: "#fef2f2",
    border: "1px solid #fca5a5",
    borderRadius: "10px",
    padding: "12px 16px",
    color: "#dc2626",
    fontSize: "13px",
    marginBottom: "12px",
  } as React.CSSProperties,
};

// ─────────────────────────────────────────────────────────────────────────────
// Sous-composant : carte d'une structure
// ─────────────────────────────────────────────────────────────────────────────

function StructureCard({ item }: { item: Structure }) {
  const [expanded, setExpanded] = useState(false);

  const formatDistance = (m?: number | null) => {
    if (!m) return null;
    return m < 1000 ? `${Math.round(m)} m` : `${(m / 1000).toFixed(1)} km`;
  };

  const dist = formatDistance(item.distance_meters);

  return (
    <div
      style={{
        ...S.card,
        borderLeft: item.is_verified ? "4px solid #10b981" : "4px solid #93c5fd",
      }}
      onClick={() => setExpanded((e) => !e)}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === "Enter" && setExpanded((prev) => !prev)}
      aria-expanded={expanded}
    >
      {/* ── En-tête ── */}
      <div style={S.cardTop}>
        <span style={S.cardName}>{item.nom_etablissement_praticien}</span>
        <div style={{ display: "flex", gap: "5px", flexWrap: "wrap", alignItems: "center" }}>
          {dist && <span style={S.badgeDistance}>📍 {dist}</span>}
          {item.is_verified && <span style={S.badgeVerified}>✓ Vérifié</span>}
          <span style={S.badgeCategorie}>{item.categorie}</span>
        </div>
      </div>

      {/* ── Spécialité ── */}
      {item.discipline_specialite && (
        <div style={S.discipline}>
          {item.discipline_specialite}
        </div>
      )}

      {/* ── Localisation (toujours visible) ── */}
      <div style={S.infoRow}>
        <IconLocation />
        <span>
          {[item.nom_commune, item.nom_daira, item.nom_wilaya]
            .filter(Boolean)
            .join(", ")}
        </span>
      </div>

      {/* ── Détails (visibles après clic) ── */}
      {expanded && (
        <div style={{ marginTop: "10px", borderTop: "1px solid #f3f4f6", paddingTop: "10px" }}>
          {item.adresse && (
            <div style={S.infoRow}>
              <IconLocation />
              <span>{item.adresse}</span>
            </div>
          )}
          {item.telephone && (
            <div style={S.infoRow}>
              <IconPhone />
              <a
                href={`tel:${item.telephone}`}
                style={{ color: "#0369a1", textDecoration: "none", fontWeight: 600 }}
                onClick={(e) => e.stopPropagation()}
              >
                {item.telephone}
              </a>
            </div>
          )}
          {item.horaires && (
            <div style={S.infoRow}>
              <IconClock />
              <span
                style={{
                  background: item.horaires.toLowerCase().includes("24h")
                    ? "#fef9c3"
                    : "#f9fafb",
                  borderRadius: "6px",
                  padding: "1px 7px",
                  fontSize: "12px",
                  fontWeight: 600,
                  color: item.horaires.toLowerCase().includes("24h") ? "#854d0e" : "#374151",
                }}
              >
                {item.horaires}
              </span>
            </div>
          )}
          {item.statut_remarques && (
            <div style={{ ...S.infoRow, fontSize: "12px", color: "#6b7280", marginTop: "6px" }}>
              <span style={{ fontStyle: "italic" }}>{item.statut_remarques}</span>
            </div>
          )}
          {item.latitude && item.longitude && (
            <a
              href={`https://maps.google.com/?q=${item.latitude},${item.longitude}`}
              target="_blank"
              rel="noopener noreferrer"
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "4px",
                marginTop: "8px",
                color: "#0369a1",
                fontSize: "12px",
                fontWeight: 600,
                textDecoration: "none",
              }}
              onClick={(e) => e.stopPropagation()}
            >
              <IconGPS /> Voir sur Google Maps
            </a>
          )}
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Composant principal : AnnuaireSearch
// ─────────────────────────────────────────────────────────────────────────────

const PAGE_SIZE = 20;

export default function AnnuaireSearch() {
  // Champs de recherche
  const [q, setQ] = useState("");
  const [codeWilaya, setCodeWilaya] = useState("");
  const [nomCommune, setNomCommune] = useState("");
  const [categorie, setCategorie] = useState("");
  const [discipline, setDiscipline] = useState("");
  const [radiusKm, setRadiusKm] = useState(10);

  // Données
  const [results, setResults] = useState<Structure[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [execMs, setExecMs] = useState<number | null>(null);
  const [categories, setCategories] = useState<CategorieStats[]>([]);

  // GPS
  const [userLat, setUserLat] = useState<number | null>(null);
  const [userLon, setUserLon] = useState<number | null>(null);
  const [gpsActive, setGpsActive] = useState(false);
  const [gpsLoading, setGpsLoading] = useState(false);

  const totalPages = Math.ceil(total / PAGE_SIZE);

  // Charger les catégories au montage
  useEffect(() => {
    getCategoriesStats().then(setCategories).catch(() => {});
  }, []);

  // ── Déclenchement de la recherche ──
  const doSearch = useCallback(
    async (pageIndex = 0) => {
      setLoading(true);
      setError(null);
      try {
        let resp: StructureListResponse;

        if (gpsActive && userLat !== null && userLon !== null && !q && !categorie && !discipline && !codeWilaya && !nomCommune) {
          // Mode GPS pur → endpoint /nearby
          resp = await getNearbyStructures(userLat, userLon, radiusKm, {
            limit: PAGE_SIZE,
          });
        } else {
          resp = await searchStructures({
            q: q || undefined,
            code_wilaya: codeWilaya || undefined,
            nom_commune: nomCommune || undefined,
            categorie: categorie || undefined,
            discipline: discipline || undefined,
            lat: gpsActive && userLat !== null ? userLat : undefined,
            lon: gpsActive && userLon !== null ? userLon : undefined,
            radius_km: gpsActive ? radiusKm : undefined,
            limit: PAGE_SIZE,
            offset: pageIndex * PAGE_SIZE,
          });
        }

        setResults(resp.data);
        setTotal(resp.total);
        setExecMs(resp.execution_time_ms);
        setPage(pageIndex);
      } catch (err: any) {
        setError(err?.message || "Erreur de connexion à l'API MEDIZY.");
        setResults([]);
        setTotal(0);
      } finally {
        setLoading(false);
      }
    },
    [q, codeWilaya, nomCommune, categorie, discipline, gpsActive, userLat, userLon, radiusKm]
  );

  // Recherche automatique à chaque changement de filtre (avec debounce 350 ms)
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => doSearch(0), 350);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [q, codeWilaya, nomCommune, categorie, discipline, gpsActive, userLat, userLon, radiusKm]);

  // ── Géolocalisation ──
  const handleGPS = () => {
    if (!navigator.geolocation) {
      setError("La géolocalisation n'est pas supportée par votre navigateur.");
      return;
    }
    setGpsLoading(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setUserLat(pos.coords.latitude);
        setUserLon(pos.coords.longitude);
        setGpsActive(true);
        setGpsLoading(false);
      },
      (err) => {
        setError("Impossible d'accéder à votre position GPS. Vérifiez les permissions.");
        setGpsLoading(false);
      },
      { timeout: 8000, enableHighAccuracy: true }
    );
  };

  const handleDisableGPS = () => {
    setGpsActive(false);
    setUserLat(null);
    setUserLon(null);
  };

  // ─── Rendu ───────────────────────────────────────────────────────────────

  return (
    <div style={S.container}>
      {/* ── En-tête ── */}
      <div style={S.header}>
        <h1 style={S.title}>🏥 Annuaire Sanitaire National</h1>
        <p style={S.subtitle}>
          41 421 structures de santé · 58 wilayas · Algérie
        </p>
      </div>

      {/* ── Barre de recherche principale ── */}
      <div style={S.searchBar}>
        <div style={S.inputWrapper}>
          <span style={S.inputIcon}><IconSearch /></span>
          <input
            id="annuaire-search-q"
            style={S.input}
            type="search"
            placeholder="Nom, Dr, Clinique, adresse…"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            aria-label="Recherche textuelle libre"
          />
        </div>

        {/* GPS toggle */}
        {gpsActive ? (
          <button style={{ ...S.btnGps, background: "#059669" }} onClick={handleDisableGPS} type="button">
            <IconGPS /> GPS actif · {radiusKm} km
          </button>
        ) : (
          <button
            style={{ ...S.btnGps, opacity: gpsLoading ? 0.6 : 1 }}
            onClick={handleGPS}
            type="button"
            disabled={gpsLoading}
          >
            <IconGPS /> {gpsLoading ? "Localisation…" : "Ma position"}
          </button>
        )}
      </div>

      {/* ── Filtres secondaires ── */}
      <div style={S.filtersRow}>
        <select
          id="annuaire-filter-wilaya"
          style={S.select}
          value={codeWilaya}
          onChange={(e) => setCodeWilaya(e.target.value)}
          aria-label="Wilaya"
        >
          <option value="">Toutes les wilayas</option>
          {Array.from({ length: 58 }, (_, i) => i + 1).map((n) => (
            <option key={n} value={String(n).padStart(2, "0")}>
              {String(n).padStart(2, "0")}
            </option>
          ))}
        </select>

        <select
          id="annuaire-filter-categorie"
          style={S.select}
          value={categorie}
          onChange={(e) => setCategorie(e.target.value)}
          aria-label="Catégorie"
        >
          <option value="">Toutes les catégories</option>
          {categories.map((c) => (
            <option key={c.categorie} value={c.categorie}>
              {c.categorie} ({c.total.toLocaleString()})
            </option>
          ))}
        </select>

        <input
          id="annuaire-filter-discipline"
          style={{ ...S.input, paddingLeft: "12px", maxWidth: "200px" }}
          type="text"
          placeholder="Spécialité (Cardio…)"
          value={discipline}
          onChange={(e) => setDiscipline(e.target.value)}
          aria-label="Spécialité médicale"
        />

        <input
          id="annuaire-filter-commune"
          style={{ ...S.input, paddingLeft: "12px", maxWidth: "180px" }}
          type="text"
          placeholder="Commune…"
          value={nomCommune}
          onChange={(e) => setNomCommune(e.target.value)}
          aria-label="Nom de commune"
        />

        {gpsActive && (
          <select
            id="annuaire-filter-radius"
            style={S.select}
            value={radiusKm}
            onChange={(e) => setRadiusKm(Number(e.target.value))}
            aria-label="Rayon de recherche GPS"
          >
            {[1, 2, 5, 10, 20, 50].map((r) => (
              <option key={r} value={r}>{r} km</option>
            ))}
          </select>
        )}
      </div>

      {/* ── Erreur ── */}
      {error && <div style={S.error} role="alert">⚠️ {error}</div>}

      {/* ── Méta-résultats ── */}
      {!loading && !error && (
        <div style={S.meta}>
          <span>
            <strong>{total.toLocaleString()}</strong> résultat{total > 1 ? "s" : ""}
            {gpsActive && userLat && ` · dans un rayon de ${radiusKm} km`}
          </span>
          {execMs !== null && (
            <span style={{ color: execMs < 200 ? "#10b981" : "#f59e0b" }}>
              ⚡ {execMs} ms
            </span>
          )}
        </div>
      )}

      {/* ── Contenu ── */}
      {loading ? (
        <div style={S.loading}>⏳ Chargement…</div>
      ) : results.length === 0 && !error ? (
        <div style={S.noResults}>
          <p>🔍 Aucun établissement trouvé pour ces critères.</p>
          <p style={{ fontSize: "13px" }}>Essayez d'élargir le rayon, changer de wilaya ou vider un filtre.</p>
        </div>
      ) : (
        <div style={S.list} role="list" aria-label="Liste des établissements">
          {results.map((item) => (
            <div key={item.id} role="listitem">
              <StructureCard item={item} />
            </div>
          ))}
        </div>
      )}

      {/* ── Pagination ── */}
      {totalPages > 1 && !loading && (
        <nav style={S.pagination} aria-label="Pagination">
          <button
            style={S.pageBtn(false, page === 0)}
            onClick={() => doSearch(page - 1)}
            disabled={page === 0}
            type="button"
          >
            ‹ Préc.
          </button>

          {Array.from({ length: Math.min(totalPages, 7) }, (_, i) => {
            const p = page <= 3 ? i : page - 3 + i;
            if (p >= totalPages) return null;
            return (
              <button
                key={p}
                style={S.pageBtn(p === page, false)}
                onClick={() => doSearch(p)}
                type="button"
                aria-current={p === page ? "page" : undefined}
              >
                {p + 1}
              </button>
            );
          })}

          <button
            style={S.pageBtn(false, page >= totalPages - 1)}
            onClick={() => doSearch(page + 1)}
            disabled={page >= totalPages - 1}
            type="button"
          >
            Suiv. ›
          </button>
        </nav>
      )}
    </div>
  );
}
