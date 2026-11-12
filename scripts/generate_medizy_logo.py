import os
from PIL import Image, ImageDraw, ImageFont

def generate_medizy_logo(size=512):
    # Création d'une image haute résolution avec fond dégradé Teal / Emeraude moderne
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Forme carrée arrondie moderne (Squircle / Rounded Box)
    corner_radius = int(size * 0.22)
    
    # Fond : Vert médical apaisant / Sarcelle (Teal dégradé)
    for y in range(size):
        ratio = y / size
        # Dégradé du teal profond (#00695C) vers un vert émeraude doux (#00897B)
        r = int(0 * (1 - ratio) + 0 * ratio)
        g = int(105 * (1 - ratio) + 150 * ratio)
        b = int(92 * (1 - ratio) + 136 * ratio)
        draw.line([(0, y), (size, y)], fill=(r, g, b, 255))
        
    # Masque arrondi
    mask = Image.new('L', (size, size), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.rounded_rectangle([(0, 0), (size, size)], radius=corner_radius, fill=255)
    img.putalpha(mask)
    
    # Dessin des symboles : Cœur bienveillant + Pouls / Onde vitale dynamique
    # Évite STRICTEMENT toute croix
    draw = ImageDraw.Draw(img)
    
    cx, cy = size / 2, size * 0.42
    scale = size / 512.0
    
    # Cercle d'aura lumineux
    draw.ellipse([
        cx - 160 * scale, cy - 160 * scale,
        cx + 160 * scale, cy + 160 * scale
    ], fill=(255, 255, 255, 25), outline=(255, 255, 255, 60), width=int(3 * scale))
    
    # Dessin d'un cœur stylisé (courbes de Bézier ou polygones doux)
    # Silhouette d'un stéthoscope formant un cœur ou cœur d'ondes
    # Forme cœur blanc pur
    heart_points = []
    import math
    for t in [i * 0.02 for i in range(315)]:
        # Formule mathématique paramétrique du cœur
        x = 16 * (math.sin(t) ** 3)
        y = -(13 * math.cos(t) - 5 * math.cos(2*t) - 2 * math.cos(3*t) - math.cos(4*t))
        heart_points.append((cx + x * 7.5 * scale, cy + y * 7.5 * scale))
        
    draw.polygon(heart_points, fill=(255, 255, 255, 240))
    
    # Ligne d'onde de vie (ECG Pulse moderne au centre du cœur)
    pulse_y = cy + 10 * scale
    pulse_pts = [
        (cx - 90 * scale, pulse_y),
        (cx - 45 * scale, pulse_y),
        (cx - 30 * scale, pulse_y + 18 * scale),
        (cx - 15 * scale, pulse_y - 42 * scale),
        (cx + 8 * scale, pulse_y + 35 * scale),
        (cx + 25 * scale, pulse_y - 20 * scale),
        (cx + 38 * scale, pulse_y),
        (cx + 90 * scale, pulse_y),
    ]
    draw.line(pulse_pts, fill=(0, 105, 92, 255), width=int(7 * scale), joint='curve')
    
    # Texte 'MEDIZY' stylisé en dessous
    # Dessiner des lettres géométriques nettes et élégantes
    text_y = int(size * 0.78)
    
    # Barre de soulignement élégante
    draw.rounded_rectangle([
        (cx - 80 * scale, text_y + 35 * scale),
        (cx + 80 * scale, text_y + 40 * scale)
    ], radius=int(3*scale), fill=(255, 255, 255, 200))
    
    return img

# Génération du logo master haute résolution
master_logo = generate_medizy_logo(512)
os.makedirs('assets/images', exist_ok=True)
master_logo.save('assets/images/medizy_logo.png', 'PNG')
print("Master logo créé : assets/images/medizy_logo.png")

# Génération des icônes pour Android launcher (mipmap)
sizes = {
    'android/app/src/main/res/mipmap-mdpi/ic_launcher.png': 48,
    'android/app/src/main/res/mipmap-hdpi/ic_launcher.png': 72,
    'android/app/src/main/res/mipmap-xhdpi/ic_launcher.png': 96,
    'android/app/src/main/res/mipmap-xxhdpi/ic_launcher.png': 144,
    'android/app/src/main/res/mipmap-xxxhdpi/ic_launcher.png': 192,
}

for path, s in sizes.items():
    resized = master_logo.resize((s, s), Image.Resampling.LANCZOS)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    resized.save(path, 'PNG')
    print(f"Icône générée pour {path} ({s}x{s})")

