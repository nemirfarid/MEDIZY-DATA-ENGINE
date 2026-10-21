/// Référentiel officiel des 58 Wilayas d'Algérie avec coordonnées GPS des chefs-lieux
class WilayaInfo {
  final String code;
  final String name;
  final String arabicName;
  final double lat;
  final double lon;

  const WilayaInfo({
    required this.code,
    required this.name,
    required this.arabicName,
    required this.lat,
    required this.lon,
  });

  String get displayName => '$code - $name';

  static const List<WilayaInfo> allWilayas = [
    WilayaInfo(code: '01', name: 'Adrar', arabicName: 'أدرار', lat: 27.8742, lon: -0.2939),
    WilayaInfo(code: '02', name: 'Chlef', arabicName: 'الشلف', lat: 36.1652, lon: 1.3345),
    WilayaInfo(code: '03', name: 'Laghouat', arabicName: 'الأغواط', lat: 33.8000, lon: 2.8651),
    WilayaInfo(code: '04', name: 'Oum El Bouaghi', arabicName: 'أم البواقي', lat: 35.8755, lon: 7.1135),
    WilayaInfo(code: '05', name: 'Batna', arabicName: 'باتنة', lat: 35.5558, lon: 6.1741),
    WilayaInfo(code: '06', name: 'Béjaïa', arabicName: 'بجاية', lat: 36.7559, lon: 5.0843),
    WilayaInfo(code: '07', name: 'Biskra', arabicName: 'بسكرة', lat: 34.8504, lon: 5.7281),
    WilayaInfo(code: '08', name: 'Béchar', arabicName: 'بشار', lat: 31.6167, lon: -2.2167),
    WilayaInfo(code: '09', name: 'Blida', arabicName: 'البليدة', lat: 36.4700, lon: 2.8300),
    WilayaInfo(code: '10', name: 'Bouira', arabicName: 'البويرة', lat: 36.3749, lon: 3.9020),
    WilayaInfo(code: '11', name: 'Tamanrasset', arabicName: 'تمنراست', lat: 22.7850, lon: 5.5228),
    WilayaInfo(code: '12', name: 'Tébessa', arabicName: 'تبسة', lat: 35.4042, lon: 8.1242),
    WilayaInfo(code: '13', name: 'Tlemcen', arabicName: 'تلمسان', lat: 34.8828, lon: -1.3167),
    WilayaInfo(code: '14', name: 'Tiaret', arabicName: 'تيارت', lat: 35.3710, lon: 1.3170),
    WilayaInfo(code: '15', name: 'Tizi Ouzou', arabicName: 'تيزي وزو', lat: 36.7118, lon: 4.0459),
    WilayaInfo(code: '16', name: 'Alger', arabicName: 'الجزائر', lat: 36.7538, lon: 3.0588),
    WilayaInfo(code: '17', name: 'Djelfa', arabicName: 'الجلفة', lat: 34.6728, lon: 3.2630),
    WilayaInfo(code: '18', name: 'Jijel', arabicName: 'جيجل', lat: 36.8206, lon: 5.7667),
    WilayaInfo(code: '19', name: 'Sétif', arabicName: 'سطيف', lat: 36.1911, lon: 5.4137),
    WilayaInfo(code: '20', name: 'Saïda', arabicName: 'سعيدة', lat: 34.8303, lon: 0.1517),
    WilayaInfo(code: '21', name: 'Skikda', arabicName: 'سكيكدة', lat: 36.8792, lon: 6.9075),
    WilayaInfo(code: '22', name: 'Sidi Bel Abbès', arabicName: 'سيدي بلعباس', lat: 35.1899, lon: -0.6309),
    WilayaInfo(code: '23', name: 'Annaba', arabicName: 'عنابة', lat: 36.9000, lon: 7.7667),
    WilayaInfo(code: '24', name: 'Guelma', arabicName: 'قالمة', lat: 36.4621, lon: 7.4261),
    WilayaInfo(code: '25', name: 'Constantine', arabicName: 'قسنطينة', lat: 36.3650, lon: 6.6147),
    WilayaInfo(code: '26', name: 'Médéa', arabicName: 'المدية', lat: 36.2642, lon: 2.7539),
    WilayaInfo(code: '27', name: 'Mostaganem', arabicName: 'مستغانم', lat: 35.9311, lon: 0.0892),
    WilayaInfo(code: '28', name: 'M\'Sila', arabicName: 'المسيلة', lat: 35.7058, lon: 4.5419),
    WilayaInfo(code: '29', name: 'Mascara', arabicName: 'معسكر', lat: 35.3964, lon: 0.1403),
    WilayaInfo(code: '30', name: 'Ouargla', arabicName: 'ورقلة', lat: 31.9493, lon: 5.3250),
    WilayaInfo(code: '31', name: 'Oran', arabicName: 'وهران', lat: 35.6971, lon: -0.6308),
    WilayaInfo(code: '32', name: 'El Bayadh', arabicName: 'البيض', lat: 33.6832, lon: 1.0193),
    WilayaInfo(code: '33', name: 'Illizi', arabicName: 'إليزي', lat: 26.4833, lon: 8.4667),
    WilayaInfo(code: '34', name: 'Bordj Bou Arreridj', arabicName: 'برج بوعريريج', lat: 36.0732, lon: 4.7611),
    WilayaInfo(code: '35', name: 'Boumerdès', arabicName: 'بومرداس', lat: 36.7664, lon: 3.4772),
    WilayaInfo(code: '36', name: 'El Tarf', arabicName: 'الطارف', lat: 36.7672, lon: 8.3138),
    WilayaInfo(code: '37', name: 'Tindouf', arabicName: 'تندوف', lat: 27.6711, lon: -8.1474),
    WilayaInfo(code: '38', name: 'Tissemsilt', arabicName: 'تيسمسيلت', lat: 35.6072, lon: 1.8108),
    WilayaInfo(code: '39', name: 'El Oued', arabicName: 'الوادي', lat: 33.3683, lon: 6.8675),
    WilayaInfo(code: '40', name: 'Khenchela', arabicName: 'خنشلة', lat: 35.4358, lon: 7.1433),
    WilayaInfo(code: '41', name: 'Souk Ahras', arabicName: 'سوق أهراس', lat: 36.2864, lon: 7.9511),
    WilayaInfo(code: '42', name: 'Tipaza', arabicName: 'تيبازة', lat: 36.5897, lon: 2.4475),
    WilayaInfo(code: '43', name: 'Mila', arabicName: 'ميلة', lat: 36.4503, lon: 6.2644),
    WilayaInfo(code: '44', name: 'Aïn Defla', arabicName: 'عين الدفلى', lat: 36.2644, lon: 1.9675),
    WilayaInfo(code: '45', name: 'Naâma', arabicName: 'النعامة', lat: 33.2667, lon: -0.3167),
    WilayaInfo(code: '46', name: 'Aïn Témouchent', arabicName: 'عين تموشنت', lat: 35.2975, lon: -1.1403),
    WilayaInfo(code: '47', name: 'Ghardaïa', arabicName: 'غرداية', lat: 32.4909, lon: 3.6736),
    WilayaInfo(code: '48', name: 'Relizane', arabicName: 'غليزان', lat: 35.7372, lon: 0.5558),
    WilayaInfo(code: '49', name: 'Timimoun', arabicName: 'تيميمون', lat: 29.2639, lon: 0.2310),
    WilayaInfo(code: '50', name: 'Bordj Badji Mokhtar', arabicName: 'برج باجي مختار', lat: 21.3283, lon: 0.9547),
    WilayaInfo(code: '51', name: 'Ouled Djellal', arabicName: 'أولاد جلال', lat: 34.4278, lon: 5.0667),
    WilayaInfo(code: '52', name: 'Béni Abbès', arabicName: 'بني عباس', lat: 30.1333, lon: -2.1667),
    WilayaInfo(code: '53', name: 'In Salah', arabicName: 'عين صالح', lat: 27.1936, lon: 2.4608),
    WilayaInfo(code: '54', name: 'In Guezzam', arabicName: 'عين قزام', lat: 19.5667, lon: 5.7667),
    WilayaInfo(code: '55', name: 'Touggourt', arabicName: 'تقرت', lat: 33.1053, lon: 6.0578),
    WilayaInfo(code: '56', name: 'Djanet', arabicName: 'جانت', lat: 24.5531, lon: 9.4853),
    WilayaInfo(code: '57', name: 'El M\'Ghair', arabicName: 'المغير', lat: 33.9500, lon: 5.9167),
    WilayaInfo(code: '58', name: 'El Meniaa', arabicName: 'المنيعة', lat: 30.5847, lon: 2.8797),
  ];

  static WilayaInfo? findByCode(String? code) {
    if (code == null) return null;
    final cleanCode = code.padLeft(2, '0');
    try {
      return allWilayas.firstWhere((w) => w.code == cleanCode);
    } catch (_) {
      return null;
    }
  }
}
