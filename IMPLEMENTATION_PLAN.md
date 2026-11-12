# Medizy v2.0 Implementation Plan

## Objectives

1. **Google Maps Only** - Remove all open-source maps (OSM), keep only Google Maps with two modes:
   - Standard (Plan) - `lyrs=m`
   - Satellite/Hybrid - `lyrs=y`
   - Both with medical POI only (`s.t:36|p.v:on`) and all other POI disabled (`s.t:2|p.v:off`)

2. **Medizy Logo Markers** - Replace all specialty icons with Medizy logo on map, properly positioned at GPS coordinates

3. **Arabic Localization** - Full word-by-word translation + abbreviation for long texts on home screen

4. **1541 Communes Processing** - Systematic wilaya-by-wilaya, commune-by-commune processing of all 40,752 health facilities

5. **Frontend Perfection** - Enhanced UI with feminine touches, premium feel

---

## Phase 1: Google Maps Configuration (Critical)

### Current State
- `offline_map_view.dart` lines 673-678: Already has Google Maps URLs but also OSM fallback
- Uses `flutter_map` with `TileLayer`

### Required Changes
1. Remove OSM entirely (`_mapLayerMode == 0`)
2. Keep only two modes:
   - Mode 0: Google Maps Standard (Plan) - `lyrs=m&apistyle=s.t:2|p.v:off,s.t:36|p.v:on`
   - Mode 1: Google Maps Satellite - `lyrs=y&apistyle=s.t:2|p.v:off,s.t:36|p.v:on`
3. Add proper Google Maps API key handling (or use keyless approach with rate limiting)
4. Implement custom tile provider with proper headers

### Files to Modify
- `lib/features/map/offline_map_view.dart` - Main map view
- `lib/features/map/utils/specialty_marker_theme.dart` - Markers
- `lib/core/theme/medizy_theme.dart` - Theme constants

---

## Phase 2: Medizy Logo Markers on Map

### Requirements
- Every health facility marker uses Medizy logo (from `assets/images/medizy_logo.png`)
- Markers must be at exact GPS coordinates (latitude/longitude from database)
- Marker should show facility type via color coding or small badge
- Performance: Max 150 markers at zoom ≥ 11 (viewport mode), aggregated at lower zoom

### Implementation
1. Create `MedizyMapMarker` widget using `Image.asset` with the logo
2. Color tint based on facility category (using `SpecialtyMarkerTheme` colors)
3. Add small category badge overlay
4. Ensure proper z-index and clustering at high density

### Files to Modify
- `lib/features/map/offline_map_view.dart` - MarkerLayer implementation
- `lib/features/map/utils/specialty_marker_theme.dart` - Add Medizy marker factory
- Create new: `lib/features/map/widgets/medizy_map_marker.dart`

---

## Phase 3: Arabic Localization System

### Current State
- `lib/core/services/medizy_locale.dart` - Has basic translation system
- `isArabic` static flag, `t(fr, ar)` method
- `categoryAbbrArabic` for home screen abbreviations

### Required Enhancements
1. **Full word-by-word translation** for ALL UI strings
2. **Arabic toggle button** in app bar (home screen + map screen)
3. **RTL support** for Arabic layout
4. **Abbreviation system** for long category names on home screen cards
5. **Persist language preference** (SharedPreferences)

### Files to Modify
- `lib/core/services/medizy_locale.dart` - Expand dictionaries, add RTL
- `lib/main.dart` - Add locale initialization
- `lib/features/home/presentation/screens/medizy_home_screen.dart` - Arabic button
- `lib/features/map/offline_map_view.dart` - Arabic button
- `lib/features/home/presentation/widgets/category_grid.dart` - Abbreviations

---

## Phase 4: 1541 Communes Processing Pipeline

### Data Analysis
- 58 Wilayas ✓
- 1,541 Communes ✓ (in `communes` table with `nom_fr` and `nom_ar`)
- 40,752 Health facilities ✓ (in `facilities` table)
- Categories: 9 types (Établissement Public, Clinique Privée, Pharmacie d'Officine, etc.)

### Processing Strategy: Wilaya → Commune sequential

**Wilaya Order**: 01→58 (Adrar → Tindouf)

For each wilaya:
1. Load all communes for that wilaya from `communes` table
2. For each commune:
   - Query facilities in that commune
   - Validate GPS coordinates match Google Maps
   - Generate/Update alignment data
   - Create Medizy marker data

### Python Script: `tools/process_1541_communes.py`
```python
# Sequential processing
for wilaya_code in sorted(wilaya_codes):  # 01 to 58
    communes = get_communes_for_wilaya(wilaya_code)
    for commune in sorted(communes):  # alphabetical
        facilities = get_facilities_for_commune(wilaya_code, commune)
        process_commune(wilaya_code, commune, facilities)
        save_progress()
```

### Output
- Updated `sante_dz_bundled.db` with verified coordinates
- Alignment report per wilaya/commune
- Google Maps Place IDs for each facility (for future enrichment)

### Files to Create
- `tools/process_1541_communes.py` - Main processing script
- `tools/google_maps_aligner.py` - Google Maps API alignment
- `tools/verify_coordinates.py` - Coordinate verification

---

## Phase 5: Frontend Perfection (Premium + Feminine)

### Home Screen Enhancements
1. **Hero section** with animated Medizy logo
2. **Category cards** with:
   - Medizy logo + abbreviated Arabic names
   - Facility count badges
   - Subtle gradient backgrounds (feminine palette: teal, rose, coral, lavender)
   - Hover/tap animations
3. **Bottom action bar** - Enhanced with icons + labels
4. **Arabic toggle** - Top right with flag/icon

### Map Screen Enhancements
1. **Clean app bar** with:
   - Wilaya/Commune selector (existing, enhance)
   - Arabic toggle button
   - Layer switcher (Plan/Satellite)
   - SOS button
2. **FacetFilterBar** - Already well designed, polish animations
3. **Floating action buttons** - Grouped, with labels on long press
4. **Facility detail sheet** - Premium card design with:
   - Medizy branding
   - One-tap: Call, WhatsApp, Google Maps route, Share, Favorite
   - Arabic translations

### Color Palette (Feminine Medical Premium)
```dart
// Primary: Teal medical (trust)
primary: 0xFF00695C
primaryLight: 0xFF00ACC1
primaryDark: 0xFF004D40

// Accent: Rose/Coral (feminine warmth)
accent: 0xFFE91E63
accentLight: 0xFFF06292
accentDark: 0xFFC2185B

// Secondary: Lavender (calm)
secondary: 0xFF9C27B0
secondaryLight: 0xFFBA68C8

// Surface: Off-white with subtle warmth
surface: 0xFFFAFAFA
background: 0xFFF5F9FC
```

### Files to Modify
- `lib/core/theme/medizy_theme.dart` - Complete theme overhaul
- `lib/features/home/presentation/screens/medizy_home_screen.dart` - Premium redesign
- `lib/features/home/presentation/widgets/category_grid.dart` - Card redesign
- `lib/features/map/offline_map_view.dart` - Polish
- `lib/features/map/widgets/facility_detail_sheet.dart` - Premium sheet
- `lib/features/map/widgets/facet_filter_bar.dart` - Animations

---

## Phase 6: Integration & Testing

### Database Sync
- Regenerate `sante_dz_bundled.db` after coordinate verification
- Update `medizy_wilayas_index.json` and `medizy_categories_index.json`
- Verify all 1,541 communes have data

### Test Coverage
- Unit tests for locale system
- Widget tests for Arabic toggle
- Integration tests for map markers
- Performance test: 150 markers at 60 FPS

### Build Verification
```bash
flutter test
flutter build apk --release
flutter build ios --release
```

---

## Execution Order

| Phase | Priority | Estimated Effort | Dependencies |
|-------|----------|------------------|--------------|
| 1. Google Maps Only | CRITICAL | 2-3 hours | None |
| 2. Medizy Logo Markers | CRITICAL | 2-3 hours | Phase 1 |
| 3. Arabic Localization | HIGH | 3-4 hours | None (parallel) |
| 4. 1541 Communes Pipeline | HIGH | 4-6 hours | Database access |
| 5. Frontend Perfection | HIGH | 4-5 hours | Phases 1-3 |
| 6. Integration & Testing | MEDIUM | 2-3 hours | All phases |

**Total: ~18-24 hours**

---

## Key Technical Decisions

1. **Google Maps without API Key**: Use `mt1.google.com/vt/lyrs=...` tile URLs (keyless, rate-limited but works for mobile)
2. **Medizy Logo as Marker**: Use `Image.asset` with `ColorFiltered` for category colors
3. **Arabic RTL**: Use `Directionality` widget with `TextDirection.rtl` when `MedizyLocale.isArabic`
4. **Commune Processing**: Python script with SQLite, outputs verification CSV per wilaya
5. **Feminine UI**: Subtle gradients, rounded corners (24px), soft shadows, teal/rose/lavender palette

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Google Maps tile blocking | Fallback to cached tiles + OSM as last resort |
| 40K markers performance | Viewport limiting (150 max), clustering at low zoom |
| Arabic text overflow | Abbreviations + `TextOverflow.ellipsis` + `FittedBox` |
| Coordinate drift | Batch verify against Google Maps Geocoding API |
| iOS Google Maps policy | Use `google_maps_flutter` plugin as alternative if needed |

---

## Next Steps

1. Start Phase 1: Modify `offline_map_view.dart` to remove OSM
2. Create `MedizyMapMarker` widget
3. Expand `medizy_locale.dart` with complete translations
4. Write commune processing Python script
5. Redesign theme and home screen
6. Full integration test