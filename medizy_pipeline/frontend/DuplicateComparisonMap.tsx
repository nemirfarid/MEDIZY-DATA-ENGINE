import React, { useState, useMemo } from 'react';
import { DuplicateComparisonData } from './types';

interface DuplicateComparisonMapProps {
  data: DuplicateComparisonData;
  onApprove?: () => void;
  onReject?: (suggestedReason: string) => void;
  onClose?: () => void;
}

export const DuplicateComparisonMap: React.FC<DuplicateComparisonMapProps> = ({
  data,
  onApprove,
  onReject,
  onClose,
}) => {
  const { proposed, existing, distance_meters, is_proximity_duplicate } = data;
  const [zoomLevel, setZoomLevel] = useState<number>(1);
  const [activeTab, setActiveTab] = useState<'map' | 'diff'>('map');

  // Calcul cartographique de la position relative SVG des deux points
  const mapProjection = useMemo(() => {
    const lat1 = proposed.latitude;
    const lon1 = proposed.longitude;
    const lat2 = existing.latitude;
    const lon2 = existing.longitude;

    const centerLat = (lat1 + lat2) / 2;
    const centerLon = (lon1 + lon2) / 2;

    const dLat = (lat1 - lat2) * 111320; // mètres
    const dLon = (lon1 - lon2) * 111320 * Math.cos((centerLat * Math.PI) / 180); // mètres

    // Dimensions du canevas SVG
    const svgWidth = 520;
    const svgHeight = 320;
    const scale = Math.min(1.8, Math.max(0.6, 120 / (Math.max(Math.abs(dLat), Math.abs(dLon), 40)))) * zoomLevel;

    // Centrage des coordonnées
    const cx = svgWidth / 2;
    const cy = svgHeight / 2;

    const proposedX = cx + (dLon / 2) * scale;
    const proposedY = cy - (dLat / 2) * scale;

    const existingX = cx - (dLon / 2) * scale;
    const existingY = cy + (dLat / 2) * scale;

    // Rayon de 100m en pixels sur le canevas
    const radius100mPx = 100 * scale;

    return {
      svgWidth,
      svgHeight,
      proposedX,
      proposedY,
      existingX,
      existingY,
      radius100mPx,
      centerLat,
      centerLon,
    };
  }, [proposed, existing, zoomLevel]);

  return (
    <div style={styles.modalOverlay}>
      <div style={styles.modalCard}>
        {/* Header */}
        <div style={styles.modalHeader}>
          <div style={styles.headerTitleGroup}>
            <span style={styles.headerIcon}>🧭</span>
            <div>
              <h2 style={styles.modalTitle}>Analyse Comparative de Proximité Géographique</h2>
              <p style={styles.modalSubtitle}>
                Détection de doublon territorial • Comparaison côte à côte avant décision
              </p>
            </div>
          </div>
          {onClose && (
            <button onClick={onClose} style={styles.closeBtn} title="Fermer la vue">
              ✕
            </button>
          )}
        </div>

        {/* Proximity Alert Banner */}
        <div
          style={{
            ...styles.alertBanner,
            backgroundColor: is_proximity_duplicate ? '#FEF2F2' : '#EFF6FF',
            borderColor: is_proximity_duplicate ? '#EF4444' : '#3B82F6',
          }}
        >
          <div style={styles.alertContent}>
            <span style={styles.alertIcon}>{is_proximity_duplicate ? '⚠️' : 'ℹ️'}</span>
            <div>
              <strong style={{ color: is_proximity_duplicate ? '#991B1B' : '#1E40AF', fontSize: '14px' }}>
                {is_proximity_duplicate
                  ? `Doublon potentiel identifié : Écart de ${distance_meters} mètres (< 100 m requis)`
                  : `Établissements distincts : Écart mesuré à ${distance_meters} mètres`}
              </strong>
              <p style={{ margin: '4px 0 0 0', fontSize: '12px', color: is_proximity_duplicate ? '#B91C1C' : '#2563EB' }}>
                {is_proximity_duplicate
                  ? "La proposition citoyenne est géographiquement superposée à un établissement déjà certifié dans MEDIZY."
                  : "La distance dépasse le périmètre critique de 100 m. Vérifiez si les deux structures coexistent."}
              </p>
            </div>
          </div>
          <div style={styles.badgeDistance}>
            <span style={styles.badgeDistanceNum}>{distance_meters} m</span>
            <span style={styles.badgeDistanceLabel}>distance</span>
          </div>
        </div>

        {/* Tab Navigation */}
        <div style={styles.tabBar}>
          <button
            style={{
              ...styles.tabItem,
              ...(activeTab === 'map' ? styles.tabItemActive : {}),
            }}
            onClick={() => setActiveTab('map')}
          >
            🗺️ Carte Miniature & Rayon 100m
          </button>
          <button
            style={{
              ...styles.tabItem,
              ...(activeTab === 'diff' ? styles.tabItemActive : {}),
            }}
            onClick={() => setActiveTab('diff')}
          >
            📋 Comparateur d'Attributs Détaillé
          </button>
        </div>

        {/* Tab 1: Mini Map View */}
        {activeTab === 'map' && (
          <div style={styles.mapContainer}>
            <div style={styles.mapCanvasWrapper}>
              <svg
                width="100%"
                height="320"
                viewBox={`0 0 ${mapProjection.svgWidth} ${mapProjection.svgHeight}`}
                style={styles.svgCanvas}
              >
                {/* Grille cartographique de fond */}
                <defs>
                  <pattern id="grid" width="30" height="30" patternUnits="userSpaceOnUse">
                    <path d="M 30 0 L 0 0 0 30" fill="none" stroke="#E2E8F0" strokeWidth="0.8" />
                  </pattern>
                  <radialGradient id="grad-pulse" cx="50%" cy="50%" r="50%">
                    <stop offset="0%" stopColor="#3B82F6" stopOpacity="0.4" />
                    <stop offset="100%" stopColor="#3B82F6" stopOpacity="0" />
                  </radialGradient>
                  <radialGradient id="grad-threshold" cx="50%" cy="50%" r="50%">
                    <stop offset="0%" stopColor="#10B981" stopOpacity="0.12" />
                    <stop offset="90%" stopColor="#10B981" stopOpacity="0.05" />
                    <stop offset="100%" stopColor="#10B981" stopOpacity="0.4" />
                  </radialGradient>
                </defs>

                <rect width="100%" height="100%" fill="url(#grid)" />

                {/* Cercle du seuil critique de 100 mètres autour de l'établissement existant */}
                <circle
                  cx={mapProjection.existingX}
                  cy={mapProjection.existingY}
                  r={mapProjection.radius100mPx}
                  fill="url(#grad-threshold)"
                  stroke="#10B981"
                  strokeWidth="1.5"
                  strokeDasharray="4 3"
                />
                <text
                  x={mapProjection.existingX}
                  y={mapProjection.existingY + mapProjection.radius100mPx + 14}
                  textAnchor="middle"
                  fill="#059669"
                  fontSize="10"
                  fontWeight="600"
                >
                  Zone critique 100 m
                </text>

                {/* Ligne reliant les deux établissements avec la distance */}
                <line
                  x1={mapProjection.existingX}
                  y1={mapProjection.existingY}
                  x2={mapProjection.proposedX}
                  y2={mapProjection.proposedY}
                  stroke="#E11D48"
                  strokeWidth="2"
                  strokeDasharray="5 4"
                />

                {/* Badge de distance au milieu de la ligne */}
                <g
                  transform={`translate(${
                    (mapProjection.existingX + mapProjection.proposedX) / 2
                  }, ${(mapProjection.existingY + mapProjection.proposedY) / 2 - 8})`}
                >
                  <rect
                    x="-32"
                    y="-12"
                    width="64"
                    height="20"
                    rx="10"
                    fill="#1E293B"
                    opacity="0.9"
                  />
                  <text
                    x="0"
                    y="2"
                    textAnchor="middle"
                    fill="#FFFFFF"
                    fontSize="11"
                    fontWeight="700"
                  >
                    {distance_meters} m
                  </text>
                </g>

                {/* Marqueur: Établissement Existant (Vert) */}
                <g transform={`translate(${mapProjection.existingX}, ${mapProjection.existingY})`}>
                  <circle r="16" fill="#10B981" opacity="0.2" />
                  <circle r="10" fill="#059669" stroke="#FFFFFF" strokeWidth="2" />
                  <text x="0" y="4" textAnchor="middle" fill="#FFFFFF" fontSize="10" fontWeight="bold">
                    ✓
                  </text>
                  <rect
                    x="-60"
                    y="-36"
                    width="120"
                    height="20"
                    rx="4"
                    fill="#065F46"
                  />
                  <text
                    x="0"
                    y="-23"
                    textAnchor="middle"
                    fill="#ECFDF5"
                    fontSize="10"
                    fontWeight="600"
                  >
                    Existant #{existing.id}
                  </text>
                </g>

                {/* Marqueur: Établissement Proposé (Bleu) */}
                <g transform={`translate(${mapProjection.proposedX}, ${mapProjection.proposedY})`}>
                  <circle r="22" fill="url(#grad-pulse)" />
                  <circle r="10" fill="#2563EB" stroke="#FFFFFF" strokeWidth="2" />
                  <text x="0" y="4" textAnchor="middle" fill="#FFFFFF" fontSize="10" fontWeight="bold">
                    ★
                  </text>
                  <rect
                    x="-65"
                    y="16"
                    width="130"
                    height="20"
                    rx="4"
                    fill="#1E40AF"
                  />
                  <text
                    x="0"
                    y="29"
                    textAnchor="middle"
                    fill="#EFF6FF"
                    fontSize="10"
                    fontWeight="600"
                  >
                    Proposition Citoyenne
                  </text>
                </g>

                {/* Boussole / Orientation */}
                <g transform="translate(30, 35)">
                  <circle r="15" fill="#FFFFFF" stroke="#CBD5E1" strokeWidth="1" />
                  <path d="M 0 -11 L 3 3 L -3 3 Z" fill="#EF4444" />
                  <path d="M 0 11 L 3 -3 L -3 -3 Z" fill="#94A3B8" />
                  <text x="0" y="-13" textAnchor="middle" fill="#EF4444" fontSize="8" fontWeight="bold">
                    N
                  </text>
                </g>
              </svg>

              {/* Zoom Controls */}
              <div style={styles.mapControls}>
                <button
                  style={styles.zoomBtn}
                  onClick={() => setZoomLevel((z) => Math.min(2.5, z + 0.3))}
                  title="Zoom avant"
                >
                  +
                </button>
                <button
                  style={styles.zoomBtn}
                  onClick={() => setZoomLevel((z) => Math.max(0.6, z - 0.3))}
                  title="Zoom arrière"
                >
                  −
                </button>
                <button
                  style={styles.zoomResetBtn}
                  onClick={() => setZoomLevel(1)}
                  title="Réinitialiser la vue"
                >
                  ⟲
                </button>
              </div>
            </div>

            {/* Légende rapide */}
            <div style={styles.legendRow}>
              <div style={styles.legendItem}>
                <span style={{ ...styles.legendDot, backgroundColor: '#2563EB' }} />
                <span>Proposition citoyenne (lat: {proposed.latitude.toFixed(5)}, lon: {proposed.longitude.toFixed(5)})</span>
              </div>
              <div style={styles.legendItem}>
                <span style={{ ...styles.legendDot, backgroundColor: '#059669' }} />
                <span>Existant validé (lat: {existing.latitude.toFixed(5)}, lon: {existing.longitude.toFixed(5)})</span>
              </div>
            </div>
          </div>
        )}

        {/* Tab 2: Diff / Side-by-Side Comparison */}
        {activeTab === 'diff' && (
          <div style={styles.diffTableWrapper}>
            <table style={styles.diffTable}>
              <thead>
                <tr>
                  <th style={styles.diffTh}>Critère</th>
                  <th style={{ ...styles.diffTh, backgroundColor: '#EFF6FF', color: '#1E40AF' }}>
                    ★ Proposition Citoyenne
                  </th>
                  <th style={{ ...styles.diffTh, backgroundColor: '#ECFDF5', color: '#065F46' }}>
                    ✓ Existant en Base (#{existing.id})
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td style={styles.diffTdLabel}>Nom de l'établissement</td>
                  <td style={{ ...styles.diffTd, fontWeight: '700', color: '#1E3A8A' }}>{proposed.name}</td>
                  <td style={{ ...styles.diffTd, fontWeight: '700', color: '#064E3B' }}>{existing.name}</td>
                </tr>
                <tr>
                  <td style={styles.diffTdLabel}>Typologie médicale</td>
                  <td style={styles.diffTd}>
                    <span style={styles.typeBadge}>{proposed.type || 'Non spécifié'}</span>
                  </td>
                  <td style={styles.diffTd}>
                    <span style={{ ...styles.typeBadge, backgroundColor: '#D1FAE5', color: '#065F46' }}>
                      {existing.type}
                    </span>
                  </td>
                </tr>
                <tr>
                  <td style={styles.diffTdLabel}>Wilaya / Commune</td>
                  <td style={styles.diffTd}>{proposed.wilaya} {proposed.commune ? `(${proposed.commune})` : ''}</td>
                  <td style={styles.diffTd}>{existing.wilaya} {existing.commune ? `(${existing.commune})` : ''}</td>
                </tr>
                <tr>
                  <td style={styles.diffTdLabel}>Adresse physique</td>
                  <td style={styles.diffTd}>{proposed.address || '—'}</td>
                  <td style={styles.diffTd}>{existing.address || '—'}</td>
                </tr>
                <tr>
                  <td style={styles.diffTdLabel}>Numéro de contact</td>
                  <td style={styles.diffTd}>{proposed.phone || '—'}</td>
                  <td style={styles.diffTd}>{existing.phone || '—'}</td>
                </tr>
                <tr>
                  <td style={styles.diffTdLabel}>Source de la donnée</td>
                  <td style={styles.diffTd}>
                    Citoyen : {proposed.submitter_name || 'Anonyme'}
                    {proposed.submitter_notes && (
                      <div style={styles.submitterNotes}>« {proposed.submitter_notes} »</div>
                    )}
                  </td>
                  <td style={styles.diffTd}>
                    {existing.source} {existing.is_verified ? '• Certifié officiel' : ''}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        )}

        {/* Footer Actions */}
        <div style={styles.modalFooter}>
          <div style={styles.footerNote}>
            {is_proximity_duplicate ? (
              <span style={{ color: '#DC2626', fontSize: '13px', fontWeight: '500' }}>
                ⚠️ Recommandation : Rejeter comme doublon ou fusionner les coordonnées.
              </span>
            ) : (
              <span style={{ color: '#059669', fontSize: '13px', fontWeight: '500' }}>
                ✓ Distance supérieure au seuil : Création d'une structure distincte envisageable.
              </span>
            )}
          </div>
          <div style={styles.actionButtons}>
            {onReject && (
              <button
                onClick={() =>
                  onReject(`Doublon avéré avec l'établissement #${existing.id} (${existing.name}, distant de ${distance_meters}m)`)
                }
                style={styles.rejectBtn}
              >
                🗑️ Rejeter comme Doublon
              </button>
            )}
            {onApprove && (
              <button onClick={onApprove} style={styles.approveBtn}>
                ✓ Approuver la Nouvelle Structure
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

// Styles CSS-in-JS avec typographie soignée et thème MEDIZY
const styles: Record<string, React.CSSProperties> = {
  modalOverlay: {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(15, 23, 42, 0.75)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 9999,
    padding: '16px',
    backdropFilter: 'blur(4px)',
  },
  modalCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: '16px',
    width: '100%',
    maxWidth: '780px',
    boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25)',
    overflow: 'hidden',
    display: 'flex',
    flexDirection: 'column',
    maxHeight: '92vh',
  },
  modalHeader: {
    padding: '20px 24px',
    borderBottom: '1px solid #E2E8F0',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: '#F8FAFC',
  },
  headerTitleGroup: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
  },
  headerIcon: {
    fontSize: '28px',
  },
  modalTitle: {
    margin: 0,
    fontSize: '18px',
    fontWeight: '700',
    color: '#0F172A',
  },
  modalSubtitle: {
    margin: '3px 0 0 0',
    fontSize: '12px',
    color: '#64748B',
  },
  closeBtn: {
    background: 'transparent',
    border: 'none',
    fontSize: '18px',
    cursor: 'pointer',
    color: '#94A3B8',
    padding: '6px',
  },
  alertBanner: {
    margin: '16px 24px 0 24px',
    padding: '12px 16px',
    borderRadius: '10px',
    borderWidth: '1px',
    borderStyle: 'solid',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  alertContent: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
  },
  alertIcon: {
    fontSize: '22px',
  },
  badgeDistance: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    backgroundColor: '#FFFFFF',
    padding: '4px 10px',
    borderRadius: '8px',
    border: '1px solid #E2E8F0',
  },
  badgeDistanceNum: {
    fontSize: '14px',
    fontWeight: '800',
    color: '#E11D48',
  },
  badgeDistanceLabel: {
    fontSize: '9px',
    textTransform: 'uppercase',
    color: '#64748B',
    fontWeight: '600',
  },
  tabBar: {
    display: 'flex',
    gap: '8px',
    padding: '16px 24px 0 24px',
    borderBottom: '1px solid #E2E8F0',
  },
  tabItem: {
    padding: '8px 16px',
    background: 'none',
    border: 'none',
    borderBottom: '2px solid transparent',
    fontSize: '13px',
    fontWeight: '600',
    color: '#64748B',
    cursor: 'pointer',
  },
  tabItemActive: {
    color: '#2563EB',
    borderBottomColor: '#2563EB',
  },
  mapContainer: {
    padding: '16px 24px',
  },
  mapCanvasWrapper: {
    position: 'relative',
    borderRadius: '12px',
    overflow: 'hidden',
    border: '1px solid #CBD5E1',
    backgroundColor: '#F8FAFC',
  },
  svgCanvas: {
    display: 'block',
  },
  mapControls: {
    position: 'absolute',
    top: '12px',
    right: '12px',
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
  },
  zoomBtn: {
    width: '30px',
    height: '30px',
    backgroundColor: '#FFFFFF',
    border: '1px solid #CBD5E1',
    borderRadius: '6px',
    cursor: 'pointer',
    fontSize: '16px',
    fontWeight: 'bold',
    color: '#1E293B',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    boxShadow: '0 2px 4px rgba(0,0,0,0.06)',
  },
  zoomResetBtn: {
    width: '30px',
    height: '30px',
    backgroundColor: '#FFFFFF',
    border: '1px solid #CBD5E1',
    borderRadius: '6px',
    cursor: 'pointer',
    fontSize: '13px',
    fontWeight: 'bold',
    color: '#64748B',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  legendRow: {
    display: 'flex',
    gap: '16px',
    marginTop: '10px',
    fontSize: '11px',
    color: '#64748B',
  },
  legendItem: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
  },
  legendDot: {
    width: '8px',
    height: '8px',
    borderRadius: '50%',
  },
  diffTableWrapper: {
    padding: '16px 24px',
    overflowY: 'auto',
    maxHeight: '340px',
  },
  diffTable: {
    width: '100%',
    borderCollapse: 'collapse',
    fontSize: '13px',
  },
  diffTh: {
    textAlign: 'left',
    padding: '10px 14px',
    borderBottom: '2px solid #E2E8F0',
    fontWeight: '700',
    fontSize: '12px',
    backgroundColor: '#F8FAFC',
  },
  diffTdLabel: {
    padding: '10px 14px',
    borderBottom: '1px solid #F1F5F9',
    fontWeight: '600',
    color: '#475569',
    width: '28%',
  },
  diffTd: {
    padding: '10px 14px',
    borderBottom: '1px solid #F1F5F9',
    color: '#1E293B',
  },
  typeBadge: {
    display: 'inline-block',
    padding: '3px 8px',
    borderRadius: '6px',
    fontSize: '11px',
    fontWeight: '600',
    backgroundColor: '#DBEAFE',
    color: '#1E40AF',
  },
  submitterNotes: {
    marginTop: '4px',
    fontSize: '11px',
    fontStyle: 'italic',
    color: '#64748B',
  },
  modalFooter: {
    padding: '16px 24px',
    borderTop: '1px solid #E2E8F0',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: '#F8FAFC',
  },
  footerNote: {
    maxWidth: '380px',
  },
  actionButtons: {
    display: 'flex',
    gap: '10px',
  },
  rejectBtn: {
    padding: '10px 18px',
    backgroundColor: '#EF4444',
    color: '#FFFFFF',
    border: 'none',
    borderRadius: '8px',
    fontSize: '13px',
    fontWeight: '600',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    boxShadow: '0 2px 4px rgba(239, 68, 68, 0.2)',
  },
  approveBtn: {
    padding: '10px 18px',
    backgroundColor: '#059669',
    color: '#FFFFFF',
    border: 'none',
    borderRadius: '8px',
    fontSize: '13px',
    fontWeight: '600',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    boxShadow: '0 2px 4px rgba(5, 150, 105, 0.2)',
  },
};
