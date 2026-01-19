-- ================================================================
-- 1. GENEL DURUM VE SATIR SAYISI KARŞILAŞTIRMASI
-- ================================================================
-- Bu sorgu, her iki tablodaki toplam yol parçası (edge) sayısını ve
-- toplam yol uzunluğunu (km cinsinden) karşılaştırır.
-- Eğer satır sayıları birbirine çok yakınsa, yaya haritası araba haritasının kopyası olabilir.

SELECT 
    'araba (edges)' as tablo_adi, 
    COUNT(*) as satir_sayisi,
    ROUND(SUM(cost)::numeric / 1000.0, 2) as toplam_uzunluk_km
FROM edges
UNION ALL
SELECT 
    'yaya (edges_walk)' as tablo_adi, 
    COUNT(*) as satir_sayisi,
    ROUND(SUM(cost)::numeric / 1000.0, 2) as toplam_uzunluk_km
FROM edges_walk;


-- ================================================================
-- 2. ÖRTÜŞME ANALİZİ (BİREBİR AYNI YOLLAR)
-- ================================================================
-- Bu sorgu, yaya yollarının ne kadarının araba yollarıyla birebir aynı (geometrik olarak) olduğunu kontrol eder.
-- Eğer oran %100'e yakınsa, yaya için özel yollar (kaldırım, patika vb.) eksik demektir.

WITH match_stats AS (
    SELECT 
        (SELECT COUNT(*) FROM edges_walk) as total_walk,
        (SELECT COUNT(*) 
         FROM edges_walk w 
         JOIN edges e ON w.geometry = e.geometry
        ) as matching_edges
)
SELECT 
    total_walk as yaya_yol_sayisi,
    matching_edges as araba_ile_ayni_olan_sayi,
    ROUND((matching_edges::numeric / NULLIF(total_walk, 0) * 100), 1) as aynilik_orani_yuzde
FROM match_stats;


-- ================================================================
-- 3. ÖRNEK VERİ (İLK 10 KAYIT)
-- ================================================================
-- Tablolarınızda 'highway' (yol tipi) sütunu bulunmadığı için sadece
-- ID, Maliyet (Metre) ve Başlangıç Noktası bilgisini listeliyoruz.

SELECT 
    id, 
    cost as metre, 
    ST_AsText(ST_StartPoint(geometry)) as baslangic_noktasi
FROM edges_walk
LIMIT 10;


-- ================================================================
-- 4. HIGHWAY VE YENİDEN OLUŞTURMA HAKKINDA NOT
-- ================================================================
/*
NOT: Veritabanınızdaki 'edges' ve 'edges_walk' tablolarında 'highway', 'type' veya 'osm_id' 
gibi yolun türünü (otoban, patika, merdiven vb.) belirten sütunlar BULUNMAMAKTADIR.
Sadece rota hesabı için gerekli olan minimum veriler (id, kaynak, hedef, uzunluk, geometri) tutulmuştur.

Bu nedenle:
1. "Highway dağılımı" analizi SQL ile yapılamaz.
2. "Motorway/trunk" filtrelemesi SQL ile yapılamaz.
3. Ham veri veritabanında olmadığı için SQL ile 'CREATE TABLE' yaparak doğru yaya ağını üretemeyiz.

ÇÖZÜM:
Doğru yaya haritasını oluşturmak için Python scriptini (rebuild_walk_data.py) kullanarak 
OSM'den "yaya" (walk) modunda taze veri indirmemiz ve veritabanına kaydetmemiz gerekmektedir.
*/
