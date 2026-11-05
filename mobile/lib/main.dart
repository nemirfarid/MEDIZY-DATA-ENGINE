import 'package:flutter/material.dart';

void main() => runApp(const MedizyApp());

class MedizyApp extends StatelessWidget {
  const MedizyApp({super.key});

  @override
  Widget build(BuildContext context) {
    const ink = Color(0xFF16324F);
    const teal = Color(0xFF1CA6A3);
    return MaterialApp(
      title: 'MEDIZY',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        useMaterial3: true,
        colorScheme: ColorScheme.fromSeed(
          seedColor: teal,
          primary: teal,
          secondary: const Color(0xFF5AC6B5),
          surface: const Color(0xFFF6F9FC),
        ),
        scaffoldBackgroundColor: const Color(0xFFF6F9FC),
        appBarTheme: const AppBarTheme(
          backgroundColor: Color(0xFFF6F9FC),
          foregroundColor: ink,
          elevation: 0,
          centerTitle: false,
        ),
        fontFamily: 'Roboto',
      ),
      home: const DirectoryHome(),
    );
  }
}

class DirectoryHome extends StatelessWidget {
  const DirectoryHome({super.key});

  static const categories = <_Category>[
    _Category('Hôpitaux', Icons.local_hospital_rounded, Color(0xFF3977D5)),
    _Category('Cliniques', Icons.apartment_rounded, Color(0xFF8B65C8)),
    _Category('Pharmacies', Icons.medication_rounded, Color(0xFF27A58C)),
    _Category('Laboratoires', Icons.science_rounded, Color(0xFFE59A37)),
    _Category('Médecins', Icons.person_search_rounded, Color(0xFFDE6F83)),
    _Category('Dentistes', Icons.mood_rounded, Color(0xFF4299B5)),
    _Category('Maternités', Icons.child_friendly_rounded, Color(0xFFCB78A6)),
    _Category('Autres', Icons.health_and_safety_rounded, Color(0xFF6E879B)),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Row(children: [
          Container(
            width: 38,
            height: 38,
            decoration: BoxDecoration(
              gradient: const LinearGradient(
                colors: [Color(0xFF20B8AA), Color(0xFF327FD1)],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
              borderRadius: BorderRadius.circular(13),
            ),
            child: const Icon(Icons.location_on_rounded, color: Colors.white, size: 23),
          ),
          const SizedBox(width: 10),
          const Text('MEDIZY', style: TextStyle(fontWeight: FontWeight.w900, letterSpacing: 1.1)),
        ]),
        actions: [
          IconButton(
            tooltip: 'Profil et paramètres',
            onPressed: () {},
            icon: const Icon(Icons.tune_rounded),
          ),
          const SizedBox(width: 8),
        ],
      ),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.fromLTRB(18, 8, 18, 28),
          children: [
            Container(
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(
                gradient: const LinearGradient(
                  colors: [Color(0xFF153B58), Color(0xFF187E89)],
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                ),
                borderRadius: BorderRadius.circular(26),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('Votre santé, près de vous',
                      style: TextStyle(color: Colors.white, fontSize: 23, fontWeight: FontWeight.w800)),
                  const SizedBox(height: 8),
                  Text('Trouvez une structure de santé en Algérie',
                      style: TextStyle(color: Colors.white.withValues(alpha: .82), fontSize: 14)),
                  const SizedBox(height: 18),
                  Container(
                    decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(16)),
                    child: const TextField(
                      decoration: InputDecoration(
                        hintText: 'Structure, spécialité, commune…',
                        prefixIcon: Icon(Icons.search_rounded, color: Color(0xFF1CA6A3)),
                        border: InputBorder.none,
                        contentPadding: EdgeInsets.symmetric(vertical: 16),
                      ),
                    ),
                  ),
                  const SizedBox(height: 14),
                  Row(children: [
                    const Icon(Icons.near_me_rounded, color: Color(0xFF9CE5D7), size: 18),
                    const SizedBox(width: 6),
                    Text('Explorer autour de moi',
                        style: TextStyle(color: Colors.white.withValues(alpha: .92), fontWeight: FontWeight.w600)),
                    const Spacer(),
                    const Icon(Icons.arrow_forward_rounded, color: Colors.white, size: 18),
                  ]),
                ],
              ),
            ),
            const SizedBox(height: 24),
            const Row(children: [
              Expanded(child: Text('Explorer par catégorie',
                  style: TextStyle(fontSize: 18, fontWeight: FontWeight.w800, color: Color(0xFF16324F)))),
              Text('Tout voir', style: TextStyle(color: Color(0xFF168F91), fontWeight: FontWeight.w700)),
            ]),
            const SizedBox(height: 14),
            GridView.builder(
              shrinkWrap: true,
              physics: const NeverScrollableScrollPhysics(),
              itemCount: categories.length,
              gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                crossAxisCount: 4,
                crossAxisSpacing: 10,
                mainAxisSpacing: 14,
                childAspectRatio: .78,
              ),
              itemBuilder: (context, index) {
                final item = categories[index];
                return Column(children: [
                  Container(
                    width: 58,
                    height: 58,
                    decoration: BoxDecoration(
                      color: item.color.withValues(alpha: .12),
                      borderRadius: BorderRadius.circular(20),
                    ),
                    child: Icon(item.icon, color: item.color, size: 27),
                  ),
                  const SizedBox(height: 8),
                  Text(item.name, textAlign: TextAlign.center,
                      maxLines: 2, style: const TextStyle(fontSize: 11.5, fontWeight: FontWeight.w600)),
                ]);
              },
            ),
            const SizedBox(height: 10),
            const Row(children: [
              Expanded(child: Text('Carte à proximité',
                  style: TextStyle(fontSize: 18, fontWeight: FontWeight.w800, color: Color(0xFF16324F)))),
              Icon(Icons.open_in_full_rounded, color: Color(0xFF168F91), size: 19),
            ]),
            const SizedBox(height: 12),
            Container(
              height: 190,
              decoration: BoxDecoration(
                color: const Color(0xFFE4EDF0),
                borderRadius: BorderRadius.circular(24),
                border: Border.all(color: const Color(0xFFD4E1E7)),
              ),
              child: Stack(children: [
                Positioned.fill(
                  child: ClipRRect(
                    borderRadius: BorderRadius.circular(24),
                    child: CustomPaint(painter: _MapPreviewPainter()),
                  ),
                ),
                Positioned(
                  left: 20, top: 18,
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                    decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(13),
                        boxShadow: const [BoxShadow(color: Color(0x18000000), blurRadius: 12)]),
                    child: const Row(children: [
                      Icon(Icons.layers_rounded, size: 16, color: Color(0xFF356B82)),
                      SizedBox(width: 6),
                      Text('Carte', style: TextStyle(fontWeight: FontWeight.w700, fontSize: 12)),
                    ]),
                  ),
                ),
                const Center(
                  child: Column(mainAxisSize: MainAxisSize.min, children: [
                    Icon(Icons.location_on_rounded, color: Color(0xFF159C9A), size: 40),
                    Text('Carte interactive bientôt disponible',
                        style: TextStyle(color: Color(0xFF36596A), fontSize: 11, fontWeight: FontWeight.w600)),
                  ]),
                ),
              ]),
            ),
            const SizedBox(height: 20),
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(color: Colors.white, borderRadius: BorderRadius.circular(20)),
              child: const Row(children: [
                Icon(Icons.privacy_tip_rounded, color: Color(0xFF1CA6A3)),
                SizedBox(width: 10),
                Expanded(child: Text('Vos données restent sur votre appareil. Import privé à configurer.',
                    style: TextStyle(fontSize: 12, color: Color(0xFF526A7A)))),
              ]),
            ),
          ],
        ),
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: 0,
        destinations: const [
          NavigationDestination(icon: Icon(Icons.home_rounded), label: 'Accueil'),
          NavigationDestination(icon: Icon(Icons.map_rounded), label: 'Carte'),
          NavigationDestination(icon: Icon(Icons.bookmark_rounded), label: 'Favoris'),
        ],
      ),
    );
  }
}

class _Category {
  const _Category(this.name, this.icon, this.color);
  final String name;
  final IconData icon;
  final Color color;
}

class _MapPreviewPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final road = Paint()..color = const Color(0xFFF9FCFD)..strokeWidth = 12..strokeCap = StrokeCap.round;
    final fine = Paint()..color = const Color(0xFFCFDDE1)..strokeWidth = 2;
    final park = Paint()..color = const Color(0xFFD2E7D7);
    canvas.drawRect(Rect.fromLTWH(size.width * .08, size.height * .15, size.width * .27, size.height * .25), park);
    canvas.drawRect(Rect.fromLTWH(size.width * .68, size.height * .60, size.width * .23, size.height * .22), park);
    final paths = [
      Path()..moveTo(-10, size.height * .72)..cubicTo(size.width*.25,size.height*.48,size.width*.45,size.height*.92,size.width+10,size.height*.25),
      Path()..moveTo(size.width*.18,-10)..cubicTo(size.width*.4,size.height*.3,size.width*.62,size.height*.4,size.width*.75,size.height+10),
      Path()..moveTo(-10,size.height*.28)..lineTo(size.width+10,size.height*.65),
    ];
    for (final p in paths) { canvas.drawPath(p, road); canvas.drawPath(p, fine); }
  }
  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
