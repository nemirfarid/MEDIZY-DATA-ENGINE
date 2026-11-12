/// Système global de localisation et traduction intégrale Français / Arabe pour Medizy
/// Gère les traductions "mot à mot", les abréviations, et le support RTL pour l'interface Premium.
import 'package:flutter/material.dart';

class MedizyLocale {
  static bool isArabic = false;

  /// Change la langue et notifie les listeners
  static void setArabic(bool value) {
    isArabic = value;
    // TODO: Notify listeners via ChangeNotifier or Riverpod
  }

  /// Bascule entre FR et AR
  static void toggleLanguage() {
    isArabic = !isArabic;
  }

  /// Traduction simple FR/AR
  static String t(String fr, String ar) {
    return isArabic ? ar : fr;
  }

  /// Direction du texte selon la langue
  static TextDirection get textDirection => isArabic ? TextDirection.rtl : TextDirection.ltr;

  /// Alignement selon la langue
  static Alignment get startAlignment => isArabic ? Alignment.centerRight : Alignment.centerLeft;
  static Alignment get endAlignment => isArabic ? Alignment.centerLeft : Alignment.centerRight;

  /// Padding horizontal adaptatif (start/end)
  static EdgeInsets horizontalPadding(double padding) =>
      isArabic ? EdgeInsets.only(right: padding) : EdgeInsets.only(left: padding);
  static EdgeInsets horizontalPaddingSym(double padding) => EdgeInsets.symmetric(horizontal: padding);

  // ============================================
  // DICTIONNAIRE UI COMPLET — MOT À MOT
  // ============================================
  static final Map<String, String> uiLabels = {
    // Écran d'accueil
    'Annuaire Sanitaire National': 'الدليل الصحي الوطني',
    'Sélectionnez une catégorie pour consulter la carte': 'اختر تخصصاً لاستعراض الخريطة',
    'SOS Urgences 24/7': 'طوارئ صحية 24/7',
    'Près de moi': 'بالقرب مني',
    'Rechercher': 'بحث',
    'Catégories': 'التخصصات',
    'Toutes les catégories': 'جميع التخصصات',
    'Structures de santé': 'هياكل صحية',
    'Aucune structure trouvée': 'لم يتم العثور على هياكل',
    'Chargement...': 'جاري التحميل...',

    // Carte
    'Itinéraire Google Maps': 'مسار خرائط جوجل',
    'Appeler': 'اتصال',
    'WhatsApp': 'واتساب',
    'Guidage': 'توجيه',
    'Partager': 'مشاركة',
    'Ajouter aux favoris': 'إضافة للمفضلة',
    'Retirer des favoris': 'إزالة من المفضلة',
    'Signaler une anomalie': 'الإبلاغ عن خطأ',
    'Détails': 'التفاصيل',
    'Fermer': 'إغلاق',
    'Voir sur la carte': 'عرض على الخريطة',

    // Filtres
    'Wilaya': 'الولاية',
    'Commune': 'البلدية',
    'Catégorie': 'التخصص / الفئة',
    'Urgences & Garde': 'استعجالات ومناوبات',
    'Urgences & Garde 24/7': 'طوارئ ومناوبة 24/7',
    'Conventionné Chifa': 'مؤمن بطاقة الشفاء',
    'Mes favoris': 'مفضلاتي',
    'Réinitialiser': 'إعادة تعيين',
    'Tout le pays': 'كل الجزائر',
    'Toutes communes': 'كل البلديات',
    'Toutes catégories': 'جميع التخصصات',
    'Filtres actifs': 'مرشحات نشطة',
    'Effacer les filtres': 'مسح المرشحات',

    // Wilayas (noms)
    'Adrar': 'أدرار',
    'Chlef': 'الشلف',
    'Laghouat': 'الأغواط',
    'Oum El Bouaghi': 'أم البواقي',
    'Batna': 'باتنة',
    'Béjaïa': 'بجاية',
    'Biskra': 'بسكرة',
    'Béchar': 'بشار',
    'Blida': 'البليدة',
    'Bouira': 'البويرة',
    'Tamanrasset': 'تمنراست',
    'Tébessa': 'تبسة',
    'Tlemcen': 'تلمسان',
    'Tiaret': 'تيارت',
    'Tizi Ouzou': 'تيزي وزو',
    'Alger': 'الجزائر',
    'Djelfa': 'الجلفة',
    'Jijel': 'جيجل',
    'Sétif': 'سطيف',
    'Saïda': 'سعيدة',
    'Skikda': 'سكيكدة',
    'Sidi Bel Abbès': 'سيدي بلعباس',
    'Annaba': 'عنابة',
    'Guelma': 'قالمة',
    'Constantine': 'قسنطينة',
    'Médéa': 'المدية',
    'Mostaganem': 'مستغانم',
    'M\'Sila': 'المسيلة',
    'Mascara': 'معسكر',
    'Ouargla': 'ورقلة',
    'Oran': 'وهران',
    'El Bayadh': 'البيض',
    'Illizi': 'إليزي',
    'Bordj Bou Arreridj': 'برج بوعريريج',
    'Boumerdès': 'بومرداس',
    'El Tarf': 'الطارف',
    'Tindouf': 'تندوف',
    'Tissemsilt': 'تيسمسيلت',
    'El Oued': 'الوادي',
    'Khenchela': 'خنشلة',
    'Souk Ahras': 'سوق أهراس',
    'Tipaza': 'تيبازة',
    'Mila': 'ميلة',
    'Aïn Defla': 'عين الدفلى',
    'Naâma': 'النعام',
    'Aïn Témouchent': 'عين تموشنت',
    'Ghardaïa': 'غرداية',
    'Relizane': 'غليزان',

    // Fiche détail
    'Carnet médical local': 'دفتر طبي محلي',
    'Note privée': 'ملاحظة خاصة',
    'Enregistrer la note': 'حفظ الملاحظة',
    'Téléphone': 'الهاتف',
    'Adresse': 'العنوان',
    'Horaires': 'أوقات العمل',
    'Spécialité': 'التخصص',
    'Type': 'النوع',
    'Wilaya détectée': 'تم تحديد الولاية',
    'fiches à proximité': 'هياكل قريبة',
    'WGS84': 'إحداثيات',
    'Itinéraire': 'المسار',
    'Copier': 'نسخ',
    'Copier le numéro': 'نسخ الرقم',
    'Copier l\'adresse': 'نسخ العنوان',
    'Ajouté aux favoris': 'تمت الإضافة للمفضلة',
    'Retiré des favoris': 'تم الحذف من المفضلة',
    'Urgence / Garde': 'استعجالات / مناوبة',
    'CHIFA': 'شفاء',
    'DCI ACTIVE': 'المادة الفعالة',
    'Labo': 'مخبر',

    // Recherche
    'Rechercher médecin, pharmacie, clinique...': 'ابحث عن طبيب، صيدلية، عيادة...',
    'Rechercher une commune...': 'ابحث عن بلدية...',
    'Aucun résultat': 'لا توجد نتائج',
    'Résultats trouvés': 'نتائج تم العثور عليها',

    // SOS
    'SOS Urgences': 'طوارئ صحية',
    'Appeler le SAMU': 'الاتصال بـ SAMU',
    'Numéros d\'urgence': 'أرقام الطوارئ',
    'Gardes de nuit': 'مناوبات ليلية',
    'Pharmacies de garde': 'صيدليات المناوبة',

    // Paramètres
    'Langue': 'اللغة',
    'Français': 'فرنسية',
    'Arabe': 'عربية',
    'Thème': 'المظهر',
    'Clair': 'فاتح',
    'Sombre': 'مظلم',
    'À propos': 'حول التطبيق',
    'Version': 'الإصدار',
    'Conditions d\'utilisation': 'شروط الاستخدام',
    'Politique de confidentialité': 'سياسة الخصوصية',
    'Contact': 'اتصل بنا',

    // Divers
    'OK': 'موافق',
    'Annuler': 'إلغاء',
    'Confirmer': 'تأكيد',
    'Supprimer': 'حذف',
    'Modifier': 'تعديل',
    'Enregistrer': 'حفظ',
    'Oui': 'نعم',
    'Non': 'لا',
  };

  // ============================================
  // CATÉGORIES SANTÉ — TRADUCTION MOT À MOT
  // ============================================
  static final Map<String, String> categoryArabic = {
    // Catégories principales (base de données)
    'Établissement Public': 'مؤسسة عمومية',
    'Clinique Privée': 'عيادة خاصة',
    "Pharmacie d'Officine": 'صيدلية',
    'Médecine Générale': 'طب عام',
    'Médecine Spécialisée': 'طب متخصص',
    "Laboratoire d'analyses": 'مخبر تحاليل',
    "Centre d'Imagerie": 'مركز تصوير',
    'Chirurgie Dentaire': 'جراحة أسنان',
    'Paramédical & Rééducation': 'طب مساعد وإعادة تأهيل',

    // Spécialités détaillées (slugs)
    'généraliste': 'طبيب عام',
    'dentiste': 'طبيب أسنان',
    'pédiatre': 'طبيب أطفال',
    'pharmacie': 'صيدلية',
    'clinique': 'عيادة / مستشفى',
    'laboratoire': 'مخبر تحاليل',
    'cardiologue': 'طبيب قلب',
    'imagerie': 'أشعة وتصوير',
    'gynécologue': 'طبيبة نساء',
    'ophtalmologue': 'طبيب عيون',
    'urgences': 'استعجالات',
    'chirurgien': 'جراح متخصص',
    'psychiatre': 'طبيب نفسي',
    'dermatologue': 'طبيب جلد',
    'orl': 'أنف وأذن وحنجرة',
    'rhumatologue': 'طبيب مفاصل',
    'pneumologue': 'طبيب صدر',
    'kinésithérapeute': 'أخصائي علاج طبيعي',
    'urologue': 'طبيب كلى',
    'néphrologue': 'طبيب كلى',
    'gastro-entérologue': 'طبيب جهاز هضمي',
    'neurologue': 'طبيب أعصاب',
    'endocrinologue': 'طبيب غدد صماء',
    'oncologue': 'طبيب أورام',
    'hématologue': 'طبيب دم',
    'infectiologue': 'طبيب أمراض معدية',
    'allergologue': 'طبيب حساسية',
    'gériatre': 'طبيب مسنين',
    'médecine du travail': 'طب العمل',
    'médecine légale': 'طب شرعي',
    'radiologue': 'طبيب أشعة',
    'anesthésiste': 'طبيب تخدير',
    'réanimateur': 'طبيب إنعاش',
    'chirurgien général': 'جراح عام',
    'chirurgien cardiaque': 'جراح قلب',
    'chirurgien orthopédique': 'جراح عظام',
    'chirurgien plasticien': 'جراح تجميل',
    'chirurgien vasculaire': 'جراح أوعية',
    'chirurgien digestif': 'جراح جهاز هضمي',
    'chirurgien urologique': 'جراح مسالك',
    'chirurgien maxillo-facial': 'جراح فكين',
    'chirurgien thoracique': 'جراح صدر',
    'chirurgien pédiatrique': 'جراح أطفال',
    'ophtalmologiste': 'طبيب عيون',
    'orl (oto-rhino-laryngologiste)': 'أنف وأذن وحنجرة',
    'stomatologue': 'طبيب فم وأسنان',
    'orthodontiste': 'تقويم أسنان',
    'parodontologue': 'طبيب لثة',
    'sage-femme': 'قابلة',
    'infirmier': 'ممرض',
    'orthophoniste': 'أخصائي نطق',
    'orthoptiste': 'أخصائي تقويم بصر',
    'podologue': 'أخصائي قدم',
    'diététicien': 'أخصائي تغذية',
    'psychologue': 'أخصائي نفسي',
    'psychomotricien': 'أخصائي حركية نفسية',
    'ergothérapeute': 'أخصائي علاج وظيفي',
    'audioprothésiste': 'أخصائي سمعيات',
    'opticienne': 'أخصائي بصريات',
    'pharmacien': 'صيدلي',
    'préparateur en pharmacie': 'مساعد صيدلي',
    'manipulateur radio': 'مناور أشعة',
    'technicien de laboratoire': 'تقني مخبر',
    'ambulancier': 'مسعف',
    'brancardier': 'حامل مرضى',
    'agent de service hospitalier': 'عامل خدمات مستشفى',
  };

  // ============================================
  // ABRÉVIATIONS ARABE — POUR BOUTONS ACCUEIL
  // ============================================
  static final Map<String, String> categoryAbbrArabic = {
    'Établissement Public': 'مؤسسة',
    'Clinique Privée': 'عيادة',
    "Pharmacie d'Officine": 'صيدلية',
    'Médecine Générale': 'طب عام',
    'Médecine Spécialisée': 'تخصصي',
    "Laboratoire d'analyses": 'مخبر',
    "Centre d'Imagerie": 'تصوير',
    'Chirurgie Dentaire': 'أسنان',
    'Paramédical & Rééducation': 'إعادة تأهيل',

    // Slugs
    'généraliste': 'عام',
    'dentiste': 'أسنان',
    'pédiatre': 'أطفال',
    'pharmacie': 'صيدلية',
    'clinique': 'عيادة',
    'laboratoire': 'مخبر',
    'cardiologue': 'قلب',
    'imagerie': 'أشعة',
    'gynécologue': 'نساء',
    'ophtalmologue': 'عيون',
    'urgences': 'طوارئ',
    'chirurgien': 'جراح',
    'psychiatre': 'نفسي',
    'dermatologue': 'جلد',
    'orl': 'أذن',
    'rhumatologue': 'مفاصل',
    'pneumologue': 'صدر',
    'kinésithérapeute': 'علاج طبيعي',
    'urologue': 'كلى',
    'néphrologue': 'كلى',
    'gastro-entérologue': 'هضمي',
    'neurologue': 'أعصاب',
    'endocrinologue': 'غدد',
    'oncologue': 'أورام',
    'hématologue': 'دم',
    'infectiologue': 'معدية',
    'allergologue': 'حساسية',
    'gériatre': 'مسنين',
    'radiologue': 'أشعة',
    'anesthésiste': 'تخدير',
    'réanimateur': 'إنعاش',
    'sage-femme': 'قابلة',
    'infirmier': 'ممرض',
    'orthophoniste': 'نطق',
    'orthoptiste': 'بصر',
    'podologue': 'قدم',
    'diététicien': 'تغذية',
    'psychologue': 'نفسي',
    'psychomotricien': 'حركية',
    'ergothérapeute': 'وظيفي',
    'audioprothésiste': 'سمعيات',
    'opticienne': 'بصريات',
    'pharmacien': 'صيدلي',
    'manipulateur radio': 'أشعة',
    'technicien de laboratoire': 'مخبر',
    'ambulancier': 'إسعاف',
    'brancardier': 'نقل',
    'agent de service hospitalier': 'خدمات',
  };

  // ============================================
  // WILAYAS — NOM ARABE (pour sélecteur)
  // ============================================
  static final Map<String, String> wilayaArabic = {
    '01': 'أدرار',
    '02': 'الشلف',
    '03': 'الأغواط',
    '04': 'أم البواقي',
    '05': 'باتنة',
    '06': 'بجاية',
    '07': 'بسكرة',
    '08': 'بشار',
    '09': 'البليدة',
    '10': 'البويرة',
    '11': 'تمنراست',
    '12': 'تبسة',
    '13': 'تلمسان',
    '14': 'تيارت',
    '15': 'تيزي وزو',
    '16': 'الجزائر',
    '17': 'الجلفة',
    '18': 'جيجل',
    '19': 'سطيف',
    '20': 'سعيدة',
    '21': 'سكيكدة',
    '22': 'سيدي بلعباس',
    '23': 'عنابة',
    '24': 'قالمة',
    '25': 'قسنطينة',
    '26': 'المدية',
    '27': 'مستغانم',
    '28': 'المسيلة',
    '29': 'معسكر',
    '30': 'ورقلة',
    '31': 'وهران',
    '32': 'البيض',
    '33': 'إليزي',
    '34': 'برج بوعريريج',
    '35': 'بومرداس',
    '36': 'الطارف',
    '37': 'تندوف',
    '38': 'تيسمسيلت',
    '39': 'الوادي',
    '40': 'خنشلة',
    '41': 'سوق أهراس',
    '42': 'تيبازة',
    '43': 'ميلة',
    '44': 'عين الدفلى',
    '45': 'النعام',
    '46': 'عين تموشنت',
    '47': 'غرداية',
    '48': 'غليزان',
    // Nouvelles wilayas (49-58)
    '49': 'تيميمون',
    '50': 'برج باجي مختار',
    '51': 'أولاد جلال',
    '52': 'بني عباس',
    '53': 'إين قزام',
    '54': 'تقرت',
    '55': 'المغير',
    '56': 'المنيعة',
    '57': 'ajanet', // Janet
    '58': 'المدية', // El M'Ghair - à vérifier
  };

  // ============================================
  // MÉTHODES DE TRADUCTION
  // ============================================

  /// Traduit une clé UI
  static String translateUI(String key) {
    if (!isArabic) return key;
    return uiLabels[key] ?? key;
  }

  /// Traduit une catégorie (nom complet ou slug)
  static String translateCategory(String cat, {bool useAbbr = false}) {
    if (!isArabic) return cat;
    final lower = cat.trim().toLowerCase();
    final dict = useAbbr ? categoryAbbrArabic : categoryArabic;

    // Recherche exacte d'abord
    if (dict.containsKey(cat)) return dict[cat]!;
    if (dict.containsKey(lower)) return dict[lower]!;

    // Recherche partielle (contient)
    for (final entry in dict.entries) {
      if (lower.contains(entry.key.toLowerCase())) {
        return entry.value;
      }
    }
    return cat;
  }

  /// Traduit un nom de wilaya par son code
  static String translateWilaya(String code) {
    if (!isArabic) return code;
    return wilayaArabic[code] ?? code;
  }

  /// Traduit une commune (utilise la base de données)
  static String translateCommune(String communeFr, String? communeAr) {
    if (!isArabic) return communeFr;
    return communeAr ?? communeFr;
  }

  /// Formate un nombre avec séparateurs selon la locale
  static String formatNumber(int number) {
    if (!isArabic) {
      return number.toString().replaceAllMapped(
        RegExp(r'(\d{1,3})(?=(\d{3})+(?!\d))'),
        (Match m) => '${m[1]} ',
      );
    }
    // Chiffres arabes
    const arabicDigits = ['٠', '١', '٢', '٣', '٤', '٥', '٦', '٧', '٨', '٩'];
    return number.toString().split('').map((d) => arabicDigits[int.parse(d)]).join('');
  }

  /// Obtient le nom affiché pour une catégorie (avec abbréviation si nécessaire)
  static String getCategoryDisplayName(String category, {bool useAbbr = false, int maxLength = 20}) {
    final translated = translateCategory(category, useAbbr: useAbbr);
    if (translated.length <= maxLength) return translated;
    // Tronquer avec ellipsis
    return '${translated.substring(0, maxLength - 1)}…';
  }
}
