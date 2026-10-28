/**
 * MEDIZY / SANTÉ DZ — Hook React de Cartographie Interactive
 * ==========================================================
 * Déclenche automatiquement le rechargement des structures de santé
 * lors du déplacement du viewport de la carte (bounds) avec debounce (300ms).
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { Facility, FacilityType, MapBounds } from './types';
import { searchFacilities } from './facilitiesApi';

interface UseFacilitiesMapOptions {
  initialBounds?: MapBounds;
  typeFilter?: FacilityType;
  wilayaFilter?: string;
  searchQuery?: string;
  debounceMs?: number;
}

export function useFacilitiesMap(options: UseFacilitiesMapOptions = {}) {
  const {
    initialBounds,
    typeFilter,
    wilayaFilter,
    searchQuery,
    debounceMs = 300,
  } = options;

  const [bounds, setBounds] = useState<MapBounds | undefined>(initialBounds);
  const [facilities, setFacilities] = useState<Facility[]>([]);
  const [total, setTotal] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const debounceTimerRef = useRef<NodeJS.Timeout | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const fetchFacilities = useCallback(
    async (currentBounds?: MapBounds) => {
      if (!currentBounds) return;

      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
      abortControllerRef.current = new AbortController();

      setLoading(true);
      setError(null);

      try {
        const result = await searchFacilities({
          bounds: currentBounds,
          type: typeFilter,
          wilaya: wilayaFilter,
          q: searchQuery,
          limit: 100, // Limite optimale pour affichage fluide des marqueurs carto
        });
        setFacilities(result.data);
        setTotal(result.total);
      } catch (err: any) {
        if (err.name !== 'AbortError') {
          setError(err.message || 'Erreur lors du chargement des structures.');
        }
      } finally {
        setLoading(false);
      }
    },
    [typeFilter, wilayaFilter, searchQuery]
  );

  // Mise à jour des bornes avec debounce lors du drag / zoom de la carte
  const onMapBoundsChange = useCallback(
    (newBounds: MapBounds) => {
      setBounds(newBounds);
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
      debounceTimerRef.current = setTimeout(() => {
        fetchFacilities(newBounds);
      }, debounceMs);
    },
    [fetchFacilities, debounceMs]
  );

  // Déclencher le rechargement si les filtres changent
  useEffect(() => {
    if (bounds) {
      fetchFacilities(bounds);
    }
  }, [typeFilter, wilayaFilter, searchQuery]);

  return {
    facilities,
    total,
    loading,
    error,
    bounds,
    onMapBoundsChange,
    refetch: () => bounds && fetchFacilities(bounds),
  };
}
