import streamlit as st
import sqlite3
from datetime import datetime

# Konfigurasi Database
@st.cache_resource
def get_connection():
    conn = sqlite3.connect('database/inventaris.db', check_same_thread=False)
    return conn

def init_db():
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS inventaris (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nama_barang TEXT NOT NULL,
            jumlah_stok INTEGER NOT NULL CHECK (jumlah_stok >= 0),
            satuan TEXT NOT NULL,
            keterangan TEXT
        )
    ''')
    conn.commit()

init_db()

# Fungsi CRUD
def create_data(nama, jumlah, satuan, keterangan):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO inventaris (nama_barang, jumlah_stok, satuan, keterangan)
        VALUES (?, ?, ?, ?)
    ''', (nama, jumlah, satuan, keterangan))
    conn.commit()

def read_data():
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM inventaris", conn)
    return df

def update_data(id, nama, jumlah, satuan, keterangan):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        UPDATE inventaris
        SET nama_barang = ?, jumlah_stok = ?, satuan = ?, keterangan = ?
        WHERE id = ?
    ''', (nama, jumlah, satuan, keterangan, id))
    conn.commit()

def delete_data(id):
    conn = get_connection()
    c = conn.cursor()
    c.execute('DELETE FROM inventaris WHERE id = ?', (id,))
    conn.commit()

# Konfigurasi UI
st.set_page_config(page_title="Inventaris ATK", layout="wide")
st.title("Sistem Manajemen Inventaris ATK")

menu = ["Lihat Data", "Tambah Data", "Edit Data", "Hapus Data"]
choice = st.sidebar.selectbox("Menu", menu)

if choice == "Lihat Data":
    st.header("Daftar Inventaris")
    df = read_data()
    st.dataframe(df, use_container_width=True)

elif choice == "Tambah Data":
    st.header("Tambah Barang Baru")
    with st.form("form_tambah", clear_on_submit=True):
        nama = st.text_input("Nama Barang*", key="nama")
        jumlah = st.number_input("Jumlah Stok*", min_value=0, key="jumlah")
        satuan = st.selectbox("Satuan*", ["pcs", "box", "rim", "lusin"], key="satuan")
        keterangan = st.text_area("Keterangan Tambahan", key="keterangan")
        
        submitted = st.form_submit_button("Simpan")
        if submitted:
            if nama and jumlah >= 0 and satuan:
                try:
                    create_data(nama, jumlah, satuan, keterangan)
                    st.success("Data berhasil disimpan!")
                except Exception as e:
                    st.error(f"Gagal menyimpan data: {str(e)}")
            else:
                st.warning("Mohon lengkapi field wajib (*)")

elif choice == "Edit Data":
    st.header("Edit Barang")
    df = read_data()
    if df.empty:
        st.info("Tidak ada data untuk diedit")
    else:
        edit_id = st.selectbox("Pilih ID Barang", df['id'].tolist())
        selected_row = df[df['id'] == edit_id].iloc[0]
        
        with st.form(f"form_edit_{edit_id}"):
            nama = st.text_input("Nama Barang*", value=selected_row['nama_barang'])
            jumlah = st.number_input("Jumlah Stok*", 
                                    value=selected_row['jumlah_stok'], 
                                    min_value=0)
            satuan = st.selectbox("Satuan*", 
                                ["pcs", "box", "rim", "lusin"], 
                                index=["pcs", "box", "rim", "lusin"].index(selected_row['satuan']))
            keterangan = st.text_area("Keterangan Tambahan", 
                                    value=selected_row['keterangan'])
            
            submitted = st.form_submit_button("Update")
            if submitted:
                if nama and jumlah >= 0 and satuan:
                    try:
                        update_data(edit_id, nama, jumlah, satuan, keterangan)
                        st.success("Data berhasil diperbarui!")
                    except Exception as e:
                        st.error(f"Gagal memperbarui data: {str(e)}")
                else:
                    st.warning("Mohon lengkapi field wajib (*)")

elif choice == "Hapus Data":
    st.header("Hapus Barang")
    df = read_data()
    if df.empty:
        st.info("Tidak ada data untuk dihapus")
    else:
        delete_id = st.selectbox("Pilih ID Barang yang akan dihapus", df['id'].tolist())
        selected_row = df[df['id'] == delete_id].iloc[0]
        
        st.warning(f"Yakin ingin menghapus: {selected_row['nama_barang']}?")
        if st.button("Hapus Permanen"):
            try:
                delete_data(delete_id)
                st.success("Data berhasil dihapus!")
            except Exception as e:
                st.error(f"Gagal menghapus data: {str(e)}")