PROJE KURULUM (ADIM ADIM)

BU BELGENİN AMACI:
Bu projeyi (İstanbul Ulaşım Navigasyon Sistemi) başka bir geliştiricinin bilgisayarına eksiksiz olarak taşımak ve çalıştırmak için yapılması gerekenleri açıklar.

GEREKLİ DOSYALAR VE KLASÖRLER

Taşıma işlemine başlamadan önce aşağıdaki klasörleri bir USB belleğe veya Google Drive'a kopyalayın:

istanbul_ulasim Klasörü (İçinde app.py ve static klasörü olan ana proje)

data Klasörü (İçinde poi_district_overrides.json vb. olan veri klasörü)

requirements.txt (Bu dosyayı birazdan oluşturacağız)

veritabani_yedegi.sql (Veritabanı yedeği)

ADIM 1: YENİ BİLGİSAYARA GEREKLİ PROGRAMLARIN KURULMASI

Yeni bilgisayarda şu 3 şeyin kurulu olduğundan emin olun. Yoksa kurun:

Python 3.x: (Kurarken "Add Python to PATH" seçeneğini mutlaka işaretleyin!)

PostgreSQL: (Veritabanı sunucusu)

PostGIS Eklentisi: (PostgreSQL kurarken Stack Builder ile veya sonradan eklenmeli)

ADIM 2: VERİTABANININ TAŞINMASI (EN KRİTİK ADIM)

Projenin kalbi veritabanıdır. Var olan bilgisayardan alıp yeni bilgisayara yüklememiz lazım.

A. Var olan Bilgisayarda (Yedek Alma):

pgAdmin veya terminali açın.

Şu komutu çalıştırarak yedeği alın (Terminal/CMD'de):
pg_dump -U postgres -d istanbul_ulasim_db -F p -f veritabani_yedegi.sql
(Şifre sorarsa girin)

B. Yeni Bilgisayarda (Yedek Yükleme):

pgAdmin'i açın.

Databases üzerine sağ tıklayıp -> Create -> Database.

İsim olarak: istanbul_ulasim_db verin ve kaydedin.

Bu yeni veritabanına sağ tıklayıp Query Tool (Sorgu Aracı)'nı açın.

Şu komutu yazıp çalıştırın (PostGIS'i aktif etmek için şart):
CREATE EXTENSION postgis;
CREATE EXTENSION pgrouting;

Şimdi CMD (Komut Satırı)'nı açın ve yedeği yükleyin:
psql -U postgres -d istanbul_ulasim_db -f veritabani_yedegi.sql

ADIM 3: PYTHON KÜTÜPHANELERİNİN KURULMASI

Yeni bilgisayarda projenin çalışması için gerekli kütüphaneleri yüklemeliyiz.

Proje klasörünün içine (app.py'nin yanına) requirements.txt adında bir dosya oluşturun ve içine şunları yazın:

Flask
psycopg2
folium
branca


Yeni bilgisayarda CMD'yi açın. Proje klasörüne gidin (cd masaustu/proje_klasoru vb.)

Şu komutu yazın:
pip install -r requirements.txt

ADIM 4: KOD İÇİNDE YAPILMASI GEREKEN DEĞİŞİKLİKLER (CONFIG)

Yeni bilgisayardaki veritabanı şifresi mevcut bilgisayardakiyle aynı olmayabilir. app.py dosyasını açıp şu satırları bulup değiştirmelisiniz:

Dosya: app.py
Satır: Yaklaşık 60-80 arası (DB_CONFIG kısmı)

# SİZDEKİ KOD (Örnek):
DB_HOST = "localhost"
DB_NAME = "istanbul_ulasim_db"
DB_USER = "postgres"
DB_PASS = "12345"  <-- BURAYI DEĞİŞTİRİN!

# YENİ BİLGİSAYARA GÖRE DÜZENLEME:
# PostgreSQL şifresi neyse onu yazın.
# Eğer şifre bilinmiyorsa pgAdmin kurulumunda belirlenen şifredir.

ADIM 5: KLASÖR YOLLARININ KONTROLÜ

Projeniz data klasörüne ihtiyaç duyar.
Kodda şu satıra dikkat edin (app.py Satır 15-17 civarı):

POI_OVERRIDE_PATH = os.path.normpath(
    os.path.join(app.root_path, "..", "data", "poi_district_overrides.json")
)


Önemli Not:
Yeni bilgisayara klasörü kopyalarken yapıyı bozmayın.
Klasör yapısı şöyle OLMALIDIR:

Masaüstü/
└── PROJE-KLASORU/       <-- Ana Kapsayıcı
    ├── data/            <-- Veri klasörü burada
    │   └── poi_district_overrides.json
    └── istanbul_ulasim/ <-- Kod klasörü burada
        ├── app.py
        └── static/


Eğer sadece istanbul_ulasim klasörünü kopyalarsanız, sistem data klasörünü bulamaz ve hata verir. Mutlaka üst klasörle birlikte taşıyın.

ADIM 6: PROJEYİ ÇALIŞTIRMA

Her şey hazırsa:

CMD'yi açın.

istanbul_ulasim klasörünün içine girin.

Komutu yazın:
python app.py

Ekranda şunu görmelisiniz:
* Running on http://127.0.0.1:5000

Tarayıcıyı açıp bu adrese gidin.

OLASI HATALAR VE ÇÖZÜMLERİ

Hata: FATAL: password authentication failed for user "postgres"

Çözüm: app.py içindeki DB_PASS (şifre) yanlıştır. Doğru şifreyi öğrenip düzeltin.

Hata: function pgr_dijkstra does not exist

Çözüm: Veritabanına pgrouting eklentisi kurulmamış. Adım 2-B-5'i tekrar yapın.

Hata: FileNotFoundError: ... poi_district_overrides.json

Çözüm: data klasörünü kopyalamayı unuttunuz veya yanlış yere koydunuz. Adım 5'teki klasör yapısını kontrol edin.

Hata: ModuleNotFoundError: No module named 'folium'

Çözüm: Kütüphaneler yüklenmemiş. pip install folium yazarak elle yükleyin.
