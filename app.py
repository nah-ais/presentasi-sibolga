import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import re
from collections import Counter

# ─── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="WVI Dashboard – Analisa Pasca Bencana",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    
    .main-header {
        background: linear-gradient(135deg, #1a3a5c 0%, #2563eb 50%, #0ea5e9 100%);
        padding: 2.5rem 2rem;
        border-radius: 16px;
        margin-bottom: 2rem;
        color: white;
        text-align: center;
    }
    .main-header h1 { font-size: 2.2rem; font-weight: 700; margin: 0 0 0.5rem 0; }
    .main-header p  { font-size: 1rem; opacity: 0.85; margin: 0; }
    
    .metric-card {
        background: white;
        border: 1px solid #e5e7eb;
        border-radius: 12px;
        padding: 1.25rem 1.5rem;
        text-align: center;
        box-shadow: 0 1px 4px rgba(0,0,0,.06);
        transition: box-shadow .2s;
    }
    .metric-card:hover { box-shadow: 0 4px 16px rgba(0,0,0,.10); }
    .metric-card .value { font-size: 2rem; font-weight: 700; color: #1d4ed8; }
    .metric-card .label { font-size: 0.8rem; color: #6b7280; margin-top: .25rem; text-transform: uppercase; letter-spacing: .05em; }
    
    .section-title {
        font-size: 1.25rem;
        font-weight: 600;
        color: #1e293b;
        padding-bottom: 0.5rem;
        border-bottom: 3px solid #2563eb;
        margin-bottom: 1.25rem;
    }
    
    .quote-card {
        background: #f0f9ff;
        border-left: 4px solid #0ea5e9;
        border-radius: 0 8px 8px 0;
        padding: 0.9rem 1.1rem;
        margin-bottom: 0.7rem;
        font-size: 0.88rem;
        color: #1e3a5f;
        line-height: 1.5;
    }
    .quote-card .tag {
        display: inline-block;
        background: #dbeafe;
        color: #1d4ed8;
        border-radius: 20px;
        padding: 0.15rem 0.6rem;
        font-size: 0.72rem;
        font-weight: 600;
        margin-bottom: 0.4rem;
    }
    
    .category-badge {
        display: inline-block;
        padding: 0.3rem 0.75rem;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
        margin: 0.15rem;
    }
    
    .sidebar-info {
        background: #f8fafc;
        border-radius: 10px;
        padding: 1rem;
        font-size: 0.82rem;
        color: #374151;
        margin-top: 1rem;
    }
    
    div[data-testid="stMetric"] {
        background: white;
        border: 1px solid #e5e7eb;
        border-radius: 12px;
        padding: 1rem;
        box-shadow: 0 1px 4px rgba(0,0,0,.05);
    }
</style>
""", unsafe_allow_html=True)

# ─── Load & Clean Data ─────────────────────────────────────────────────────────
@st.cache_data
def load_data():
    df = pd.read_csv("data/rawDataset_-_WVI.csv")
    
    # Standardise column names
    df.columns = [c.strip() for c in df.columns]
    
    # Drop fully-empty rows
    df = df.dropna(how="all").copy()
    
    # Clean text columns
    for col in ["Umur", "Jenis Kelamin", "Wilayah", "Lembaga", "Tanggapan"]:
        df[col] = df[col].astype(str).str.strip()
        df[col] = df[col].replace({"nan": "", "None": ""})
    
    # Drop rows with empty Tanggapan
    df = df[df["Tanggapan"] != ""].copy()
    
    # Normalise Umur labels
    umur_map = {
        "8 sampai 11 tahun": "8–11 tahun",
        "12 sampai 15 tahun": "12–15 tahun",
        "15 sampai 17 tahun": "15–17 tahun",
    }
    df["Umur"] = df["Umur"].replace(umur_map)
    
    # Normalise gender
    jk_map = {
        "Laki laki": "Laki-laki",
        "Laki-laki": "Laki-laki",
        "Perempuan": "Perempuan",
    }
    df["Jenis Kelamin"] = df["Jenis Kelamin"].replace(jk_map)
    
    return df.reset_index(drop=True)


# ─── Keyword Categorisation ────────────────────────────────────────────────────
KEYWORDS = {
    # 1. PENDIDIKAN
    "pendidikan": {
        "Ketidakhadiran / Tidak Sekolah": [
            "tidak sekolah", "tidak bisa sekolah", "tidak bisa belajar",
            "belajar darurat", "belajar di posko", "sekolah darurat",
            "berhenti sekolah", "tidak lanjut kuliah", "tidak lanjut sekolah",
            "sekolah hancur", "tidak bisa ke sekolah", "tidak bisa merasakan belajar",
        ],
        "Kekhawatiran Pendidikan": [
            "ujian", "ujian ukk", "ujian sekolah", "melanjutkan sekolah",
            "kelanjutan sekolah", "kondisi sekolah", "sekolah bukan meja",
            "menulis menggunakan paha", "buku sekolah", "buku-buku untuk sekolah",
            "belajar normal", "belajar", "sekolah", "kuliah",
        ],
        "Hambatan Pendidikan Akibat Bencana": [
            "impian terhambat", "sekolah pun sangat darurat", "buku hanyut",
            "tidak bisa ujian", "posko belajar", "sekolah di posko",
        ],
    },

    # 2. PERLINDUNGAN ANAK
    "perlindungan": {
        "Kehilangan & Korban Jiwa": [
            "hanyut", "meninggal", "korban jiwa", "nyawa hilang", "korban",
            "orang hanyut", "mati", "kehilangan orang tua", "kehilangan keluarga",
            "mama hanyut", "ayah hanyut", "adik hanyut", "belum ditemukan",
            "jenazah", "kehilangan nyawa",
        ],
        "Ketakutan & Trauma": [
            "takut", "trauma", "cemas", "gelisah", "panik", "khawatir",
            "ketakutan", "sedih", "nangis", "menangis", "teriak",
            "tidak aman", "terpuruk", "tidak tenang", "mimpi buruk",
        ],
        "Keselamatan & Evakuasi": [
            "menyelamatkan", "lari ke tempat aman", "evakuasi", "selamat",
            "pengungsian", "posko", "zona aman", "menyelamatkan diri",
            "menyelamatkan adik", "menyelamatkan mama", "lari ke posko",
        ],
        "Kehilangan Rumah & Harta": [
            "rumah hancur", "rumah hanyut", "tidak punya tempat tinggal",
            "rumah roboh", "kehilangan rumah", "barang hanyut",
            "barang kesayangan", "handphone hilang", "harta benda",
        ],
    },

    # 3. KESEHATAN
    "kesehatan": {
        "Sakit Fisik (Anggota Tubuh)": [
            "bahu sakit", "pinggang sakit", "sakit pinggang", "perut sakit",
            "sakit perut", "kaki sakit", "tangan sakit", "pegal", "capek",
            "lelah", "kelelahan", "kram", "kesemutan", "lemas",
            "kesakitan", "nyeri", "terluka", "terkilir",
        ],
        "Penyakit & Gejala": [
            "gatal-gatal", "gatal", "diare", "demam", "panas", "mual", "muntah",
            "sakit perut", "masuk angin", "pusing", "kepala pusing",
            "kurang enak badan", "sakit selama 1 minggu",
        ],
        "Kedinginan & Kondisi Lingkungan": [
            "kedinginan", "dingin", "basah", "lumpur", "kotor", "air kotor",
            "tidak nyaman", "kondisi dingin",
        ],
        "Akses Air Bersih": [
            "kesulitan mencari air", "air mati", "air susah", "air bersih",
            "angkat air", "mengangkat air", "sumur lumpur", "air tidak ada",
            "ambil air", "mengambil air",
        ],
    },

    # 4. KESEJAHTERAAN SOSIAL
    "kesejahteraan": {
        "Kondisi Ekonomi": [
            "ekonomi susah", "ekonomi menurun", "pekerjaan sulit",
            "sulit mencari pekerjaan", "pencarian sulit", "harga mahal",
            "bahan mahal", "tidak punya uang", "tidak punya tempat tinggal",
            "perekonomian terhambat", "perekonomian tidak membaik",
            "pekerjaan orangtua makin sulit",
        ],
        "Ketahanan Pangan": [
            "makan indomie", "makan mie instan", "makanan kurang sehat",
            "bahan makanan menipis", "kelaparan", "kekurangan makanan",
            "susah bahan pangan", "makan tidak teratur", "serba instan",
            "bosan makan", "menu sama", "air minum susah",
        ],
        "Bantuan & Dukungan Pemerintah": [
            "pemerintah", "bantuan", "posko pengungsi", "beras bulog",
            "beras bantuan", "makanan bantuan", "tenda pengungsian",
            "pak bupati", "pak prabowo", "bapak desa",
        ],
        "Dukungan Sosial & Kebersamaan": [
            "bercerita", "bertemu keluarga", "bertemu teman", "saling membantu",
            "kebersamaan", "cerita ke teman", "berkumpul", "menceritakan",
            "ingin bertemu", "mau cerita", "tuhan", "berdoa", "saudara",
        ],
    },
}


def classify_row(text: str):
    """Return dict of category -> sub-category list for a given response."""
    text_lower = text.lower()
    results = {}
    for cat, subcats in KEYWORDS.items():
        matched = []
        for subcat, kws in subcats.items():
            for kw in kws:
                if kw in text_lower:
                    if subcat not in matched:
                        matched.append(subcat)
                    break
        if matched:
            results[cat] = matched
    return results


@st.cache_data
def classify_data(df):
    df = df.copy()
    df["categories"] = df["Tanggapan"].apply(classify_row)
    
    for cat in ["pendidikan", "perlindungan", "kesehatan", "kesejahteraan"]:
        df[f"is_{cat}"] = df["categories"].apply(lambda x: cat in x)
        df[f"sub_{cat}"] = df["categories"].apply(
            lambda x: x.get(cat, [])
        )
    return df


# ─── Colour Palettes ───────────────────────────────────────────────────────────
PALETTE_MAIN = ["#2563eb", "#0ea5e9", "#06b6d4", "#8b5cf6", "#d946ef", "#f59e0b", "#10b981"]
COLOR_GENDER = {"Perempuan": "#d946ef", "Laki-laki": "#2563eb"}
COLOR_WILAYAH = {"Sibolga Utara": "#2563eb", "Tapsel": "#0ea5e9", "Tapteng": "#8b5cf6"}
COLOR_UMUR = {"8–11 tahun": "#06b6d4", "12–15 tahun": "#2563eb", "15–17 tahun": "#8b5cf6"}


# ─── Helper: Donut Chart ───────────────────────────────────────────────────────
def donut(labels, values, colors, title, hole=0.55):
    fig = go.Figure(go.Pie(
        labels=labels, values=values,
        hole=hole,
        marker=dict(colors=colors, line=dict(color="white", width=2)),
        textinfo="percent+label",
        hovertemplate="%{label}: %{value} (%{percent})<extra></extra>",
    ))
    fig.update_layout(
        title=dict(text=title, font=dict(size=14, color="#1e293b"), x=0.5),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
        margin=dict(t=50, b=60, l=20, r=20),
        height=320,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def hbar(categories, values, color="#2563eb", title="", xlabel="Jumlah"):
    df_tmp = pd.DataFrame({"Kategori": categories, "Jumlah": values})
    df_tmp = df_tmp.sort_values("Jumlah")
    fig = px.bar(
        df_tmp, x="Jumlah", y="Kategori", orientation="h",
        color_discrete_sequence=[color],
        title=title,
        labels={"Jumlah": xlabel, "Kategori": ""},
    )
    fig.update_traces(marker_line_color="white", marker_line_width=0.5)
    fig.update_layout(
        height=max(280, len(categories)*50),
        margin=dict(t=50, b=30, l=20, r=30),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=True, gridcolor="#f0f0f0"),
        yaxis=dict(tickfont=dict(size=11)),
        title=dict(font=dict(size=14, color="#1e293b")),
    )
    return fig


def show_quotes(df_sub, n=4, tag=""):
    samples = df_sub["Tanggapan"].dropna().sample(min(n, len(df_sub)), random_state=42).tolist()
    for q in samples:
        st.markdown(
            f'<div class="quote-card"><span class="tag">{tag}</span><br>{q}</div>',
            unsafe_allow_html=True,
        )


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════════════
df_raw  = load_data()
df      = classify_data(df_raw)

# Sidebar navigation
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/5/5f/World_Vision_logo.svg/200px-World_Vision_logo.svg.png", width=140)
    st.markdown("---")
    page = st.radio(
        "📊 Navigasi Dashboard",
        [
            "🏠 Distribusi Umum",
            "📚 Kondisi Pendidikan",
            "🛡️ Perlindungan Anak",
            "🏥 Kondisi Kesehatan",
            "🤝 Kesejahteraan Sosial",
        ],
    )
    st.markdown("---")
    st.markdown(
        '<div class="sidebar-info">'
        '<b>Dataset</b>: WVI Pasca Bencana Banjir<br>'
        f'<b>Total Responden</b>: {len(df)}<br>'
        '<b>Wilayah</b>: Sibolga Utara, Tapsel, Tapteng<br>'
        '<b>Lembaga</b>: World Vision Indonesia'
        '</div>',
        unsafe_allow_html=True,
    )


# ─── Sidebar Filter ────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🔍 Filter Data")
    sel_wilayah = st.multiselect(
        "Wilayah", df["Wilayah"].unique().tolist(),
        default=df["Wilayah"].unique().tolist()
    )
    sel_gender = st.multiselect(
        "Jenis Kelamin", df["Jenis Kelamin"].unique().tolist(),
        default=df["Jenis Kelamin"].unique().tolist()
    )
    sel_umur = st.multiselect(
        "Kelompok Usia", df["Umur"].unique().tolist(),
        default=df["Umur"].unique().tolist()
    )

df_f = df[
    df["Wilayah"].isin(sel_wilayah) &
    df["Jenis Kelamin"].isin(sel_gender) &
    df["Umur"].isin(sel_umur)
].copy()


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 1 – Distribusi Umum
# ══════════════════════════════════════════════════════════════════════════════
if page == "🏠 Distribusi Umum":
    st.markdown("""
    <div class="main-header">
      <h1>🌊 Distribusi Umum Responden</h1>
      <p>Gambaran keseluruhan profil responden pasca bencana banjir – WVI 2025</p>
    </div>
    """, unsafe_allow_html=True)

    # KPI Row
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Responden", len(df_f))
    c2.metric("Lokasi / Wilayah", df_f["Wilayah"].nunique())
    c3.metric("Perempuan", int((df_f["Jenis Kelamin"] == "Perempuan").sum()))
    c4.metric("Laki-laki", int((df_f["Jenis Kelamin"] == "Laki-laki").sum()))
    c5.metric("Kelompok Usia", df_f["Umur"].nunique())

    st.markdown("---")

    # Row 1 – Lokasi & Gender
    col1, col2 = st.columns(2)

    with col1:
        st.markdown('<div class="section-title">📍 Jumlah Responden per Wilayah</div>', unsafe_allow_html=True)
        wil_cnt = df_f["Wilayah"].value_counts().reset_index()
        wil_cnt.columns = ["Wilayah", "Jumlah"]
        fig_wil = px.bar(
            wil_cnt, x="Wilayah", y="Jumlah",
            color="Wilayah",
            color_discrete_map=COLOR_WILAYAH,
            text="Jumlah",
            labels={"Jumlah": "Jumlah Responden"},
        )
        fig_wil.update_traces(textposition="outside", marker_line_width=0)
        fig_wil.update_layout(
            showlegend=False, height=320,
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(t=20, b=30), yaxis=dict(showgrid=True, gridcolor="#f0f0f0"),
        )
        st.plotly_chart(fig_wil, use_container_width=True)

    with col2:
        st.markdown('<div class="section-title">⚥ Perbandingan Gender</div>', unsafe_allow_html=True)
        g_cnt = df_f["Jenis Kelamin"].value_counts()
        fig_g = donut(
            g_cnt.index.tolist(), g_cnt.values.tolist(),
            [COLOR_GENDER.get(l, "#ccc") for l in g_cnt.index],
            "Distribusi Jenis Kelamin",
        )
        st.plotly_chart(fig_g, use_container_width=True)

    # Row 2 – Usia & Wilayah × Gender
    col3, col4 = st.columns(2)

    with col3:
        st.markdown('<div class="section-title">👶 Distribusi Kelompok Usia</div>', unsafe_allow_html=True)
        u_cnt = df_f["Umur"].value_counts()
        fig_u = donut(
            u_cnt.index.tolist(), u_cnt.values.tolist(),
            [COLOR_UMUR.get(l, "#ccc") for l in u_cnt.index],
            "Kelompok Usia",
        )
        st.plotly_chart(fig_u, use_container_width=True)

    with col4:
        st.markdown('<div class="section-title">📊 Wilayah × Jenis Kelamin</div>', unsafe_allow_html=True)
        cross = df_f.groupby(["Wilayah", "Jenis Kelamin"]).size().reset_index(name="Jumlah")
        fig_cross = px.bar(
            cross, x="Wilayah", y="Jumlah", color="Jenis Kelamin",
            barmode="group",
            color_discrete_map=COLOR_GENDER,
            text="Jumlah",
        )
        fig_cross.update_traces(textposition="outside", marker_line_width=0)
        fig_cross.update_layout(
            height=320, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(t=20, b=30), yaxis=dict(showgrid=True, gridcolor="#f0f0f0"),
            legend=dict(orientation="h", yanchor="bottom", y=-0.3, x=0.3),
        )
        st.plotly_chart(fig_cross, use_container_width=True)

    # Row 3 – Usia × Wilayah & Kategori Coverage
    col5, col6 = st.columns(2)

    with col5:
        st.markdown('<div class="section-title">🎂 Kelompok Usia × Wilayah</div>', unsafe_allow_html=True)
        cross2 = df_f.groupby(["Wilayah", "Umur"]).size().reset_index(name="Jumlah")
        fig_uage = px.bar(
            cross2, x="Wilayah", y="Jumlah", color="Umur",
            barmode="stack",
            color_discrete_map=COLOR_UMUR,
            text="Jumlah",
        )
        fig_uage.update_traces(textposition="inside", marker_line_width=0)
        fig_uage.update_layout(
            height=320, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(t=20, b=30), yaxis=dict(showgrid=True, gridcolor="#f0f0f0"),
            legend=dict(orientation="h", yanchor="bottom", y=-0.3, x=0.2),
        )
        st.plotly_chart(fig_uage, use_container_width=True)

    with col6:
        st.markdown('<div class="section-title">📌 Cakupan Kategori Kondisi</div>', unsafe_allow_html=True)
        cats = {
            "Pendidikan": df_f["is_pendidikan"].sum(),
            "Perlindungan Anak": df_f["is_perlindungan"].sum(),
            "Kesehatan": df_f["is_kesehatan"].sum(),
            "Kesejahteraan Sosial": df_f["is_kesejahteraan"].sum(),
        }
        fig_cov = go.Figure(go.Bar(
            x=list(cats.keys()),
            y=list(cats.values()),
            marker_color=["#2563eb", "#d946ef", "#10b981", "#f59e0b"],
            text=list(cats.values()),
            textposition="outside",
        ))
        fig_cov.update_layout(
            height=320, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(t=20, b=30), showlegend=False,
            yaxis=dict(showgrid=True, gridcolor="#f0f0f0"),
            xaxis=dict(tickfont=dict(size=12)),
        )
        st.plotly_chart(fig_cov, use_container_width=True)

    # Row 4 – Gender × Usia
    st.markdown('<div class="section-title">⚥🎂 Distribusi Gender per Kelompok Usia</div>', unsafe_allow_html=True)
    cross3 = df_f.groupby(["Umur", "Jenis Kelamin"]).size().reset_index(name="Jumlah")
    fig_gu = px.bar(
        cross3, x="Umur", y="Jumlah", color="Jenis Kelamin",
        barmode="group", color_discrete_map=COLOR_GENDER, text="Jumlah",
    )
    fig_gu.update_traces(textposition="outside", marker_line_width=0)
    fig_gu.update_layout(
        height=280, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(t=20, b=30), yaxis=dict(showgrid=True, gridcolor="#f0f0f0"),
        legend=dict(orientation="h", yanchor="bottom", y=-0.35, x=0.35),
    )
    st.plotly_chart(fig_gu, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 2 – Kondisi Pendidikan
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📚 Kondisi Pendidikan":
    st.markdown("""
    <div class="main-header" style="background: linear-gradient(135deg,#1e3a5f,#2563eb,#06b6d4);">
      <h1>📚 Kondisi Pendidikan</h1>
      <p>Dampak bencana terhadap akses dan kelangsungan pendidikan anak</p>
    </div>
    """, unsafe_allow_html=True)

    cat = "pendidikan"
    subcats_list = list(KEYWORDS[cat].keys())
    df_cat = df_f[df_f[f"is_{cat}"]].copy()

    # KPI
    c1, c2, c3 = st.columns(3)
    c1.metric("Responden Terkait Pendidikan", len(df_cat))
    c2.metric("% dari Total", f"{len(df_cat)/len(df_f)*100:.1f}%")
    c3.metric("Sub-Kategori", len(subcats_list))

    st.markdown("---")
    col1, col2 = st.columns([1.2, 1])

    with col1:
        st.markdown('<div class="section-title">📊 Distribusi Sub-Kategori Pendidikan</div>', unsafe_allow_html=True)
        sub_counts = Counter()
        for subs in df_cat[f"sub_{cat}"]:
            sub_counts.update(subs)
        if sub_counts:
            fig_sub = hbar(
                list(sub_counts.keys()), list(sub_counts.values()),
                color="#2563eb", title="Frekuensi Sub-Kategori"
            )
            st.plotly_chart(fig_sub, use_container_width=True)

    with col2:
        st.markdown('<div class="section-title">🌍 Distribusi per Wilayah</div>', unsafe_allow_html=True)
        wil_sub = df_cat.groupby("Wilayah").size().reset_index(name="Jumlah")
        fig_wil2 = px.pie(wil_sub, names="Wilayah", values="Jumlah",
                          color="Wilayah", color_discrete_map=COLOR_WILAYAH,
                          hole=0.5)
        fig_wil2.update_layout(height=300, margin=dict(t=20, b=50),
                                paper_bgcolor="rgba(0,0,0,0)",
                                legend=dict(orientation="h", y=-0.2, x=0.2))
        st.plotly_chart(fig_wil2, use_container_width=True)

    # Breakdown
    col3, col4 = st.columns(2)
    with col3:
        st.markdown('<div class="section-title">⚥ Gender</div>', unsafe_allow_html=True)
        g2 = df_cat["Jenis Kelamin"].value_counts()
        fig_g2 = donut(g2.index.tolist(), g2.values.tolist(),
                       [COLOR_GENDER.get(l, "#ccc") for l in g2.index], "")
        st.plotly_chart(fig_g2, use_container_width=True)

    with col4:
        st.markdown('<div class="section-title">🎂 Kelompok Usia</div>', unsafe_allow_html=True)
        u2 = df_cat["Umur"].value_counts()
        fig_u2 = donut(u2.index.tolist(), u2.values.tolist(),
                       [COLOR_UMUR.get(l, "#ccc") for l in u2.index], "")
        st.plotly_chart(fig_u2, use_container_width=True)

    # Quotes per sub-category
    st.markdown("---")
    st.markdown('<div class="section-title">💬 Contoh Tanggapan per Sub-Kategori</div>', unsafe_allow_html=True)
    for subcat, kws in KEYWORDS[cat].items():
        mask = df_f["Tanggapan"].str.lower().apply(
            lambda t: any(k in t for k in kws)
        )
        df_sub = df_f[mask]
        if len(df_sub) == 0:
            continue
        with st.expander(f"📌 {subcat}  ({len(df_sub)} responden)", expanded=False):
            show_quotes(df_sub, n=5, tag=subcat)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 3 – Perlindungan Anak
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🛡️ Perlindungan Anak":
    st.markdown("""
    <div class="main-header" style="background: linear-gradient(135deg,#7c1c6f,#d946ef,#f59e0b);">
      <h1>🛡️ Perlindungan Anak</h1>
      <p>Ancaman keselamatan, trauma psikologis, dan kerentanan anak dalam bencana</p>
    </div>
    """, unsafe_allow_html=True)

    cat = "perlindungan"
    subcats_list = list(KEYWORDS[cat].keys())
    df_cat = df_f[df_f[f"is_{cat}"]].copy()

    c1, c2, c3 = st.columns(3)
    c1.metric("Responden Terkait Perlindungan", len(df_cat))
    c2.metric("% dari Total", f"{len(df_cat)/len(df_f)*100:.1f}%")
    c3.metric("Sub-Kategori", len(subcats_list))

    st.markdown("---")
    col1, col2 = st.columns([1.2, 1])

    with col1:
        st.markdown('<div class="section-title">📊 Distribusi Sub-Kategori Perlindungan</div>', unsafe_allow_html=True)
        sub_counts = Counter()
        for subs in df_cat[f"sub_{cat}"]:
            sub_counts.update(subs)
        if sub_counts:
            fig_sub = hbar(
                list(sub_counts.keys()), list(sub_counts.values()),
                color="#d946ef", title="Frekuensi Sub-Kategori"
            )
            st.plotly_chart(fig_sub, use_container_width=True)

    with col2:
        st.markdown('<div class="section-title">🌍 Distribusi per Wilayah</div>', unsafe_allow_html=True)
        wil_sub = df_cat.groupby("Wilayah").size().reset_index(name="Jumlah")
        fig_wil2 = px.pie(wil_sub, names="Wilayah", values="Jumlah",
                          color="Wilayah", color_discrete_map=COLOR_WILAYAH, hole=0.5)
        fig_wil2.update_layout(height=300, margin=dict(t=20, b=50),
                                paper_bgcolor="rgba(0,0,0,0)",
                                legend=dict(orientation="h", y=-0.2, x=0.2))
        st.plotly_chart(fig_wil2, use_container_width=True)

    col3, col4 = st.columns(2)
    with col3:
        st.markdown('<div class="section-title">⚥ Gender</div>', unsafe_allow_html=True)
        g2 = df_cat["Jenis Kelamin"].value_counts()
        fig_g2 = donut(g2.index.tolist(), g2.values.tolist(),
                       [COLOR_GENDER.get(l, "#ccc") for l in g2.index], "")
        st.plotly_chart(fig_g2, use_container_width=True)

    with col4:
        st.markdown('<div class="section-title">🎂 Kelompok Usia</div>', unsafe_allow_html=True)
        u2 = df_cat["Umur"].value_counts()
        fig_u2 = donut(u2.index.tolist(), u2.values.tolist(),
                       [COLOR_UMUR.get(l, "#ccc") for l in u2.index], "")
        st.plotly_chart(fig_u2, use_container_width=True)

    st.markdown("---")
    st.markdown('<div class="section-title">💬 Contoh Tanggapan per Sub-Kategori</div>', unsafe_allow_html=True)
    for subcat, kws in KEYWORDS[cat].items():
        mask = df_f["Tanggapan"].str.lower().apply(lambda t: any(k in t for k in kws))
        df_sub = df_f[mask]
        if len(df_sub) == 0:
            continue
        with st.expander(f"📌 {subcat}  ({len(df_sub)} responden)", expanded=False):
            show_quotes(df_sub, n=5, tag=subcat)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 4 – Kondisi Kesehatan
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🏥 Kondisi Kesehatan":
    st.markdown("""
    <div class="main-header" style="background: linear-gradient(135deg,#065f46,#10b981,#06b6d4);">
      <h1>🏥 Kondisi Kesehatan</h1>
      <p>Keluhan fisik, penyakit, dan akses sanitasi anak pasca bencana</p>
    </div>
    """, unsafe_allow_html=True)

    cat = "kesehatan"
    subcats_list = list(KEYWORDS[cat].keys())
    df_cat = df_f[df_f[f"is_{cat}"]].copy()

    c1, c2, c3 = st.columns(3)
    c1.metric("Responden Terkait Kesehatan", len(df_cat))
    c2.metric("% dari Total", f"{len(df_cat)/len(df_f)*100:.1f}%")
    c3.metric("Sub-Kategori", len(subcats_list))

    st.markdown("---")
    col1, col2 = st.columns([1.2, 1])

    with col1:
        st.markdown('<div class="section-title">📊 Distribusi Sub-Kategori Kesehatan</div>', unsafe_allow_html=True)
        sub_counts = Counter()
        for subs in df_cat[f"sub_{cat}"]:
            sub_counts.update(subs)
        if sub_counts:
            fig_sub = hbar(
                list(sub_counts.keys()), list(sub_counts.values()),
                color="#10b981", title="Frekuensi Sub-Kategori"
            )
            st.plotly_chart(fig_sub, use_container_width=True)

    with col2:
        st.markdown('<div class="section-title">🌍 Distribusi per Wilayah</div>', unsafe_allow_html=True)
        wil_sub = df_cat.groupby("Wilayah").size().reset_index(name="Jumlah")
        fig_wil2 = px.pie(wil_sub, names="Wilayah", values="Jumlah",
                          color="Wilayah", color_discrete_map=COLOR_WILAYAH, hole=0.5)
        fig_wil2.update_layout(height=300, margin=dict(t=20, b=50),
                                paper_bgcolor="rgba(0,0,0,0)",
                                legend=dict(orientation="h", y=-0.2, x=0.2))
        st.plotly_chart(fig_wil2, use_container_width=True)

    col3, col4 = st.columns(2)
    with col3:
        st.markdown('<div class="section-title">⚥ Gender</div>', unsafe_allow_html=True)
        g2 = df_cat["Jenis Kelamin"].value_counts()
        fig_g2 = donut(g2.index.tolist(), g2.values.tolist(),
                       [COLOR_GENDER.get(l, "#ccc") for l in g2.index], "")
        st.plotly_chart(fig_g2, use_container_width=True)

    with col4:
        st.markdown('<div class="section-title">🎂 Kelompok Usia</div>', unsafe_allow_html=True)
        u2 = df_cat["Umur"].value_counts()
        fig_u2 = donut(u2.index.tolist(), u2.values.tolist(),
                       [COLOR_UMUR.get(l, "#ccc") for l in u2.index], "")
        st.plotly_chart(fig_u2, use_container_width=True)

    st.markdown("---")
    st.markdown('<div class="section-title">💬 Contoh Tanggapan per Sub-Kategori</div>', unsafe_allow_html=True)
    for subcat, kws in KEYWORDS[cat].items():
        mask = df_f["Tanggapan"].str.lower().apply(lambda t: any(k in t for k in kws))
        df_sub = df_f[mask]
        if len(df_sub) == 0:
            continue
        with st.expander(f"📌 {subcat}  ({len(df_sub)} responden)", expanded=False):
            show_quotes(df_sub, n=5, tag=subcat)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE 5 – Kesejahteraan Sosial
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🤝 Kesejahteraan Sosial":
    st.markdown("""
    <div class="main-header" style="background: linear-gradient(135deg,#78350f,#f59e0b,#fbbf24);">
      <h1>🤝 Kesejahteraan Sosial</h1>
      <p>Kondisi ekonomi, ketahanan pangan, bantuan, dan dukungan sosial pasca bencana</p>
    </div>
    """, unsafe_allow_html=True)

    cat = "kesejahteraan"
    subcats_list = list(KEYWORDS[cat].keys())
    df_cat = df_f[df_f[f"is_{cat}"]].copy()

    c1, c2, c3 = st.columns(3)
    c1.metric("Responden Terkait Kesejahteraan", len(df_cat))
    c2.metric("% dari Total", f"{len(df_cat)/len(df_f)*100:.1f}%")
    c3.metric("Sub-Kategori", len(subcats_list))

    st.markdown("---")
    col1, col2 = st.columns([1.2, 1])

    with col1:
        st.markdown('<div class="section-title">📊 Distribusi Sub-Kategori Kesejahteraan</div>', unsafe_allow_html=True)
        sub_counts = Counter()
        for subs in df_cat[f"sub_{cat}"]:
            sub_counts.update(subs)
        if sub_counts:
            fig_sub = hbar(
                list(sub_counts.keys()), list(sub_counts.values()),
                color="#f59e0b", title="Frekuensi Sub-Kategori"
            )
            st.plotly_chart(fig_sub, use_container_width=True)

    with col2:
        st.markdown('<div class="section-title">🌍 Distribusi per Wilayah</div>', unsafe_allow_html=True)
        wil_sub = df_cat.groupby("Wilayah").size().reset_index(name="Jumlah")
        fig_wil2 = px.pie(wil_sub, names="Wilayah", values="Jumlah",
                          color="Wilayah", color_discrete_map=COLOR_WILAYAH, hole=0.5)
        fig_wil2.update_layout(height=300, margin=dict(t=20, b=50),
                                paper_bgcolor="rgba(0,0,0,0)",
                                legend=dict(orientation="h", y=-0.2, x=0.2))
        st.plotly_chart(fig_wil2, use_container_width=True)

    col3, col4 = st.columns(2)
    with col3:
        st.markdown('<div class="section-title">⚥ Gender</div>', unsafe_allow_html=True)
        g2 = df_cat["Jenis Kelamin"].value_counts()
        fig_g2 = donut(g2.index.tolist(), g2.values.tolist(),
                       [COLOR_GENDER.get(l, "#ccc") for l in g2.index], "")
        st.plotly_chart(fig_g2, use_container_width=True)

    with col4:
        st.markdown('<div class="section-title">🎂 Kelompok Usia</div>', unsafe_allow_html=True)
        u2 = df_cat["Umur"].value_counts()
        fig_u2 = donut(u2.index.tolist(), u2.values.tolist(),
                       [COLOR_UMUR.get(l, "#ccc") for l in u2.index], "")
        st.plotly_chart(fig_u2, use_container_width=True)

    st.markdown("---")
    st.markdown('<div class="section-title">💬 Contoh Tanggapan per Sub-Kategori</div>', unsafe_allow_html=True)
    for subcat, kws in KEYWORDS[cat].items():
        mask = df_f["Tanggapan"].str.lower().apply(lambda t: any(k in t for k in kws))
        df_sub = df_f[mask]
        if len(df_sub) == 0:
            continue
        with st.expander(f"📌 {subcat}  ({len(df_sub)} responden)", expanded=False):
            show_quotes(df_sub, n=5, tag=subcat)

    # Extra: sunburst of all categories
    st.markdown("---")
    st.markdown('<div class="section-title">🌐 Peta Kondisi Lintas Kategori</div>', unsafe_allow_html=True)
    rows_all = []
    for cat_key, subcats in KEYWORDS.items():
        cat_label = {
            "pendidikan": "Pendidikan",
            "perlindungan": "Perlindungan Anak",
            "kesehatan": "Kesehatan",
            "kesejahteraan": "Kesejahteraan Sosial",
        }[cat_key]
        for subcat, kws in subcats.items():
            n = df_f["Tanggapan"].str.lower().apply(lambda t: any(k in t for k in kws)).sum()
            if n > 0:
                rows_all.append({"Kategori": cat_label, "Sub-Kategori": subcat, "Jumlah": n})
    df_sun = pd.DataFrame(rows_all)
    if not df_sun.empty:
        fig_sun = px.sunburst(
            df_sun, path=["Kategori", "Sub-Kategori"], values="Jumlah",
            color="Kategori",
            color_discrete_map={
                "Pendidikan": "#2563eb",
                "Perlindungan Anak": "#d946ef",
                "Kesehatan": "#10b981",
                "Kesejahteraan Sosial": "#f59e0b",
            },
        )
        fig_sun.update_layout(height=500, margin=dict(t=20, b=20),
                               paper_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_sun, use_container_width=True)
