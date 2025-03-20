import streamlit as st
import sqlite3
import pandas as pd
import os
import logging
from datetime import datetime
import plotly.express as px

# ==================================================================================
# KONFIGURASI AWAL
# ==================================================================================
st.set_page_config(
    page_title="Sistem Manajemen Inventaris",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================================================================================
# KONFIGURASI DATABASE
# ==================================================================================
if not os.path.exists('database'):
    os.makedirs('database')

@st.cache_resource
def get_db():
    return sqlite3.connect('database/inventaris_professional.db', check_same_thread=False)

def init_db():
    conn = get_db()
    c = conn.cursor()
    
    # Tabel Inventaris
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
    
    # Trigger untuk update stok
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
# STYLING & CSS
# ==================================================================================
st.markdown("""
    <style>
        .stApp {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        }
        .header {
            padding: 2rem 1rem;
            background-color: #2d3436;
            color: white;
            border-radius: 10px;
            margin-bottom: 2rem;
        }
        .metric {
            background-color: #f8f9fa;
            padding: 1rem;
            border-radius: 10px;
            margin: 0.5rem 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .dataframe {
            border: 1px solid #dee2e6;
            border-radius: 5px;
        }
        .stSelectbox > div:first-child {
            background-color: #f8f9fa;
            border-radius: 5px;
        }
    </style>
""", unsafe_allow_html=True)

# ==================================================================================
# FUNGSI UTAMA
# ==================================================================================
def fetch_items():
    return pd.read_sql("SELECT * FROM items", get_db())

def fetch_transactions():
    return pd.read_sql("""
        SELECT t.*, i.nama 
        FROM transactions t 
        JOIN items i ON t.item_id = i.id
    """, get_db())

def get_item_id_by_name(name):
    df = pd.read_sql(f"SELECT id FROM items WHERE nama='{name}'", get_db())
    return df['id'].values[0] if not df.empty else None

# ==================================================================================
# SIDEBAR NAVIGASI
# ==================================================================================
with st.sidebar:
    st.markdown("""
        <div class="header">
            <h1 style="color: white;">📦 Inventaris Pro</h1>
            <p>Sistem Manajemen Stok Profesional</p>
        </div>
    """, unsafe_allow_html=True)
    
    menu = st.radio("Menu Utama", [
        "Dashboard",
        "Data Barang",
        "Transaksi",
        "Laporan",
        "Pengaturan"
    ], index=0, format_func=lambda x: "📊 Dashboard" if x == "Dashboard" else 
                                "📦 Data Barang" if x == "Data Barang" else 
                                "🔄 Transaksi" if x == "Transaksi" else 
                                "📄 Laporan" if x == "Laporan" else 
                                "⚙️ Pengaturan")

# ==================================================================================
# HALAMAN UTAMA
# ==================================================================================
if menu == "Dashboard":
    st.header("📊 Dashboard Overview")
    
    col1, col2, col3 = st.columns(3)
    items = fetch_items()
    
    with col1:
        st.markdown('<div class="metric">', unsafe_allow_html=True)
        st.metric("Total Barang", len(items))
        st.markdown('</div>', unsafe_allow_html=True)
        
    with col2:
        st.markdown('<div class="metric">', unsafe_allow_html=True)
        st.metric("Total Stok", items['stok'].sum())
        st.markdown('</div>', unsafe_allow_html=True)
        
    with col3:
        st.markdown('<div class="metric">', unsafe_allow_html=True)
        low_stock = len(items[items['stok'] < 10])
        st.metric("Stok < 10", low_stock, delta_color="inverse")
        st.markdown('</div>', unsafe_allow_html=True)
        
    # Chart stok
    if not items.empty:
        fig = px.bar(items, 
                    x='nama', 
                    y='stok',
                    title="Stok Barang",
                    labels={'nama':'Barang', 'stok':'Jumlah Stok'},
                    color='stok',
                    color_continuous_scale='Viridis')
        st.plotly_chart(fig, use_container_width=True)

elif menu == "Data Barang":
    st.header("📦 Data Barang")
    
    tab1, tab2 = st.tabs(["Daftar Barang", "Tambah Barang"])
    
    with tab1:
        items = fetch_items()
        st.dataframe(items, use_container_width=True, height=400)
        
        # Export options
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Export ke Excel"):
                with st.spinner("Mengexport data..."):
                    items.to_excel("inventaris.xlsx", index=False)
                    st.success("Export berhasil! File: inventaris.xlsx")
                    
        with col2:
            if st.button("Export ke CSV"):
                with st.spinner("Mengexport data..."):
                    items.to_csv("inventaris.csv", index=False)
                    st.success("Export berhasil! File: inventaris.csv")
    
    with tab2:
        with st.form("form_barang", clear_on_submit=True):
            st.subheader("Tambah Barang Baru")
            nama = st.text_input("Nama Barang*")
            stok = st.number_input("Stok Awal*", min_value=0)
            satuan = st.selectbox("Satuan*", ["pcs", "box", "rim", "lusin"])
            keterangan = st.text_area("Keterangan")
            
            if st.form_submit_button("Simpan", type="primary"):
                if nama and stok >= 0 and satuan:
                    try:
                        conn = get_db()
                        conn.cursor().execute(
                            "INSERT INTO items (nama, stok, satuan, keterangan) VALUES (?, ?, ?, ?)",
                            (nama, stok, satuan, keterangan)
                        )
                        conn.commit()
                        st.success(f"Barang {nama} berhasil ditambahkan!")
                    except sqlite3.IntegrityError:
                        st.error("Nama barang sudah ada!")
                else:
                    st.warning("Lengkapi field wajib")

elif menu == "Transaksi":
    st.header("🔄 Manajemen Transaksi")
    
    transaksi = fetch_transactions()
    if transaksi.empty:
        st.warning("Belum ada transaksi")
    else:
        st.dataframe(transaksi, use_container_width=True)
    
    tab_masuk, tab_keluar = st.tabs(["Tambah Masuk", "Tambah Keluar"])
    
    with tab_masuk:
        with st.form("form_masuk"):
            st.subheader("Tambah Stok Masuk")
            item = st.selectbox("Barang", fetch_items()['nama'].tolist())
            jumlah = st.number_input("Jumlah*", min_value=1)
            keterangan = st.text_area("Keterangan")
            
            if st.form_submit_button("Proses Masuk", type="primary"):
                if item and jumlah > 0:
                    try:
                        item_id = get_item_id_by_name(item)
                        conn = get_db()
                        conn.cursor().execute(
                            "INSERT INTO transactions (item_id, tipe, jumlah, keterangan) VALUES (?, ?, ?, ?)",
                            (item_id, 'masuk', jumlah, keterangan)
                        )
                        conn.commit()
                        st.success(f"Stok {item} berhasil ditambahkan!")
                    except Exception as e:
                        st.error(f"Gagal: {str(e)}")
                else:
                    st.warning("Data tidak lengkap")
    
    with tab_keluar:
        with st.form("form_keluar"):
            st.subheader("Kurangi Stok Keluar")
            item = st.selectbox("Barang", fetch_items()['nama'].tolist())
            jumlah = st.number_input("Jumlah*", min_value=1)
            keterangan = st.text_area("Keterangan")
            
            if st.form_submit_button("Proses Keluar", type="primary"):
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
                        st.success(f"Stok {item} berhasil dikurangi!")
                    except Exception as e:
                        st.error(f"Gagal: {str(e)}")
                else:
                    st.error("Stok tidak mencukupi")

elif menu == "Laporan":
    st.header("📄 Laporan Stok")
    
    # Filter tanggal
    col1, col2 = st.columns(2)
    start_date = col1.date_input("Tanggal Mulai", datetime.now().replace(day=1))
    end_date = col2.date_input("Tanggal Akhir", datetime.now())
    
    # Query laporan
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
                    barmode='group')
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Tidak ada data untuk periode ini")

elif menu == "Pengaturan":
    st.header("⚙️ Pengaturan Sistem")
    st.warning("Fitur pengaturan belum diimplementasikan", icon="⚠️")

# ==================================================================================
# FOOTER
# ==================================================================================
st.sidebar.markdown("""
    <div style="margin-top: 2rem; padding: 1rem; background: #f8f9fa; border-radius: 10px;">
        <p style="margin:0; text-align: center;">© 2024 Sistem Inventaris Pro</p>
        <p style="margin:0; text-align: center;">Versi 1.0.0</p>
    </div>
""", unsafe_allow_html=True)