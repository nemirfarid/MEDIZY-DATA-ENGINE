import 'dart:io';
import 'package:sqlite3/sqlite3.dart';
import '../models/dz_medication.dart';

/// Service local ultra-rapide de gestion et recherche des médicaments et génériques algériens (DCI).
/// Fonctionne 100 % hors-ligne avec indexation plein texte FTS5 SQLite.
class DzMedicationService {
  Database? _db;
  bool _ownsDb = false;
  bool _isInitialized = false;

  bool get isInitialized => _isInitialized;

  /// Données initiales de référence pour la pharmacopée algérienne (Princeps et Génériques locaux)
  static const List<Map<String, dynamic>> initialMedications = [
    // --- 1. PARACÉTAMOL ---
    {
      'nom_commercial': 'Doliprane',
      'dci': 'Paracétamol',
      'dosage': '1 000 mg',
      'forme': 'Comprimé',
      'laboratoire': 'Sanofi',
      'remboursable_chifa': 1,
      'prix_dzd': 180.0,
      'is_princeps': 1,
    },
    {
      'nom_commercial': 'Doliprane',
      'dci': 'Paracétamol',
      'dosage': '500 mg',
      'forme': 'Comprimé',
      'laboratoire': 'Sanofi',
      'remboursable_chifa': 1,
      'prix_dzd': 120.0,
      'is_princeps': 1,
    },
    {
      'nom_commercial': 'Paracétamol Saidal',
      'dci': 'Paracétamol',
      'dosage': '1 000 mg',
      'forme': 'Comprimé',
      'laboratoire': 'Saidal',
      'remboursable_chifa': 1,
      'prix_dzd': 130.0,
      'is_princeps': 0,
    },
    {
      'nom_commercial': 'Paracétamol Saidal',
      'dci': 'Paracétamol',
      'dosage': '500 mg',
      'forme': 'Comprimé',
      'laboratoire': 'Saidal',
      'remboursable_chifa': 1,
      'prix_dzd': 90.0,
      'is_princeps': 0,
    },
    {
      'nom_commercial': 'Efferalgan',
      'dci': 'Paracétamol',
      'dosage': '1 000 mg',
      'forme': 'Comprimé effervescent',
      'laboratoire': 'UPSA',
      'remboursable_chifa': 1,
      'prix_dzd': 210.0,
      'is_princeps': 1,
    },
    {
      'nom_commercial': 'Panadol',
      'dci': 'Paracétamol',
      'dosage': '500 mg',
      'forme': 'Comprimé',
      'laboratoire': 'GSK',
      'remboursable_chifa': 1,
      'prix_dzd': 150.0,
      'is_princeps': 0,
    },
    {
      'nom_commercial': 'Algidol',
      'dci': 'Paracétamol',
      'dosage': '1 000 mg',
      'forme': 'Comprimé',
      'laboratoire': 'Biopharm',
      'remboursable_chifa': 1,
      'prix_dzd': 140.0,
      'is_princeps': 0,
    },
    {
      'nom_commercial': 'Para-Denk',
      'dci': 'Paracétamol',
      'dosage': '500 mg',
      'forme': 'Comprimé',
      'laboratoire': 'Denk Pharma',
      'remboursable_chifa': 1,
      'prix_dzd': 145.0,
      'is_princeps': 0,
    },

    // --- 2. AMOXICILLINE + ACIDE CLAVULANIQUE ---
    {
      'nom_commercial': 'Augmentin',
      'dci': 'Amoxicilline + Acide Clavulanique',
      'dosage': '1 g/125 mg',
      'forme': 'Comprimé pelliculé',
      'laboratoire': 'GSK',
      'remboursable_chifa': 1,
      'prix_dzd': 720.0,
      'is_princeps': 1,
    },
    {
      'nom_commercial': 'Augmentin',
      'dci': 'Amoxicilline + Acide Clavulanique',
      'dosage': '500 mg/62.5 mg',
      'forme': 'Comprimé',
      'laboratoire': 'GSK',
      'remboursable_chifa': 1,
      'prix_dzd': 480.0,
      'is_princeps': 1,
    },
    {
      'nom_commercial': 'Klavox',
      'dci': 'Amoxicilline + Acide Clavulanique',
      'dosage': '1 g/125 mg',
      'forme': 'Comprimé',
      'laboratoire': 'Hikma',
      'remboursable_chifa': 1,
      'prix_dzd': 580.0,
      'is_princeps': 0,
    },
    {
      'nom_commercial': 'Curam',
      'dci': 'Amoxicilline + Acide Clavulanique',
      'dosage': '1 g/125 mg',
      'forme': 'Comprimé dispersible',
      'laboratoire': 'Sandoz',
      'remboursable_chifa': 1,
      'prix_dzd': 610.0,
      'is_princeps': 0,
    },
    {
      'nom_commercial': 'Amoksiklav',
      'dci': 'Amoxicilline + Acide Clavulanique',
      'dosage': '1 g/125 mg',
      'forme': 'Comprimé',
      'laboratoire': 'Biopharm',
      'remboursable_chifa': 1,
      'prix_dzd': 560.0,
      'is_princeps': 0,
    },
    {
      'nom_commercial': 'Clavamox Saidal',
      'dci': 'Amoxicilline + Acide Clavulanique',
      'dosage': '1 g/125 mg',
      'forme': 'Comprimé',
      'laboratoire': 'Saidal',
      'remboursable_chifa': 1,
      'prix_dzd': 520.0,
      'is_princeps': 0,
    },

    // --- 3. METFORMINE ---
    {
      'nom_commercial': 'Glucophage',
      'dci': 'Metformine',
      'dosage': '850 mg',
      'forme': 'Comprimé pelliculé',
      'laboratoire': 'Merck',
      'remboursable_chifa': 1,
      'prix_dzd': 320.0,
      'is_princeps': 1,
    },
    {
      'nom_commercial': 'Glucophage',
      'dci': 'Metformine',
      'dosage': '1 000 mg',
      'forme': 'Comprimé pelliculé',
      'laboratoire': 'Merck',
      'remboursable_chifa': 1,
      'prix_dzd': 390.0,
      'is_princeps': 1,
    },
    {
      'nom_commercial': 'Metfor Saidal',
      'dci': 'Metformine',
      'dosage': '850 mg',
      'forme': 'Comprimé',
      'laboratoire': 'Saidal',
      'remboursable_chifa': 1,
      'prix_dzd': 220.0,
      'is_princeps': 0,
    },
    {
      'nom_commercial': 'Metfor Saidal',
      'dci': 'Metformine',
      'dosage': '1 000 mg',
      'forme': 'Comprimé',
      'laboratoire': 'Saidal',
      'remboursable_chifa': 1,
      'prix_dzd': 260.0,
      'is_princeps': 0,
    },
    {
      'nom_commercial': 'Diaformin',
      'dci': 'Metformine',
      'dosage': '850 mg',
      'forme': 'Comprimé',
      'laboratoire': 'Biopharm',
      'remboursable_chifa': 1,
      'prix_dzd': 240.0,
      'is_princeps': 0,
    },

    // --- 4. ATORVASTATINE ---
    {
      'nom_commercial': 'Tahor',
      'dci': 'Atorvastatine',
      'dosage': '20 mg',
      'forme': 'Comprimé pelliculé',
      'laboratoire': 'Pfizer',
      'remboursable_chifa': 1,
      'prix_dzd': 890.0,
      'is_princeps': 1,
    },
    {
      'nom_commercial': 'Tahor',
      'dci': 'Atorvastatine',
      'dosage': '10 mg',
      'forme': 'Comprimé',
      'laboratoire': 'Pfizer',
      'remboursable_chifa': 1,
      'prix_dzd': 590.0,
      'is_princeps': 1,
    },
    {
      'nom_commercial': 'Ator Saidal',
      'dci': 'Atorvastatine',
      'dosage': '20 mg',
      'forme': 'Comprimé',
      'laboratoire': 'Saidal',
      'remboursable_chifa': 1,
      'prix_dzd': 490.0,
      'is_princeps': 0,
    },
    {
      'nom_commercial': 'Cardyl',
      'dci': 'Atorvastatine',
      'dosage': '20 mg',
      'forme': 'Comprimé',
      'laboratoire': 'Biopharm',
      'remboursable_chifa': 1,
      'prix_dzd': 520.0,
      'is_princeps': 0,
    },

    // --- 5. OMÉPRAZOLE ---
    {
      'nom_commercial': 'Mopral',
      'dci': 'Oméprazole',
      'dosage': '20 mg',
      'forme': 'Gélule gastro-résistante',
      'laboratoire': 'AstraZeneca',
      'remboursable_chifa': 1,
      'prix_dzd': 450.0,
      'is_princeps': 1,
    },
    {
      'nom_commercial': 'Zoltum Saidal',
      'dci': 'Oméprazole',
      'dosage': '20 mg',
      'forme': 'Gélule gastro-résistante',
      'laboratoire': 'Saidal',
      'remboursable_chifa': 1,
      'prix_dzd': 310.0,
      'is_princeps': 0,
    },
    {
      'nom_commercial': 'Gastrim',
      'dci': 'Oméprazole',
      'dosage': '20 mg',
      'forme': 'Gélule gastro-résistante',
      'laboratoire': 'Biopharm',
      'remboursable_chifa': 1,
      'prix_dzd': 330.0,
      'is_princeps': 0,
    },
    {
      'nom_commercial': 'Omepra Sophal',
      'dci': 'Oméprazole',
      'dosage': '20 mg',
      'forme': 'Gélule',
      'laboratoire': 'Sophal',
      'remboursable_chifa': 1,
      'prix_dzd': 295.0,
      'is_princeps': 0,
    },

    // --- 6. SALBUTAMOL ---
    {
      'nom_commercial': 'Ventoline',
      'dci': 'Salbutamol',
      'dosage': '100 mcg/dose',
      'forme': 'Aérosol doseur',
      'laboratoire': 'GSK',
      'remboursable_chifa': 1,
      'prix_dzd': 390.0,
      'is_princeps': 1,
    },
    {
      'nom_commercial': 'Asthalin',
      'dci': 'Salbutamol',
      'dosage': '100 mcg/dose',
      'forme': 'Aérosol doseur',
      'laboratoire': 'Cipla',
      'remboursable_chifa': 1,
      'prix_dzd': 290.0,
      'is_princeps': 0,
    },
    {
      'nom_commercial': 'Salbair',
      'dci': 'Salbutamol',
      'dosage': '100 mcg/dose',
      'forme': 'Aérosol',
      'laboratoire': 'Inpha-Medis',
      'remboursable_chifa': 1,
      'prix_dzd': 280.0,
      'is_princeps': 0,
    },

    // --- 7. ACIDE ACÉTYLSALICYLIQUE ---
    {
      'nom_commercial': 'Kardegic',
      'dci': 'Acide Acétylsalicylique',
      'dosage': '160 mg',
      'forme': 'Sachet pour solution buvable',
      'laboratoire': 'Sanofi',
      'remboursable_chifa': 1,
      'prix_dzd': 240.0,
      'is_princeps': 1,
    },
    {
      'nom_commercial': 'Kardegic',
      'dci': 'Acide Acétylsalicylique',
      'dosage': '75 mg',
      'forme': 'Sachet',
      'laboratoire': 'Sanofi',
      'remboursable_chifa': 1,
      'prix_dzd': 210.0,
      'is_princeps': 1,
    },
    {
      'nom_commercial': 'Aspegic Saidal',
      'dci': 'Acide Acétylsalicylique',
      'dosage': '100 mg',
      'forme': 'Sachet',
      'laboratoire': 'Saidal',
      'remboursable_chifa': 1,
      'prix_dzd': 140.0,
      'is_princeps': 0,
    },

    // --- 8. CÉFIXIME ---
    {
      'nom_commercial': 'Oroken',
      'dci': 'Céfixime',
      'dosage': '200 mg',
      'forme': 'Comprimé pelliculé',
      'laboratoire': 'Sanofi',
      'remboursable_chifa': 1,
      'prix_dzd': 890.0,
      'is_princeps': 1,
    },
    {
      'nom_commercial': 'Cefix Saidal',
      'dci': 'Céfixime',
      'dosage': '200 mg',
      'forme': 'Comprimé',
      'laboratoire': 'Saidal',
      'remboursable_chifa': 1,
      'prix_dzd': 610.0,
      'is_princeps': 0,
    },
    {
      'nom_commercial': 'Suprax',
      'dci': 'Céfixime',
      'dosage': '200 mg',
      'forme': 'Comprimé',
      'laboratoire': 'Hikma',
      'remboursable_chifa': 1,
      'prix_dzd': 650.0,
      'is_princeps': 0,
    },

    // --- 9. AZITHROMYCINE ---
    {
      'nom_commercial': 'Zithromax',
      'dci': 'Azithromycine',
      'dosage': '500 mg',
      'forme': 'Comprimé pelliculé',
      'laboratoire': 'Pfizer',
      'remboursable_chifa': 1,
      'prix_dzd': 780.0,
      'is_princeps': 1,
    },
    {
      'nom_commercial': 'Azix',
      'dci': 'Azithromycine',
      'dosage': '500 mg',
      'forme': 'Comprimé',
      'laboratoire': 'Biopharm',
      'remboursable_chifa': 1,
      'prix_dzd': 520.0,
      'is_princeps': 0,
    },
    {
      'nom_commercial': 'Zitrocin Saidal',
      'dci': 'Azithromycine',
      'dosage': '500 mg',
      'forme': 'Comprimé',
      'laboratoire': 'Saidal',
      'remboursable_chifa': 1,
      'prix_dzd': 490.0,
      'is_princeps': 0,
    },

    // --- 10. PHLOROGLUCINOL (SPASFON) ---
    {
      'nom_commercial': 'Spasfon',
      'dci': 'Phloroglucinol',
      'dosage': '80 mg',
      'forme': 'Comprimé enrobé',
      'laboratoire': 'Teva',
      'remboursable_chifa': 1,
      'prix_dzd': 260.0,
      'is_princeps': 1,
    },
    {
      'nom_commercial': 'Spasfon Lyoc',
      'dci': 'Phloroglucinol',
      'dosage': '80 mg',
      'forme': 'Lyophilisat oral',
      'laboratoire': 'Teva',
      'remboursable_chifa': 1,
      'prix_dzd': 320.0,
      'is_princeps': 1,
    },
    {
      'nom_commercial': 'Spasmocalm Saidal',
      'dci': 'Phloroglucinol',
      'dosage': '80 mg',
      'forme': 'Comprimé',
      'laboratoire': 'Saidal',
      'remboursable_chifa': 1,
      'prix_dzd': 180.0,
      'is_princeps': 0,
    },
  ];

  /// Initialise la base SQLite : attachement à une base existante, création en mémoire ou sur disque
  void initialize({Database? db, String? customPath}) {
    if (_isInitialized && _db != null) return;

    if (db != null) {
      _db = db;
      _ownsDb = false;
    } else {
      final candidatePaths = [
        if (customPath != null) customPath,
        'assets/data/sante_dz_bundled.db',
        r'C:\SANTE_DZ_SCRAPER\assets\data\sante_dz_bundled.db',
      ];

      String? resolvedPath;
      for (final p in candidatePaths) {
        if (File(p).existsSync()) {
          resolvedPath = p;
          break;
        }
      }

      if (resolvedPath != null) {
        try {
          _db = sqlite3.open(resolvedPath, mode: OpenMode.readWrite);
          _ownsDb = true;
        } catch (_) {
          _db = sqlite3.open(resolvedPath, mode: OpenMode.readOnly);
          _ownsDb = true;
        }
      } else {
        _db = sqlite3.openInMemory();
        _ownsDb = true;
      }
    }

    _ensureSchemaAndSeed();
    _isInitialized = true;
  }

  /// Création de la table relationnelle et de l'index FTS5 si inexistants
  void _ensureSchemaAndSeed() {
    if (_db == null) return;

    try {
      _db!.execute('''
        CREATE TABLE IF NOT EXISTS medicaments_dz (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          nom_commercial TEXT NOT NULL,
          dci TEXT NOT NULL,
          dosage TEXT NOT NULL,
          forme TEXT NOT NULL,
          laboratoire TEXT NOT NULL,
          remboursable_chifa INTEGER NOT NULL DEFAULT 1,
          prix_dzd REAL,
          is_princeps INTEGER NOT NULL DEFAULT 0
        );
      ''');

      _db!.execute('''
        CREATE VIRTUAL TABLE IF NOT EXISTS medicaments_fts USING fts5(
          nom_commercial,
          dci,
          dosage,
          forme,
          laboratoire,
          content='medicaments_dz',
          content_rowid='id'
        );
      ''');

      // Triggers pour synchronisation automatique FTS5
      _db!.execute('''
        CREATE TRIGGER IF NOT EXISTS medicaments_ai AFTER INSERT ON medicaments_dz BEGIN
          INSERT INTO medicaments_fts(rowid, nom_commercial, dci, dosage, forme, laboratoire)
          VALUES (new.id, new.nom_commercial, new.dci, new.dosage, new.forme, new.laboratoire);
        END;
      ''');

      // Peuple les données si la table est vide
      final countRow = _db!.select('SELECT COUNT(*) AS total FROM medicaments_dz;');
      final count = countRow.first['total'] as int;
      if (count == 0) {
        seedInitialMedications();
      }
    } catch (_) {
      // Si la base est en lecture seule stricte et déjà peuplée, on ignore l'erreur d'écriture
    }
  }

  /// Insertion du lot de médicaments initiaux
  void seedInitialMedications() {
    if (_db == null) return;

    final stmt = _db!.prepare('''
      INSERT INTO medicaments_dz (
        nom_commercial, dci, dosage, forme, laboratoire, remboursable_chifa, prix_dzd, is_princeps
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
    ''');

    for (final m in initialMedications) {
      stmt.execute([
        m['nom_commercial'],
        m['dci'],
        m['dosage'],
        m['forme'],
        m['laboratoire'],
        m['remboursable_chifa'],
        m['prix_dzd'],
        m['is_princeps'],
      ]);
    }
    stmt.dispose();
  }

  /// Recherche plein-texte FTS5 ultra-rapide par nom commercial, DCI ou laboratoire
  List<DzMedication> search(String query, {int limit = 50}) {
    if (_db == null) return [];
    final cleanQuery = query.trim().replaceAll("'", "''");
    if (cleanQuery.isEmpty) return getAllMedications(limit: limit);

    try {
      // 1. Essai via l'index plein texte FTS5
      final ftsQuery = cleanQuery
          .split(RegExp(r'\s+'))
          .where((s) => s.isNotEmpty)
          .map((s) => '"$s"*')
          .join(' ');

      final results = _db!.select('''
        SELECT m.id, m.nom_commercial, m.dci, m.dosage, m.forme,
               m.laboratoire, m.remboursable_chifa, m.prix_dzd, m.is_princeps
        FROM medicaments_fts f
        JOIN medicaments_dz m ON m.id = f.rowid
        WHERE medicaments_fts MATCH ?
        LIMIT ?;
      ''', [ftsQuery, limit]);

      if (results.isNotEmpty) {
        return results.map((r) => DzMedication.fromMap(r)).toList();
      }
    } catch (_) {
      // Fallback vers recherche standard LIKE
    }

    // 2. Fallback SQL LIKE si FTS5 ne trouve rien ou en cas de syntaxe complexe
    final pattern = '%$cleanQuery%';
    final results = _db!.select('''
      SELECT id, nom_commercial, dci, dosage, forme,
             laboratoire, remboursable_chifa, prix_dzd, is_princeps
      FROM medicaments_dz
      WHERE nom_commercial LIKE ?
         OR dci LIKE ?
         OR laboratoire LIKE ?
      LIMIT ?;
    ''', [pattern, pattern, pattern, limit]);

    return results.map((r) => DzMedication.fromMap(r)).toList();
  }

  /// Récupère tous les médicaments enregistrés
  List<DzMedication> getAllMedications({int limit = 100}) {
    if (_db == null) return [];
    final results = _db!.select('''
      SELECT id, nom_commercial, dci, dosage, forme,
             laboratoire, remboursable_chifa, prix_dzd, is_princeps
      FROM medicaments_dz
      ORDER BY dci ASC, is_princeps DESC, nom_commercial ASC
      LIMIT ?;
    ''', [limit]);

    return results.map((r) => DzMedication.fromMap(r)).toList();
  }

  /// Récupère tous les équivalents et génériques partageant la même DCI.
  /// Idéal pour parer aux ruptures de stock d'un produit (ex: Doliprane -> Paracétamol Saidal, Panadol...).
  DciEquivalenceResult getEquivalentsFor(String brandOrDci) {
    if (_db == null) {
      return DciEquivalenceResult(
        searchedQuery: brandOrDci,
        dci: '',
        allEquivalents: const [],
        generics: const [],
        princepsList: const [],
        localProducers: const [],
      );
    }

    final trimmed = brandOrDci.trim();
    if (trimmed.isEmpty) {
      return DciEquivalenceResult(
        searchedQuery: brandOrDci,
        dci: '',
        allEquivalents: const [],
        generics: const [],
        princepsList: const [],
        localProducers: const [],
      );
    }

    // 1. Recherche du médicament cible pour identifier sa DCI
    final directMatches = search(trimmed, limit: 5);
    String detectedDci = trimmed;
    DzMedication? target;

    if (directMatches.isNotEmpty) {
      // Chercher une correspondance exacte sur nom commercial en priorité
      target = directMatches.firstWhere(
        (m) => m.nomCommercial.toLowerCase() == trimmed.toLowerCase(),
        orElse: () => directMatches.first,
      );
      detectedDci = target.dci;
    }

    // 2. Extraction de l'ensemble des équivalents partageant cette DCI
    final rows = _db!.select('''
      SELECT id, nom_commercial, dci, dosage, forme,
             laboratoire, remboursable_chifa, prix_dzd, is_princeps
      FROM medicaments_dz
      WHERE LOWER(dci) = LOWER(?)
      ORDER BY is_princeps DESC, remboursable_chifa DESC, nom_commercial ASC;
    ''', [detectedDci]);

    final allEquivalents = rows.map((r) => DzMedication.fromMap(r)).toList();
    final generics = allEquivalents.where((m) => !m.isPrinceps).toList();
    final princepsList = allEquivalents.where((m) => m.isPrinceps).toList();
    final localProducers = allEquivalents.where((m) => m.isLocalProducer).toList();

    return DciEquivalenceResult(
      searchedQuery: trimmed,
      dci: detectedDci,
      targetMedication: target,
      allEquivalents: allEquivalents,
      generics: generics,
      princepsList: princepsList,
      localProducers: localProducers,
    );
  }

  /// Retourne la liste unique de toutes les DCI disponibles
  List<String> getAvailableDcis() {
    if (_db == null) return [];
    final rows = _db!.select('SELECT DISTINCT dci FROM medicaments_dz ORDER BY dci ASC;');
    return rows.map((r) => r['dci'] as String).toList();
  }

  void dispose() {
    if (_ownsDb) {
      _db?.dispose();
    }
    _db = null;
    _isInitialized = false;
  }
}
