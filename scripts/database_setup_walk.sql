-- İstanbul Yaya Yolu Ağı (Walking Network) Veritabanı Kurulumu ve Analiz Sorguları

-- 1. Tablo Yapıları (Python scripti tarafından otomatik oluşturulur, referans için buradadır)

-- nodes_walk: Yaya yolu düğümleri (kavşaklar, noktalar)
-- id: SERIAL PRIMARY KEY (pgRouting için 1'den başlayan unique integer ID)
-- osm_id: BIGINT (OpenStreetMap orijinal ID'si)
-- geometry: GEOMETRY(Point, 4326)

-- edges_walk: Yaya yolu kenarları (yollar)
-- id: SERIAL PRIMARY KEY
-- source: INTEGER (Başlangıç düğümü ID'si -> nodes_walk.id)
-- target: INTEGER (Bitiş düğümü ID'si -> nodes_walk.id)
-- cost: DOUBLE PRECISION (Maliyet/Mesafe - metre cinsinden)
-- reverse_cost: DOUBLE PRECISION (Ters yön maliyeti - yaya yolları genelde çift yönlüdür)
-- osm_id: TEXT (OpenStreetMap yol ID'si)
-- geometry: GEOMETRY(LineString, 4326)

-- 2. İndeksler (Performans için kritik)
-- Bu indeksler script tarafından oluşturulmuştur.
-- CREATE INDEX idx_nodes_walk_geom ON nodes_walk USING GIST(geometry);
-- CREATE INDEX idx_edges_walk_geom ON edges_walk USING GIST(geometry);
-- CREATE INDEX idx_edges_walk_source ON edges_walk(source);
-- CREATE INDEX idx_edges_walk_target ON edges_walk(target);

-- 3. Örnek Rota Sorgusu (pgRouting)
-- Kartal - Maltepe arası örnek (ID'ler dinamik değişebilir, Nearest Node ile bulunmalı)
/*
SELECT * FROM pgr_dijkstra(
    'SELECT id, source, target, cost, reverse_cost FROM edges_walk',
    (SELECT id FROM nodes_walk ORDER BY geometry <-> ST_SetSRID(ST_Point(29.1897, 40.8887), 4326) LIMIT 1), -- Kartal Start
    (SELECT id FROM nodes_walk ORDER BY geometry <-> ST_SetSRID(ST_Point(29.1309, 40.9248), 4326) LIMIT 1), -- Maltepe End
    true
);
*/

-- 4. Kapsama Analizi
-- Hangi ilçelerin verisi var? (Yaklaşık bounding box kontrolü)
SELECT ST_Extent(geometry) as bbox FROM nodes_walk;

-- 5. Bağlantı Kontrolü (Dead-end analizi)
-- Bir düğüme giren/çıkan yol sayısı
/*
SELECT id, cnt FROM (
    SELECT source as id, count(*) as cnt FROM edges_walk GROUP BY source
    UNION ALL
    SELECT target as id, count(*) as cnt FROM edges_walk GROUP BY target
) t LIMIT 10;
*/
