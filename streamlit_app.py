import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import base64
import os
from st_aggrid import AgGrid, GridOptionsBuilder

# ==================================================================================
# KONFIGURASI AWAL
# ==================================================================================
st.set_page_config(
    page_title="Inventaris Pro",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================================================================================
# PENINGKATAN SISTEM STYLING
# ==================================================================================
st.markdown("""
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        body {
            font-family: 'Inter', sans-serif;
            background-color: #f5f5f5;
            color: #333333;
        }
        .stApp {
            max-width: 2000px;
            margin: 0 auto;
            padding: 2rem;
        }
        .login-container {
            max-width: 450px;
            margin: 10% auto;
            padding: 3rem;
            background: white;
            border-radius: 18px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.15);
        }
        .header {
            background: linear-gradient(135deg, #4CAF50, #45a049);
            padding: 3rem;
            border-radius: 18px;
            margin-bottom: 2rem;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }
        .metric-card {
            padding: 2rem;
            border-radius: 15px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            transition: transform 0.3s ease;
        }
        .metric-card:hover {
            transform: translateY(-5px);
        }
        .metric-icon {
            font-size: 2.5rem;
            color: #4CAF50;
        }
        .metric-value {
            font-size: 2.25rem;
            font-weight: 700;
            color: #2d3436;
        }
        .metric-label {
            font-size: 1.1rem;
            color: #7f8c8d;
            margin-top: 0.75rem;
        }
        .sidebar .sidebar-content {
            background: #ffffff;
            border-radius: 18px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }
        .stButton>button {
            background: #4CAF50;
            color: white;
            border-radius: 12px;
            padding: 1rem 2rem;
            font-weight: 600;
            transition: background 0.3s ease;
        }
        .stButton>button:hover {
            background: #45a049;
        }
        .dataframe {
            border-radius: 12px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }
        .stTabs [data-baseweb="tab-list"] {
            gap: 2px;
        }
        .stTabs [data-baseweb="tab"] {
            padding: 1rem 2rem;
            border-radius: 12px 12px 0 0;
            background: #f0f2f6;
            transition: background 0.3s ease;
        }
        .stTabs [aria-selected="true"] {
            background: white;
            border-bottom: 2px solid #4CAF50;
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
    c.execute('''
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nama TEXT UNIQUE NOT NULL,
            stok INTEGER NOT NULL,
            satuan TEXT NOT NULL,
            keterangan TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER NOT NULL,
            tipe TEXT CHECK(tipe IN ('masuk', 'keluar')) NOT NULL,
            jumlah INTEGER NOT NULL,
            tanggal DATE NOT NULL,
            keterangan TEXT,
            FOREIGN KEY(item_id) REFERENCES items(id)
        )
    ''')
    c.execute("SELECT * FROM users WHERE username='superadmin'")
    if not c.fetchone():
        c.execute(
            "INSERT INTO users (username, password, role) VALUES ('superadmin', 'superadmin123', 'superadmin')")
        conn.commit()

# ==================================================================================
# FUNGSI PEMBANTU UNTUK GAMBAR
# ==================================================================================


def get_image_base64(image_path):
    if not os.path.exists(image_path):
        return None
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode('utf-8')


def get_logo_base64():
    return get_image_base64("stock.png")


def get_profile_image(role):
    image_map = {
        "superadmin": "superadmin.png",
        "admin": "admin.png",
        "user": "user.png"
    }
    image_path = image_map.get(role, "user.png")
    base64_image = get_image_base64(image_path)
    if not base64_image:
        return get_image_base64("user.png")
    return f"data:image/png;base64,{base64_image}"

# ==================================================================================
# HALAMAN LOGIN
# ==================================================================================


def login_page():
    logo_base64 = get_logo_base64()
    if logo_base64:
        st.markdown(f"""
            <div style="text-align: center; margin-bottom: 2rem;">
                <img src="data:image/png;base64,{logo_base64}" 
                     style="width: 150px; height: auto;">
            </div>
        """, unsafe_allow_html=True)
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
# SISTEM AUTHENTIKASI
# ==================================================================================


def verify_login(username, password):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT role FROM users WHERE username=? AND password=?",
              (username, password))
    result = c.fetchone()
    return result[0] if result else None


def check_access(required_roles):
    if not st.session_state.get("authenticated", False):
        st.error("Anda harus login!")
        st.stop()
    if st.session_state.role not in required_roles:
        st.error("Anda tidak memiliki akses ke halaman ini!")
        st.stop()

# ==================================================================================
# HEADER DAN SIDEBAR
# ==================================================================================


def render_header():
    st.markdown("""
        <div class="header">
            <h1 style="color: white; margin-bottom: 1rem;">📦 Inventaris Pro</h1>
            <p style="color: rgba(255,255,255,0.8); font-size: 1.25rem;">
                Solusi Manajemen Stok untuk Bisnis Modern
            </p>
        </div>
    """, unsafe_allow_html=True)


def render_sidebar():
    with st.sidebar:
        profile_image = get_profile_image(st.session_state.role)
        st.markdown(f"""
            <div style="
                display: flex;
                align-items: center;
                justify-content: center;
                text-align: center;
                margin: 2rem 0;
                padding: 1rem;
                border-radius: 15px;
                box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            ">
                <img src="{profile_image}" style="width: 100px; height: auto; margin-right: 1rem; border-radius: 50%;">
                <div>
                    <h3 style="color: #1e3799; margin: 0;">Halo, {st.session_state.username}</h3>
                    <p style="color: #6c757d; margin: 0.5rem 0 0;">Role: {st.session_state.role}</p>
                </div>
            </div>
        """, unsafe_allow_html=True)
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
                                  "🔄 Transaksi" if x == "Transaksi" else
                                  "📄 Laporan" if x == "Laporan" else
                                  "⚙️ Pengaturan"
        )

# ==================================================================================
# HALAMAN DASHBOARD
# ==================================================================================


def dashboard_page():
    check_access(["superadmin", "admin", "user"])
    render_header()
    items = pd.read_sql("SELECT * FROM items", get_db())
    transactions = pd.read_sql("""
        SELECT t.*, i.nama 
        FROM transactions t 
        JOIN items i ON t.item_id = i.id
        ORDER BY t.tanggal DESC
    """, get_db()).head(5)

    # Metric Cards
    col1, col2, col3 = st.columns(3)
    with col1:
        create_metric_card(
            icon="fas fa-boxes",
            value=len(items),
            label="Total Barang",
            color="#4CAF50"
        )
    with col2:
        create_metric_card(
            icon="fas fa-layer-group",
            value=items['stok'].sum(),
            label="Total Stok",
            color="#4CAF50"
        )
    with col3:
        low_stock = len(items[items['stok'] < 10])
        create_metric_card(
            icon="fas fa-exclamation-triangle",
            value=low_stock,
            label="Stok Kritis",
            color="#4CAF50"
        )

    # Stok Distribution Chart
    st.subheader("Distribusi Stok Barang")
    if not items.empty:
        fig = px.bar(
            items,
            x='nama',
            y='stok',
            title="Klik pada legenda untuk filter",
            labels={'nama': 'Barang', 'stok': 'Jumlah Stok'},
            color='stok',
            color_continuous_scale='Viridis',
            hover_data={'nama': True, 'stok': True, 'satuan': True}
        )
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=20, r=20, t=30, b=20),
            xaxis_tickangle=45,
            font=dict(size=14),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
            annotations=[
                dict(
                    x=0.5,
                    y=1.15,
                    xref="paper",
                    yref="paper",
                    text="Stok Minimum: 10",
                    showarrow=False,
                    font=dict(color="red", size=12)
                )
            ]
        )
        fig.add_hline(y=10, line_dash="dot", line_color="red")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Tidak ada data barang", icon="⚠️")

    # Recent Transactions
    st.subheader("Aktivitas Terakhir")
    if not transactions.empty:
        transactions['status'] = transactions['tipe'].apply(
            lambda x: "✅ Masuk" if x == "masuk" else "❌ Keluar"
        )
        st.dataframe(
            transactions[['tanggal', 'nama', 'status', 'jumlah']],
            column_config={
                "tanggal": st.column_config.DateColumn("Tanggal", format="DD MMM YYYY"),
                "nama": st.column_config.TextColumn("Barang"),
                "status": st.column_config.TextColumn("Status",
                                                      help="✅ Masuk = Penambahan stok | ❌ Keluar = Pengurangan stok",
                                                      width="medium"
                                                      ),
                "jumlah": st.column_config.NumberColumn("Jumlah", format="%d")
            },
            hide_index=True,
            use_container_width=True
        )
    else:
        st.info("Belum ada aktivitas", icon="ℹ️")

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
                        # Insert transaction
                        conn.cursor().execute(
                            "INSERT INTO transactions (item_id, tipe, jumlah, tanggal, keterangan) VALUES (?, ?, ?, ?, ?)",
                            (item_id, 'masuk', jumlah, tanggal, keterangan)
                        )
                        # Update stock
                        conn.cursor().execute(
                            "UPDATE items SET stok = stok + ? WHERE id = ?",
                            (jumlah, item_id)
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
                        # Insert transaction
                        conn.cursor().execute(
                            "INSERT INTO transactions (item_id, tipe, jumlah, tanggal, keterangan) VALUES (?, ?, ?, ?, ?)",
                            (item_id, 'keluar', jumlah, tanggal, keterangan)
                        )
                        # Update stock
                        conn.cursor().execute(
                            "UPDATE items SET stok = stok - ? WHERE id = ?",
                            (jumlah, item_id)
                        )
                        conn.commit()
                        st.success(f"Stok {item} berhasil dikurangi!")
                    except Exception as e:
                        st.error(f"Gagal: {str(e)}")

# ==================================================================================
# HALAMAN LAPORAN (DIPERBAIKI)
# ==================================================================================


def laporan_page():
    check_access(["superadmin", "admin", "user"])
    render_header()

    # Fungsi untuk menghasilkan laporan
    def generate_report(items, start_date, end_date, aggregation):
        date_format = {
            "Harian": "%Y-%m-%d",
            "Mingguan": "%Y-%U",
            "Bulanan": "%Y-%m",
            "Tahunan": "%Y"
        }[aggregation]

        query = f"""
            SELECT 
                strftime('{date_format}', tanggal) AS periode,
                i.nama,
                SUM(CASE WHEN tipe='masuk' THEN jumlah ELSE 0 END) AS total_masuk,
                SUM(CASE WHEN tipe='keluar' THEN jumlah ELSE 0 END) AS total_keluar
            FROM transactions 
            JOIN items i ON transactions.item_id = i.id
            WHERE tanggal BETWEEN ? AND ?
            GROUP BY periode, i.nama
        """
        return pd.read_sql(query, get_db(), params=(start_date, end_date))

    # Filter dan kontrol
    st.subheader("Pengaturan Laporan")
    col1, col2, col3 = st.columns(3)
    items = pd.read_sql("SELECT nama FROM items", get_db())
    selected_items = col1.multiselect("Filter Barang", items['nama'].unique())
    aggregation = col2.selectbox(
        "Aggregasi", ["Harian", "Mingguan", "Bulanan", "Tahunan"])

    start_date = col3.date_input(
        "Tanggal Mulai", datetime.now() - timedelta(days=30))
    end_date = col3.date_input("Tanggal Akhir", datetime.now())

    # Proses data
    if selected_items:
        filtered_items = ", ".join([f"'{item}'" for item in selected_items])
        query_filter = f" AND i.nama IN ({filtered_items})"
    else:
        query_filter = ""

    df = generate_report(items, start_date, end_date, aggregation)

    # Tampilkan hasil
    if not df.empty:
        # Ringkasan metrik
        total_masuk = df['total_masuk'].sum()
        total_keluar = df['total_keluar'].sum()

        col1, col2, col3 = st.columns(3)
        col1.metric("Total Masuk", f"{total_masuk} item")
        col2.metric("Total Keluar", f"{total_keluar} item")
        col3.metric("Net Perubahan", f"{total_masuk - total_keluar} item")

        # Chart interaktif
        fig = px.line(df,
                      x='periode',
                      y=['total_masuk', 'total_keluar'],
                      color='nama',
                      title='Tren Stok',
                      labels={
                          'periode': 'Periode',
                          'value': 'Jumlah'
                      })
        fig.update_layout(hovermode='x unified')
        st.plotly_chart(fig, use_container_width=True)

        # Tabel detail
        st.subheader("Data Detail")
        gb = GridOptionsBuilder.from_dataframe(df)
        gb.configure_pagination(paginationPageSize=10)
        gb.configure_side_bar()
        gb.configure_default_column(
            resizable=True,
            filterable=True,
            sortable=True,
            autoHeight=True,
            flex=1  # Auto-expand columns
        )
        # Konfigurasi kolom spesifik
        gb.configure_column(
            "periode", header_name="Periode", minWidth=150, flex=1)
        gb.configure_column("nama", header_name="Barang", minWidth=200, flex=2)
        gb.configure_column("total_masuk", header_name="Total Masuk",
                            type=["numericColumn"], minWidth=150, flex=1)
        gb.configure_column("total_keluar", header_name="Total Keluar",
                            type=["numericColumn"], minWidth=150, flex=1)

        gridOptions = gb.build()
        gridOptions['domLayout'] = 'autoHeight'  # Auto height
        # Auto-fit columns
        gridOptions['onGridReady'] = 'function(params) { params.api.sizeColumnsToFit(); }'

        AgGrid(
            df,
            gridOptions=gridOptions,
            enable_enterprise_modules=False,
            allow_unsafe_jscode=True,
            height=400,
            width='100%',
            fit_columns_on_grid_load=True,
            theme='streamlit',
            update_mode='MODEL_CHANGED'
        )

        # Export options
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Export ke Excel"):
                with pd.ExcelWriter("laporan.xlsx", engine='openpyxl') as writer:
                    df.to_excel(writer, index=False)
                st.success("File Excel berhasil dibuat!")
        with col2:
            if st.button("Export ke CSV"):
                df.to_csv("laporan.csv", index=False)
                st.success("File CSV berhasil dibuat!")
    else:
        st.warning("Tidak ada data untuk parameter yang dipilih")


# ==================================================================================
# HALAMAN PENGGATURAN (DIPERBAIKI)
# ==================================================================================
def pengaturan_page():
    check_access(["superadmin"])
    render_header()

    tab1, tab2 = st.tabs([
        "🔑 Ubah Password",
        "👥 Manajemen User"
    ])

    # =====================================
    # TAB UBAH PASSWORD
    # =====================================
    with tab1:
        st.subheader("Ubah Password Superadmin")
        with st.container():
            with st.form("password_form", border=True):
                st.markdown("### Kebijakan Password")
                st.caption(
                    "• Minimal 8 karakter | • Mengandung huruf besar dan kecil | • Mengandung angka")

                password_lama = st.text_input("Password Lama", type="password")
                password_baru = st.text_input("Password Baru", type="password")
                konfirmasi = st.text_input(
                    "Konfirmasi Password", type="password")

                if st.form_submit_button("Simpan Perubahan", type="primary", use_container_width=True):
                    errors = []
                    if not password_lama:
                        errors.append("Password lama wajib diisi")
                    if len(password_baru) < 8:
                        errors.append("Password baru minimal 8 karakter")
                    if password_baru != konfirmasi:
                        errors.append("Konfirmasi password tidak cocok")

                    if errors:
                        for error in errors:
                            st.error(error)
                    else:
                        try:
                            conn = get_db()
                            c = conn.cursor()
                            c.execute("SELECT password FROM users WHERE username=?",
                                      (st.session_state.username,))
                            current_pass = c.fetchone()[0]

                            if password_lama != current_pass:
                                st.error("Password lama salah!")
                            else:
                                c.execute("UPDATE users SET password=? WHERE username=?",
                                          (password_baru, st.session_state.username))
                                conn.commit()
                                st.success("Password berhasil diperbarui!")
                                st.balloons()
                        except Exception as e:
                            st.error(f"Terjadi kesalahan: {str(e)}")

    # =====================================
    # TAB MANAJEMEN USER (GABUNGAN)
    # =====================================
    with tab2:
        st.subheader("Manajemen Pengguna")
        user_list = pd.read_sql(
            "SELECT * FROM users WHERE role != 'superadmin'", get_db())

        # Mode operasi
        mode = st.radio("Pilih Mode", ["Tambah User", "Edit/Hapus User"],
                        horizontal=True, label_visibility="collapsed")

        if mode == "Tambah User":
            with st.form("tambah_user_form", border=True):
                st.markdown("### Tambah User Baru")
                new_username = st.text_input("Username*")
                new_password = st.text_input("Password*", type="password")
                new_role = st.selectbox("Role*", ["admin", "user"])

                if st.form_submit_button("Tambah User", type="primary", use_container_width=True):
                    if not new_username or not new_password:
                        st.error("Semua field wajib diisi!")
                    else:
                        try:
                            conn = get_db()
                            conn.cursor().execute(
                                "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                                (new_username, new_password, new_role)
                            )
                            conn.commit()
                            st.success(
                                f"User {new_username} berhasil ditambahkan!")
                        except sqlite3.IntegrityError:
                            st.error("Username sudah ada!")
                        except Exception as e:
                            st.error(f"Error: {str(e)}")

        else:  # Mode Edit/Hapus
            if user_list.empty:
                st.warning("Tidak ada user yang bisa dikelola")
            else:
                selected_user = st.selectbox(
                    "Pilih User", user_list['username'].tolist())
                user_data = user_list[user_list['username']
                                      == selected_user].iloc[0]

                # Form Edit
                with st.form("edit_user_form", border=True):
                    st.markdown(f"### Edit User: {selected_user}")
                    edit_password = st.text_input(
                        "Password Baru", type="password")
                    edit_role = st.selectbox("Role*", ["admin", "user"],
                                             index=0 if user_data['role'] == 'admin' else 1)

                    col1, col2 = st.columns([1, 1])
                    with col1:
                        edit_submit = st.form_submit_button(
                            "Simpan Perubahan", type="primary", use_container_width=True)
                    with col2:
                        delete_submit = st.form_submit_button(
                            "⚠️ Hapus User", type="primary", use_container_width=True)

                    # Handle edit
                    if edit_submit:
                        try:
                            conn = get_db()
                            conn.cursor().execute(
                                "UPDATE users SET password=?, role=? WHERE username=?",
                                (edit_password, edit_role, selected_user)
                            )
                            conn.commit()
                            st.success(
                                f"User {selected_user} berhasil diperbarui!")
                        except Exception as e:
                            st.error(f"Error: {str(e)}")

                    # Handle delete
                    if delete_submit:
                        if st.checkbox(f"Konfirmasi hapus {selected_user}"):
                            try:
                                conn = get_db()
                                conn.cursor().execute("DELETE FROM users WHERE username=?", (selected_user,))
                                conn.commit()
                                st.success(
                                    f"User {selected_user} berhasil dihapus!")
                                st.rerun()  # Refresh halaman setelah hapus
                            except Exception as e:
                                st.error(f"Error: {str(e)}")
                        else:
                            st.error(
                                "Centang kotak konfirmasi untuk menghapus")


# ==================================================================================
# FUNGSI PEMBANTU
# ==================================================================================


def create_metric_card(icon, value, label, color):
    st.markdown(f"""
        <div class="metric-card" style="border-left: 5px solid {color};">
            <div style="display: flex; align-items: center; gap: 1rem;">
                <i class="{icon} metric-icon"></i>
                <div>
                    <h2 class="metric-value">{value}</h2>
                    <p class="metric-label">{label}</p>
                </div>
            </div>
        </div>
    """, unsafe_allow_html=True)


# ==================================================================================
# MAIN EXECUTION
# ==================================================================================
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    login_page()
else:
    init_db()
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
