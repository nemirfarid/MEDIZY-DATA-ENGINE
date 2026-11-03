import fs from "node:fs";
import path from "node:path";
import { sante } from "@geoalgeria/sante";
import { cliniques } from "@geoalgeria/cliniques";
import { pharmacies } from "@geoalgeria/pharmacies";
const out="data/staging/geoalgeria"; fs.mkdirSync(out,{recursive:true});
const sources=[["geoalgeria_sante",sante(),"Ministry of Health registry; GeoAlgeria geocoding"],["geoalgeria_cliniques",cliniques(),"OpenStreetMap ODbL via GeoAlgeria"],["geoalgeria_pharmacies",pharmacies(),"OpenStreetMap ODbL via GeoAlgeria"]];
const summary={generated_at:new Date().toISOString(),production_database_modified:false,sources:[]};
const esc=v=>"\""+String(v??"").replaceAll("\"","\"\"")+"\"";
for(const [source,rows,provenance] of sources){
 const mapped=rows.map((r,i)=>({source,source_id:String(r.id??r.osm_id??i),name:r.name??r.name_fr??r.name_ar??"",name_fr:r.name_fr??"",name_ar:r.name_ar??"",category:r.type??r.type_label_fr??r.category??"",wilaya_code:r.wilaya_code??"",wilaya:r.wilaya??"",commune_code:r.commune_code??"",commune:r.commune??"",latitude:r.lat??r.latitude??"",longitude:r.lng??r.lon??r.longitude??"",phone:r.phone??"",website:r.website??"",address:r.address??"",source_refs:JSON.stringify(r.refs??{}),source_provenance:provenance,review_status:"candidate_needs_human_review"}));
 const fields=Object.keys(mapped[0]??{source:"",source_id:"",name:""});
 fs.writeFileSync(path.join(out,source+".json"),JSON.stringify(mapped,null,2));
 fs.writeFileSync(path.join(out,source+".csv"),[fields.map(esc).join(","),...mapped.map(r=>fields.map(k=>esc(r[k])).join(","))].join("\n"));
 summary.sources.push({source,rows:mapped.length,unique_source_ids:new Set(mapped.map(r=>r.source_id)).size,provenance});
}
fs.writeFileSync(path.join(out,"manifest.json"),JSON.stringify(summary,null,2)); console.log(JSON.stringify(summary,null,2));