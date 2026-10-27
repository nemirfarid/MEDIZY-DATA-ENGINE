/// Utilitaire de formatage et de génération de liens WhatsApp pour les pharmacies et cliniques d'Algérie.
class WhatsAppUtils {
  /// Message d'ouverture standard bilingue Darija algérienne / Français
  static const String defaultInquiryMessage =
      "السلام عليكم، هل هذا الدواء متوفر لديكم؟ / Bonjour, ce médicament est-il disponible dans votre officine ?";

  /// Vérifie si un numéro de téléphone donné correspond à un mobile algérien (Djezzy 07, Ooredoo 05, Mobilis 06)
  /// Accepte les formats locaux (05, 06, 07) et internationaux (+213, 00213, 213).
  static bool isAlgerianMobile(String? phone) {
    if (phone == null || phone.trim().isEmpty) return false;
    final cleaned = phone.replaceAll(RegExp(r'[^0-9+]'), '');

    // Numéros mobiles locaux algériens à 10 chiffres (05xx, 06xx, 07xx)
    if (RegExp(r'^0[567][0-9]{8}$').hasMatch(cleaned)) {
      return true;
    }

    // Format international (+213 ou 00213 ou 213 suivi de 5, 6 ou 7 et 8 chiffres)
    if (RegExp(r'^(\+213|00213|213)[567][0-9]{8}$').hasMatch(cleaned)) {
      return true;
    }

    // Format international avec zéro résiduel (+21305..., 0021305..., 21305...)
    if (RegExp(r'^(\+213|00213|213)0[567][0-9]{8}$').hasMatch(cleaned)) {
      return true;
    }

    // Format court à 9 chiffres sans indicatif ni zéro initial (ex: 550123456)
    if (RegExp(r'^[567][0-9]{8}$').hasMatch(cleaned)) {
      return true;
    }

    return false;
  }

  /// Formate le numéro pour l'API WhatsApp wa.me.
  /// Le format requis est l'indicatif international sans le signe '+' ni le '0' initial (ex: 213550123456).
  static String? formatForWhatsApp(String? phone) {
    if (phone == null || phone.trim().isEmpty) return null;
    final cleaned = phone.replaceAll(RegExp(r'[^0-9+]'), '');

    // Cas 1 : Format local 05/06/07 (ex: 0550123456)
    final localMatch = RegExp(r'^0([567][0-9]{8})$').firstMatch(cleaned);
    if (localMatch != null) {
      return '213${localMatch.group(1)}';
    }

    // Cas 2 : Format international +213 ou 00213 (ex: +213550123456 ou +2130550123456)
    if (cleaned.startsWith('+213') || cleaned.startsWith('00213')) {
      final prefixLen = cleaned.startsWith('+213') ? 4 : 5;
      var rest = cleaned.substring(prefixLen);
      if (rest.startsWith('0')) {
        rest = rest.substring(1);
      }
      if (RegExp(r'^[567][0-9]{8}$').hasMatch(rest)) {
        return '213$rest';
      }
      // Tolérance pour numéros fixes convertis si nécessaires
      if (RegExp(r'^[1-9][0-9]{7,8}$').hasMatch(rest)) {
        return '213$rest';
      }
    }

    // Cas 3 : Format 213 sans '+' (ex: 213550123456 ou 2130550123456)
    if (cleaned.startsWith('213')) {
      var rest = cleaned.substring(3);
      if (rest.startsWith('0')) {
        rest = rest.substring(1);
      }
      if (RegExp(r'^[567][0-9]{8}$').hasMatch(rest)) {
        return '213$rest';
      }
      if (RegExp(r'^[1-9][0-9]{7,8}$').hasMatch(rest)) {
        return '213$rest';
      }
    }

    // Cas 4 : 9 chiffres directs commençant par 5, 6 ou 7
    if (RegExp(r'^[567][0-9]{8}$').hasMatch(cleaned)) {
      return '213$cleaned';
    }

    // Cas 5 : Numéro fixe avec 0 initial (ex: 021 73 11 22) formaté au cas où une officine a WhatsApp Business fixe
    final fixMatch = RegExp(r'^0([1-9][0-9]{7,8})$').firstMatch(cleaned);
    if (fixMatch != null) {
      return '213${fixMatch.group(1)}';
    }

    return null;
  }

  /// Génère l'URL officielle `https://wa.me/213XXXXXXXXX?text=...`
  /// Intègre le message d'ouverture bilingue et la mention optionnelle du médicament recherché.
  static String? generateWhatsAppUrl({
    required String? phone,
    String? medicationName,
    String? customMessage,
    bool attachPrescriptionNote = true,
  }) {
    final formattedNumber = formatForWhatsApp(phone);
    if (formattedNumber == null) return null;

    String text;
    if (customMessage != null && customMessage.trim().isNotEmpty) {
      text = customMessage.trim();
    } else if (medicationName != null && medicationName.trim().isNotEmpty) {
      text = "السلام عليكم، هل دواء ($medicationName) متوفر لديكم في الصيدلية؟ / Bonjour, le médicament ($medicationName) est-il disponible dans votre officine ?";
      if (attachPrescriptionNote) {
        text += "\n(Je vous joins la photo de mon ordonnance ci-dessous / أرفق لكم صورة الوصفة الطبية)";
      }
    } else {
      text = defaultInquiryMessage;
      if (attachPrescriptionNote) {
        text += "\n(Je vous joins la photo de mon ordonnance ci-dessous / أرفق لكم صورة الوصفة الطبية)";
      }
    }

    final encodedText = Uri.encodeComponent(text);
    return 'https://wa.me/$formattedNumber?text=$encodedText';
  }
}
