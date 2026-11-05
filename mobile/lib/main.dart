import 'dart:convert';
import 'dart:io';
import 'package:csv/csv.dart';
import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart' show compute;
import 'package:flutter/services.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
void main()=>runApp(const MedizyApp());

List<Map<String,String>> _parseDirectoryIsolate(List<int> input) {
      final text = utf8.decode(gzip.decode(input), allowMalformed: true);
      final rows = const CsvToListConverter(shouldParseNumbers: false).convert(text);
      if (rows.length < 2) return <Map<String,String>>[];
      final headers = rows.first.map((v) => v.toString().trim()).toList();
      final result = <Map<String,String>>[];
      for (final row in rows.skip(1)) {
        if (row.every((v) => v.toString().trim().isEmpty)) continue;
        final item = <String,String>{};
        for (var i=0; i<headers.length && i<row.length; i++) {
          item[headers[i]] = row[i].toString().trim();
        }
        result.add(item);
      }
      return result;
  }

Future<List<Map<String,String>>> _parseDirectory(List<int> bytes) => compute(_parseDirectoryIsolate, bytes);

const teal=Color(0xff159c98),navy=Color(0xff17354f);
class MedizyApp extends StatelessWidget{const MedizyApp({super.key});@override Widget build(BuildContext c)=>MaterialApp(title:'MEDIZY',debugShowCheckedModeBanner:false,theme:ThemeData(useMaterial3:true,colorScheme:ColorScheme.fromSeed(seedColor:teal)),home:const Home());}
class S{
 S(this.d);final Map<String,String>d;
 String get name=>g(['nom','name','structure','etablissement','établissement','designation','désignation'])??'Structure de santé';
 String get type=>g(['categorie','catégorie','type','category','nature'])??'Autres';
 String get wilaya=>g(['wilaya'])??'';String get commune=>g(['commune','ville','city'])??'';String get address=>g(['adresse','address'])??'';
 String? g(List<String>a){String n(String x)=>x.toLowerCase().replaceAll(RegExp(r'[^a-z0-9]'),'');for(final e in d.entries){if(a.any((x)=>n(x)==n(e.key))&&e.value.trim().isNotEmpty)return e.value.trim();}for(final e in d.entries){if(a.any((x)=>n(e.key).contains(n(x)))&&e.value.trim().isNotEmpty)return e.value.trim();}return null;}
 double? numv(List<String>a){final v=g(a);return v==null?null:double.tryParse(v.replaceAll(',','.').replaceAll(RegExp(r'[^0-9.\-]'),''));}
 double? get lat=>numv(['latitude','lat']);double? get lon=>numv(['longitude','lon','lng']);String get text=>d.values.join(' ').toLowerCase();
}
class Home extends StatefulWidget{const Home({super.key});@override State<Home>createState()=>HS();}
class HS extends State<Home>{
 List<S> data=[];Set<int> fav={};String q='',cat='Toutes';int tab=0;bool loading=true;String? err;final mc=MapController();
 @override void initState(){super.initState();load();}
 Future<void> load() async {
  try {
    final bytes = (await rootBundle.load('assets/Annuaire_Sante_Algerie_UNIQUE_MASTER_PREMIUM.csv.gz')).buffer.asUint8List();
    final rows = await _parseDirectory(bytes);
    if (rows.isEmpty) throw Exception('CSV vide');
    final parsed = rows.map(S.new).toList(growable: false);
    if (mounted) setState(() => data = parsed);
  } catch (e) {
    if (mounted) setState(() => err = 'Chargement impossible : $e');
  } finally {
    if (mounted) setState(() => loading = false);
  }
}

 List<String>get cats=>['Toutes',...{for(final s in data)s.type}.where((x)=>x.isNotEmpty).toList()..sort()];
 List<S>get filtered=>data.where((s)=>(cat=='Toutes'||s.type.toLowerCase()==cat.toLowerCase())&&(q.isEmpty||s.text.contains(q.toLowerCase()))).toList();
 @override Widget build(BuildContext c)=>Scaffold(appBar:AppBar(title:const Text('MEDIZY',style:TextStyle(fontWeight:FontWeight.w900))),body:tab==1?map():tab==2?list(data.where((s)=>fav.contains(data.indexOf(s))).toList()):home(),bottomNavigationBar:NavigationBar(selectedIndex:tab,onDestinationSelected:(v)=>setState(()=>tab=v),destinations:const [NavigationDestination(icon:Icon(Icons.home),label:'Annuaire'),NavigationDestination(icon:Icon(Icons.map),label:'Carte'),NavigationDestination(icon:Icon(Icons.bookmark),label:'Favoris')]));
 Widget home()=>Column(children:[Padding(padding:const EdgeInsets.all(12),child:TextField(onChanged:(v)=>setState(()=>q=v),decoration:InputDecoration(hintText:'Structure, commune, wilaya…',prefixIcon:const Icon(Icons.search,color:teal),filled:true,border:OutlineInputBorder(borderRadius:BorderRadius.circular(14),borderSide:BorderSide.none)))),SizedBox(height:46,child:ListView(scrollDirection:Axis.horizontal,children:cats.map((x)=>Padding(padding:const EdgeInsets.symmetric(horizontal:3),child:ChoiceChip(label:Text(x),selected:cat==x,onSelected:(_)=>setState(()=>cat=x)))).toList())),Expanded(child:list(filtered))]);
 Widget list(List<S> xs){
  if(loading)return const Center(child:CircularProgressIndicator());
  if(err!=null)return Center(child:Text(err!));
  if(xs.isEmpty)return Center(child:Text(data.isEmpty?'Annuaire absent':'Aucun résultat'));
  return ListView.builder(itemCount:xs.length,itemBuilder:(context,i){
   final s=xs[i]; final id=data.indexOf(s);
   return Card(child:ListTile(
    leading:const Icon(Icons.local_hospital,color:teal),
    title:Text(s.name,maxLines:2),
    subtitle:Text([s.type,s.commune,s.wilaya,s.address].where((x)=>x.isNotEmpty).join(' • '),maxLines:2),
    trailing:IconButton(icon:Icon(fav.contains(id)?Icons.bookmark:Icons.bookmark_border),onPressed:(){setState((){if(fav.contains(id)){fav.remove(id);}else{fav.add(id);}});}),
    onTap:(){showModalBottomSheet(context:context,builder:(sheetContext)=>SafeArea(child:SingleChildScrollView(padding:const EdgeInsets.all(16),child:Column(crossAxisAlignment:CrossAxisAlignment.start,children:[Text(s.name,style:const TextStyle(fontSize:20,fontWeight:FontWeight.bold)),...s.d.entries.where((e)=>e.value.isNotEmpty).take(40).map((e)=>Text(e.key+': '+e.value))]))));}
   ));
  });
 }

 Widget map(){final ps=filtered.where((s)=>s.lat!=null&&s.lon!=null&&s.lat!>=-90&&s.lat!<=90&&s.lon!>=-180&&s.lon!<=180).toList();return FlutterMap(mapController:mc,options:const MapOptions(initialCenter:LatLng(36.75,3.05),initialZoom:5),children:[TileLayer(urlTemplate:'https://tile.openstreetmap.org/{z}/{x}/{y}.png',userAgentPackageName:'dz.medizy.mobile'),MarkerLayer(markers:ps.map((s)=>Marker(point:LatLng(s.lat!,s.lon!),child:const Icon(Icons.location_on,color:teal,size:36))).toList()),const RichAttributionWidget(attributions:[TextSourceAttribution('© OpenStreetMap contributors')]),Positioned(top:8,left:8,right:8,child:Material(child:TextField(onChanged:(v)=>setState(()=>q=v),decoration:const InputDecoration(prefixIcon:Icon(Icons.search),hintText:'Rechercher',border:InputBorder.none)))),Positioned(bottom:8,left:8,right:8,child:Card(child:Padding(padding:const EdgeInsets.all(12),child:Text('${ps.length} géolocalisées / ${data.length} structures'))))]);}
}