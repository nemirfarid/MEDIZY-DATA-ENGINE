/**
 * MEDIZY / SANTÉ DZ — Composant Visuel de Fiche Établissement (React/Next.js)
 * =========================================================================
 * Affiche la fiche de l'établissement avec ses métadonnées, le badge informatif
 * ("Fiche informative publique" vs "Établissement vérifié") et le CTA de revendication.
 */

import React from 'react';
import { Facility } from './types';

interface FacilityCardProps {
  facility: Facility;
  onClaim?: (facility: Facility) => void;
  onSelect?: (facility: Facility) => void;
}

export const FacilityCard: React.FC<FacilityCardProps> = ({
  facility,
  onClaim,
  onSelect,
}) => {
  const {
    id,
    name,
    type,
    wilaya,
    commune,
    address,
    phone,
    distance_meters,
    is_claimed,
    badge,
  } = facility;

  const formattedDistance =
    distance_meters !== null && distance_meters !== undefined
      ? distance_meters < 1000
        ? `${Math.round(distance_meters)} m`
        : `${(distance_meters / 1000).toFixed(1)} km`
      : null;

  // Couleurs de badges selon le type de structure
  const getTypeColor = (facType: string) => {
    switch (facType) {
      case 'CHU':
      case 'EPH':
        return '#0284c7'; // Bleu hospitalier
      case 'Polyclinique':
      case 'EPSP':
        return '#0d9488'; // Turquoise soins de proximité
      case 'Urgences':
        return '#dc2626'; // Rouge urgences
      case 'Clinique':
        return '#7c3aed'; // Violet clinique privée
      default:
        return '#475569';
    }
  };

  return (
    <div
      onClick={() => onSelect && onSelect(facility)}
      style={{
        backgroundColor: '#ffffff',
        borderRadius: '12px',
        padding: '16px',
        boxShadow: '0 4px 12px rgba(0, 0, 0, 0.06)',
        border: is_claimed ? '1px solid #e2e8f0' : '1px dashed #cbd5e1',
        display: 'flex',
        flexDirection: 'column',
        gap: '12px',
        fontFamily: 'Inter, system-ui, -apple-system, sans-serif',
        transition: 'all 0.2s ease',
        cursor: onSelect ? 'pointer' : 'default',
      }}
    >
      {/* En-tête : Type et Statut */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span
          style={{
            fontSize: '11px',
            fontWeight: 700,
            textTransform: 'uppercase',
            letterSpacing: '0.5px',
            padding: '3px 8px',
            borderRadius: '6px',
            backgroundColor: `${getTypeColor(type)}15`,
            color: getTypeColor(type),
          }}
        >
          {type}
        </span>

        {/* Badge Public Informative vs Vérifié */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          {is_claimed ? (
            <span
              style={{
                fontSize: '11px',
                fontWeight: 600,
                color: '#15803d',
                backgroundColor: '#dcfce7',
                padding: '3px 8px',
                borderRadius: '12px',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '4px',
              }}
            >
              ✓ Vérifié
            </span>
          ) : (
            <span
              title="Cette structure est répertoriée à titre informatif à partir des données publiques (OSM/DSP)."
              style={{
                fontSize: '11px',
                fontWeight: 600,
                color: '#0369a1',
                backgroundColor: '#e0f2fe',
                padding: '3px 8px',
                borderRadius: '12px',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '4px',
              }}
            >
              ℹ Fiche publique
            </span>
          )}

          {formattedDistance && (
            <span style={{ fontSize: '12px', color: '#64748b', fontWeight: 500 }}>
              • {formattedDistance}
            </span>
          )}
        </div>
      </div>

      {/* Nom de l'établissement */}
      <h3
        style={{
          margin: 0,
          fontSize: '16px',
          fontWeight: 700,
          color: '#0f172a',
          lineHeight: 1.3,
        }}
      >
        {name}
      </h3>

      {/* Localisation : Wilaya & Commune */}
      <div style={{ fontSize: '13px', color: '#475569', display: 'flex', alignItems: 'center', gap: '4px' }}>
        <span>📍</span>
        <span>
          {[commune, wilaya].filter(Boolean).join(', ')}
        </span>
      </div>

      {/* Adresse si disponible */}
      {address && (
        <p style={{ margin: 0, fontSize: '12px', color: '#64748b', lineHeight: 1.4 }}>
          {address}
        </p>
      )}

      {/* Actions : Appel téléphonique et Bouton Revendication */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginTop: '6px',
          paddingTop: '10px',
          borderTop: '1px solid #f1f5f9',
        }}
      >
        {phone ? (
          <a
            href={`tel:${phone.replace(/\s+/g, '')}`}
            onClick={(e) => e.stopPropagation()}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              fontSize: '13px',
              fontWeight: 600,
              color: '#0284c7',
              textDecoration: 'none',
            }}
          >
            📞 {phone}
          </a>
        ) : (
          <span style={{ fontSize: '12px', color: '#94a3b8', fontStyle: 'italic' }}>
            Téléphone non renseigné
          </span>
        )}

        {/* Bouton de Revendication pour les professionnels de santé */}
        {!is_claimed && (
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              if (onClaim) onClaim(facility);
              else if (badge.claim_url) window.location.href = badge.claim_url;
            }}
            style={{
              fontSize: '12px',
              fontWeight: 600,
              color: '#0f766e',
              backgroundColor: '#ccfbf1',
              border: 'none',
              padding: '6px 12px',
              borderRadius: '6px',
              cursor: 'pointer',
              transition: 'background 0.2s',
            }}
          >
            Revendiquer cet établissement
          </button>
        )}
      </div>
    </div>
  );
};
