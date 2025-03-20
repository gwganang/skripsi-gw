import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# === DATABASE CONFIG ===
@st.cache_resource
def get_connection():
    return sqlite3.connect('database/inventaris.db', check_same_thread=False)

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
        BEGIN
            UPDATE inventaris
            SET jumlah_stok = jumlah_stok - NEW.jumlah
            WHERE id = NEW.item_id
            AND jumlah_stok >= NEW.jumlah;
        END;
    ''')
    
    conn.commit()

init_db()

# === FUNGSI CRUD ===
def get_items():
    conn = get_connection()
    return pd.read_sql("SELECT * FROM inventaris", conn)

def get_transaksi_masuk():
    conn = get_connection()
    return pd.read_sql("""
        SELECT tm.*, i.nama_barang 
        FROM transaksi_masuk tm 
        JOIN inventaris i ON tm.item_id = i.id
    """, conn)

def get_transaksi_keluar():
    conn = get_connection()
    return pd.read_sql("""
        SELECT tk.*, i.nama_barang 
        FROM transaksi_keluar tk 
        JOIN inventaris i ON tk.item_id = i.id
    """, conn)

# === STREAMLIT UI ===
st.set_page_config(page_title="Sistem Inventaris", layout="wide")
menu = ["Data Barang", "Transaksi Masuk", "Transaksi Keluar"]
choice = st.sidebar.radio("Menu", menu)

if choice == "Data Barang":
    st.header("Data Barang")
    df = get_items()
    st.dataframe(df)
    
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
    st.dataframe(df)
    
    with st.form("transaksi_masuk"):
        item = st.selectbox("Barang", get_items()['nama_barang'].tolist())
        jumlah = st.number_input("Jumlah*", min_value=1)
        keterangan = st.text_area("Keterangan")
        
        if st.form_submit_button("Tambah Transaksi"):
            item_id = get_items()[get_items()['nama_barang'] == item].iloc[0]['id']
            conn = get_connection()
            conn.cursor().execute(
                "INSERT INTO transaksi_masuk (item_id, jumlah, keterangan) VALUES (?, ?, ?)",
                (item_id, jumlah, keterangan)
            )
            conn.commit()
            # Update stok
            conn.cursor().execute(
                "UPDATE inventaris SET jumlah_stok = jumlah_stok + ? WHERE id = ?",
                (jumlah, item_id)
            )
            conn.commit()
            st.success("Transaksi berhasil!")

elif choice == "Transaksi Keluar":
    st.header("Transaksi Barang Keluar")
    df = get_transaksi_keluar()
    st.dataframe(df)
    
    with st.form("transaksi_keluar"):
        item = st.selectbox("Barang", get_items()['nama_barang'].tolist())
        jumlah = st.number_input("Jumlah*", min_value=1)
        keterangan = st.text_area("Keterangan")
        
        if st.form_submit_button("Proses Transaksi"):
            item_data = get_items()[get_items()['nama_barang'] == item].iloc[0]
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

# === STOK VALIDATION ===
st.sidebar.header("Stok Darurat")
df = get_items()
if not df.empty:
    st.sidebar.dataframe(df[['nama_barang', 'jumlah_stok']])
else:
    st.sidebar.warning("Tidak ada data barang")