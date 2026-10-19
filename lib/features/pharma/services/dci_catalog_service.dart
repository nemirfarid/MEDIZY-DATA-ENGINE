/// Entrée du catalogue DCI national algérien.
class DciEntry {
  final String dci;
  final String therapeuticClass;
  final List<String> commercialBrands;
  final List<String> availableDosages;
  final List<String> availableForms;

  const DciEntry({
    required this.dci,
    required this.therapeuticClass,
    required this.commercialBrands,
    required this.availableDosages,
    required this.availableForms,
  });
}

/// Catalogue national des Dénominations Communes Internationales (DCI) pour l'Algérie.
class DciCatalogService {
  static const List<DciEntry> _catalog = [
    DciEntry(
      dci: 'Paracétamol',
      therapeuticClass: 'Antalgique / Antipyrétique',
      commercialBrands: ['Doliprane', 'Efferalgan', 'Panadol', 'Algidol', 'Para-Denk'],
      availableDosages: ['500 mg', '1 000 mg', '150 mg/5ml'],
      availableForms: ['Comprimé', 'Sachet', 'Sirop', 'Suppositoire'],
    ),
    DciEntry(
      dci: 'Amoxicilline',
      therapeuticClass: 'Antibiotique (Pénicilline)',
      commercialBrands: ['Amoxil', 'Clamoxyl', 'Hiconcil', 'Ospamox'],
      availableDosages: ['500 mg', '1 g', '250 mg/5ml'],
      availableForms: ['Gélule', 'Comprimé dispersible', 'Suspension buvable'],
    ),
    DciEntry(
      dci: 'Amoxicilline + Acide Clavulanique',
      therapeuticClass: 'Antibiotique à large spectre',
      commercialBrands: ['Augmentin', 'Curam', 'Klavox', 'Amoksiklav'],
      availableDosages: ['1 g/125 mg', '500 mg/62.5 mg', '100 mg/12.5 mg/ml'],
      availableForms: ['Comprimé', 'Poudre pour suspension', 'Injectable'],
    ),
    DciEntry(
      dci: 'Metformine',
      therapeuticClass: 'Antidiabétique oral',
      commercialBrands: ['Glucophage', 'Metfor', 'Diaformin', 'Stagid'],
      availableDosages: ['500 mg', '850 mg', '1 000 mg'],
      availableForms: ['Comprimé pelliculé'],
    ),
    DciEntry(
      dci: 'Atorvastatine',
      therapeuticClass: 'Hypolipémiant (Statine)',
      commercialBrands: ['Tahor', 'Lipitor', 'Ator', 'Cardyl'],
      availableDosages: ['10 mg', '20 mg', '40 mg', '80 mg'],
      availableForms: ['Comprimé'],
    ),
    DciEntry(
      dci: 'Acide Acétylsalicylique',
      therapeuticClass: 'Antiagrégant plaquettaire',
      commercialBrands: ['Kardegic', 'Aspirine Protect', 'Asasantin'],
      availableDosages: ['75 mg', '100 mg', '160 mg', '300 mg'],
      availableForms: ['Sachet', 'Comprimé'],
    ),
    DciEntry(
      dci: 'Oméprazole',
      therapeuticClass: 'Inhibiteur de la pompe à protons (IPP)',
      commercialBrands: ['Mopral', 'Zoltum', 'Gastrim', 'Omepra'],
      availableDosages: ['10 mg', '20 mg', '40 mg'],
      availableForms: ['Gélule gastro-résistante', 'Injectable'],
    ),
    DciEntry(
      dci: 'Salbutamol',
      therapeuticClass: 'Bronchodilatateur (Asthme)',
      commercialBrands: ['Ventoline', 'Asthalin', 'Salbair'],
      availableDosages: ['100 mcg/dose', '2 mg', '5 mg/ml'],
      availableForms: ['Aérosol doseur', 'Solution pour nébulisation', 'Sirop'],
    ),
    DciEntry(
      dci: 'Céfixime',
      therapeuticClass: 'Antibiotique (Céphalosporine 3G)',
      commercialBrands: ['Oroken', 'Cefix', 'Suprax', 'Denk-Cefix'],
      availableDosages: ['200 mg', '400 mg', '100 mg/5ml'],
      availableForms: ['Comprimé', 'Suspension buvable'],
    ),
    DciEntry(
      dci: 'Azithromycine',
      therapeuticClass: 'Antibiotique (Macrolide)',
      commercialBrands: ['Zithromax', 'Azix', 'Zitrocin', 'Macrozit'],
      availableDosages: ['250 mg', '500 mg', '200 mg/5ml'],
      availableForms: ['Comprimé', 'Suspension buvable'],
    ),
  ];

  List<DciEntry> get allEntries => List.unmodifiable(_catalog);

  /// Recherche par DCI ou par nom de marque commerciale
  List<DciEntry> search(String query) {
    if (query.trim().isEmpty) return [];
    final q = query.trim().toLowerCase();

    return _catalog.where((entry) {
      if (entry.dci.toLowerCase().contains(q)) return true;
      if (entry.therapeuticClass.toLowerCase().contains(q)) return true;
      return entry.commercialBrands.any((brand) => brand.toLowerCase().contains(q));
    }).toList();
  }

  /// Détecte la DCI correspondante à partir d'un nom de marque commerciale
  DciEntry? findByBrandName(String brandName) {
    final b = brandName.trim().toLowerCase();
    for (final entry in _catalog) {
      if (entry.commercialBrands.any((brand) => brand.toLowerCase() == b)) {
        return entry;
      }
    }
    return null;
  }
}
