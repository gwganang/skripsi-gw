import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
from datetime import datetime

# ==================================================================================
# KONFIGURASI AWAL
# ==================================================================================
st.set_page_config(
    page_title="Inventaris Pro",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ==================================================================================
# SISTEM STYLING
# ==================================================================================
st.markdown("""
    <style>
        body {
            font-family: 'Inter', sans-serif;
            background-color: #f0f2f6;
        }
        .login-container {
            max-width: 400px;
            margin: 15% auto;
            padding: 2rem;
            background: white;
            border-radius: 15px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }
        .header {
            background: linear-gradient(135deg, #2d4263, #1e3799);
            padding: 2rem;
            border-radius: 15px;
            margin-bottom: 2rem;
        }
        .sidebar .sidebar-content {
            background: #f8f9fa;
            border-radius: 15px;
        }
        .stButton>button {
            background: #1e3799;
            color: white;
            border-radius: 8px;
            padding: 0.8rem 2rem;
        }
    </style>
""", unsafe_allow_html=True)

# ==================================================================================
# DATABASE & LOGIC
# ==================================================================================


@st.cache_resource
def get_db():
    return sqlite3.connect('database.db', check_same_thread=False)


def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT CHECK(role IN ('superadmin', 'admin', 'user')) NOT NULL DEFAULT 'user'
        )
    ''')
    c.execute("SELECT * FROM users WHERE username='superadmin'")
    if not c.fetchone():
        c.execute(
            "INSERT INTO users (username, password, role) VALUES ('superadmin', 'superadmin123', 'superadmin')")
        conn.commit()

# ==================================================================================
# SISTEM AUTHENTIKASI (Tanpa Hashing)
# ==================================================================================


def verify_login(username, password):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT role FROM users WHERE username=? AND password=?",
              (username, password))
    result = c.fetchone()
    return result[0] if result else None

# ==================================================================================
# HALAMAN LOGIN
# ==================================================================================


def login_page():
    st.markdown('<div class="login-container">', unsafe_allow_html=True)
    st.markdown("<h2 style='text-align: center;'>🔐 Login</h2>",
                unsafe_allow_html=True)
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")
        if submitted:
            role = verify_login(username, password)
            if role:
                st.session_state.update({
                    "authenticated": True,
                    "role": role,
                    "username": username
                })
                st.success("Login berhasil! Redirecting...")
                st.rerun()
            else:
                st.error("Username/password salah!")

# ==================================================================================
# HALAMAN UTAMA
# ==================================================================================


def render_header():
    st.markdown("""
        <div class="header">
            <h1>📦 Inventaris Pro</h1>
            <p>Solusi Manajemen Stok untuk Bisnis Modern</p>
        </div>
    """, unsafe_allow_html=True)


def render_sidebar():
    with st.sidebar:
        # --- MODIFIKASI UNTUK GAMBAR PROFIL ---
        role = st.session_state.role
        image_path = f"icon/{role}.png"

        st.markdown(f"""
            <div style="display: flex; align-items: center; margin: 2rem 0;">
                <img src="{image_path}" style="width: 60px; height: 60px; border-radius: 50%; margin-right: 15px;">
                <div>
                    <h3 style="color: #1e3799; margin: 0;">Halo, {st.session_state.username}</h3>
                    <p style="color: #6c757d; margin: 0;">Role: {role}</p>
                </div>
            </div>
        """, unsafe_allow_html=True)
        # --- AKHIR MODIFIKASI ---

        if st.session_state.role == "superadmin":
            menu = ["Dashboard", "Data Barang",
                    "Transaksi", "Laporan", "Pengaturan"]
        elif st.session_state.role == "admin":
            menu = ["Dashboard", "Data Barang", "Transaksi", "Laporan"]
        else:
            menu = ["Dashboard", "Laporan"]
        return st.radio(
            "Menu",
            menu,
            format_func=lambda x: "📊 Dashboard" if x == "Dashboard" else
            "📦 Data Barang" if x == "Data Barang" else
            "💸 Transaksi" if x == "Transaksi" else
            "📜 Laporan" if x == "Laporan" else
            "🛠️ Pengaturan"
        )

# ==================================================================================
# PROTEKSI HALAMAN
# ==================================================================================


def check_access(required_roles):
    if not st.session_state.get("authenticated", False):
        st.error("Anda harus login!")
        st.stop()
    if st.session_state.role not in required_roles:
        st.error("Anda tidak memiliki akses ke halaman ini!")
        st.stop()

# ==================================================================================
# HALAMAN DASHBOARD
# ==================================================================================


def dashboard_page():
    check_access(["superadmin", "admin", "user"])
    render_header()
    items = pd.read_sql("SELECT * FROM items", get_db())
    if items.empty:
        st.warning("Tidak ada data barang")
        return
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("""
            <div style="background: rgba(255,255,255,0.8); padding: 1rem; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.05);">
        """, unsafe_allow_html=True)
        st.metric("Total Barang", len(items))
        st.markdown("</div>", unsafe_allow_html=True)
    with col2:
        st.markdown("""
            <div style="background: rgba(255,255,255,0.8); padding: 1rem; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.05);">
        """, unsafe_allow_html=True)
        st.metric("Total Stok", items['stok'].sum())
        st.markdown("</div>", unsafe_allow_html=True)
    with col3:
        st.markdown("""
            <div style="background: rgba(255,255,255,0.8); padding: 1rem; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.05);">
        """, unsafe_allow_html=True)
        low_stock = len(items[items['stok'] < 10])
        st.metric("Stok Kritis", low_stock)
        st.markdown("</div>", unsafe_allow_html=True)
    fig = px.bar(
        items,
        x='nama',
        y='stok',
        title="Distribusi Stok Barang",
        labels={'nama': 'Barang', 'stok': 'Stok'},
        color='stok',
        color_continuous_scale='Tealgrn'
    )
    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=20, r=20, t=30, b=20)
    )
    st.plotly_chart(fig, use_container_width=True)
    st.subheader("Aktivitas Terakhir")
    transactions = pd.read_sql("""
        SELECT t.*, i.nama 
        FROM transactions t 
        JOIN items i ON t.item_id = i.id
        ORDER BY t.tanggal DESC
    """, get_db()).head(5)
    if not transactions.empty:
        st.dataframe(
            transactions[['tanggal', 'nama', 'tipe', 'jumlah']],
            column_config={
                "tanggal": "Waktu",
                "nama": "Barang",
                "tipe": "Tipe",
                "jumlah": st.column_config.NumberColumn("Jumlah", format="%d")
            },
            hide_index=True,
            use_container_width=True
        )
    else:
        st.info("Belum ada aktivitas")

# ==================================================================================
# HALAMAN DATA BARANG
# ==================================================================================


def barang_page():
    check_access(["superadmin", "admin"])
    render_header()
    tab1, tab2 = st.tabs(["Daftar Barang", "Tambah Barang"])
    with tab1:
        items = pd.read_sql("SELECT * FROM items", get_db())
        if items.empty:
            st.warning("Tidak ada data barang")
        else:
            st.dataframe(
                items,
                column_config={
                    "nama": "Nama Barang",
                    "stok": st.column_config.NumberColumn("Stok", format="%d"),
                    "satuan": "Satuan",
                    "keterangan": "Keterangan"
                },
                use_container_width=True,
                height=300
            )
    with tab2:
        with st.form("tambah_barang", border=True):
            st.subheader("Tambah Barang Baru")
            col1, col2 = st.columns(2)
            nama = col1.text_input(
                "Nama Barang*", placeholder="Contoh: Kertas A4")
            satuan = col2.selectbox("Satuan*", ["pcs", "box", "rim", "lusin"])
            stok = st.number_input("Stok Awal*", min_value=0)
            keterangan = st.text_area(
                "Keterangan", placeholder="Catatan tambahan...")
            if st.form_submit_button("Simpan", type="primary"):
                if not nama:
                    st.error("Nama barang wajib diisi!")
                elif stok < 0:
                    st.error("Stok tidak boleh negatif!")
                else:
                    try:
                        conn = get_db()
                        conn.cursor().execute(
                            "INSERT INTO items (nama, stok, satuan, keterangan) VALUES (?, ?, ?, ?)",
                            (nama.strip(), stok, satuan, keterangan)
                        )
                        conn.commit()
                        st.success(f"Barang {nama} berhasil ditambahkan!")
                    except sqlite3.IntegrityError:
                        st.error("Nama barang sudah ada!")
                    except Exception as e:
                        st.error(f"Error: {str(e)}")

# ==================================================================================
# HALAMAN TRANSAKSI
# ==================================================================================


def transaksi_page():
    check_access(["superadmin", "admin"])
    render_header()
    tab_masuk, tab_keluar = st.tabs(["Tambah Masuk", "Tambah Keluar"])
    with tab_masuk:
        with st.form("form_masuk", border=True):
            st.subheader("Tambah Stok Masuk")
            item = st.selectbox("Barang", pd.read_sql(
                "SELECT nama FROM items", get_db())['nama'].tolist())
            jumlah = st.number_input("Jumlah*", min_value=1)
            tanggal = st.date_input("Tanggal", value=datetime.now())
            keterangan = st.text_area("Keterangan")
            if st.form_submit_button("Proses Masuk", type="primary"):
                if not item or jumlah <= 0:
                    st.error("Lengkapi data!")
                else:
                    try:
                        item_id = pd.read_sql(
                            f"SELECT id FROM items WHERE nama='{item}'", get_db()).iloc[0]['id']
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
        with st.form("form_keluar", border=True):
            st.subheader("Kurangi Stok Keluar")
            item = st.selectbox("Barang", pd.read_sql(
                "SELECT nama FROM items", get_db())['nama'].tolist())
            jumlah = st.number_input("Jumlah*", min_value=1)
            tanggal = st.date_input("Tanggal", value=datetime.now())
            keterangan = st.text_area("Keterangan")
            if st.form_submit_button("Proses Keluar", type="primary"):
                item_data = pd.read_sql(
                    f"SELECT * FROM items WHERE nama='{item}'", get_db())
                if item_data.empty:
                    st.error("Barang tidak ditemukan!")
                elif item_data['stok'].values[0] < jumlah:
                    st.error("Stok tidak mencukupi!")
                else:
                    try:
                        item_id = item_data['id'].values[0]
                        conn = get_db()
                        conn.cursor().execute(
                            "INSERT INTO transactions (item_id, tipe, jumlah, tanggal, keterangan) VALUES (?, ?, ?, ?, ?)",
                            (item_id, 'keluar', jumlah, tanggal, keterangan)
                        )
                        conn.commit()
                        st.success(f"Stok {item} berhasil dikurangi!")
                    except Exception as e:
                        st.error(f"Gagal: {str(e)}")

# ==================================================================================
# HALAMAN LAPORAN
# ==================================================================================


def laporan_page():
    check_access(["superadmin", "admin", "user"])
    render_header()
    items = pd.read_sql("SELECT nama FROM items", get_db())
    if items.empty:
        st.warning("Tidak ada data barang")
        return
    col1, col2 = st.columns(2)
    start_date = col1.date_input(
        "Tanggal Mulai", datetime.now().replace(day=1))
    end_date = col2.date_input("Tanggal Akhir", datetime.now())
    query = """
        SELECT 
            strftime('%Y-%m', tanggal) AS bulan,
            i.nama,
            SUM(CASE WHEN tipe='masuk' THEN jumlah ELSE 0 END) AS total_masuk,
            SUM(CASE WHEN tipe='keluar' THEN jumlah ELSE 0 END) AS total_keluar
        FROM transactions 
        JOIN items i ON transactions.item_id = i.id
        WHERE tanggal BETWEEN ? AND ?
        GROUP BY bulan, i.nama
    """
    laporan = pd.read_sql(query, get_db(), params=(start_date, end_date))
    if not laporan.empty:
        st.dataframe(laporan, use_container_width=True)
        fig = px.bar(
            laporan,
            x='bulan',
            y=['total_masuk', 'total_keluar'],
            title="Laporan Bulanan",
            barmode='group',
            labels={'value': 'Jumlah', 'variable': 'Tipe'}
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Tidak ada data untuk periode ini")

# ==================================================================================
# HALAMAN PENGGUNA (Sesuai Skema Anda)
# ==================================================================================


def pengaturan_page():
    check_access(["superadmin"])
    render_header()
    tab1, tab2, tab3 = st.tabs(["Ubah Password", "Kelola User", "Hapus User"])
    with tab1:
        with st.form("ubah_password"):
            st.subheader("Ubah Password")
            password_lama = st.text_input("Password Lama", type="password")
            password_baru = st.text_input("Password Baru", type="password")
            konfirmasi = st.text_input("Konfirmasi Password", type="password")
            if st.form_submit_button("Simpan", type="primary"):
                if not password_lama or not password_baru or not konfirmasi:
                    st.error("Lengkapi semua field!")
                elif password_baru != konfirmasi:
                    st.error("Password baru tidak cocok!")
                else:
                    try:
                        conn = get_db()
                        c = conn.cursor()
                        c.execute(
                            "SELECT password FROM users WHERE username=?", (st.session_state.username,))
                        current_pass = c.fetchone()[0]
                        if password_lama == current_pass:
                            c.execute("UPDATE users SET password=? WHERE username=?",
                                      (password_baru, st.session_state.username))
                            conn.commit()
                            st.success("Password berhasil diubah!")
                        else:
                            st.error("Password lama salah!")
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
    with tab2:
        st.subheader("Tambah/Edit User")
        with st.form("user_form"):
            username = st.text_input("Username*")
            password = st.text_input("Password*", type="password")
            role = st.selectbox("Role*", ["admin", "user"])
            submit_type = st.radio("Tipe", ["Tambah", "Edit"], horizontal=True)
            if st.form_submit_button("Proses", type="primary"):
                if not username or not password:
                    st.error("Data tidak lengkap!")
                else:
                    try:
                        conn = get_db()
                        c = conn.cursor()
                        if submit_type == "Tambah":
                            c.execute(
                                "INSERT INTO users (username, password, role) VALUES (?, ?, ?)", (username, password, role))
                        else:
                            c.execute(
                                "UPDATE users SET password=?, role=? WHERE username=?", (password, role, username))
                        conn.commit()
                        st.success(f"User {username} berhasil diperbarui!")
                    except sqlite3.IntegrityError:
                        st.error("Username sudah ada!")
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
    with tab3:
        st.subheader("Hapus User")
        users = pd.read_sql(
            "SELECT username FROM users WHERE role != 'superadmin'", get_db())
        hapus_username = st.selectbox("Pilih User", users)
        if st.button("Hapus User", type="primary"):
            try:
                conn = get_db()
                conn.cursor().execute("DELETE FROM users WHERE username=?", (hapus_username,))
                conn.commit()
                st.success(f"User {hapus_username} berhasil dihapus!")
            except Exception as e:
                st.error(f"Error: {str(e)}")


# ==================================================================================
# MAIN EXECUTION
# ==================================================================================
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    login_page()
else:
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
    st.sidebar.markdown("---")
    if st.sidebar.button("Logout", use_container_width=True):
        st.session_state.clear()
        st.rerun()
