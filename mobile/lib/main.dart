import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';

void main() => runApp(const MedizyApp());

const _teal = Color(0xFF159C98);
const _navy = Color(0xFF17354F);
const _categories = <_Category>[
  _Category('Hôpitaux', Icons.local_hospital_rounded, Color(0xFF3977D5)),
  _Category('Cliniques', Icons.apartment_rounded, Color(0xFF8B65C8)),
  _Category('Pharmacies', Icons.medication_rounded, Color(0xFF27A58C)),
  _Category('Laboratoires', Icons.science_rounded, Color(0xFFE59A37)),
  _Category('Médecins', Icons.person_search_rounded, Color(0xFFDE6F83)),
  _Category('Dentistes', Icons.mood_rounded, Color(0xFF4299B5)),
  _Category('Maternités', Icons.child_friendly_rounded, Color(0xFFCB78A6)),
  _Category('Autres', Icons.health_and_safety_rounded, Color(0xFF6E879B)),
];

class MedizyApp extends StatelessWidget {
  const MedizyApp({super.key});
  @override
  Widget build(BuildContext context) => MaterialApp(
    title: 'MEDIZY',
    debugShowCheckedModeBanner: false,
    theme: ThemeData(
      useMaterial3: true,
      colorScheme: ColorScheme.fromSeed(seedColor: _teal, primary: _teal),
      scaffoldBackgroundColor: const Color(0xFFF5F8FB),
      appBarTheme: const AppBarTheme(backgroundColor: Color(0xFFF5F8FB), foregroundColor: _navy),
    ),
    home: const DirectoryHome(),
  );
}

class DirectoryHome extends StatefulWidget {
  const DirectoryHome({super.key});
  @override
  State<DirectoryHome> createState() => _DirectoryHomeState();
}

class _DirectoryHomeState extends State<DirectoryHome> {
  int _tab = 0;
  String _query = '';
  String? _category;
  final _controller = MapController();

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Row(children: [
          Container(width: 38,height: 38,decoration: BoxDecoration(
            gradient: const LinearGradient(colors: [Color(0xFF20B8AA),Color(0xFF327FD1)]),
            borderRadius: BorderRadius.circular(13)),
            child: const Icon(Icons.location_on_rounded,color: Colors.white)),
          const SizedBox(width: 10),
          const Text('MEDIZY',style: TextStyle(fontWeight: FontWeight.w900,letterSpacing: 1.1)),
        ]),
        actions: [IconButton(tooltip:'Paramètres',onPressed:()=>_showInfo(context),icon:const Icon(Icons.tune_rounded))],
      ),
      body: SafeArea(child: _tab == 0 ? _home() : _tab == 1 ? _map() : _favorites()),
      bottomNavigationBar: NavigationBar(
        selectedIndex:_tab,
        onDestinationSelected:(v)=>setState(()=>_tab=v),
        destinations: const [
          NavigationDestination(icon:Icon(Icons.home_rounded),label:'Accueil'),
          NavigationDestination(icon:Icon(Icons.map_rounded),label:'Carte'),
          NavigationDestination(icon:Icon(Icons.bookmark_rounded),label:'Favoris'),
        ],
      ),
    );
  }

  Widget _home() => ListView(padding:const EdgeInsets.fromLTRB(18,8,18,24),children:[
    Container(padding:const EdgeInsets.all(20),decoration:BoxDecoration(
      gradient:const LinearGradient(colors:[Color(0xFF153B58),Color(0xFF187E89)]),
      borderRadius:BorderRadius.circular(26)),child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[
      const Text('Votre santé, près de vous',style:TextStyle(color:Colors.white,fontSize:23,fontWeight:FontWeight.w800)),
      const SizedBox(height:7),Text('Explorez les structures de santé en Algérie',style:TextStyle(color:Colors.white.withOpacity(.85))),
      const SizedBox(height:17),TextField(onChanged:(v)=>setState(()=>_query=v),decoration:InputDecoration(
        filled:true,fillColor:Colors.white,hintText:'Structure, spécialité, commune…',
        prefixIcon:const Icon(Icons.search_rounded,color:_teal),border:OutlineInputBorder(borderRadius:BorderRadius.circular(16),borderSide:BorderSide.none))),
      const SizedBox(height:14),InkWell(onTap:()=>setState(()=>_tab=1),child:const Row(children:[
        Icon(Icons.near_me_rounded,color:Color(0xFF9CE5D7),size:18),SizedBox(width:7),
        Text('Ouvrir la carte',style:TextStyle(color:Colors.white,fontWeight:FontWeight.w600)),
        Spacer(),Icon(Icons.arrow_forward_rounded,color:Colors.white)])),
    ])),
    const SizedBox(height:23),
    const Text('Explorer par catégorie',style:TextStyle(fontSize:18,fontWeight:FontWeight.w800,color:_navy)),
    const SizedBox(height:13),
    GridView.builder(shrinkWrap:true,physics:const NeverScrollableScrollPhysics(),itemCount:_categories.length,
      gridDelegate:const SliverGridDelegateWithFixedCrossAxisCount(crossAxisCount:4,crossAxisSpacing:9,mainAxisSpacing:12,childAspectRatio:.78),
      itemBuilder:(context,i){final c=_categories[i];return InkWell(onTap:()=>setState(()=>_category=c.name),child:Column(children:[
        Container(width:58,height:58,decoration:BoxDecoration(color:c.color.withOpacity(.12),borderRadius:BorderRadius.circular(19)),
          child:Icon(c.icon,color:c.color,size:27)),const SizedBox(height:7),
        Text(c.name,textAlign:TextAlign.center,maxLines:2,style:const TextStyle(fontSize:11.5,fontWeight:FontWeight.w600)),
      ]));}),
    const SizedBox(height:12),
    Row(children:[const Expanded(child:Text('Carte à proximité',style:TextStyle(fontSize:18,fontWeight:FontWeight.w800,color:_navy))),
      TextButton(onPressed:()=>setState(()=>_tab=1),child:const Text('Explorer'))]),
    InkWell(onTap:()=>setState(()=>_tab=1),child:Container(height:190,decoration:BoxDecoration(
      borderRadius:BorderRadius.circular(23),gradient:const LinearGradient(colors:[Color(0xFFDCEFEA),Color(0xFFE5EDF6)])),
      child:Stack(children:[Positioned.fill(child:CustomPaint(painter:_MapPreviewPainter())),
        Center(child:Container(padding:const EdgeInsets.symmetric(horizontal:17,vertical:12),decoration:BoxDecoration(
          color:Colors.white.withOpacity(.94),borderRadius:BorderRadius.circular(16)),child:const Row(mainAxisSize:MainAxisSize.min,children:[
          Icon(Icons.map_rounded,color:_teal),SizedBox(width:9),Text('Voir la carte',style:TextStyle(fontWeight:FontWeight.w700,color:_navy)),
        ])))]))),
    const SizedBox(height:18),_privacyCard(),
  ]);

  Widget _map() => Stack(children:[
    FlutterMap(mapController:_controller,options:const MapOptions(initialCenter:LatLng(35.95,0.10),initialZoom:8),
      children:[TileLayer(urlTemplate:'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
        userAgentPackageName:'dz.medizy.mobile'),const RichAttributionWidget(attributions:[TextSourceAttribution('© OpenStreetMap contributors')])]),
    Positioned(top:14,left:14,right:14,child:Material(elevation:3,borderRadius:BorderRadius.circular(16),child:TextField(
      onChanged:(v)=>setState(()=>_query=v),decoration:const InputDecoration(hintText:'Rechercher une structure…',
      prefixIcon:Icon(Icons.search_rounded),border:InputBorder.none,contentPadding:EdgeInsets.all(14))))),
    Positioned(bottom:18,left:16,right:16,child:Card(child:Padding(padding:const EdgeInsets.all(14),child:Row(children:[
      const Icon(Icons.info_outline_rounded,color:_teal),const SizedBox(width:10),const Expanded(child:Text(
      'Carte OpenStreetMap. Importez votre annuaire pour afficher les structures et leurs coordonnées.',
      style:TextStyle(fontSize:12))),IconButton(onPressed:()=>_controller.move(const LatLng(35.95,0.10),8),icon:const Icon(Icons.my_location_rounded))
    ])))),
  ]);

  Widget _favorites()=>Center(child:Padding(padding:const EdgeInsets.all(28),child:Column(mainAxisSize:MainAxisSize.min,children:[
    Icon(Icons.bookmark_border_rounded,size:54,color:_teal),const SizedBox(height:12),
    const Text('Vos favoris',style:TextStyle(fontSize:20,fontWeight:FontWeight.bold,color:_navy)),
    const SizedBox(height:7),const Text('Les structures enregistrées apparaîtront ici.',textAlign:TextAlign.center),
  ])));

  Widget _privacyCard()=>Container(padding:const EdgeInsets.all(15),decoration:BoxDecoration(color:Colors.white,borderRadius:BorderRadius.circular(18),),
    child:const Row(children:[Icon(Icons.lock_rounded,color:_teal),SizedBox(width:9),Expanded(child:Text(
      'Mode privé : aucune donnée médicale personnelle n’est demandée. L’annuaire local reste à importer.',
      style:TextStyle(fontSize:12,color:Color(0xFF526A7A))))]));

  void _showInfo(BuildContext context)=>showAboutDialog(context:context,applicationName:'MEDIZY',
    applicationVersion:'0.2.0',children:[const Text('Annuaire santé privé. Les données de structures ne sont pas encore importées.')]);
}

class _Category {
  const _Category(this.name,this.icon,this.color);
  final String name;final IconData icon;final Color color;
}

class _MapPreviewPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    final road = Paint()..color = Colors.white.withOpacity(.85)..strokeWidth = 9..style = PaintingStyle.stroke;
    final fine = Paint()..color = const Color(0xFFB7D5C8)..strokeWidth = 2..style = PaintingStyle.stroke;
    final p = ui.Path()..moveTo(-10,size.height*.72)..cubicTo(size.width*.25,size.height*.4,size.width*.35,size.height*.95,size.width*.58,size.height*.48)..cubicTo(size.width*.7,size.height*.2,size.width*.85,size.height*.65,size.width+10,size.height*.3);
    canvas.drawPath(p,road); canvas.drawPath(p,fine);
    final p2=ui.Path()..moveTo(size.width*.15,-5)..cubicTo(size.width*.4,size.height*.35,size.width*.5,size.height*.15,size.width*.75,size.height+5);
    canvas.drawPath(p2,road); canvas.drawPath(p2,fine);
  }
  @override bool shouldRepaint(covariant CustomPainter oldDelegate)=>false;
}
