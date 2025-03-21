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
# DATABASE & LOGIC (Disesuaikan)
# ==================================================================================


@st.cache_resource
def get_db():
    conn = sqlite3.connect('database.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    c = conn.cursor()

    # Tabel Users (tanpa hashing)
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,  -- Kolom password tanpa hash
            role TEXT CHECK(role IN ('superadmin', 'admin', 'user')) NOT NULL DEFAULT 'user'
        )
    ''')

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
            tanggal DATE DEFAULT CURRENT_DATE,
            keterangan TEXT,
            FOREIGN KEY(item_id) REFERENCES items(id)
        )
    ''')

    # Trigger Update Stok
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

    # Sample data user (password plaintext)
    c.execute("SELECT * FROM users WHERE username='superadmin'")
    if not c.fetchone():
        c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                  ("superadmin", "superadmin123", "superadmin"))
        c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                  ("admin", "admin123", "admin"))
        c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                  ("user", "user123", "user"))
        conn.commit()

    conn.close()


init_db()

# ==================================================================================
# SISTEM AUTHENTIKASI (Tanpa Hashing)
# ==================================================================================


def verify_login(username, password):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT role FROM users WHERE username=? AND password=?",
              (username, password))  # Bandingkan langsung tanpa hash
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
                st.session_state.update({
                    "authenticated": True,
                    "role": role,
                    "username": username
                })
                st.success("Login berhasil! Redirecting...")
                st.experimental_rerun()
            else:
                st.error("Username/password salah!")

# ==================================================================================
# HALAMAN PENGGUNA (Disesuaikan)
# ==================================================================================


def pengaturan_page():
    check_access(["superadmin"])
    render_header()

    tab1, tab2, tab3 = st.tabs(["Ubah Password", "Kelola User", "Hapus User"])

    # Tab Ubah Password
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
                        c.execute("SELECT password FROM users WHERE username=?",
                                  (st.session_state.username,))
                        current_pass = c.fetchone()['password']

                        if password_lama == current_pass:  # Bandingkan plaintext
                            c.execute("UPDATE users SET password=? WHERE username=?",
                                      (password_baru, st.session_state.username))
                            conn.commit()
                            st.success("Password berhasil diubah!")
                        else:
                            st.error("Password lama salah!")
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
                    finally:
                        conn.close()

    # Tab Kelola User
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
                            c.execute("INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                                      # Simpan password plaintext
                                      (username, password, role))
                        else:
                            c.execute("UPDATE users SET password=?, role=? WHERE username=?",
                                      (password, role, username))

                        conn.commit()
                        st.success(f"User {username} berhasil diperbarui!")
                    except sqlite3.IntegrityError:
                        st.error("Username sudah ada!")
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
                    finally:
                        conn.close()

    # Tab Hapus User
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
            finally:
                conn.close()

# ==================================================================================
# FUNGSI LAINNYA TETAP SAMA
# ==================================================================================
# ... (fungsi render_header, render_sidebar, dashboard_page, barang_page, transaksi_page, laporan_page tetap sama)


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

    # Tombol Logout
    st.sidebar.markdown("---")
    if st.sidebar.button("Logout", use_container_width=True):
        st.session_state.clear()
        st.experimental_rerun()
