import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
from datetime import datetime
from hashlib import sha256

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

    # Tabel Users
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT CHECK(role IN ('superadmin', 'admin', 'user')) NOT NULL DEFAULT 'user'
        )
    ''')

    # Tabel Items
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
            tanggal DATE DEFAULT CURRENT_DATE,
            keterangan TEXT,
            FOREIGN KEY(item_id) REFERENCES items(id)
        )
    ''')

    # Trigger Stok
    c.execute('''
        CREATE TRIGGER IF NOT EXISTS update_stok
        AFTER INSERT ON transactions
        FOR EACH ROW
        WHEN (SELECT stok FROM items WHERE id = NEW.item_id) >= NEW.jumlah OR NEW.tipe = 'masuk'
        BEGIN
            UPDATE items
            SET stok = stok + (CASE 
                                WHEN NEW.tipe = 'masuk' THEN NEW.jumlah
                                WHEN NEW.tipe = 'keluar' THEN -NEW.jumlah
                               END)
            WHERE id = NEW.item_id;
        END;
    ''')

    # Sample admin jika belum ada
    c.execute("SELECT * FROM users WHERE username='superadmin'")
    if not c.fetchone():
        password_hash = sha256("superadmin123".encode()).hexdigest()
        c.execute("INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                  ("superadmin", password_hash, "superadmin"))
        conn.commit()

    conn.close()


init_db()

# ==================================================================================
# SISTEM AUTHENTIKASI
# ==================================================================================


def hash_password(password):
    return sha256(password.encode()).hexdigest()


def verify_login(username, password):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT role FROM users WHERE username=? AND password_hash=?",
              (username, hash_password(password)))
    result = c.fetchone()
    conn.close()
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
                st.session_state.authenticated = True
                st.session_state.role = role
                st.session_state.username = username
                st.experimental_rerun()
            else:
                st.error("Username/password salah!")

# ==================================================================================
# HALAMAN PENGATURAN (CRUD User)
# ==================================================================================


def pengaturan_page():
    render_header()

    if st.session_state.role == "superadmin":
        tab1, tab2 = st.tabs(["Ubah Password", "Manajemen User"])

        # Tab Ubah Password
        with tab1:
            with st.form("ubah_password"):
                st.subheader("Ubah Password")
                password_lama = st.text_input("Password Lama", type="password")
                password_baru = st.text_input("Password Baru", type="password")
                konfirmasi_password = st.text_input(
                    "Konfirmasi Password", type="password")

                if st.form_submit_button("Simpan", type="primary"):
                    if not password_lama or not password_baru or not konfirmasi_password:
                        st.error("Lengkapi semua field!")
                    elif password_baru != konfirmasi_password:
                        st.error("Password baru tidak cocok!")
                    else:
                        conn = get_db()
                        c = conn.cursor()
                        c.execute("SELECT password_hash FROM users WHERE username=?",
                                  (st.session_state.username,))
                        current_hash = c.fetchone()[0]

                        if hash_password(password_lama) == current_hash:
                            new_hash = hash_password(password_baru)
                            c.execute("UPDATE users SET password_hash=? WHERE username=?",
                                      (new_hash, st.session_state.username))
                            conn.commit()
                            st.success("Password berhasil diubah!")
                        else:
                            st.error("Password lama salah!")
                        conn.close()

        # Tab Manajemen User (Superadmin only)
        with tab2:
            st.subheader("Manajemen User")
            users = pd.read_sql("SELECT username, role FROM users", get_db())
            st.dataframe(users, use_container_width=True)

            with st.expander("Tambah/Edit User"):
                with st.form("user_form"):
                    username = st.text_input("Username*")
                    password = st.text_input("Password*", type="password")
                    role = st.selectbox("Role*", ["admin", "user"])
                    submit_type = st.radio(
                        "Tipe", ["Tambah", "Edit"], horizontal=True)

                    if st.form_submit_button("Proses"):
                        if not username or not password:
                            st.error("Data tidak lengkap!")
                        else:
                            conn = get_db()
                            c = conn.cursor()
                            if submit_type == "Tambah":
                                try:
                                    c.execute("INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                                              (username, hash_password(password), role))
                                    conn.commit()
                                    st.success(
                                        f"User {username} berhasil ditambahkan!")
                                except sqlite3.IntegrityError:
                                    st.error("Username sudah ada!")
                            else:
                                c.execute("UPDATE users SET password_hash=?, role=? WHERE username=?",
                                          (hash_password(password), role, username))
                                conn.commit()
                                st.success(
                                    f"User {username} berhasil diupdate!")
                            conn.close()

            with st.expander("Hapus User"):
                hapus_username = st.selectbox("Pilih User",
                                              pd.read_sql("SELECT username FROM users", get_db())['username'].tolist())
                if st.button("Hapus", type="primary"):
                    conn = get_db()
                    c = conn.cursor()
                    c.execute("DELETE FROM users WHERE username=?",
                              (hapus_username,))
                    conn.commit()
                    st.success(f"User {hapus_username} berhasil dihapus!")
                    conn.close()

    elif st.session_state.role in ["admin", "user"]:
        with st.form("ubah_password"):
            st.subheader("Ubah Password")
            password_lama = st.text_input("Password Lama", type="password")
            password_baru = st.text_input("Password Baru", type="password")
            konfirmasi_password = st.text_input(
                "Konfirmasi Password", type="password")

            if st.form_submit_button("Simpan", type="primary"):
                if not password_lama or not password_baru or not konfirmasi_password:
                    st.error("Lengkapi semua field!")
                elif password_baru != konfirmasi_password:
                    st.error("Password baru tidak cocok!")
                else:
                    conn = get_db()
                    c = conn.cursor()
                    c.execute("SELECT password_hash FROM users WHERE username=?",
                              (st.session_state.username,))
                    current_hash = c.fetchone()[0]

                    if hash_password(password_lama) == current_hash:
                        new_hash = hash_password(password_baru)
                        c.execute("UPDATE users SET password_hash=? WHERE username=?",
                                  (new_hash, st.session_state.username))
                        conn.commit()
                        st.success("Password berhasil diubah!")
                    else:
                        st.error("Password lama salah!")
                    conn.close()
    else:
        st.error("Akses ditolak!")

# ==================================================================================
# PROTEKSI HALAMAN
# ==================================================================================


def check_access(required_role):
    if 'authenticated' not in st.session_state or not st.session_state.authenticated:
        st.error("Anda harus login!")
        st.stop()
    if st.session_state.role not in required_role:
        st.error("Anda tidak memiliki akses ke halaman ini!")
        st.stop()

# ==================================================================================
# HALAMAN UTAMA (SISANYA SAMA DENGAN KODE SEBELUMNYA)
# ==================================================================================
# ... (kode untuk dashboard_page, barang_page, transaksi_page, laporan_page)

# ==================================================================================
# RENDER SIDEBAR DENGAN PROTEKSI ROLE
# ==================================================================================


def render_sidebar():
    with st.sidebar:
        st.markdown(f"""
            <div style="text-align: center; margin: 2rem 0;">
                <h3 style="color: #1e3799;">Selamat Datang, <br>{st.session_state.username}</h3>
            </div>
        """, unsafe_allow_html=True)

        if st.session_state.role == "superadmin":
            menu = ["Dashboard", "Data Barang",
                    "Transaksi", "Laporan", "Pengaturan"]
        elif st.session_state.role == "admin":
            menu = ["Dashboard", "Data Barang", "Transaksi", "Laporan"]
        else:
            menu = ["Dashboard", "Laporan"]

        return st.radio("Menu", menu,
                        format_func=lambda x: "📊 Dashboard" if x == "Dashboard" else
                        "📦 Data Barang" if x == "Data Barang" else
                        "🔄 Transaksi" if x == "Transaksi" else
                        "📄 Laporan" if x == "Laporan" else
                        "⚙️ Pengaturan")


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
        check_access(["superadmin", "admin", "user"])
        dashboard_page()
    elif menu == "Data Barang":
        check_access(["superadmin", "admin"])
        barang_page()
    elif menu == "Transaksi":
        check_access(["superadmin", "admin"])
        transaksi_page()
    elif menu == "Laporan":
        check_access(["superadmin", "admin", "user"])
        laporan_page()
    elif menu == "Pengaturan":
        check_access(["superadmin"])
        pengaturan_page()

    # Tambahkan tombol logout di sidebar
    st.sidebar.markdown("---")
    if st.sidebar.button("Logout", use_container_width=True):
        st.session_state.clear()
        st.experimental_rerun()
