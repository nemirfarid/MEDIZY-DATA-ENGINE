/**
 * MEDIZY / SANTÉ DZ — Formulaire de Signalement d'Établissement Manquant
 * ======================================================================
 * Permet aux utilisateurs et professionnels d'enrichir la carte en fournissant
 * un nom, une wilaya et un lien Google Maps (avec extraction automatique des coordonnées).
 */

import React, { useState } from 'react';
import { FacilityType, SuggestFacilityPayload, SuggestFacilityResponse } from './types';
import { submitFacilitySuggestion } from './facilitiesApi';

const WILAYAS_LIST = [
  'Adrar', 'Chlef', 'Laghouat', 'Oum El Bouaghi', 'Batna', 'Béjaïa', 'Biskra', 'Béchar',
  'Blida', 'Bouira', 'Tamanrasset', 'Tébessa', 'Tlemcen', 'Tiaret', 'Tizi Ouzou', 'Alger',
  'Djelfa', 'Jijel', 'Sétif', 'Saïda', 'Skikda', 'Sidi Bel Abbès', 'Annaba', 'Guelma',
  'Constantine', 'Médéa', 'Mostaganem', "M'Sila", 'Mascara', 'Ouargla', 'Oran', 'El Bayadh',
  'Illizi', 'Bordj Bou Arréridj', 'Boumerdès', 'El Tarf', 'Tindouf', 'Tissemsilt', 'El Oued',
  'Khenchela', 'Souk Ahras', 'Tipaza', 'Mila', 'Aïn Defla', 'Naâma', 'Aïn Témouchent',
  'Ghardaïa', 'Relizane', 'Timimoun', 'Bordj Badji Mokhtar', 'Ouled Djellal', 'Béni Abbès',
  'In Salah', 'In Guezzam', 'Touggourt', 'Djanet', 'El Meghaier', 'El Meniaa'
];

interface SuggestFacilityModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: (response: SuggestFacilityResponse) => void;
  defaultWilaya?: string;
}

export const SuggestFacilityModal: React.FC<SuggestFacilityModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
  defaultWilaya = 'Alger',
}) => {
  const [formData, setFormData] = useState<SuggestFacilityPayload>({
    name: '',
    type: 'Polyclinique',
    wilaya: defaultWilaya,
    commune: '',
    address: '',
    phone: '',
    google_maps_url: '',
    submitter_name: '',
    submitter_email: '',
    submitter_notes: '',
  });

  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [successResult, setSuccessResult] = useState<SuggestFacilityResponse | null>(null);

  if (!isOpen) return null;

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!formData.name || formData.name.trim().length < 3) {
      setError('Veuillez saisir un nom d\'établissement valide (minimum 3 caractères).');
      return;
    }

    if (!formData.wilaya) {
      setError('Veuillez sélectionner une wilaya.');
      return;
    }

    setLoading(true);

    try {
      const response = await submitFacilitySuggestion(formData);
      setSuccessResult(response);
      if (onSuccess) onSuccess(response);
    } catch (err: any) {
      setError(err.message || 'Échec de la soumission. Veuillez vérifier vos données.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(15, 23, 42, 0.65)',
        backdropFilter: 'blur(4px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 9999,
        padding: '16px',
        fontFamily: 'Inter, system-ui, sans-serif',
      }}
    >
      <div
        style={{
          backgroundColor: '#ffffff',
          borderRadius: '16px',
          width: '100%',
          maxWidth: '540px',
          maxHeight: '90vh',
          overflowY: 'auto',
          boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1)',
          padding: '24px',
          display: 'flex',
          flexDirection: 'column',
          gap: '16px',
        }}
      >
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <h2 style={{ margin: 0, fontSize: '18px', fontWeight: 700, color: '#0f172a' }}>
              Signaler un établissement manquant
            </h2>
            <p style={{ margin: '4px 0 0', fontSize: '13px', color: '#64748b' }}>
              Aidez la communauté MEDIZY en ajoutant une structure publique ou privée.
            </p>
          </div>
          <button
            onClick={onClose}
            style={{
              background: 'none',
              border: 'none',
              fontSize: '20px',
              cursor: 'pointer',
              color: '#94a3b8',
            }}
          >
            ✕
          </button>
        </div>

        {/* Écran de Succès */}
        {successResult ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', padding: '16px 0' }}>
            <div
              style={{
                backgroundColor: '#f0fdf4',
                border: '1px solid #bbf7d0',
                borderRadius: '8px',
                padding: '16px',
                color: '#166534',
                fontSize: '14px',
                lineHeight: 1.5,
              }}
            >
              <strong>✓ Merci pour votre contribution !</strong>
              <p style={{ margin: '8px 0 0' }}>{successResult.message}</p>
              {successResult.parsed_coordinates && (
                <p style={{ margin: '6px 0 0', fontSize: '12px', color: '#15803d' }}>
                  Coordonnées GPS extraites avec succès : ({successResult.parsed_coordinates.latitude.toFixed(4)},{' '}
                  {successResult.parsed_coordinates.longitude.toFixed(4)})
                </p>
              )}
            </div>
            <button
              onClick={onClose}
              style={{
                backgroundColor: '#0284c7',
                color: '#ffffff',
                border: 'none',
                padding: '10px',
                borderRadius: '8px',
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              Fermer
            </button>
          </div>
        ) : (
          /* Formulaire de Soumission */
          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            {error && (
              <div
                style={{
                  backgroundColor: '#fef2f2',
                  border: '1px solid #fecaca',
                  borderRadius: '6px',
                  padding: '10px',
                  color: '#991b1b',
                  fontSize: '13px',
                }}
              >
                {error}
              </div>
            )}

            {/* Nom */}
            <div>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, color: '#334155', marginBottom: '4px' }}>
                Nom de l'établissement *
              </label>
              <input
                type="text"
                name="name"
                value={formData.name}
                onChange={handleChange}
                placeholder="Ex: Polyclinique Bab El Oued, Clinique Chifa..."
                required
                style={{
                  width: '100%',
                  padding: '9px 12px',
                  borderRadius: '6px',
                  border: '1px solid #cbd5e1',
                  fontSize: '14px',
                  boxSizing: 'border-box',
                }}
              />
            </div>

            {/* Type & Wilaya */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, color: '#334155', marginBottom: '4px' }}>
                  Type d'établissement
                </label>
                <select
                  name="type"
                  value={formData.type}
                  onChange={handleChange}
                  style={{
                    width: '100%',
                    padding: '9px 12px',
                    borderRadius: '6px',
                    border: '1px solid #cbd5e1',
                    fontSize: '14px',
                    backgroundColor: '#fff',
                  }}
                >
                  <option value="CHU">CHU (Hôpital Universitaire)</option>
                  <option value="EPH">EPH (Hôpital Public)</option>
                  <option value="EPSP">EPSP (Santé de Proximité)</option>
                  <option value="Polyclinique">Polyclinique</option>
                  <option value="Clinique">Clinique Privée</option>
                  <option value="Urgences">Urgences Médico-Chirurgicales</option>
                  <option value="Centre de Santé">Centre de Santé / Dispensaire</option>
                  <option value="Cabinet Médical">Cabinet Médical</option>
                </select>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, color: '#334155', marginBottom: '4px' }}>
                  Wilaya *
                </label>
                <select
                  name="wilaya"
                  value={formData.wilaya}
                  onChange={handleChange}
                  style={{
                    width: '100%',
                    padding: '9px 12px',
                    borderRadius: '6px',
                    border: '1px solid #cbd5e1',
                    fontSize: '14px',
                    backgroundColor: '#fff',
                  }}
                >
                  {WILAYAS_LIST.map((w, idx) => (
                    <option key={w} value={w}>
                      {String(idx + 1).padStart(2, '0')} - {w}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* Commune & Téléphone */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, color: '#334155', marginBottom: '4px' }}>
                  Commune
                </label>
                <input
                  type="text"
                  name="commune"
                  value={formData.commune}
                  onChange={handleChange}
                  placeholder="Ex: Kouba, Bir Mourad Raïs..."
                  style={{
                    width: '100%',
                    padding: '9px 12px',
                    borderRadius: '6px',
                    border: '1px solid #cbd5e1',
                    fontSize: '14px',
                    boxSizing: 'border-box',
                  }}
                />
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, color: '#334155', marginBottom: '4px' }}>
                  Téléphone
                </label>
                <input
                  type="tel"
                  name="phone"
                  value={formData.phone}
                  onChange={handleChange}
                  placeholder="Ex: 021 28 XX XX"
                  style={{
                    width: '100%',
                    padding: '9px 12px',
                    borderRadius: '6px',
                    border: '1px solid #cbd5e1',
                    fontSize: '14px',
                    boxSizing: 'border-box',
                  }}
                />
              </div>
            </div>

            {/* Lien Google Maps */}
            <div>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, color: '#334155', marginBottom: '4px' }}>
                Lien Google Maps (Recommandé)
              </label>
              <input
                type="url"
                name="google_maps_url"
                value={formData.google_maps_url}
                onChange={handleChange}
                placeholder="Ex: https://maps.app.goo.gl/... ou https://maps.google.com/?q=..."
                style={{
                  width: '100%',
                  padding: '9px 12px',
                  borderRadius: '6px',
                  border: '1px solid #cbd5e1',
                  fontSize: '14px',
                  boxSizing: 'border-box',
                }}
              />
              <span style={{ fontSize: '11px', color: '#64748b' }}>
                Les coordonnées GPS (latitude/longitude) seront extraites automatiquement depuis ce lien.
              </span>
            </div>

            {/* Notes / Précisions */}
            <div>
              <label style={{ display: 'block', fontSize: '13px', fontWeight: 600, color: '#334155', marginBottom: '4px' }}>
                Remarques & Services disponibles (optionnel)
              </label>
              <textarea
                name="submitter_notes"
                value={formData.submitter_notes}
                onChange={handleChange}
                rows={2}
                placeholder="Ex: Service de garde 24h/24, maternité, radiologie..."
                style={{
                  width: '100%',
                  padding: '9px 12px',
                  borderRadius: '6px',
                  border: '1px solid #cbd5e1',
                  fontSize: '14px',
                  boxSizing: 'border-box',
                  fontFamily: 'inherit',
                }}
              />
            </div>

            {/* Boutons d'action */}
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '10px' }}>
              <button
                type="button"
                onClick={onClose}
                style={{
                  padding: '10px 16px',
                  borderRadius: '6px',
                  border: '1px solid #cbd5e1',
                  backgroundColor: '#ffffff',
                  fontSize: '13px',
                  fontWeight: 600,
                  color: '#475569',
                  cursor: 'pointer',
                }}
              >
                Annuler
              </button>
              <button
                type="submit"
                disabled={loading}
                style={{
                  padding: '10px 20px',
                  borderRadius: '6px',
                  border: 'none',
                  backgroundColor: loading ? '#93c5fd' : '#0284c7',
                  fontSize: '13px',
                  fontWeight: 600,
                  color: '#ffffff',
                  cursor: loading ? 'not-allowed' : 'pointer',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '6px',
                }}
              >
                {loading ? 'Traitement...' : 'Envoyer pour modération'}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
};
