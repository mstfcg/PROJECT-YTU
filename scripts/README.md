# scripts/ README

Bu klasor, Istanbul odakli offline harita/POI projesi icin yardimci scriptleri icerir.
Uygulama calisirken otomatik kullanilmaz; veri hazirlama ve bakim icindir.

Calistirma
- Repo kok dizininden calistirin: `python scripts/<script_adi>.py`
- Bazi scriptler ek kutuphaneler ister (osmnx, geopandas, requests vb.).
- Ayarlar genellikle scriptlerin en ustunde yer alir (DB bilgisi, bbox, zoom).
- SQL dosyalari icin: `psql -d istanbul_gis -f scripts/<dosya>.sql` (veya DB arayuzu).

Onemli notlar
- Cogu script yerel Postgres/PostGIS ve `istanbul_gis` veritabanina baglanir.
- Tile indirme scriptleri internet ister ve `istanbul_ulasim/static/tiles` altina yazar.
- Seed/update scriptleri DB uzerinde kalici degisiklik yapar; sadece ihtiyac varsa calistirin.

Klasor yapisi ve tipik ciktilar
- Harita tile'lari: `istanbul_ulasim/static/tiles`
- Offline assetler: `istanbul_ulasim/static/vendor`
- DB tablolarina yazilanlar: `nodes`, `edges`, `nodes_walk`, `edges_walk`, `pois`, `osm_addresses`
- GeoJSON kaynaklari: genellikle `data/` altindan okunur (ornegin Istanbul.osm.geojson)

Sik kullanilan senaryolar
1) Offline harita tile seti guncelleme
   - `download_extra_assets.py` (CSS/JS vendor dosyalari)
   - `download_tiles_smart.py` (Istanbul bbox icin tile indir)
2) Yol agi yeniden olusturma
   - `load_network_to_postgis.py` (nodes/edges yukle)
   - `rebuild_walk_data.py` (walk tablolarini yenile)
3) POI ilce duzeltme
   - `update_pois_districts_from_addresses.py`

Script gruplari ve amaclari

Tile/asset
- `download_extra_assets.py`: offline vendor assetlerini indirir.
- `download_tiles.py`: basit OSM tile indirme (bbox + zoom).
- `download_tiles_v2.py`: tile indirme varyanti (farkli parametreler).
- `download_tiles_v3.py`: tile indirme varyanti (farkli parametreler).
- `download_tiles_smart.py`: Istanbul bbox icin konfigurasyonlu tile indirme.
- `calc_tiles.py`: tile araligi/sayi hesaplama yardimcisi.

Seed / veri hazirlama
- `load_network_to_postgis.py`: yol agini (nodes/edges) PostGIS'e yukler.
- `rebuild_walk_data.py`: yurume agi tablolarini yeniden olusturur.
- `build_osm_addresses.py`: GeoJSON'dan `osm_addresses` tablosunu olusturur/gunceller.
- `seed_hotels_from_geojson.py`: GeoJSON'dan otel POI'leri seeder.
- `seed_metrobus_final.py`: Metrobus duraklarini seeder.
- `seed_marmaray_final.py`: Marmaray istasyonlarini seeder.
- `seed_m4_metro.py`: M4 metro istasyonlarini seeder.
- `seeded_all_metros_archived.py`: arsivlenmis metro seed scripti (referans).
- `update_pois_districts_from_addresses.py`: POI ilce alanlarini adres verisiyle gunceller.

GeoJSON / ilce sinirlari
- `create_fallback_geojsons.py`: bilinen ilce koordinatlarindan basit fallback GeoJSON kutulari uretir.
- `update_geojsons.py`: secili ilceler icin daha detayli hardcoded GeoJSON sinirlari yazar.
- `check_districts.py`: admin_level=6 sinirlarini listeler ve "Kartal" eslesmelerini kontrol eder.
- `check_kartal.py`: Kartal icin hizli DB sorgusu (multipolygons).
- `check_missing_districts.py`: osm_istanbul_multipolygons icinde eksik ilceleri arar.
- `find_best_district_matches.py`: en buyuk alanli eslesmelere gore ilce isim map onerir.
- `analyze_districts_deep.py`: hedef ilceler icin alan bazli detayli DB analizini yapar.
- `app_decompiled.py`: cache'den alinmis app.py yedegi (referans).

Walk network / DB kontrol
- `check_tables.py`: public schema tablo listesini listeler.
- `check_columns.py`: `edges` ve `edges_walk` kolon adlarini listeler.
- `check_types.py`: `edges_walk` kolon tiplerini ve ornek source/target degerlerini gosterir.
- `inspect_walk_data.py`: `nodes_walk` / `edges_walk` sayilari, kolonlar ve ornek kayitlari inceler.
- `check_walk_coverage.py`: `nodes_walk` extent ve Kartal/Maltepe + Besiktas/Taksim icin ornek rota testi yapar.
- `check_osm_points.py`: `osm_istanbul_points` icinde "Esenkent" arar.
- `check_esenkent.py`: `pois` ve `osm_points` tablolarinda "Esenkent" arar.

SQL / analiz / referans
- `check_walk_network.sql`: `edges` ile `edges_walk` sayi/uzunluk karsilastirmasi, geometri aynilik orani, ornek kayitlar.
- `database_setup_walk.sql`: `nodes_walk` / `edges_walk` schema notlari, indeksler ve ornek sorgular.

Debug / kontrol / test
- `debug_styles.py`: kategori-stil eslestirmesi ve ikon dogrulama kontrolu.
- `debug_nodes.py`: belirli node id'leri ve geocode sonucunu inceler.
- `inspect_osm.py`: hizli OSM/GeoJSON inceleme araci.
- `verify_marmaray.py`: Marmaray veri dogrulama kontrolleri.
- `test_geocode_pendik.py`: geocode fallback testi (Pendik).
- `test_route_specific.py`: belirli noktalar icin rota testi.
