"""Quick DB connection check — jalankan sebelum smoke test."""
import duckdb

con = duckdb.connect()
try:
    con.execute("INSTALL postgres; LOAD postgres;")
    con.execute(
        "ATTACH 'postgresql://readonly_user:read_only_seeknal@localhost:5533/rpo_v2'"
        " AS warehouse (TYPE POSTGRES, READ_ONLY)"
    )
    r = con.execute(
        "SELECT COUNT(DISTINCT nomor) AS jumlah_nie "
        "FROM warehouse.public.t_produk_3_erba "
        "WHERE tanggal >= '2023-01-01' AND tanggal < '2024-01-01' "
        "AND status IN ('0999','0906','9999') "
        "AND jenis_permohonan IN ('301','305') "
        "AND trader_id NOT IN (5,17,50,85)"
    ).fetchone()
    print(f"DB OK — NIE ERBA 2023: {r[0]:,}")
except Exception as e:
    print(f"DB ERROR: {e}")
finally:
    con.close()
