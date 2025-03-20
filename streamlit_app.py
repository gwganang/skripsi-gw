import streamlit as st
import sqlite3
import pandas as pd
import os
import logging

# Konfigurasi logging
logging.basicConfig(level=logging.DEBUG)

# === BAGIAN PEMBUATAN DIREKTORI ===
# Membuat direktori database jika belum ada
if not os.path.exists('database'):
    os.makedirs('database')

# === DATABASE CONNECTION ===
@st.cache_resource
def get_connection():
    try:
        return sqlite3.connect('database/inventaris.db', check_same_thread=False)
    except sqlite3.Error as e:
        st.error("Gagal terhubung ke database")
        logging.error(f"Database Error: {e}")
        raise

# === DATABASE INITIALIZATION ===
def init_db():
    conn = get_connection()
    c = conn.cursor()
    
    # Tabel Inventaris
    c.execute('''
        CREATE TABLE IF NOT EXISTS inventaris (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nama_barang TEXT NOT NULL UNIQUE,
            jumlah_stok INTEGER NOT NULL CHECK (jumlah_stok >= 0),
            satuan TEXT NOT NULL
        )
    ''')
    
    # Tabel Transaksi Masuk
    c.execute('''
        CREATE TABLE IF NOT EXISTS transaksi_masuk (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER,
            jumlah INTEGER NOT NULL CHECK (jumlah > 0),
            tanggal DATE DEFAULT CURRENT_DATE,
            keterangan TEXT,
            FOREIGN KEY(item_id) REFERENCES inventaris(id)
        )
    ''')
    
    # Tabel Transaksi Keluar
    c.execute('''
        CREATE TABLE IF NOT EXISTS transaksi_keluar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER,
            jumlah INTEGER NOT NULL CHECK (jumlah > 0),
            tanggal DATE DEFAULT CURRENT_DATE,
            keterangan TEXT,
            FOREIGN KEY(item_id) REFERENCES inventaris(id)
        )
    ''')
    
    # Trigger untuk transaksi keluar
    c.execute('''
        CREATE TRIGGER IF NOT EXISTS kurangi_stok
        AFTER INSERT ON transaksi_keluar
        FOR EACH ROW
        WHEN (SELECT jumlah_stok FROM inventaris WHERE id = NEW.item_id) >= NEW.jumlah
        BEGIN
            UPDATE inventaris
            SET jumlah_stok = jumlah_stok - NEW.jumlah
            WHERE id = NEW.item_id;
        END;
    ''')
    
    conn.commit()

init_db()

# === FUNGSI CRUD ===
def get_items():
    try:
        conn = get_connection()
        return pd.read_sql("SELECT * FROM inventaris", conn)
    except Exception as e:
        st.error("Gagal memuat data barang")
        logging.error(f"Error get_items: {e}")
        return pd.DataFrame()

def get_transaksi_masuk():
    try:
        conn = get_connection()
        return pd.read_sql("""
            SELECT tm.*, i.nama_barang 
            FROM transaksi_masuk tm 
            JOIN inventaris i ON tm.item_id = i.id
        """, conn)
    except Exception as e:
        st.error("Gagal memuat riwayat masuk")
        logging.error(f"Error get_transaksi_masuk: {e}")
        return pd.DataFrame()

def get_transaksi_keluar():
    try:
        conn = get_connection()
        return pd.read_sql("""
            SELECT tk.*, i.nama_barang 
            FROM transaksi_keluar tk 
            JOIN inventaris i ON tk.item_id = i.id
        """, conn)
    except Exception as e:
        st.error("Gagal memuat riwayat keluar")
        logging.error(f"Error get_transaksi_keluar: {e}")
        return pd.DataFrame()

# === STREAMLIT UI ===
st.set_page_config(page_title="Sistem Inventaris ATK", layout="wide")
menu = ["Data Barang", "Transaksi Masuk", "Transaksi Keluar"]
choice = st.sidebar.radio("Menu", menu)

try:
    if choice == "Data Barang":
        st.header("Data Barang")
        df = get_items()
        st.dataframe(df, use_container_width=True)
        
        with st.expander("Tambah Barang"):
            with st.form("tambah_barang"):
                nama = st.text_input("Nama Barang*")
                jumlah = st.number_input("Jumlah Stok*", min_value=0)
                satuan = st.selectbox("Satuan*", ["pcs", "box", "rim", "lusin"])
                
                if st.form_submit_button("Simpan"):
                    if nama and jumlah >= 0 and satuan:
                        try:
                            conn = get_connection()
                            conn.cursor().execute(
                                "INSERT INTO inventaris (nama_barang, jumlah_stok, satuan) VALUES (?, ?, ?)",
                                (nama, jumlah, satuan)
                            )
                            conn.commit()
                            st.success("Barang berhasil ditambahkan")
                        except sqlite3.IntegrityError:
                            st.error("Nama barang sudah ada!")
                    else:
                        st.warning("Lengkapi field wajib")

    elif choice == "Transaksi Masuk":
        st.header("Transaksi Barang Masuk")
        df = get_transaksi_masuk()
        st.dataframe(df, use_container_width=True)
        
        with st.form("transaksi_masuk"):
            item = st.selectbox("Barang", get_items()['nama_barang'].tolist())
            jumlah = st.number_input("Jumlah*", min_value=1)
            keterangan = st.text_area("Keterangan")
            
            if st.form_submit_button("Tambah Transaksi"):
                try:
                    item_id = get_items()[get_items()['nama_barang'] == item].iloc[0]['id']
                    conn = get_connection()
                    conn.cursor().execute(
                        "INSERT INTO transaksi_masuk (item_id, jumlah, keterangan) VALUES (?, ?, ?)",
                        (item_id, jumlah, keterangan)
                    )
                    conn.cursor().execute(
                        "UPDATE inventaris SET jumlah_stok = jumlah_stok + ? WHERE id = ?",
                        (jumlah, item_id)
                    )
                    conn.commit()
                    st.success("Transaksi berhasil!")
                except Exception as e:
                    st.error("Gagal menambah transaksi")
                    logging.error(f"Transaksi Masuk Error: {e}")

    elif choice == "Transaksi Keluar":
        st.header("Transaksi Barang Keluar")
        df = get_transaksi_keluar()
        st.dataframe(df, use_container_width=True)
        
        with st.form("transaksi_keluar"):
            item_list = get_items()
            if item_list.empty:
                st.warning("Tidak ada barang tersedia")
            else:
                item = st.selectbox("Barang", item_list['nama_barang'].tolist())
                jumlah = st.number_input("Jumlah*", min_value=1)
                keterangan = st.text_area("Keterangan")
                
                if st.form_submit_button("Proses Transaksi"):
                    try:
                        item_data = item_list[item_list['nama_barang'] == item].iloc[0]
                        if item_data['jumlah_stok'] >= jumlah:
                            item_id = item_data['id']
                            conn = get_connection()
                            conn.cursor().execute(
                                "INSERT INTO transaksi_keluar (item_id, jumlah, keterangan) VALUES (?, ?, ?)",
                                (item_id, jumlah, keterangan)
                            )
                            conn.commit()
                            st.success("Transaksi berhasil!")
                        else:
                            st.error("Stok tidak mencukupi!")
                    except Exception as e:
                        st.error("Gagal memproses transaksi")
                        logging.error(f"Transaksi Keluar Error: {e}")

    # Sidebar Stok Darurat
    st.sidebar.header("Stok Barang")
    df = get_items()
    if not df.empty:
        st.sidebar.dataframe(df[['nama_barang', 'jumlah_stok']], use_container_width=True)
    else:
        st.sidebar.warning("Tidak ada data barang")

except Exception as e:
    st.error("Terjadi kesalahan sistem")
    logging.critical(f"Critical Error: {e}")
