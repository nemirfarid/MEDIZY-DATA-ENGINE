import 'package:flutter/material.dart';
import '../../../core/theme/medizy_theme.dart';
import '../../../core/models/health_facility.dart';
import '../utils/specialty_marker_theme.dart';

/// Marqueur Medizy premium pour la carte
/// Utilise le logo Medizy avec coloration par catégorie
class MedizyMapMarker extends StatelessWidget {
  final HealthFacility facility;
  final bool isSelected;
  final bool isEmergency;
  final String? activeFilterCategory;
  final VoidCallback? onTap;
  final double size;

  const MedizyMapMarker({
    super.key,
    required this.facility,
    this.isSelected = false,
    this.isEmergency = false,
    this.activeFilterCategory,
    this.onTap,
    this.size = 44.0,
  });

  @override
  Widget build(BuildContext context) {
    final theme = _getMarkerTheme();
    final markerColor = theme.color;
    final isEmergencyFacility = facility.isEmergencyOrOnDuty || isEmergency;

    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        curve: Curves.easeOutCubic,
        width: isSelected ? size * 1.2 : size,
        height: isSelected ? size * 1.2 : size,
        child: Stack(
          alignment: Alignment.center,
          children: [
            // 1. Ombre portée animée
            AnimatedContainer(
              duration: const Duration(milliseconds: 200),
              width: isSelected ? size * 1.1 : size * 0.9,
              height: isSelected ? size * 1.1 : size * 0.9,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: markerColor.withValues(alpha: isSelected ? 0.4 : 0.25),
                boxShadow: [
                  BoxShadow(
                    color: markerColor.withValues(alpha: isSelected ? 0.5 : 0.3),
                    blurRadius: isSelected ? 16 : 8,
                    offset: Offset(0, isSelected ? 6 : 4),
                    spreadRadius: isSelected ? 2 : 0,
                  ),
                ],
              ),
            ),

            // 2. Cercle principal avec logo Medizy
            Container(
              width: size,
              height: size,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: Colors.white,
                boxShadow: [
                  BoxShadow(
                    color: Colors.black.withValues(alpha: 0.15),
                    blurRadius: 4,
                    offset: const Offset(0, 2),
                  ),
                ],
                border: Border.all(
                  color: isSelected ? markerColor : Colors.white,
                  width: isSelected ? 3 : 2.5,
                ),
              ),
              child: Center(
                child: SizedBox(
                  width: size * 0.55,
                  height: size * 0.55,
                  child: ColorFiltered(
                    colorFilter: ColorFilter.mode(
                      markerColor,
                      BlendMode.srcIn,
                    ),
                    child: Image.asset(
                      'assets/images/medizy_logo.png',
                      fit: BoxFit.contain,
                      errorBuilder: (context, error, stackTrace) {
                        // Fallback: icône médicale si logo indisponible
                        return Icon(
                          theme.icon,
                          color: markerColor,
                          size: size * 0.55,
                        );
                      },
                    ),
                  ),
                ),
              ),
            ),

            // 3. Badge urgence (pulse animation)
            if (isEmergencyFacility)
              Positioned(
                top: -2,
                right: -2,
                child: _EmergencyPulseBadge(
                  color: MedizyTheme.error,
                  size: size * 0.3,
                ),
              ),

            // 4. Indicateur de sélection (anneau externe)
            if (isSelected)
              Positioned.fill(
                child: IgnorePointer(
                  child: Container(
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      border: Border.all(
                        color: markerColor,
                        width: 2,
                      ),
                    ),
                    child: Center(
                      child: Container(
                        width: size * 1.35,
                        height: size * 1.35,
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          border: Border.all(
                            color: markerColor.withValues(alpha: 0.3),
                            width: 1.5,
                          ),
                        ),
                      ),
                    ),
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }

  SpecialtyMarkerTheme _getMarkerTheme() {
    return SpecialtyMarkerTheme.forCategory(
      facility.categorie,
      facilityName: facility.nom,
      isEmergency: isEmergency || facility.isEmergencyOrOnDuty,
      activeFilterCategory: activeFilterCategory,
    );
  }
}

/// Badge d'urgence avec animation pulse
class _EmergencyPulseBadge extends StatefulWidget {
  final Color color;
  final double size;

  const _EmergencyPulseBadge({
    required this.color,
    required this.size,
  });

  @override
  State<_EmergencyPulseBadge> createState() => _EmergencyPulseBadgeState();
}

class _EmergencyPulseBadgeState extends State<_EmergencyPulseBadge>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;
  late final Animation<double> _scaleAnimation;
  late final Animation<double> _opacityAnimation;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      duration: const Duration(milliseconds: 1500),
      vsync: this,
    )..repeat(reverse: true);

    _scaleAnimation = Tween<double>(begin: 0.85, end: 1.15).animate(
      CurvedAnimation(parent: _controller, curve: Curves.easeInOut),
    );

    _opacityAnimation = Tween<double>(begin: 0.7, end: 1.0).animate(
      CurvedAnimation(parent: _controller, curve: Curves.easeInOut),
    );
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _controller,
      builder: (context, child) {
        return Transform.scale(
          scale: _scaleAnimation.value,
          child: Opacity(
            opacity: _opacityAnimation.value,
            child: Container(
              width: widget.size,
              height: widget.size,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: widget.color,
                boxShadow: [
                  BoxShadow(
                    color: widget.color.withValues(alpha: 0.5),
                    blurRadius: 6,
                    spreadRadius: 1,
                  ),
                ],
                border: Border.all(color: Colors.white, width: 2),
              ),
              child: Icon(
                Icons.emergency_rounded,
                color: Colors.white,
                size: widget.size * 0.55,
              ),
            ),
          ),
        );
      },
    );
  }
}

/// Marqueur d'agrégation pour vue nationale (wilaya)
class MedizyClusterMarker extends StatelessWidget {
  final String wilayaCode;
  final String wilayaName;
  final int count;
  final bool isSelected;
  final VoidCallback? onTap;
  final double size;

  const MedizyClusterMarker({
    super.key,
    required this.wilayaCode,
    required this.wilayaName,
    required this.count,
    this.isSelected = false,
    this.onTap,
    this.size = 160,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        width: size,
        height: 44,
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        decoration: BoxDecoration(
          gradient: MedizyTheme.heroGradient,
          borderRadius: BorderRadius.circular(28),
          border: Border.all(
            color: isSelected ? Colors.white : Colors.white.withValues(alpha: 0.8),
            width: isSelected ? 3 : 2,
          ),
          boxShadow: [
            BoxShadow(
              color: MedizyTheme.primaryDark.withValues(alpha: 0.4),
              blurRadius: isSelected ? 16 : 8,
              offset: Offset(0, isSelected ? 6 : 4),
              spreadRadius: isSelected ? 2 : 0,
            ),
            BoxShadow(
              color: Colors.black.withValues(alpha: 0.1),
              blurRadius: 4,
              offset: const Offset(0, 2),
            ),
          ],
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            // Logo Medizy mini
            Container(
              width: 28,
              height: 28,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: Colors.white.withValues(alpha: 0.2),
              ),
              child: Center(
                child: Image.asset(
                  'assets/images/medizy_logo.png',
                  width: 18,
                  height: 18,
                  color: Colors.white,
                  errorBuilder: (_, __, ___) => Icon(
                    Icons.local_hospital_rounded,
                    color: Colors.white,
                    size: 16,
                  ),
                ),
              ),
            ),
            const SizedBox(width: 10),
            // Texte
            Flexible(
              child: Text(
                '$wilayaCode - $wilayaName : $count',
                style: const TextStyle(
                  color: Colors.white,
                  fontWeight: FontWeight.w700,
                  fontSize: 13,
                  fontFamily: 'Cairo',
                  letterSpacing: 0.2,
                ),
                overflow: TextOverflow.ellipsis,
              ),
            ),
            if (isSelected) ...[
              const SizedBox(width: 6),
              Container(
                width: 8,
                height: 8,
                decoration: const BoxDecoration(
                  shape: BoxShape.circle,
                  color: Colors.amberAccent,
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

/// Marqueur pour la position utilisateur
class MedizyUserLocationMarker extends StatelessWidget {
  final bool hasRealGps;
  final double size;

  const MedizyUserLocationMarker({
    super.key,
    required this.hasRealGps,
    this.size = 48,
  });

  @override
  Widget build(BuildContext context) {
    final color = hasRealGps ? MedizyTheme.primaryLight : MedizyTheme.textTertiary;

    return SizedBox(
      width: size,
      height: size,
      child: Stack(
        alignment: Alignment.center,
        children: [
          // Cercle pulsant (précision GPS)
          _GpsPulseRing(
            color: color,
            size: size * 2.5,
            hasRealGps: hasRealGps,
          ),
          // Position centrale
          Container(
            width: size * 0.65,
            height: size * 0.65,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: Colors.white,
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withValues(alpha: 0.2),
                  blurRadius: 4,
                  offset: const Offset(0, 2),
                ),
              ],
              border: Border.all(color: color, width: 3),
            ),
            child: Center(
              child: Container(
                width: size * 0.3,
                height: size * 0.3,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: color,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _GpsPulseRing extends StatefulWidget {
  final Color color;
  final double size;
  final bool hasRealGps;

  const _GpsPulseRing({
    required this.color,
    required this.size,
    required this.hasRealGps,
  });

  @override
  State<_GpsPulseRing> createState() => _GpsPulseRingState();
}

class _GpsPulseRingState extends State<_GpsPulseRing>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;
  late final Animation<double> _scaleAnimation;
  late final Animation<double> _opacityAnimation;

  @override
  void initState() {
    super.initState();
    if (widget.hasRealGps) {
      _controller = AnimationController(
        duration: const Duration(milliseconds: 2000),
        vsync: this,
      )..repeat();

      _scaleAnimation = Tween<double>(begin: 0.6, end: 1.3).animate(
        CurvedAnimation(parent: _controller, curve: Curves.easeOut),
      );

      _opacityAnimation = Tween<double>(begin: 0.4, end: 0.0).animate(
        CurvedAnimation(parent: _controller, curve: Curves.easeOut),
      );
    }
  }

  @override
  void dispose() {
    if (widget.hasRealGps) _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (!widget.hasRealGps) return const SizedBox.shrink();

    return AnimatedBuilder(
      animation: _controller,
      builder: (context, child) {
        return Transform.scale(
          scale: _scaleAnimation.value,
          child: Opacity(
            opacity: _opacityAnimation.value,
            child: Container(
              width: widget.size,
              height: widget.size,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                border: Border.all(
                  color: widget.color.withValues(alpha: 0.5),
                  width: 2,
                ),
              ),
            ),
          ),
        );
      },
    );
  }
}