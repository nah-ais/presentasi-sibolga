# WVI Pasca Bencana – Dashboard Analisa

Dashboard Streamlit 5 halaman untuk menganalisa kondisi anak pasca bencana banjir.

## Cara Menjalankan

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Struktur Folder
```
wvi_dashboard/
├── app.py              # Aplikasi utama Streamlit
├── requirements.txt    # Dependensi Python
├── README.md           # Dokumentasi ini
└── data/
    └── rawDataset_-_WVI.csv   # Dataset asli
```

## Halaman Dashboard
1. **🏠 Distribusi Umum** – Profil responden (wilayah, gender, usia)
2. **📚 Kondisi Pendidikan** – Dampak bencana pada pendidikan anak
3. **🛡️ Perlindungan Anak** – Keselamatan, trauma, kehilangan
4. **🏥 Kondisi Kesehatan** – Keluhan fisik dan penyakit
5. **🤝 Kesejahteraan Sosial** – Ekonomi, pangan, bantuan, dukungan sosial

## Fitur
- Filter interaktif (wilayah, gender, usia kelompok) di sidebar
- Klasifikasi otomatis tanggapan menggunakan keyword matching
- Visualisasi: bar chart, donut chart, sunburst, grouped bar
- Contoh kutipan asli per sub-kategori
