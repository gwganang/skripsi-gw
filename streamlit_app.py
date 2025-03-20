import streamlit as st
import sqlite3
import pandas as pd
import os
import plotly.express as px
from datetime import datetime

# ==================================================================================
# KONFIGURASI AWAL
# ==================================================================================
st.set_page_config(
    page_title="Inventaris Pro",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://github.com/username/repo',
        'Report a bug': "https://github.com/username/repo/issues",
        'About': "Sistem Manajemen Inventaris v2.1"
    }
)

# ==================================================================================
# SISTEM STYLING
# ==================================================================================
st.markdown("""
    <style>
        /* Global Styles */
        body {
            font-family: 'Inter', sans-serif;
            color: #333333;
        }
        .block-container {
            padding: 2rem;
        }
        
        /* Header */
        .header {
            background: linear-gradient(135deg, #2d4263, #1e3799);
            padding: 2rem;
            border-radius: 15px;
            margin-bottom: 2rem;
        }
        .header h1 {
            color: white;
            margin: 0;
        }
        
        /* Navigation */
        .sidebar .sidebar-content {
            background: #f8f9fa;
            border-radius: 15px;
        }
        .sidebar .nav-link {
            padding: 12px 20px;
            border-radius: 8px;
            transition: all 0.3s;
        }
        .sidebar .nav-link.active {
            background: #1e3799;
            color: white;
        }
        
        /* Cards */
        .card {
            background: white;
            border-radius: 12px;
            padding: 1.5rem;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
            transition: transform 0.2s;
        }
        .card:hover {
            transform: translateY(-3px);
        }
        
        /* Tables */
        .dataframe {
            border: 1px solid #dee2e6;
            border-radius: 8px;
        }
        
        /* Forms */
        .stForm {
            background: #ffffff;
            padding: 2rem;
            border-radius: 12px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        }
        .stButton>button {
            background: #1e3799;
            border: none;
            padding: 0.8rem 2rem;
            border-radius: 8px;
            color: white;
            font-weight: 500;
        }
        
        /* Toast Notifications */
        .stToast {
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
    </style>
""", unsafe_allow_html=True)

# ==================================================================================
# DATABASE & LOGIC
# ==================================================================================
# Membuat direktori database jika belum ada
if not os.path.exists('database'):
    os.makedirs('database')

@st.cache_resource
def get_db():
    """Koneksi ke database SQLite"""
    return sqlite3.connect('database/database.db', check_same_thread=False)

def init_db():
    """Inisialisasi struktur database"""
    conn = get_db()
    c = conn.cursor()
    
    # Tabel Barang
    c.execute('''
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nama TEXT UNIQUE NOT NULL,
            stok INTEGER NOT NULL CHECK(stok >= 0),
            satuan TEXT NOT NULL,
            keterangan TEXT
        )
    ''')
    
    # Tabel Transaksi
    c.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER,
            tipe TEXT CHECK(tipe IN ('masuk', 'keluar')) NOT NULL,
            jumlah INTEGER NOT NULL CHECK(jumlah > 0),
            tanggal TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            keterangan TEXT,
            FOREIGN KEY(item_id) REFERENCES items(id)
        )
    ''')
    
    # Trigger untuk update stok otomatis
    c.execute('''
        CREATE TRIGGER IF NOT EXISTS update_stok
        AFTER INSERT ON transactions
        FOR EACH ROW
        BEGIN
            UPDATE items
            SET stok = stok + (CASE 
                                WHEN NEW.tipe = 'masuk' THEN NEW.jumlah
                                WHEN NEW.tipe = 'keluar' THEN -NEW.jumlah
                               END)
            WHERE id = NEW.item_id;
        END;
    ''')
    conn.commit()

init_db()

# ==================================================================================
# FUNGSI UTILITAS
# ==================================================================================
def fetch_items():
    """Mengambil semua data barang"""
    return pd.read_sql("SELECT * FROM items", get_db())

def fetch_transactions():
    """Mengambil semua transaksi dengan join ke items"""
    return pd.read_sql("""
        SELECT t.*, i.nama 
        FROM transactions t 
        JOIN items i ON t.item_id = i.id
    """, get_db())

def get_item_id_by_name(name):
    """Mendapatkan item ID berdasarkan nama"""
    df = pd.read_sql(f"SELECT id FROM items WHERE nama='{name}'", get_db())
    return df['id'].values[0] if not df.empty else None

# ==================================================================================
# KOMPONEN UI/UX
# ==================================================================================
def render_header():
    """Header aplikasi"""
    st.markdown("""
        <div class="header">
            <h1>📦 Inventaris Pro</h1>
            <p>Solusi Manajemen Stok untuk Bisnis Modern</p>
        </div>
    """, unsafe_allow_html=True)

def render_sidebar():
    """Sidebar navigasi"""
    with st.sidebar:
        st.markdown("""
            <div style="text-align: center; margin: 2rem 0;">
                <img src="https://via.placeholder.com/150" 
                     style="border-radius: 50%; box-shadow: 0 2px 10px rgba(0,0,0,0.1);"/>
                <h3 style="color: #1e3799; margin-top: 1rem;">Menu Utama</h3>
            </div>
        """, unsafe_allow_html=True)
        
        menu = st.radio("",
            ["Dashboard", "Data Barang", "Transaksi", "Laporan", "Pengaturan"],
            format_func=lambda x: "📊 Dashboard" if x == "Dashboard" else 
                                "📦 Data Barang" if x == "Data Barang" else 
                                "🔄 Transaksi" if x == "Transaksi" else 
                                "📄 Laporan" if x == "Laporan" else 
                                "⚙️ Pengaturan",
            label_visibility="collapsed"
        )
        
        st.markdown("""
            <div style="position: fixed; bottom: 20px; width: 230px; text-align: center;">
                <p style="color: #6c757d;">Dibuat dengan ❤️ oleh Tim Dev</p>
            </div>
        """, unsafe_allow_html=True)
    return menu

# ==================================================================================
# HALAMAN UTAMA
# ==================================================================================
def dashboard_page():
    """Halaman dashboard"""
    render_header()
    
    col1, col2, col3 = st.columns(3)
    items = fetch_items()
    
    with col1:
        with st.container(border=True):
            st.metric("Total Barang", len(items), 
                     delta="+0", 
                     delta_color="off",
                     help="Jumlah total item yang terdaftar")
            
    with col2:
        with st.container(border=True):
            st.metric("Total Stok", items['stok'].sum(),
                     delta="+0", 
                     delta_color="off",
                     help="Jumlah stok keseluruhan")
            
    with col3:
        with st.container(border=True):
            low_stock = len(items[items['stok'] < 10])
            st.metric("Stok Kritis", low_stock,
                     delta="+0", 
                     delta_color="inverse",
                     help="Item dengan stok < 10")
    
    # Visualisasi stok
    if not items.empty:
        fig = px.bar(
            items,
            x='nama',
            y='stok',
            title="Distribusi Stok Barang",
            labels={'nama':'Barang', 'stok':'Jumlah Stok'},
            color='stok',
            color_continuous_scale='Tealgrn'
        )
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(size=12),
            margin=dict(l=20, r=20, t=30, b=20)
        )
        st.plotly_chart(fig, use_container_width=True)
        
    # Aktivitas terakhir
    st.subheader("Aktivitas Terakhir")
    transactions = fetch_transactions().tail(5)
    if not transactions.empty:
        st.dataframe(
            transactions[['tanggal', 'nama', 'tipe', 'jumlah']],
            column_config={
                "tanggal": "Waktu",
                "nama": "Barang",
                "tipe": st.column_config.TextColumn(
                    "Tipe",
                    help="masuk/keluar",
                    default="N/A"
                ),
                "jumlah": st.column_config.NumberColumn(
                    "Jumlah",
                    format="%d"
                )
            },
            hide_index=True,
            use_container_width=True
        )
    else:
        st.info("Belum ada aktivitas")

def barang_page():
    """Halaman manajemen barang"""
    render_header()
    
    tab1, tab2 = st.tabs(["**Daftar Barang**", "**Tambah Barang**"])
    
    with tab1:
        items = fetch_items()
        gb = st.dataframe(
            items,
            column_config={
                "nama": "Nama Barang",
                "stok": st.column_config.NumberColumn(
                    "Stok",
                    format="%d",
                    help="Jumlah stok saat ini"
                ),
                "satuan": "Satuan",
                "keterangan": "Keterangan"
            },
            use_container_width=True,
            height=300
        )
        
        # Aksi massal
        col1, col2 = st.columns([1, 4])
        with col1:
            st.selectbox("Aksi Massal", ["Hapus", "Export"], label_visibility="collapsed")
        with col2:
            st.button("Terapkan", use_container_width=True)
        
    with tab2:
        with st.form("tambah_barang", border=True):
            st.subheader("Tambah Barang Baru")
            
            col1, col2 = st.columns(2)
            with col1:
                nama = st.text_input("Nama Barang*", placeholder="Contoh: Kertas A4")
            with col2:
                satuan = st.selectbox("Satuan*", ["pcs", "box", "rim", "lusin"])
                
            stok = st.number_input("Stok Awal*", min_value=0, step=1)
            keterangan = st.text_area("Keterangan", placeholder="Catatan tambahan...")
            
            submitted = st.form_submit_button("Simpan", type="primary", use_container_width=True)
            
            if submitted:
                if nama and stok >= 0 and satuan:
                    try:
                        conn = get_db()
                        conn.cursor().execute(
                            "INSERT INTO items (nama, stok, satuan, keterangan) VALUES (?, ?, ?, ?)",
                            (nama, stok, satuan, keterangan)
                        )
                        conn.commit()
                        st.toast(f"✅ Barang {nama} berhasil ditambahkan!", icon="🎉")
                    except sqlite3.IntegrityError:
                        st.toast("❌ Nama barang sudah ada!", icon="⚠️")
                else:
                    st.toast("⚠️ Lengkapi field wajib", icon="❌")

def transaksi_page():
    """Halaman transaksi"""
    render_header()
    
    tab_masuk, tab_keluar = st.tabs(["Tambah Masuk", "Tambah Keluar"])
    
    with tab_masuk:
        with st.form("form_masuk", border=True):
            st.subheader("Tambah Stok Masuk")
            
            item = st.selectbox("Barang", fetch_items()['nama'].tolist())
            jumlah = st.number_input("Jumlah*", min_value=1)
            keterangan = st.text_area("Keterangan")
            
            if st.form_submit_button("Proses Masuk", type="primary", use_container_width=True):
                if item and jumlah > 0:
                    try:
                        item_id = get_item_id_by_name(item)
                        conn = get_db()
                        conn.cursor().execute(
                            "INSERT INTO transactions (item_id, tipe, jumlah, keterangan) VALUES (?, ?, ?, ?)",
                            (item_id, 'masuk', jumlah, keterangan)
                        )
                        conn.commit()
                        st.toast(f"✅ Stok {item} berhasil ditambahkan!", icon="🎉")
                    except Exception as e:
                        st.toast(f"❌ Gagal: {str(e)}", icon="⚠️")
                else:
                    st.toast("⚠️ Lengkapi data", icon="❌")
    
    with tab_keluar:
        with st.form("form_keluar", border=True):
            st.subheader("Kurangi Stok Keluar")
            
            item = st.selectbox("Barang", fetch_items()['nama'].tolist())
            jumlah = st.number_input("Jumlah*", min_value=1)
            keterangan = st.text_area("Keterangan")
            
            if st.form_submit_button("Proses Keluar", type="primary", use_container_width=True):
                item_data = fetch_items()[fetch_items()['nama'] == item]
                if not item_data.empty and item_data.iloc[0]['stok'] >= jumlah:
                    try:
                        item_id = get_item_id_by_name(item)
                        conn = get_db()
                        conn.cursor().execute(
                            "INSERT INTO transactions (item_id, tipe, jumlah, keterangan) VALUES (?, ?, ?, ?)",
                            (item_id, 'keluar', jumlah, keterangan)
                        )
                        conn.commit()
                        st.toast(f"✅ Stok {item} berhasil dikurangi!", icon="🎉")
                    except Exception as e:
                        st.toast(f"❌ Gagal: {str(e)}", icon="⚠️")
                else:
                    st.toast("⚠️ Stok tidak mencukupi", icon="❌")

def laporan_page():
    """Halaman laporan"""
    render_header()
    
    col1, col2 = st.columns(2)
    start_date = col1.date_input("Tanggal Mulai", datetime.now().replace(day=1))
    end_date = col2.date_input("Tanggal Akhir", datetime.now())
    
    query = f"""
        SELECT 
            strftime('%Y-%m', tanggal) AS bulan,
            i.nama,
            SUM(CASE WHEN tipe='masuk' THEN jumlah ELSE 0 END) AS total_masuk,
            SUM(CASE WHEN tipe='keluar' THEN jumlah ELSE 0 END) AS total_keluar
        FROM transactions 
        JOIN items i ON transactions.item_id = i.id
        WHERE tanggal BETWEEN '{start_date}' AND '{end_date}'
        GROUP BY bulan, i.nama
    """
    laporan = pd.read_sql(query, get_db())
    
    if not laporan.empty:
        st.dataframe(laporan, use_container_width=True)
        fig = px.bar(laporan, 
                    x='bulan', 
                    y=['total_masuk', 'total_keluar'],
                    title="Laporan Bulanan",
                    barmode='group',
                    labels={'value': 'Jumlah', 'variable': 'Tipe Transaksi'})
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Tidak ada data untuk periode ini")

def pengaturan_page():
    """Halaman pengaturan"""
    render_header()
    st.warning("Fitur pengaturan belum diimplementasikan", icon="⚠️")

# ==================================================================================
# MAIN EXECUTION
# ==================================================================================
def main():
    menu = render_sidebar()
    
    if menu == "Dashboard":
        dashboard_page()
    elif menu == "Data Barang":
        barang_page()
    elif menu == "Transaksi":
        transaksi_page()
    elif menu == "Laporan":
        laporan_page()
    elif menu == "Pengaturan":
        pengaturan_page()

if __name__ == "__main__":
    main()