import sqlite3

def populate():
    con = sqlite3.connect('assets/data/sante_dz_bundled.db')
    cur = con.cursor()

    # Table et FTS5
    cur.execute('''
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
        )
    ''')

    cur.execute('''
        CREATE VIRTUAL TABLE IF NOT EXISTS medicaments_fts USING fts5(
            nom_commercial,
            dci,
            dosage,
            forme,
            laboratoire,
            content='medicaments_dz',
            content_rowid='id'
        )
    ''')

    cur.execute('DELETE FROM medicaments_dz')
    cur.execute("DELETE FROM medicaments_fts")

    meds = [
        # PARACÉTAMOL
        ('Doliprane', 'Paracétamol', '1 000 mg', 'Comprimé', 'Sanofi', 1, 180.0, 1),
        ('Doliprane', 'Paracétamol', '500 mg', 'Comprimé', 'Sanofi', 1, 120.0, 1),
        ('Doliprane', 'Paracétamol', '2.4%', 'Sirop', 'Sanofi', 1, 220.0, 1),
        ('Paracétamol Saidal', 'Paracétamol', '1 000 mg', 'Comprimé', 'Saidal', 1, 130.0, 0),
        ('Paracétamol Saidal', 'Paracétamol', '500 mg', 'Comprimé', 'Saidal', 1, 90.0, 0),
        ('Efferalgan', 'Paracétamol', '1 000 mg', 'Comprimé effervescent', 'UPSA', 1, 210.0, 1),
        ('Panadol', 'Paracétamol', '500 mg', 'Comprimé', 'GSK', 1, 150.0, 0),
        ('Algidol', 'Paracétamol', '1 000 mg', 'Comprimé', 'Biopharm', 1, 140.0, 0),
        ('Para-Denk', 'Paracétamol', '500 mg', 'Comprimé', 'Denk Pharma', 1, 145.0, 0),

        # AMOXICILLINE + ACIDE CLAVULANIQUE
        ('Augmentin', 'Amoxicilline + Acide Clavulanique', '1 g/125 mg', 'Comprimé', 'GSK', 1, 720.0, 1),
        ('Augmentin', 'Amoxicilline + Acide Clavulanique', '500 mg/62.5 mg', 'Comprimé', 'GSK', 1, 480.0, 1),
        ('Klavox', 'Amoxicilline + Acide Clavulanique', '1 g/125 mg', 'Comprimé', 'Hikma', 1, 580.0, 0),
        ('Curam', 'Amoxicilline + Acide Clavulanique', '1 g/125 mg', 'Comprimé', 'Sandoz', 1, 610.0, 0),
        ('Amoksiklav', 'Amoxicilline + Acide Clavulanique', '1 g/125 mg', 'Comprimé', 'Biopharm', 1, 560.0, 0),
        ('Clavamox Saidal', 'Amoxicilline + Acide Clavulanique', '1 g/125 mg', 'Comprimé', 'Saidal', 1, 520.0, 0),

        # METFORMINE
        ('Glucophage', 'Metformine', '850 mg', 'Comprimé', 'Merck', 1, 320.0, 1),
        ('Glucophage', 'Metformine', '1 000 mg', 'Comprimé', 'Merck', 1, 390.0, 1),
        ('Metfor Saidal', 'Metformine', '850 mg', 'Comprimé', 'Saidal', 1, 220.0, 0),
        ('Metfor Saidal', 'Metformine', '1 000 mg', 'Comprimé', 'Saidal', 1, 260.0, 0),
        ('Diaformin', 'Metformine', '850 mg', 'Comprimé', 'Biopharm', 1, 240.0, 0),

        # ATORVASTATINE
        ('Tahor', 'Atorvastatine', '20 mg', 'Comprimé', 'Pfizer', 1, 890.0, 1),
        ('Tahor', 'Atorvastatine', '10 mg', 'Comprimé', 'Pfizer', 1, 590.0, 1),
        ('Ator Saidal', 'Atorvastatine', '20 mg', 'Comprimé', 'Saidal', 1, 490.0, 0),
        ('Lipitor', 'Atorvastatine', '20 mg', 'Comprimé', 'Pfizer', 1, 880.0, 1),
        ('Cardyl', 'Atorvastatine', '20 mg', 'Comprimé', 'Biopharm', 1, 520.0, 0),

        # OMÉPRAZOLE
        ('Mopral', 'Oméprazole', '20 mg', 'Gélule', 'AstraZeneca', 1, 450.0, 1),
        ('Zoltum Saidal', 'Oméprazole', '20 mg', 'Gélule', 'Saidal', 1, 310.0, 0),
        ('Gastrim', 'Oméprazole', '20 mg', 'Gélule', 'Biopharm', 1, 330.0, 0),
        ('Omepra Sophal', 'Oméprazole', '20 mg', 'Gélule', 'Sophal', 1, 295.0, 0),

        # SALBUTAMOL
        ('Ventoline', 'Salbutamol', '100 mcg/dose', 'Aérosol', 'GSK', 1, 390.0, 1),
        ('Asthalin', 'Salbutamol', '100 mcg/dose', 'Aérosol', 'Cipla', 1, 290.0, 0),
        ('Salbair', 'Salbutamol', '100 mcg/dose', 'Aérosol', 'Inpha-Medis', 1, 280.0, 0),

        # ACIDE ACÉTYLSALICYLIQUE
        ('Kardegic', 'Acide Acétylsalicylique', '160 mg', 'Sachet', 'Sanofi', 1, 240.0, 1),
        ('Kardegic', 'Acide Acétylsalicylique', '75 mg', 'Sachet', 'Sanofi', 1, 210.0, 1),
        ('Aspegic Saidal', 'Acide Acétylsalicylique', '100 mg', 'Sachet', 'Saidal', 1, 140.0, 0),

        # CÉFIXIME
        ('Oroken', 'Céfixime', '200 mg', 'Comprimé', 'Sanofi', 1, 890.0, 1),
        ('Cefix Saidal', 'Céfixime', '200 mg', 'Comprimé', 'Saidal', 1, 610.0, 0),
        ('Suprax', 'Céfixime', '200 mg', 'Comprimé', 'Hikma', 1, 650.0, 0),

        # AZITHROMYCINE
        ('Zithromax', 'Azithromycine', '500 mg', 'Comprimé', 'Pfizer', 1, 780.0, 1),
        ('Azix', 'Azithromycine', '500 mg', 'Comprimé', 'Biopharm', 1, 520.0, 0),
        ('Zitrocin Saidal', 'Azithromycine', '500 mg', 'Comprimé', 'Saidal', 1, 490.0, 0),

        # PHLOROGLUCINOL
        ('Spasfon', 'Phloroglucinol', '80 mg', 'Comprimé', 'Teva', 1, 260.0, 1),
        ('Spasfon Lyoc', 'Phloroglucinol', '80 mg', 'Lyophilisat oral', 'Teva', 1, 320.0, 1),
        ('Spasmocalm Saidal', 'Phloroglucinol', '80 mg', 'Comprimé', 'Saidal', 1, 180.0, 0),
    ]

    for m in meds:
        cur.execute('''
            INSERT INTO medicaments_dz (
                nom_commercial, dci, dosage, forme, laboratoire, remboursable_chifa, prix_dzd, is_princeps
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', m)
        mid = cur.lastrowid
        cur.execute('''
            INSERT INTO medicaments_fts (rowid, nom_commercial, dci, dosage, forme, laboratoire)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (mid, m[0], m[1], m[2], m[3], m[4]))

    con.commit()
    count = cur.execute('SELECT COUNT(*) FROM medicaments_dz').fetchone()[0]
    fts_count = cur.execute('SELECT COUNT(*) FROM medicaments_fts').fetchone()[0]
    print(f'MEDICAMENTS INSERTED: {count}, FTS INDEXED: {fts_count}')
    con.close()

if __name__ == '__main__':
    populate()
