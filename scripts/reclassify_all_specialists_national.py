import sqlite3

def run():
    conn = sqlite3.connect('assets/data/sante_dz_bundled.db')
    c = conn.cursor()

    # Rule definitions for specialty keywords in both Arabic and French
    reclassifications = [
        # Dentiste / Stomatologie
        ("Dentiste", [
            "%dentist%", "%dentaire%", "%أسنان%", "%طبيب أسنان%", "%جراحة الأسنان%", "%stomatolog%"
        ]),
        # Pédiatre
        ("Pédiatre", [
            "%pédiatr%", "%pediatr%", "%أطفال%", "%طبيب أطفال%", "%رضع%"
        ]),
        # Cardiologue
        ("Cardiologue", [
            "%cardio%", "%أمراض القلب%", "%أمراض القلب والشرايين%", "%قلب%"
        ]),
        # Ophtalmologue
        ("Ophtalmologue", [
            "%ophtalm%", "%عيون%", "%طب العيون%", "%طب و جراحة العيون%", "%opticien%"
        ]),
        # Gynécologue
        ("Gynécologue", [
            "%gynéco%", "%gyneco%", "%نساء والتوليد%", "%أمراض النساء%", "%توليد%", "%obstétri%"
        ]),
        # Dermatologue
        ("Dermatologue", [
            "%dermat%", "%أمراض جلدية%", "%جلدية%", "%تناسلية%"
        ]),
        # Orthopédiste
        ("Orthopédiste", [
            "%orthopéd%", "%orthoped%", "%عظام%", "%جراحة العظام%", "%مفاصل%"
        ]),
        # ORL
        ("ORL", [
            "% orl %", "%orl%", "%أذن%", "%أنف وأذن%", "%حنجرة%"
        ]),
        # Urologue
        ("Urologue", [
            "%urolo%", "%مسالك بولية%", "%أمراض الكلى والمسالك%"
        ]),
        # Gastro-entérologue
        ("Gastro-entérologue", [
            "%gastro%", "%جهاز هضمي%", "%أمراض الجهاز الهضمي%"
        ]),
        # Psychiatrie / Psychologie
        ("Psychiatre", [
            "%psychiat%", "%نفسية%", "%أمراض عقلية%", "%عقلية ونفسية%"
        ]),
    ]

    total_reclassified = 0
    for target_cat, patterns in reclassifications:
        for pat in patterns:
            # We target generic categories like 'Clinique', 'Médecin', 'Centre Médical'
            c.execute('''
                UPDATE facilities
                SET categorie = ?
                WHERE (LOWER(categorie) IN ('clinique', 'médecin', 'centre médical', 'centre de santé', 'structure')
                       OR LOWER(categorie) LIKE 'clinique%' OR LOWER(categorie) LIKE 'médecin%')
                  AND (LOWER(nom) LIKE ? OR LOWER(nom) LIKE ?)
                  AND LOWER(categorie) != ?
            ''', (target_cat, pat, pat.lower(), target_cat.lower()))
            if c.rowcount > 0:
                print(f"Reclassified {c.rowcount} entries to '{target_cat}' matching pattern '{pat}'")
                total_reclassified += c.rowcount

    conn.commit()
    print(f"\nTotal facilities accurately reclassified to their real specialty: {total_reclassified}")

    # Rebuild indexes
    print("Rebuilding R-Tree and FTS index...")
    c.execute("DELETE FROM facilities_rtree")
    c.execute('''
        INSERT INTO facilities_rtree (id, min_lat, max_lat, min_lon, max_lon)
        SELECT id, latitude, latitude, longitude, longitude 
        FROM facilities 
        WHERE latitude IS NOT NULL AND longitude IS NOT NULL
    ''')
    try:
        c.execute("INSERT INTO facilities_fts(facilities_fts) VALUES('rebuild')")
    except Exception as e:
        print("FTS notice:", e)

    conn.commit()
    conn.close()
    print("Done!")

if __name__ == '__main__':
    run()

