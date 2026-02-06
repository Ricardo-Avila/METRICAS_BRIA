import csv
import os
import psycopg
from datetime import datetime

# --------------------------------------------------
# CONFIGURACION
# --------------------------------------------------

CSV_DIR = "/data/procesados"

DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": int(os.getenv("DB_PORT", 5432)),
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASS"),
}

# --------------------------------------------------
# UTILIDADES
# --------------------------------------------------

def normalizar_entero(valor):
    if valor is None:
        return None
    valor = str(valor).strip()
    return int(valor) if valor.isdigit() else None


def normalizar_boolean(valor):
    if valor is None:
        return False
    valor = str(valor).strip()
    if valor in ("", " ", "0"):
        return False
    if valor in ("1", "true", "True"):
        return True
    return False


def normalizar_datetime(valor):
    if valor is None:
        return None
    valor = str(valor).strip()
    if not valor:
        return None
    try:
        return datetime.strptime(valor, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None


def obtener_csv_mas_reciente():
    if not os.path.isdir(CSV_DIR):
        raise RuntimeError(f"No existe el directorio de CSVs procesados: {CSV_DIR}")
    archivos = [
        os.path.join(CSV_DIR, f)
        for f in os.listdir(CSV_DIR)
        if f.lower().endswith(".csv")
    ]
    if not archivos:
        raise RuntimeError("No hay CSVs procesados")
    return max(archivos, key=os.path.getmtime)

# --------------------------------------------------
# INSERTS
# --------------------------------------------------

SQL_LLAMADA = """
INSERT INTO llamada (
    uuid, calldate, duration, ringing, attended,
    direction, callerid, destination,
    srcuser, srcextension, dstuser, dstextension,
    path, linkedid, astcallid
) VALUES (
    %s,%s,%s,%s,%s,
    %s,%s,%s,
    %s,%s,%s,%s,
    %s,%s,%s
)
ON CONFLICT (uuid) DO NOTHING;
"""

SQL_RUTA = """
INSERT INTO ruta_path (id_llamada, posicion, extension)
VALUES (%s, %s, %s)
ON CONFLICT (id_llamada, posicion) DO NOTHING;
"""

SQL_EXISTE_USUARIO = """
SELECT 1 FROM usuario WHERE extension = %s;
"""

# --------------------------------------------------
# MAIN
# --------------------------------------------------

def main():
    if not all([DB_CONFIG["host"], DB_CONFIG["dbname"], DB_CONFIG["user"], DB_CONFIG["password"]]):
        raise RuntimeError("Faltan variables de entorno para BD (DB_HOST, DB_NAME, DB_USER, DB_PASS)")

    csv_file = obtener_csv_mas_reciente()
    print(f"CSV detectado: {csv_file}")

    omitted_path_ext = 0
    invalid_rows = 0

    with psycopg.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:
            with open(csv_file, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f, delimiter=";")

                for row in reader:
                    uuid = (row.get("Uuid") or "").strip()
                    calldate = normalizar_datetime(row.get("Calldate"))
                    duration = normalizar_entero(row.get("Duration"))
                    ringing = normalizar_entero(row.get("Ringing"))

                    if not uuid or calldate is None or duration is None or ringing is None:
                        invalid_rows += 1
                        continue

                    src_ext = normalizar_entero(row.get("SrcExtension"))
                    dst_ext = normalizar_entero(row.get("DstExtension"))

                    # Omitir si alguna extension no existe en usuario
                    if src_ext is not None:
                        cur.execute(SQL_EXISTE_USUARIO, (src_ext,))
                        if cur.fetchone() is None:
                            continue
                    if dst_ext is not None:
                        cur.execute(SQL_EXISTE_USUARIO, (dst_ext,))
                        if cur.fetchone() is None:
                            continue

                    valores_llamada = (
                        uuid,
                        calldate,
                        duration,
                        ringing,
                        normalizar_boolean(row.get("Attended")),
                        row.get("Direction"),
                        row.get("Callerid") or None,
                        row.get("Destination") or None,
                        normalizar_entero(row.get("SrcUser")),
                        src_ext,
                        normalizar_entero(row.get("DstUser")),
                        dst_ext,
                        row.get("Path") or None,
                        row.get("Linkedid"),
                        row.get("Astcallid"),
                    )

                    cur.execute(SQL_LLAMADA, valores_llamada)

                    # -------- RUTA_PATH --------
                    path = (row.get("Path") or "").strip()
                    if path:
                        extensiones = path.split("->")
                        for pos, ext in enumerate(extensiones, start=1):
                            if ext.strip().isdigit():
                                ext_int = int(ext)
                                cur.execute(SQL_EXISTE_USUARIO, (ext_int,))
                                if cur.fetchone() is None:
                                    omitted_path_ext += 1
                                    continue
                                cur.execute(
                                    SQL_RUTA,
                                    (uuid, pos, ext_int)
                                )

        conn.commit()

    print(f"Extensiones omitidas en ruta_path: {omitted_path_ext}")
    print(f"Filas omitidas por datos invalidos: {invalid_rows}")
    print("Insercion finalizada correctamente")

if __name__ == "__main__":
    main()
