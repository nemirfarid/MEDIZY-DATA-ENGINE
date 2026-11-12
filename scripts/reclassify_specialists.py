import sqlite3

conn = sqlite3.connect('assets/data/sante_dz_bundled.db')
c = conn.cursor()

# 1. Update specialists miscategorized as generic 'Médecin' based on their name keywords
specialties_rules = [
    ('Pédiatre', ['pédiatr', 'pediatr', 'طب الأطفال', 'اطفال', 'أطفال']),
    ('Dentiste', ['dentist', 'dentaire', 'chirurgie dentaire', 'طب الأسنان', 'أسنان']),
    ('Cardiologue', ['cardio', 'أمراض القلب', 'قلب']),
    ('Gynécologue', ['gynéco', 'gyneco', 'matern', 'توليد', 'نساء']),
    ('Ophtalmologue', ['ophtalm', 'عيون', 'طب العيون', 'opticien']),
    ('Dermatologue', ['dermat', 'أمراض جلدية', 'جلد']),
    ('Orthopédiste', ['orthopéd', 'orthoped', 'عظام', 'traumato']),
    ('Gastro-entérologue', ['gastro', 'أمراض الجهاز الهضمي']),
    ('Pneumologue', ['pneumo', 'أمراض الصدر']),
    ('ORL', ['orl', 'أنف وأذن']),
    ('Psychiatre', ['psych', 'أمراض نفسية', 'نفسي']),
    ('Radiologue / Imagerie', ['radiolog', 'imagerie', 'scanner', 'irm', 'أشعة']),
    ('Laboratoire d\'Analyses', ['laboratoire', 'analyse', 'مخبر']),
]

updated_total = 0
for cat_target, keywords in specialties_rules:
    for kw in keywords:
        pattern = f'%{kw}%'
        c.execute("""
            UPDATE facilities 
            SET categorie = ? 
            WHERE (LOWER(categorie) = 'médecin' OR LOWER(categorie) = 'medecin' OR LOWER(categorie) = 'médecin généraliste')
              AND LOWER(nom) LIKE ?
        """, (cat_target, pattern))
        if c.rowcount > 0:
            print(f"Updated {c.rowcount} facilities to '{cat_target}' using keyword '{kw}'")
            updated_total += c.rowcount

conn.commit()
print(f"Total specialist facilities corrected: {updated_total}")

