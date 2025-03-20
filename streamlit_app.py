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
        'Get Help': 'https://github.com/organisasi/inventaris',
        'Report a bug': "https://github.com/organisasi/inventaris/issues",
        'About': "Sistem Manajemen Inventaris Profesional v2.0"
    }
)

# ==================================================================================
# SISTEM THEME DINAMIS
# ==================================================================================
primaryColor = "#007BFF"
backgroundColor = "#f0f2f6"
secondaryBackgroundColor = "#ffffff"
textColor = "#262730"
font = "sans serif"

st.markdown(f"""
    <style>
        .stApp {{
            background-color: {backgroundColor};
        }}
        .css-18e3th9 {{
            padding: 2rem 1rem;
        }}
        .block-container {{
            padding: 2rem;
            border-radius: 15px;
            background: white;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }}
        .stButton>button {{
            border-radius: 8px;
            border: none;
            padding: 0.8rem 1.5rem;
            transition: all 0.3s ease;
        }}
        .stButton>button:hover {{
            transform: translateY(-2px);
            box-shadow: 0 0 10px rgba(0, 123, 255, 0.3);
        }}
    </style>
""", unsafe_allow_html=True)

# ==================================================================================
# KOMPONEN NAVIGASI
# ==================================================================================
with st.sidebar:
    st.image("https://via.placeholder.com/150/92c952/FFFFFF?text=📦", width=120)
    st.write("---")
    
    menu = st.radio(
        "Menu Utama",
        ["📊 Dashboard", "📦 Data Barang", "🔄 Transaksi", "📄 Laporan", "⚙️ Pengaturan"],
        format_func=lambda x: x.split()[1],
        label_visibility="collapsed"
    )
    
    st.write("---")
    dark_mode = st.toggle("🌙 Dark Mode", key="dark_mode")

# ==================================================================================
# FUNGSI UTAMA
# ==================================================================================
@st.cache_resource
def get_db():
    return sqlite3.connect('database/inventaris.db', check_same_thread=False)

def fetch_items():
    return pd.read_sql("SELECT * FROM items", get_db())

def fetch_transactions():
    return pd.read_sql("""
        SELECT t.*, i.nama 
        FROM transactions t 
        JOIN items i ON t.item_id = i.id
    """, get_db())

# ==================================================================================
# HALAMAN DASHBOARD
# ==================================================================================
if menu == "📊 Dashboard":
    st.title("Dashboard Inventaris")
    st.markdown("### Ringkasan Stok Terkini")
    
    col1, col2, col3, col4 = st.columns(4)
    items = fetch_items()
    
    with col1:
        st.metric(
            label="Total Barang",
            value=len(items),
            delta="+0",
            delta_color="off"
        )
        
    with col2:
        st.metric(
            label="Total Stok",
            value=items['stok'].sum(),
            delta="+0",
            delta_color="off"
        )
        
    with col3:
        low_stock = len(items[items['stok'] < 10])
        st.metric(
            label="Stok Kritis",
            value=low_stock,
            delta=f"{low_stock} items",
            delta_color="inverse"
        )
        
    with col4:
        transactions = fetch_transactions()
        last_week = transactions[transactions['tanggal'] > datetime.now() - pd.Timedelta(days=7)]
        st.metric(
            label="Transaksi 7 Hari",
            value=len(last_week),
            delta="+0",
            delta_color="off"
        )
        
    # Chart Stok
    with st.container():
        st.write("---")
        st.subheader("Distribusi Stok Barang")
        
        if not items.empty:
            fig = px.bar(
                items,
                x='nama',
                y='stok',
                color='stok',
                color_continuous_scale='Bluered_r',
                labels={'nama':'Barang', 'stok':'Jumlah Stok'},
                title="Stok Barang"
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Tidak ada data barang")

# ==================================================================================
# HALAMAN DATA BARANG
# ==================================================================================
elif menu == "📦 Data Barang":
    st.title("Manajemen Data Barang")
    
    tab1, tab2, tab3 = st.tabs(["Daftar Barang", "Tambah Barang", "Edit/Hapus"])
    
    with tab1:
        items = fetch_items()
        if not items.empty:
            gb = st.data_editor(
                items,
                column_config={
                    "nama": "Nama Barang",
                    "stok": st.column_config.NumberColumn(
                        "Stok",
                        format="%d",
                        min_value=0
                    ),
                    "satuan": "Satuan",
                    "keterangan": "Keterangan"
                },
                use_container_width=True,
                num_rows="dynamic",
                disabled=["id"],
                hide_index=True
            )
            
            if st.button("Simpan Perubahan"):
                try:
                    gb.to_sql('items', get_db(), if_exists='replace', index=False)
                    st.success("Perubahan berhasil disimpan!")
                except Exception as e:
                    st.error(f"Gagal menyimpan: {e}")
        else:
            st.warning("Tidak ada data barang")
    
    with tab2:
        with st.form("tambah_barang", clear_on_submit=True):
            st.subheader("Tambah Barang Baru")
            col1, col2 = st.columns(2)
            
            with col1:
                nama = st.text_input("Nama Barang*", placeholder="Contoh: Kertas A4")
                satuan = st.selectbox("Satuan*", ["pcs", "box", "rim", "lusin"])
                
            with col2:
                stok = st.number_input("Stok Awal*", min_value=0, value=0)
                keterangan = st.text_area("Keterangan", placeholder="Opsional")
                
            submitted = st.form_submit_button("Tambah Barang", type="primary")
            
            if submitted:
                if nama and stok >= 0 and satuan:
                    try:
                        conn = get_db()
                        conn.cursor().execute(
                            "INSERT INTO items (nama, stok, satuan, keterangan) VALUES (?, ?, ?, ?)",
                            (nama, stok, satuan, keterangan)
                        )
                        conn.commit()
                        st.success(f"{nama} berhasil ditambahkan!")
                    except sqlite3.IntegrityError:
                        st.error("Nama barang sudah ada!")
                else:
                    st.warning("Lengkapi field wajib")

    with tab3:
        if not items.empty:
            item_to_edit = st.selectbox("Pilih Barang", items['nama'].tolist())
            item_data = items[items['nama'] == item_to_edit].iloc[0]
            
            with st.form(f"edit_{item_to_edit}"):
                st.subheader("Edit Barang")
                new_nama = st.text_input("Nama Barang", value=item_data['nama'])
                new_stok = st.number_input("Stok", value=item_data['stok'])
                new_satuan = st.selectbox("Satuan", ["pcs", "box", "rim", "lusin"], index=["pcs", "box", "rim", "lusin"].index(item_data['satuan']))
                new_keterangan = st.text_area("Keterangan", value=item_data['keterangan'])
                
                if st.form_submit_button("Update"):
                    try:
                        conn = get_db()
                        conn.cursor().execute(
                            "UPDATE items SET nama=?, stok=?, satuan=?, keterangan=? WHERE id=?",
                            (new_nama, new_stok, new_satuan, new_keterangan, item_data['id'])
                        )
                        conn.commit()
                        st.success("Data berhasil diperbarui!")
                    except Exception as e:
                        st.error(f"Gagal: {str(e)}")
        else:
            st.info("Tidak ada data untuk diedit")

# ==================================================================================
# HALAMAN TRANSAKSI
# ==================================================================================
elif menu == "🔄 Transaksi":
    st.title("Manajemen Transaksi")
    
    tab_masuk, tab_keluar, tab_riwayat = st.tabs(["Tambah Masuk", "Tambah Keluar", "Riwayat"])
    
    with tab_masuk:
        with st.form("transaksi_masuk"):
            st.subheader("Tambah Stok Masuk")
            col1, col2 = st.columns(2)
            
            with col1:
                item = st.selectbox("Barang", fetch_items()['nama'].tolist())
                jumlah = st.number_input("Jumlah", min_value=1, value=1)
                
            with col2:
                tanggal = st.date_input("Tanggal", datetime.now())
                keterangan = st.text_area("Keterangan", placeholder="Sumber/No. PO")
                
            if st.form_submit_button("Proses Masuk", type="primary"):
                try:
                    item_id = get_item_id_by_name(item)
                    conn = get_db()
                    conn.cursor().execute(
                        "INSERT INTO transactions (item_id, tipe, jumlah, tanggal, keterangan) VALUES (?, ?, ?, ?, ?)",
                        (item_id, 'masuk', jumlah, tanggal, keterangan)
                    )
                    conn.commit()
                    st.success(f"Stok {item} berhasil ditambahkan!")
                except Exception as e:
                    st.error(f"Gagal: {str(e)}")
    
    with tab_keluar:
        with st.form("transaksi_keluar"):
            st.subheader("Kurangi Stok Keluar")
            col1, col2 = st.columns(2)
            
            with col1:
                item = st.selectbox("Barang", fetch_items()['nama'].tolist())
                jumlah = st.number_input("Jumlah", min_value=1, value=1)
                
            with col2:
                tanggal = st.date_input("Tanggal", datetime.now())
                keterangan = st.text_area("Keterangan", placeholder="Tujuan/No. Surat")
                
            if st.form_submit_button("Proses Keluar", type="primary"):
                item_data = fetch_items()[fetch_items()['nama'] == item].iloc[0]
                if item_data['stok'] >= jumlah:
                    try:
                        item_id = get_item_id_by_name(item)
                        conn = get_db()
                        conn.cursor().execute(
                            "INSERT INTO transactions (item_id, tipe, jumlah, tanggal, keterangan) VALUES (?, ?, ?, ?, ?)",
                            (item_id, 'keluar', jumlah, tanggal, keterangan)
                        )
                        conn.commit()
                        st.success(f"Stok {item} berhasil dikurangi!")
                    except Exception as e:
                        st.error(f"Gagal: {str(e)}")
                else:
                    st.error("Stok tidak mencukupi!")

    with tab_riwayat:
        transactions = fetch_transactions()
        if not transactions.empty:
            st.dataframe(
                transactions,
                column_config={
                    "tipe": st.column_config.TextColumn(
                        "Tipe",
                        help="Masuk/Keluar",
                        width="small"
                    ),
                    "jumlah": st.column_config.NumberColumn(
                        "Jumlah",
                        format="%d"
                    ),
                    "tanggal": st.column_config.DateColumn(
                        "Tanggal"
                    )
                },
                use_container_width=True
            )
        else:
            st.info("Tidak ada riwayat transaksi")

# ==================================================================================
# HALAMAN LAPORAN
# ==================================================================================
elif menu == "📄 Laporan":
    st.title("Laporan Stok")
    
    col1, col2 = st.columns(2)
    start_date = col1.date_input("Dari Tanggal", datetime.now().replace(day=1))
    end_date = col2.date_input("Sampai Tanggal", datetime.now())
    
    query = f"""
        SELECT 
            i.nama,
            SUM(CASE WHEN tipe='masuk' THEN jumlah ELSE 0 END) AS total_masuk,
            SUM(CASE WHEN tipe='keluar' THEN jumlah ELSE 0 END) AS total_keluar,
            (SELECT stok FROM items WHERE nama = i.nama) AS stok_akhir
        FROM transactions 
        JOIN items i ON transactions.item_id = i.id
        WHERE tanggal BETWEEN '{start_date}' AND '{end_date}'
        GROUP BY i.nama
    """
    
    laporan = pd.read_sql(query, get_db())
    
    if not laporan.empty:
        st.dataframe(laporan, use_container_width=True)
        
        fig = px.bar(
            laporan,
            x='nama',
            y=['total_masuk', 'total_keluar'],
            title="Perbandingan Masuk/Keluar",
            barmode='group',
            labels={'value':'Jumlah', 'variable':'Tipe Transaksi'}
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Tidak ada data untuk periode ini")

# ==================================================================================
# HALAMAN PENGATURAN
# ==================================================================================
elif menu == "⚙️ Pengaturan":
    st.title("Pengaturan Sistem")
    st.warning("Fitur dalam pengembangan", icon="🚧")
    
    with st.expander("Backup Database"):
        st.write("Fitur backup otomatis")
        if st.button("Backup Sekarang"):
            try:
                os.system("cp database/inventaris.db database/backup.db")
                st.success("Backup berhasil!")
            except Exception as e:
                st.error(f"Gagal backup: {e}")

    with st.expander("Hak Akses"):
        st.write("Manajemen user (coming soon)")

# ==================================================================================
# FOOTER
# ==================================================================================
st.sidebar.markdown("""
    <div style="margin-top: 2rem; padding: 1rem; background: #f8f9fa; border-radius: 10px;">
        <p style="margin:0; text-align: center;">© 2024 Inventaris Pro</p>
        <p style="margin:0; text-align: center;">Support: support@inventaris.pro</p>
    </div>
""", unsafe_allow_html=True)