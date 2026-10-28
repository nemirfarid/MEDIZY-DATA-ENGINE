import React, { useState, useEffect, useCallback } from 'react';
import {
  AdminAuthToken,
  AdminSuggestion,
  DuplicateComparisonData,
  FacilityType,
  SuggestionStatus,
} from './types';
import {
  fetchAdminSuggestions,
  approveSuggestion,
  rejectSuggestion,
  fetchFacilityById,
  loginAdmin,
  logoutAdmin,
  getStoredAdminToken,
  getStoredAdminInfo,
  RateLimitHeaders,
} from './adminApi';
import { DuplicateComparisonMap } from './DuplicateComparisonMap';

export const AdminModerationDashboard: React.FC = () => {
  // État d'authentification
  const [token, setToken] = useState<string | null>(getStoredAdminToken());
  const [adminProfile, setAdminProfile] = useState<Partial<AdminAuthToken> | null>(getStoredAdminInfo());
  const [loginUsername, setLoginUsername] = useState('admin@medizy.dz');
  const [loginPassword, setLoginPassword] = useState('');
  const [loginLoading, setLoginLoading] = useState(false);
  const [loginError, setLoginError] = useState<string | null>(null);

  // Données et filtres
  const [suggestions, setSuggestions] = useState<AdminSuggestion[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<SuggestionStatus>('PENDING');
  const [onlyDuplicates, setOnlyDuplicates] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [rateLimit, setRateLimit] = useState<RateLimitHeaders>({});

  // Modales
  const [activeComparison, setActiveComparison] = useState<DuplicateComparisonData | null>(null);
  const [approvingItem, setApprovingItem] = useState<AdminSuggestion | null>(null);
  const [overrideType, setOverrideType] = useState<FacilityType | ''>('');
  const [moderationComment, setModerationComment] = useState('');
  const [rejectingItem, setRejectingItem] = useState<AdminSuggestion | null>(null);
  const [rejectReason, setRejectReason] = useState('');
  const [actionLoading, setActionLoading] = useState(false);
  const [toastMessage, setToastMessage] = useState<{ text: string; type: 'success' | 'error' } | null>(null);

  const showToast = (text: string, type: 'success' | 'error' = 'success') => {
    setToastMessage({ text, type });
    setTimeout(() => setToastMessage(null), 4000);
  };

  // Chargement des suggestions
  const loadSuggestions = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetchAdminSuggestions(statusFilter, 100, 0);
      setSuggestions(res.data.data);
      setRateLimit(res.rateLimit);
    } catch (err: any) {
      if (err.status === 401) {
        setToken(null);
        setAdminProfile(null);
      } else {
        setError(err.message || 'Impossible de récupérer la liste.');
      }
    } finally {
      setLoading(false);
    }
  }, [token, statusFilter]);

  useEffect(() => {
    if (token) {
      loadSuggestions();
    }
  }, [token, loadSuggestions]);

  // Connexion administrateur
  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoginLoading(true);
    setLoginError(null);
    try {
      const authData = await loginAdmin({ username: loginUsername, password: loginPassword });
      setToken(authData.access_token);
      setAdminProfile(authData);
      showToast(`Bienvenue, ${authData.admin_name} ! Session active pour 24h.`);
    } catch (err: any) {
      setLoginError(err.message || 'Échec de la connexion.');
    } finally {
      setLoginLoading(false);
    }
  };

  const handleLogout = () => {
    logoutAdmin();
    setToken(null);
    setAdminProfile(null);
    setSuggestions([]);
  };

  // Ouverture de l'analyse comparative de doublon
  const handleOpenComparison = async (suggestion: AdminSuggestion) => {
    if (!suggestion.latitude || !suggestion.longitude) {
      showToast("Coordonnées GPS absentes pour cette suggestion.", "error");
      return;
    }

    let existingFacility = suggestion.matched_facility;
    if (!existingFacility && suggestion.matched_facility_id) {
      existingFacility = await fetchFacilityById(suggestion.matched_facility_id);
    }

    if (!existingFacility) {
      showToast("Détails de l'établissement existant introuvables.", "error");
      return;
    }

    // Calcul de la distance réelle si non fournie
    const lat1 = suggestion.latitude;
    const lon1 = suggestion.longitude;
    const lat2 = existingFacility.latitude;
    const lon2 = existingFacility.longitude;
    const R = 6371e3;
    const phi1 = (lat1 * Math.PI) / 180;
    const phi2 = (lat2 * Math.PI) / 180;
    const deltaPhi = ((lat2 - lat1) * Math.PI) / 180;
    const deltaLambda = ((lon2 - lon1) * Math.PI) / 180;
    const a =
      Math.sin(deltaPhi / 2) * Math.sin(deltaPhi / 2) +
      Math.cos(phi1) * Math.cos(phi2) * Math.sin(deltaLambda / 2) * Math.sin(deltaLambda / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    const dist = Math.round(R * c);

    const compData: DuplicateComparisonData = {
      proposed: {
        id: suggestion.id,
        name: suggestion.name,
        type: suggestion.type,
        wilaya: suggestion.wilaya,
        commune: suggestion.commune,
        address: suggestion.address,
        phone: suggestion.phone,
        latitude: suggestion.latitude,
        longitude: suggestion.longitude,
        submitter_name: suggestion.submitter_name,
        submitter_notes: suggestion.submitter_notes,
      },
      existing: {
        id: existingFacility.id,
        name: existingFacility.name,
        type: existingFacility.type,
        wilaya: existingFacility.wilaya,
        commune: existingFacility.commune,
        address: existingFacility.address,
        phone: existingFacility.phone,
        latitude: existingFacility.latitude,
        longitude: existingFacility.longitude,
        source: existingFacility.source,
        is_verified: existingFacility.is_verified,
      },
      distance_meters: dist,
      is_proximity_duplicate: dist < 100,
    };

    setActiveComparison(compData);
  };

  // Traitement approbation
  const executeApproval = async () => {
    if (!approvingItem) return;
    setActionLoading(true);
    try {
      const res = await approveSuggestion(approvingItem.id, {
        moderator_name: adminProfile?.admin_name || 'Admin MEDIZY',
        override_type: (overrideType || undefined) as FacilityType | undefined,
        moderation_comment: moderationComment || undefined,
      });
      setRateLimit(res.rateLimit);
      showToast(`Établissement validé et publié avec succès (ID #${res.data.created_facility_id})`);
      setApprovingItem(null);
      setActiveComparison(null);
      loadSuggestions();
    } catch (err: any) {
      showToast(err.message || "Erreur lors de l'approbation.", "error");
    } finally {
      setActionLoading(false);
    }
  };

  // Traitement rejet
  const executeRejection = async () => {
    if (!rejectingItem) return;
    if (!rejectReason.trim()) {
      showToast("Veuillez renseigner le motif du rejet.", "error");
      return;
    }
    setActionLoading(true);
    try {
      const res = await rejectSuggestion(rejectingItem.id, {
        reason: rejectReason,
        moderator_name: adminProfile?.admin_name || 'Admin MEDIZY',
      });
      setRateLimit(res.rateLimit);
      showToast(`Suggestion #${rejectingItem.id} rejetée.`);
      setRejectingItem(null);
      setActiveComparison(null);
      loadSuggestions();
    } catch (err: any) {
      showToast(err.message || 'Erreur lors du rejet.', "error");
    } finally {
      setActionLoading(false);
    }
  };

  // Filtrage local
  const filteredSuggestions = suggestions.filter((s) => {
    if (onlyDuplicates && !s.matched_facility_id) return false;
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      s.name.toLowerCase().includes(q) ||
      s.wilaya.toLowerCase().includes(q) ||
      (s.commune && s.commune.toLowerCase().includes(q))
    );
  });

  // KPI calculés
  const kpiPending = suggestions.filter((s) => s.status === 'PENDING').length;
  const kpiDuplicates = suggestions.filter((s) => s.matched_facility_id != null).length;

  // Vue Login
  if (!token) {
    return (
      <div style={dashStyles.loginWrapper}>
        <div style={dashStyles.loginCard}>
          <div style={dashStyles.loginHeader}>
            <span style={{ fontSize: '36px' }}>🏥</span>
            <h1 style={dashStyles.loginTitle}>MEDIZY Admin Portal</h1>
            <p style={dashStyles.loginSubtitle}>
              Portail sécurisé de modération des établissements de santé (Algérie)
            </p>
          </div>

          {loginError && <div style={dashStyles.errorBox}>{loginError}</div>}

          <form onSubmit={handleLogin} style={dashStyles.loginForm}>
            <div style={dashStyles.formGroup}>
              <label style={dashStyles.label}>Identifiant Administrateur</label>
              <input
                type="text"
                value={loginUsername}
                onChange={(e) => setLoginUsername(e.target.value)}
                style={dashStyles.input}
                required
              />
            </div>
            <div style={dashStyles.formGroup}>
              <label style={dashStyles.label}>Mot de passe sécurisé</label>
              <input
                type="password"
                value={loginPassword}
                placeholder="••••••••••••"
                onChange={(e) => setLoginPassword(e.target.value)}
                style={dashStyles.input}
                required
              />
            </div>
            <button
              type="submit"
              disabled={loginLoading}
              style={{
                ...dashStyles.primaryBtn,
                opacity: loginLoading ? 0.7 : 1,
              }}
            >
              {loginLoading ? 'Connexion en cours...' : 'Se connecter (JWT / 2FA)'}
            </button>
          </form>

          <div style={dashStyles.loginSecurityNotice}>
            🔒 Authentification protégée par jetons cryptographiques RFC 7519 et limitation de débit
            anti-force brute (5 requêtes/min max).
          </div>
        </div>
      </div>
    );
  }

  // Dashboard Administrateur
  return (
    <div style={dashStyles.dashboardContainer}>
      {/* Toast Notification */}
      {toastMessage && (
        <div
          style={{
            ...dashStyles.toast,
            backgroundColor: toastMessage.type === 'success' ? '#059669' : '#DC2626',
          }}
        >
          {toastMessage.type === 'success' ? '✓ ' : '✕ '} {toastMessage.text}
        </div>
      )}

      {/* Header Bar */}
      <header style={dashStyles.topBar}>
        <div style={dashStyles.brandGroup}>
          <span style={{ fontSize: '26px' }}>🏥</span>
          <div>
            <h1 style={dashStyles.brandTitle}>MEDIZY — Modération Administrative</h1>
            <span style={dashStyles.brandSubtitle}>
              Base Nationale : 1 650+ structures certifiées • 58 Wilayas
            </span>
          </div>
        </div>

        <div style={dashStyles.userGroup}>
          {rateLimit.remaining && (
            <div style={dashStyles.rateLimitBadge} title="Limitation de débit Redis active">
              🛡️ Quota API : {rateLimit.remaining}/{rateLimit.limit || '60'} req/min
            </div>
          )}
          <div style={dashStyles.adminBadge}>
            <span style={dashStyles.adminDot} />
            <span>{adminProfile?.admin_name || 'Admin'}</span>
          </div>
          <button onClick={handleLogout} style={dashStyles.logoutBtn}>
            Déconnexion
          </button>
        </div>
      </header>

      {/* Main Content */}
      <main style={dashStyles.mainArea}>
        {/* KPI Counter Cards */}
        <section style={dashStyles.kpiGrid}>
          <div style={dashStyles.kpiCard}>
            <span style={dashStyles.kpiIcon}>⏳</span>
            <div>
              <div style={dashStyles.kpiValue}>{kpiPending}</div>
              <div style={dashStyles.kpiLabel}>En attente de revue</div>
            </div>
          </div>
          <div style={{ ...dashStyles.kpiCard, borderColor: '#F59E0B' }}>
            <span style={dashStyles.kpiIcon}>⚠️</span>
            <div>
              <div style={{ ...dashStyles.kpiValue, color: '#D97706' }}>{kpiDuplicates}</div>
              <div style={dashStyles.kpiLabel}>Alertes Doublons (&lt; 100m)</div>
            </div>
          </div>
          <div style={dashStyles.kpiCard}>
            <span style={dashStyles.kpiIcon}>🇩🇿</span>
            <div>
              <div style={dashStyles.kpiValue}>58</div>
              <div style={dashStyles.kpiLabel}>Wilayas couvertes</div>
            </div>
          </div>
          <div style={dashStyles.kpiCard}>
            <span style={dashStyles.kpiIcon}>🔄</span>
            <div>
              <div style={dashStyles.kpiValue}>02:00</div>
              <div style={dashStyles.kpiLabel}>Ingestion nocturne auto</div>
            </div>
          </div>
        </section>

        {/* Filter Toolbar */}
        <section style={dashStyles.toolbar}>
          <div style={dashStyles.statusTabs}>
            {(['PENDING', 'APPROVED', 'REJECTED'] as SuggestionStatus[]).map((st) => (
              <button
                key={st}
                onClick={() => setStatusFilter(st)}
                style={{
                  ...dashStyles.statusTabBtn,
                  ...(statusFilter === st ? dashStyles.statusTabBtnActive : {}),
                }}
              >
                {st === 'PENDING' ? 'En attente' : st === 'APPROVED' ? 'Approuvés' : 'Rejetés'}
              </button>
            ))}
          </div>

          <div style={dashStyles.filterControls}>
            <label style={dashStyles.checkboxLabel}>
              <input
                type="checkbox"
                checked={onlyDuplicates}
                onChange={(e) => setOnlyDuplicates(e.target.checked)}
              />
              <span>Doublons potentiels uniquement</span>
            </label>

            <input
              type="text"
              placeholder="Filtrer par nom ou wilaya..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={dashStyles.searchInput}
            />

            <button onClick={loadSuggestions} style={dashStyles.refreshBtn} title="Actualiser la liste">
              🔄 Actualiser
            </button>
          </div>
        </section>

        {/* Suggestions Table / List */}
        <section style={dashStyles.tableCard}>
          {loading ? (
            <div style={dashStyles.emptyState}>Chargement des suggestions en cours...</div>
          ) : error ? (
            <div style={dashStyles.errorState}>{error}</div>
          ) : filteredSuggestions.length === 0 ? (
            <div style={dashStyles.emptyState}>
              Aucune suggestion trouvée pour le filtre sélectionné.
            </div>
          ) : (
            <div style={dashStyles.tableWrapper}>
              <table style={dashStyles.table}>
                <thead>
                  <tr>
                    <th style={dashStyles.th}>ID</th>
                    <th style={dashStyles.th}>Établissement proposé</th>
                    <th style={dashStyles.th}>Localisation</th>
                    <th style={dashStyles.th}>Contact & Source</th>
                    <th style={dashStyles.th}>Alerte Doublon</th>
                    <th style={{ ...dashStyles.th, textAlign: 'right' }}>Actions de modération</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredSuggestions.map((item) => {
                    const isDup = Boolean(item.matched_facility_id);
                    return (
                      <tr key={item.id} style={dashStyles.tr}>
                        <td style={dashStyles.tdId}>#{item.id}</td>
                        <td style={dashStyles.td}>
                          <div style={dashStyles.facilityName}>{item.name}</div>
                          <div style={dashStyles.facilityTypeBadge}>
                            {item.type || 'Non classé'}
                          </div>
                        </td>
                        <td style={dashStyles.td}>
                          <div><strong>{item.wilaya}</strong> {item.commune ? `— ${item.commune}` : ''}</div>
                          <div style={dashStyles.addressSub}>{item.address || 'Adresse non spécifiée'}</div>
                        </td>
                        <td style={dashStyles.td}>
                          <div>{item.phone || '—'}</div>
                          <div style={dashStyles.submitterSub}>
                            Par : {item.submitter_name || 'Citoyen'}
                          </div>
                        </td>
                        <td style={dashStyles.td}>
                          {isDup ? (
                            <button
                              onClick={() => handleOpenComparison(item)}
                              style={dashStyles.dupAlertChip}
                              title="Cliquer pour afficher la comparaison cartographique côte à côte"
                            >
                              ⚠️ Doublon détecté (#{item.matched_facility_id})
                            </button>
                          ) : (
                            <span style={dashStyles.cleanChip}>✓ Inédit</span>
                          )}
                        </td>
                        <td style={{ ...dashStyles.td, textAlign: 'right' }}>
                          <div style={dashStyles.tableActionGroup}>
                            {isDup && (
                              <button
                                onClick={() => handleOpenComparison(item)}
                                style={dashStyles.compareBtn}
                                title="Examiner sur la carte miniature (< 100m)"
                              >
                                🗺️ Comparer
                              </button>
                            )}
                            {item.status === 'PENDING' && (
                              <>
                                <button
                                  onClick={() => {
                                    setApprovingItem(item);
                                    setOverrideType(item.type || '');
                                  }}
                                  style={dashStyles.approveSmallBtn}
                                >
                                  ✓ Valider
                                </button>
                                <button
                                  onClick={() => {
                                    setRejectingItem(item);
                                    setRejectReason(
                                      isDup
                                        ? `Doublon de l'établissement #${item.matched_facility_id}`
                                        : 'Informations inexactes ou incomplètes'
                                    );
                                  }}
                                  style={dashStyles.rejectSmallBtn}
                                >
                                  ✕ Rejeter
                                </button>
                              </>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </main>

      {/* Modal 1: Vue Cartographique Comparative de Doublon */}
      {activeComparison && (
        <DuplicateComparisonMap
          data={activeComparison}
          onClose={() => setActiveComparison(null)}
          onApprove={() => {
            const currentItem = suggestions.find((s) => s.id === activeComparison.proposed.id);
            if (currentItem) {
              setApprovingItem(currentItem);
              setOverrideType(currentItem.type || '');
            }
          }}
          onReject={(suggestedReason) => {
            const currentItem = suggestions.find((s) => s.id === activeComparison.proposed.id);
            if (currentItem) {
              setRejectingItem(currentItem);
              setRejectReason(suggestedReason);
            }
          }}
        />
      )}

      {/* Modal 2: Confirmation d'Approbation */}
      {approvingItem && (
        <div style={dashStyles.actionModalOverlay}>
          <div style={dashStyles.actionModalCard}>
            <h3 style={dashStyles.actionModalTitle}>
              Valider et Publier l'Établissement #{approvingItem.id}
            </h3>
            <p style={dashStyles.actionModalDesc}>
              Cette action va convertir la suggestion citoyenne en fiche officielle certifiée
              dans le répertoire national MEDIZY.
            </p>

            <div style={dashStyles.formGroup}>
              <label style={dashStyles.label}>Typologie officielle confirmée</label>
              <select
                value={overrideType}
                onChange={(e) => setOverrideType(e.target.value as FacilityType)}
                style={dashStyles.select}
              >
                <option value="">Conserver ({approvingItem.type || 'Non spécifié'})</option>
                <option value="CHU">CHU (Centre Hospitalo-Universitaire)</option>
                <option value="EPH">EPH (Établissement Public Hospitalier)</option>
                <option value="EPSP">EPSP (Établissement Public de Santé de Proximité)</option>
                <option value="Polyclinique">Polyclinique</option>
                <option value="Clinique">Clinique privée</option>
                <option value="Urgences">Centre d'Urgences</option>
              </select>
            </div>

            <div style={dashStyles.formGroup}>
              <label style={dashStyles.label}>Commentaire de certification (interne)</label>
              <input
                type="text"
                placeholder="Ex: Vérifié auprès de la DSP Alger / Décret sanitaire"
                value={moderationComment}
                onChange={(e) => setModerationComment(e.target.value)}
                style={dashStyles.input}
              />
            </div>

            <div style={dashStyles.modalButtons}>
              <button
                onClick={() => setApprovingItem(null)}
                style={dashStyles.cancelBtn}
                disabled={actionLoading}
              >
                Annuler
              </button>
              <button
                onClick={executeApproval}
                style={dashStyles.confirmApproveBtn}
                disabled={actionLoading}
              >
                {actionLoading ? 'Publication...' : 'Confirmer la Publication'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal 3: Motif de Rejet */}
      {rejectingItem && (
        <div style={dashStyles.actionModalOverlay}>
          <div style={dashStyles.actionModalCard}>
            <h3 style={{ ...dashStyles.actionModalTitle, color: '#DC2626' }}>
              Rejeter la Suggestion #{rejectingItem.id}
            </h3>
            <p style={dashStyles.actionModalDesc}>
              Veuillez motiver la décision de rejet pour archivage et traçabilité.
            </p>

            <div style={dashStyles.presetReasonGroup}>
              <button
                type="button"
                onClick={() => setRejectReason("Doublon avéré d'un établissement déjà référencé.")}
                style={dashStyles.presetBtn}
              >
                Doublon avéré
              </button>
              <button
                type="button"
                onClick={() => setRejectReason("Coordonnées géographiques incorrectes ou introuvables.")}
                style={dashStyles.presetBtn}
              >
                Coordonnées erronées
              </button>
              <button
                type="button"
                onClick={() => setRejectReason("Établissement fermé définitivement ou non agréé.")}
                style={dashStyles.presetBtn}
              >
                Établissement fermé
              </button>
            </div>

            <div style={dashStyles.formGroup}>
              <label style={dashStyles.label}>Motif du rejet (obligatoire)</label>
              <textarea
                rows={3}
                value={rejectReason}
                onChange={(e) => setRejectReason(e.target.value)}
                style={dashStyles.textarea}
                placeholder="Expliquez la raison du rejet..."
                required
              />
            </div>

            <div style={dashStyles.modalButtons}>
              <button
                onClick={() => setRejectingItem(null)}
                style={dashStyles.cancelBtn}
                disabled={actionLoading}
              >
                Annuler
              </button>
              <button
                onClick={executeRejection}
                style={dashStyles.confirmRejectBtn}
                disabled={actionLoading}
              >
                {actionLoading ? 'Rejet en cours...' : 'Confirmer le Rejet'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

// Styles CSS-in-JS du Dashboard
const dashStyles: Record<string, React.CSSProperties> = {
  dashboardContainer: {
    minHeight: '100vh',
    backgroundColor: '#F8FAFC',
    fontFamily: 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    color: '#0F172A',
  },
  topBar: {
    backgroundColor: '#FFFFFF',
    borderBottom: '1px solid #E2E8F0',
    padding: '16px 32px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  brandGroup: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
  },
  brandTitle: {
    margin: 0,
    fontSize: '18px',
    fontWeight: '800',
    color: '#0F172A',
  },
  brandSubtitle: {
    fontSize: '12px',
    color: '#64748B',
  },
  userGroup: {
    display: 'flex',
    alignItems: 'center',
    gap: '14px',
  },
  rateLimitBadge: {
    fontSize: '12px',
    padding: '4px 10px',
    backgroundColor: '#EFF6FF',
    color: '#1E40AF',
    borderRadius: '16px',
    border: '1px solid #BFDBFE',
    fontWeight: '600',
  },
  adminBadge: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    fontSize: '13px',
    fontWeight: '600',
    color: '#334155',
  },
  adminDot: {
    width: '8px',
    height: '8px',
    borderRadius: '50%',
    backgroundColor: '#10B981',
  },
  logoutBtn: {
    padding: '6px 12px',
    backgroundColor: '#F1F5F9',
    border: '1px solid #CBD5E1',
    borderRadius: '6px',
    fontSize: '12px',
    cursor: 'pointer',
    fontWeight: '500',
  },
  mainArea: {
    padding: '24px 32px',
    maxWidth: '1440px',
    margin: '0 auto',
  },
  kpiGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
    gap: '16px',
    marginBottom: '24px',
  },
  kpiCard: {
    backgroundColor: '#FFFFFF',
    padding: '18px 20px',
    borderRadius: '12px',
    border: '1px solid #E2E8F0',
    display: 'flex',
    alignItems: 'center',
    gap: '14px',
    boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
  },
  kpiIcon: {
    fontSize: '28px',
  },
  kpiValue: {
    fontSize: '24px',
    fontWeight: '800',
    color: '#0F172A',
    lineHeight: 1.2,
  },
  kpiLabel: {
    fontSize: '12px',
    color: '#64748B',
    fontWeight: '500',
  },
  toolbar: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: '16px',
    flexWrap: 'wrap',
    gap: '12px',
  },
  statusTabs: {
    display: 'flex',
    backgroundColor: '#E2E8F0',
    borderRadius: '8px',
    padding: '3px',
  },
  statusTabBtn: {
    padding: '6px 16px',
    border: 'none',
    background: 'none',
    fontSize: '13px',
    fontWeight: '600',
    color: '#64748B',
    borderRadius: '6px',
    cursor: 'pointer',
  },
  statusTabBtnActive: {
    backgroundColor: '#FFFFFF',
    color: '#0F172A',
    boxShadow: '0 1px 2px rgba(0,0,0,0.06)',
  },
  filterControls: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
  },
  checkboxLabel: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    fontSize: '13px',
    color: '#475569',
    cursor: 'pointer',
  },
  searchInput: {
    padding: '8px 14px',
    borderRadius: '8px',
    border: '1px solid #CBD5E1',
    fontSize: '13px',
    width: '240px',
  },
  refreshBtn: {
    padding: '8px 14px',
    backgroundColor: '#FFFFFF',
    border: '1px solid #CBD5E1',
    borderRadius: '8px',
    fontSize: '13px',
    fontWeight: '600',
    cursor: 'pointer',
  },
  tableCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: '12px',
    border: '1px solid #E2E8F0',
    boxShadow: '0 1px 3px rgba(0,0,0,0.04)',
    overflow: 'hidden',
  },
  tableWrapper: {
    overflowX: 'auto',
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse',
    fontSize: '13px',
  },
  th: {
    textAlign: 'left',
    padding: '12px 18px',
    backgroundColor: '#F8FAFC',
    borderBottom: '1px solid #E2E8F0',
    fontWeight: '700',
    color: '#475569',
    fontSize: '12px',
    textTransform: 'uppercase',
  },
  tr: {
    borderBottom: '1px solid #F1F5F9',
  },
  tdId: {
    padding: '14px 18px',
    fontWeight: '700',
    color: '#64748B',
  },
  td: {
    padding: '14px 18px',
  },
  facilityName: {
    fontWeight: '700',
    color: '#0F172A',
  },
  facilityTypeBadge: {
    display: 'inline-block',
    padding: '2px 8px',
    borderRadius: '4px',
    backgroundColor: '#EFF6FF',
    color: '#1D4ED8',
    fontSize: '11px',
    fontWeight: '600',
    marginTop: '4px',
  },
  addressSub: {
    fontSize: '12px',
    color: '#64748B',
    marginTop: '2px',
  },
  submitterSub: {
    fontSize: '11px',
    color: '#94A3B8',
    marginTop: '2px',
  },
  dupAlertChip: {
    padding: '4px 10px',
    borderRadius: '20px',
    backgroundColor: '#FEF3C7',
    color: '#B45309',
    border: '1px solid #FCD34D',
    fontSize: '12px',
    fontWeight: '600',
    cursor: 'pointer',
    display: 'inline-flex',
    alignItems: 'center',
    gap: '4px',
  },
  cleanChip: {
    fontSize: '12px',
    color: '#059669',
    fontWeight: '600',
  },
  tableActionGroup: {
    display: 'flex',
    gap: '6px',
    justifyContent: 'flex-end',
  },
  compareBtn: {
    padding: '6px 10px',
    backgroundColor: '#EEF2FF',
    color: '#4F46E5',
    border: '1px solid #C7D2FE',
    borderRadius: '6px',
    fontSize: '12px',
    fontWeight: '600',
    cursor: 'pointer',
  },
  approveSmallBtn: {
    padding: '6px 12px',
    backgroundColor: '#10B981',
    color: '#FFFFFF',
    border: 'none',
    borderRadius: '6px',
    fontSize: '12px',
    fontWeight: '600',
    cursor: 'pointer',
  },
  rejectSmallBtn: {
    padding: '6px 12px',
    backgroundColor: '#EF4444',
    color: '#FFFFFF',
    border: 'none',
    borderRadius: '6px',
    fontSize: '12px',
    fontWeight: '600',
    cursor: 'pointer',
  },
  emptyState: {
    padding: '48px',
    textAlign: 'center',
    color: '#64748B',
  },
  errorState: {
    padding: '32px',
    textAlign: 'center',
    color: '#DC2626',
  },
  toast: {
    position: 'fixed',
    bottom: '24px',
    right: '24px',
    color: '#FFFFFF',
    padding: '12px 20px',
    borderRadius: '8px',
    boxShadow: '0 10px 15px -3px rgba(0,0,0,0.1)',
    zIndex: 10000,
    fontWeight: '600',
    fontSize: '13px',
  },
  loginWrapper: {
    minHeight: '100vh',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#0F172A',
    padding: '16px',
  },
  loginCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: '16px',
    padding: '36px',
    width: '100%',
    maxWidth: '420px',
    boxShadow: '0 20px 25px -5px rgba(0,0,0,0.1)',
  },
  loginHeader: {
    textAlign: 'center',
    marginBottom: '24px',
  },
  loginTitle: {
    margin: '12px 0 6px 0',
    fontSize: '22px',
    fontWeight: '800',
    color: '#0F172A',
  },
  loginSubtitle: {
    margin: 0,
    fontSize: '13px',
    color: '#64748B',
  },
  errorBox: {
    backgroundColor: '#FEE2E2',
    color: '#991B1B',
    padding: '10px 14px',
    borderRadius: '8px',
    fontSize: '13px',
    marginBottom: '16px',
  },
  loginForm: {
    display: 'flex',
    flexDirection: 'column',
    gap: '16px',
  },
  formGroup: {
    display: 'flex',
    flexDirection: 'column',
    gap: '6px',
    marginBottom: '12px',
  },
  label: {
    fontSize: '12px',
    fontWeight: '600',
    color: '#475569',
  },
  input: {
    padding: '10px 14px',
    borderRadius: '8px',
    border: '1px solid #CBD5E1',
    fontSize: '14px',
  },
  select: {
    padding: '10px 14px',
    borderRadius: '8px',
    border: '1px solid #CBD5E1',
    fontSize: '14px',
    backgroundColor: '#FFFFFF',
  },
  textarea: {
    padding: '10px 14px',
    borderRadius: '8px',
    border: '1px solid #CBD5E1',
    fontSize: '14px',
    resize: 'vertical',
  },
  primaryBtn: {
    padding: '12px',
    backgroundColor: '#2563EB',
    color: '#FFFFFF',
    border: 'none',
    borderRadius: '8px',
    fontSize: '14px',
    fontWeight: '700',
    cursor: 'pointer',
    marginTop: '8px',
  },
  loginSecurityNotice: {
    marginTop: '20px',
    fontSize: '11px',
    color: '#64748B',
    textAlign: 'center',
    lineHeight: 1.4,
  },
  actionModalOverlay: {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(15, 23, 42, 0.6)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 9999,
    padding: '16px',
  },
  actionModalCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: '14px',
    padding: '28px',
    width: '100%',
    maxWidth: '520px',
    boxShadow: '0 20px 25px -5px rgba(0,0,0,0.1)',
  },
  actionModalTitle: {
    margin: '0 0 8px 0',
    fontSize: '18px',
    fontWeight: '700',
  },
  actionModalDesc: {
    margin: '0 0 20px 0',
    fontSize: '13px',
    color: '#64748B',
  },
  modalButtons: {
    display: 'flex',
    justifyContent: 'flex-end',
    gap: '10px',
    marginTop: '20px',
  },
  cancelBtn: {
    padding: '10px 16px',
    backgroundColor: '#F1F5F9',
    border: '1px solid #CBD5E1',
    borderRadius: '8px',
    fontSize: '13px',
    fontWeight: '600',
    cursor: 'pointer',
  },
  confirmApproveBtn: {
    padding: '10px 18px',
    backgroundColor: '#059669',
    color: '#FFFFFF',
    border: 'none',
    borderRadius: '8px',
    fontSize: '13px',
    fontWeight: '600',
    cursor: 'pointer',
  },
  confirmRejectBtn: {
    padding: '10px 18px',
    backgroundColor: '#EF4444',
    color: '#FFFFFF',
    border: 'none',
    borderRadius: '8px',
    fontSize: '13px',
    fontWeight: '600',
    cursor: 'pointer',
  },
  presetReasonGroup: {
    display: 'flex',
    gap: '6px',
    flexWrap: 'wrap',
    marginBottom: '12px',
  },
  presetBtn: {
    padding: '4px 8px',
    backgroundColor: '#F1F5F9',
    border: '1px solid #E2E8F0',
    borderRadius: '4px',
    fontSize: '11px',
    cursor: 'pointer',
    color: '#475569',
  },
};
