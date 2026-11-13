import 'dart:convert';
import 'dart:io' show gzip;
import 'package:path/path.dart' as p;
import 'package:sqflite/sqflite.dart';
import 'package:csv/csv.dart';
import 'package:flutter/foundation.dart' show compute;
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
import 'assistant_page.dart';

const navy = Color(0xFF49364F);
const teal = Color(0xFFC05A83);
const mint = Color(0xFFFBE8EF);
const canvas = Color(0xFFFFF8FA);
const muted = Color(0xFF8C7A8D);

void main() => runApp(const MedizyApp());

List<Map<String,String>> _parseDirectoryIsolate(List<int> input) {
  final text = utf8.decode(gzip.decode(input), allowMalformed: true);
  final rows = const CsvToListConverter(shouldParseNumbers: false).convert(text);
  if (rows.length < 2) return <Map<String,String>>[];
  final headers = rows.first.map((v) => v.toString().trim()).toList();
  String norm(String v) => v.toLowerCase().replaceAll('é','e').replaceAll('è','e').replaceAll('ê','e').replaceAll('ë','e').replaceAll('à','a').replaceAll('â','a').replaceAll('î','i').replaceAll('ï','i').replaceAll('ô','o').replaceAll('ù','u').replaceAll('û','u').replaceAll('ç','c').replaceAll(RegExp(r'[^a-z0-9]'), '');
  // Preserve every source column in SQLite; do not silently discard directory fields.
  final keep = List<int>.generate(headers.length,(i)=>i);
  final result=<Map<String,String>>[];
  for(final row in rows.skip(1)) {
    if(row.every((v)=>v.toString().trim().isEmpty)) continue;
    final item=<String,String>{};
    for(final i in keep) { if(i<headers.length&&i<row.length) item[headers[i]]=row[i].toString().trim(); }
    if(item.values.any((v)=>v.isNotEmpty)) result.add(item);
  }
  return result;
}
Future<List<Map<String,String>>> _parseDirectory(List<int> bytes)=>compute(_parseDirectoryIsolate,bytes);

class MedizyApp extends StatelessWidget {
  const MedizyApp({super.key});
  @override Widget build(BuildContext context) {
    final scheme=ColorScheme.fromSeed(seedColor:teal,brightness:Brightness.light,surface:Colors.white);
    return MaterialApp(
      title:'MEDIZY',debugShowCheckedModeBanner:false,
      theme:ThemeData(
        useMaterial3:true,colorScheme:scheme,scaffoldBackgroundColor:canvas,
        navigationBarTheme:NavigationBarThemeData(
          backgroundColor:Colors.white,indicatorColor:mint,
          labelTextStyle:WidgetStateProperty.resolveWith((states)=>TextStyle(
            fontSize:11,fontWeight:states.contains(WidgetState.selected)?FontWeight.w800:FontWeight.w500,
            color:states.contains(WidgetState.selected)?teal:muted,
          )),
        ),
      ),
      home:const Home(),
    );
  }
}

class S {
  S(this.d);
  final Map<String,String> d;
  String get name=>g(['nom','name','structure','etablissement','établissement','designation','désignation'])??'Structure de santé';
  String get type=>g(['categorie','catégorie','type','category','nature'])??'Autres';
  String get wilaya=>g(['wilaya'])??'';
  String get commune=>g(['commune','ville','city'])??'';
  String get address=>g(['adresse','address'])??'';
  String? g(List<String> aliases) {
    String n(String x)=>x.toLowerCase().replaceAll('é','e').replaceAll('è','e').replaceAll('ê','e').replaceAll('ë','e').replaceAll('à','a').replaceAll('â','a').replaceAll('î','i').replaceAll('ï','i').replaceAll('ô','o').replaceAll('ù','u').replaceAll('û','u').replaceAll('ç','c').replaceAll(RegExp(r'[^a-z0-9]'),'');
    for(final e in d.entries) { if(aliases.any((x)=>n(x)==n(e.key))&&e.value.trim().isNotEmpty)return e.value.trim(); }
    for(final e in d.entries) { if(aliases.any((x)=>n(e.key).contains(n(x)))&&e.value.trim().isNotEmpty)return e.value.trim(); }
    return null;
  }
  double? numv(List<String> aliases) { final v=g(aliases); return v==null?null:double.tryParse(v.replaceAll(',','.').replaceAll(RegExp(r'[^0-9.\-]'),'')); }
  double? get lat=>numv(['latitude','lat']);
  double? get lon=>numv(['longitude','lon','lng']);
  String get text=>d.values.join(' ').toLowerCase();
}

class Home extends StatefulWidget { const Home({super.key}); @override State<Home> createState()=>HS(); }
class HS extends State<Home> {
  List<S> data=[];
  final Set<int> fav={};
  String q='',cat='Toutes';
  int tab=0;
  bool loading=true;
  String? err;
  final mc=MapController();
  bool _didFitMap=false;

  @override void initState(){super.initState();load();}
  Future<void> load() async {
    try {
      final dbPath=await getDatabasesPath();
      final db=await openDatabase(
        p.join(dbPath,'medizy_directory.db'),
        version:1,
        onCreate:(db,version) async {
          await db.execute('CREATE TABLE facilities (id INTEGER PRIMARY KEY AUTOINCREMENT, payload TEXT NOT NULL, search_text TEXT NOT NULL, name TEXT NOT NULL, type TEXT NOT NULL, wilaya TEXT NOT NULL, commune TEXT NOT NULL, lat REAL, lon REAL)');
          await db.execute('CREATE INDEX facilities_type_idx ON facilities(type)');
          await db.execute('CREATE INDEX facilities_geo_idx ON facilities(lat,lon)');
        },
      );
      var count=Sqflite.firstIntValue(await db.rawQuery('SELECT COUNT(*) FROM facilities'))??0;
      if(count==0) {
        final bytes=(await rootBundle.load('assets/Annuaire_Sante_Algerie_UNIQUE_MASTER_PREMIUM.csv.gz')).buffer.asUint8List();
        final rows=await _parseDirectory(bytes);
        if(rows.isEmpty) throw Exception('Le fichier CSV ne contient aucune structure.');
        await db.transaction((txn) async {
          for(var start=0;start<rows.length;start+=500) {
            final batch=txn.batch();
            for(final row in rows.skip(start).take(500)) {
              final s=S(row);
              final lat=s.lat,lon=s.lon;
              batch.insert('facilities',{
                'payload':jsonEncode(row),
                'search_text':row.values.join(' ').toLowerCase(),
                'name':s.name,
                'type':s.type,
                'wilaya':s.wilaya,
                'commune':s.commune,
                'lat':lat,
                'lon':lon,
              });
            }
            await batch.commit(noResult:true);
          }
        });
        count=rows.length;
      }
      final stored=await db.query('facilities',columns:['payload'],orderBy:'id');
      final loaded=stored.map((r)=>S(Map<String,String>.from(jsonDecode(r['payload'] as String) as Map))).toList(growable:false);
      if(loaded.isEmpty) throw Exception('La base MEDIZY est vide après import.');
      if(mounted)setState(()=>data=loaded);
    } catch(e) { if(mounted)setState(()=>err='Chargement de la base MEDIZY impossible : $e'); }
    finally { if(mounted)setState(()=>loading=false); }
  }
  List<String> get cats=>['Toutes',...{for(final s in data) if(s.type.isNotEmpty)s.type}.toList()..sort()];
  List<S> get filtered=>data.where((s)=>(cat=='Toutes'||s.type.toLowerCase()==cat.toLowerCase())&&(q.isEmpty||s.text.contains(q.toLowerCase()))).toList();

  @override Widget build(BuildContext context)=>Scaffold(
    body:tab==1?map():tab==2?list(data.where((s)=>fav.contains(data.indexOf(s))).toList()):tab==3?const AssistantPage():home(),
    bottomNavigationBar:NavigationBar(height:70,selectedIndex:tab,onDestinationSelected:(v)=>setState(()=>tab=v),destinations:const [
      NavigationDestination(icon:Icon(Icons.home_outlined),selectedIcon:Icon(Icons.home_rounded),label:'Annuaire'),
      NavigationDestination(icon:Icon(Icons.map_outlined),selectedIcon:Icon(Icons.map_rounded),label:'Carte'),
      NavigationDestination(icon:Icon(Icons.bookmark_border_rounded),selectedIcon:Icon(Icons.bookmark_rounded),label:'Favoris'),
      NavigationDestination(icon:Icon(Icons.auto_awesome_outlined),selectedIcon:Icon(Icons.auto_awesome),label:'Assistant IA'),
    ]),
  );

  Widget home()=>SafeArea(bottom:false,child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[
    Padding(padding:const EdgeInsets.fromLTRB(20,12,20,16),child:Row(children:[
      Container(width:46,height:46,decoration:BoxDecoration(gradient:const LinearGradient(colors:[Color(0xFFE6A0B8),Color(0xFFB75B85)]),borderRadius:BorderRadius.circular(15),boxShadow:[BoxShadow(color:teal.withOpacity(.2),blurRadius:14,offset:const Offset(0,6))]),child:const Icon(Icons.shield_outlined,color:Colors.white,size:27)),
      const SizedBox(width:12),
      const Expanded(child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[
        Text('MEDIZY',style:TextStyle(color:navy,fontSize:21,letterSpacing:1.5,fontWeight:FontWeight.w900)),
        Text('Votre santé, plus proche.',style:TextStyle(color:muted,fontSize:12,fontWeight:FontWeight.w500)),
      ])),
      Container(padding:const EdgeInsets.symmetric(horizontal:11,vertical:8),decoration:BoxDecoration(color:Colors.white,borderRadius:BorderRadius.circular(30),border:Border.all(color:const Color(0xFFF2E5EB))),child:const Row(children:[Icon(Icons.location_on_outlined,color:teal,size:15),SizedBox(width:4),Text('Algérie',style:TextStyle(color:navy,fontSize:11,fontWeight:FontWeight.w700))])),
    ])),
    Padding(padding:const EdgeInsets.symmetric(horizontal:18),child:Container(width:double.infinity,padding:const EdgeInsets.fromLTRB(19,18,19,17),decoration:BoxDecoration(gradient:const LinearGradient(colors:[Color(0xFF765477),Color(0xFFC05A83)],begin:Alignment.topLeft,end:Alignment.bottomRight),borderRadius:BorderRadius.circular(23),boxShadow:[BoxShadow(color:navy.withOpacity(.17),blurRadius:20,offset:const Offset(0,9))]),child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[
      const Text('Trouvez les soins\nprès de chez vous.',style:TextStyle(color:Colors.white,fontSize:22,height:1.18,fontWeight:FontWeight.w800)),
      const SizedBox(height:8),
      Text(loading?'Préparation de votre annuaire de santé…':'${data.length} structures référencées dans l’annuaire',style:const TextStyle(color:Color(0xFFFFEAF1),fontSize:12,fontWeight:FontWeight.w500)),
      const SizedBox(height:16),
      TextField(onChanged:(v)=>setState(()=>q=v),style:const TextStyle(color:navy,fontSize:14,fontWeight:FontWeight.w500),decoration:InputDecoration(hintText:'Médecin, clinique, commune, wilaya…',hintStyle:const TextStyle(color:Color(0xFF9B8998),fontSize:12),prefixIcon:const Icon(Icons.search_rounded,color:teal),filled:true,fillColor:Colors.white,contentPadding:const EdgeInsets.symmetric(vertical:15),border:OutlineInputBorder(borderRadius:BorderRadius.circular(15),borderSide:BorderSide.none),enabledBorder:OutlineInputBorder(borderRadius:BorderRadius.circular(15),borderSide:BorderSide.none))),
    ]))),
    Padding(padding:const EdgeInsets.fromLTRB(20,18,20,9),child:Row(children:[
      const Expanded(child:Text('Explorer par catégorie',style:TextStyle(color:navy,fontSize:15,fontWeight:FontWeight.w800))),
      Text('${filtered.length} résultats',style:const TextStyle(color:muted,fontSize:11,fontWeight:FontWeight.w600)),
    ])),
    SizedBox(height:166,child:GridView.builder(
      padding:const EdgeInsets.symmetric(horizontal:18),
      gridDelegate:const SliverGridDelegateWithFixedCrossAxisCount(crossAxisCount:2,mainAxisExtent:74,crossAxisSpacing:9,mainAxisSpacing:8),
      itemCount:cats.length,
      itemBuilder:(context,index){
        final value=cats[index],selected=cat==value;
        final count=value=='Toutes'?data.length:data.where((s)=>s.type.toLowerCase()==value.toLowerCase()).length;
        return Material(
          color:Colors.white,
          borderRadius:BorderRadius.circular(17),
          child:InkWell(
            borderRadius:BorderRadius.circular(17),
            onTap:()=>setState(()=>cat=value),
            child:Container(
              padding:const EdgeInsets.symmetric(horizontal:11,vertical:9),
              decoration:BoxDecoration(
                borderRadius:BorderRadius.circular(17),
                border:Border.all(color:selected?teal.withOpacity(.55):const Color(0xFFF0E4EA),width:selected?1.4:1),
                boxShadow:[BoxShadow(color:navy.withOpacity(.025),blurRadius:8,offset:const Offset(0,3))],
              ),
              child:Row(children:[
                Container(width:43,height:43,decoration:BoxDecoration(
                  gradient:LinearGradient(colors:selected?[const Color(0xFFE6A0B8),const Color(0xFFB75B85)]:[mint,const Color(0xFFFFF2F6)]),
                  borderRadius:BorderRadius.circular(14),
                ),child:Icon(value=='Toutes'?Icons.local_hospital_outlined:iconFor(value),color:selected?Colors.white:teal,size:23)),
                const SizedBox(width:9),
                Expanded(child:Column(mainAxisAlignment:MainAxisAlignment.center,crossAxisAlignment:CrossAxisAlignment.start,children:[
                  Text(value,maxLines:1,overflow:TextOverflow.ellipsis,style:TextStyle(color:navy,fontSize:11,fontWeight:selected?FontWeight.w900:FontWeight.w700)),
                  const SizedBox(height:3),
                  Text('$count structures',style:const TextStyle(color:muted,fontSize:9,fontWeight:FontWeight.w600)),
                ])),
              ]),
            ),
          ),
        );
      },
    )),
    const Padding(padding:EdgeInsets.fromLTRB(20,15,20,8),child:Text('Structures de santé',style:TextStyle(color:navy,fontSize:15,fontWeight:FontWeight.w800))),
    Expanded(child:list(filtered)),
  ]));

  IconData iconFor(String type) {
    final v=type.toLowerCase();
    if(v.contains('pharm'))return Icons.medication_outlined;
    if(v.contains('labor')||v.contains('analys'))return Icons.science_outlined;
    if(v.contains('dent'))return Icons.sentiment_satisfied_alt_outlined;
    if(v.contains('clin'))return Icons.business_outlined;
    if(v.contains('hospital')||v.contains('hôpital'))return Icons.apartment_rounded;
    if(v.contains('cabinet')||v.contains('médecin'))return Icons.person_outline_rounded;
    return Icons.health_and_safety_outlined;
  }

  Widget list(List<S> items) {
    if(loading)return const Center(child:Column(mainAxisAlignment:MainAxisAlignment.center,children:[
      SizedBox(width:34,height:34,child:CircularProgressIndicator(color:teal,strokeWidth:3)),
      SizedBox(height:16),Text('Préparation de MEDIZY',style:TextStyle(color:navy,fontWeight:FontWeight.w700)),
      SizedBox(height:5),Text('Chargement de l’annuaire de santé…',style:TextStyle(color:muted,fontSize:12)),
    ]));
    if(err!=null)return Center(child:Padding(padding:const EdgeInsets.all(24),child:Column(mainAxisSize:MainAxisSize.min,children:[
      const Icon(Icons.cloud_off_outlined,color:muted,size:38),const SizedBox(height:12),Text(err!,textAlign:TextAlign.center),
      const SizedBox(height:12),OutlinedButton.icon(onPressed:(){setState((){loading=true;err=null;});load();},icon:const Icon(Icons.refresh_rounded),label:const Text('Réessayer')),
    ])));
    if(items.isEmpty)return Center(child:Column(mainAxisAlignment:MainAxisAlignment.center,children:[
      const Icon(Icons.search_off_rounded,color:Color(0xFFB7A5B1),size:40),const SizedBox(height:10),
      Text(data.isEmpty?'Annuaire indisponible':'Aucun résultat trouvé',style:const TextStyle(color:muted,fontWeight:FontWeight.w600)),
    ]));
    return ListView.builder(padding:const EdgeInsets.fromLTRB(16,0,16,18),itemCount:items.length,itemBuilder:(context,index){
      final s=items[index],id=data.indexOf(items[index]),saved=fav.contains(id);
      return Container(margin:const EdgeInsets.only(bottom:10),decoration:BoxDecoration(color:Colors.white,borderRadius:BorderRadius.circular(17),border:Border.all(color:const Color(0xFFF3E9EE)),boxShadow:[BoxShadow(color:navy.withOpacity(.035),blurRadius:12,offset:const Offset(0,4))]),child:InkWell(borderRadius:BorderRadius.circular(17),onTap:()=>showDetails(s),child:Padding(padding:const EdgeInsets.all(13),child:Row(children:[
        Container(width:49,height:49,decoration:BoxDecoration(color:mint,borderRadius:BorderRadius.circular(15)),child:Icon(iconFor(s.type),color:teal,size:24)),
        const SizedBox(width:12),
        Expanded(child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[
          Text(s.name,maxLines:2,overflow:TextOverflow.ellipsis,style:const TextStyle(color:navy,fontSize:13,height:1.25,fontWeight:FontWeight.w800)),
          const SizedBox(height:5),Text(s.type,maxLines:1,overflow:TextOverflow.ellipsis,style:const TextStyle(color:teal,fontSize:10,fontWeight:FontWeight.w700)),
          if(s.commune.isNotEmpty||s.wilaya.isNotEmpty)Padding(padding:const EdgeInsets.only(top:4),child:Row(children:[
            const Icon(Icons.location_on_outlined,color:muted,size:12),const SizedBox(width:3),
            Expanded(child:Text([s.commune,s.wilaya].where((v)=>v.isNotEmpty).join(' · '),maxLines:1,overflow:TextOverflow.ellipsis,style:const TextStyle(color:muted,fontSize:10))),
          ])),
        ])),
        IconButton(tooltip:saved?'Retirer des favoris':'Ajouter aux favoris',visualDensity:VisualDensity.compact,onPressed:()=>setState(()=>saved?fav.remove(id):fav.add(id)),icon:Icon(saved?Icons.bookmark_rounded:Icons.bookmark_border_rounded,color:saved?teal:const Color(0xFF9AAAB5))),
      ]))));
    });
  }

  void showDetails(S s)=>showModalBottomSheet<void>(context:context,isScrollControlled:true,backgroundColor:Colors.transparent,builder:(ctx)=>Container(constraints:BoxConstraints(maxHeight:MediaQuery.of(ctx).size.height*.78),decoration:const BoxDecoration(color:Colors.white,borderRadius:BorderRadius.vertical(top:Radius.circular(26))),child:SafeArea(child:Column(mainAxisSize:MainAxisSize.min,children:[
    const SizedBox(height:10),Container(width:38,height:4,decoration:BoxDecoration(color:const Color(0xFFEBDDE5),borderRadius:BorderRadius.circular(10))),
    Padding(padding:const EdgeInsets.fromLTRB(20,20,20,12),child:Row(children:[
      Container(width:48,height:48,decoration:BoxDecoration(color:mint,borderRadius:BorderRadius.circular(15)),child:Icon(iconFor(s.type),color:teal,size:24)),
      const SizedBox(width:12),Expanded(child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[
        Text(s.name,style:const TextStyle(color:navy,fontSize:16,fontWeight:FontWeight.w800)),const SizedBox(height:3),
        Text(s.type,style:const TextStyle(color:teal,fontSize:12,fontWeight:FontWeight.w700)),
      ])),
    ])),
    const Divider(height:1,color:Color(0xFFECF1F4)),
    Flexible(child:ListView(shrinkWrap:true,padding:const EdgeInsets.fromLTRB(20,10,20,24),children:s.d.entries.where((e)=>e.value.trim().isNotEmpty).take(40).map((e)=>Padding(padding:const EdgeInsets.symmetric(vertical:9),child:Row(crossAxisAlignment:CrossAxisAlignment.start,children:[
      Expanded(flex:2,child:Text(e.key,style:const TextStyle(color:muted,fontSize:12,fontWeight:FontWeight.w600))),
      Expanded(flex:3,child:Text(e.value,style:const TextStyle(color:navy,fontSize:12,fontWeight:FontWeight.w600))),
    ]))).toList())),
  ]))));

  Widget map() {
    if(loading)return const Center(child:CircularProgressIndicator(color:teal));
    if(err!=null)return list(const <S>[]);
    final points=filtered.where((s)=>s.lat!=null&&s.lon!=null&&s.lat!>=18&&s.lat!<=38&&s.lon!>=-9&&s.lon!<=12&&(s.lat!=0||s.lon!=0)).toList();
    if(points.isNotEmpty&&!_didFitMap) {
      _didFitMap=true;
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if(!mounted)return;
        final bounds=LatLngBounds.fromPoints(points.map((s)=>LatLng(s.lat!,s.lon!)).toList());
        mc.fitCamera(CameraFit.bounds(bounds:bounds,padding:const EdgeInsets.all(52)));
      });
    }
    return FlutterMap(mapController:mc,options:const MapOptions(initialCenter:LatLng(28.0,1.6),initialZoom:4.2),children:[
      TileLayer(urlTemplate:'https://tile.openstreetmap.org/{z}/{x}/{y}.png',userAgentPackageName:'dz.medizy.mobile'),
      MarkerLayer(markers:points.map((s)=>Marker(point:LatLng(s.lat!,s.lon!),width:42,height:46,child:GestureDetector(onTap:()=>showDetails(s),child:const Icon(Icons.location_on_rounded,color:teal,size:38)))).toList()),
      const RichAttributionWidget(attributions:[TextSourceAttribution('© OpenStreetMap contributors')]),
      Positioned(top:12,left:12,right:12,child:Material(elevation:3,borderRadius:BorderRadius.circular(15),child:TextField(onChanged:(v)=>setState((){q=v;_didFitMap=false;}),decoration:InputDecoration(prefixIcon:const Icon(Icons.search_rounded,color:teal),hintText:'Rechercher une structure…',filled:true,fillColor:Colors.white,border:OutlineInputBorder(borderRadius:BorderRadius.circular(15),borderSide:BorderSide.none))))),
      Positioned(bottom:14,left:14,right:14,child:Container(padding:const EdgeInsets.symmetric(horizontal:16,vertical:13),decoration:BoxDecoration(color:Colors.white,borderRadius:BorderRadius.circular(15),boxShadow:[BoxShadow(color:navy.withOpacity(.12),blurRadius:16,offset:const Offset(0,5))]),child:Row(children:[
        const Icon(Icons.place_outlined,color:teal),const SizedBox(width:9),Expanded(child:Text(points.isEmpty?'Aucune coordonnée GPS fiable dans cette sélection':'${points.length} structures géolocalisées sur ${data.length}',style:const TextStyle(color:navy,fontWeight:FontWeight.w700,fontSize:12))),
      ]))),
    ]);
  }
}
