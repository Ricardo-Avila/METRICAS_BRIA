import csv
import re
import os
import shutil
from datetime import datetime, timedelta
import glob
import psycopg


def limpiar_columnas(fieldnames):
    if not fieldnames:
        return []
    columnas_a_eliminar = {
        "RecordFile",
        "SrcCompany",
        "SrcType",
        "SrcName",
        "DstCompany",
        "DstType",
        "DstName",
        "ExternalId",
        "SurveyResult",
        "UserData",
        "TranscriptionPath",
        "Summary",
        "Comment"
    }

    # 1) Eliminar columnas indeseadas
    columnas = [c for c in fieldnames if c not in columnas_a_eliminar]

    # 2) Mover Uuid al inicio si existe
    if "Uuid" in columnas:
        columnas.remove("Uuid")
        columnas.insert(0, "Uuid")

    # 3) (Opcional) Asegurar Calldate como segunda columna
    if "Calldate" in columnas and columnas.index("Calldate") != 1:
        columnas.remove("Calldate")
        columnas.insert(1, "Calldate")

    return columnas


DEBUG_PATH = os.getenv("DEBUG_PATH", "false").lower() in ("1", "true", "yes")
CSV_TIME_OFFSET_HOURS = int(os.getenv("CSV_TIME_OFFSET_HOURS", "6"))
FILTRO_BD_ACTIVO = os.getenv("FILTRO_BD_ACTIVO", "true").lower() in ("1", "true", "yes")


def _noop(*_args, **_kwargs):
    return None


def _procesar_path(path, log):

    log("\n===========================")
    log("INPUT ORIGINAL:", repr(path))
    log("===========================")

    # Convertir a string
    if path is None:
        log("-> Path es None, regreso vacio")
        return ""

    path = str(path)
    log("Como string:", repr(path))

    path = path.strip()
    log("Despues de strip:", repr(path))

    # Detectar vacio real
    if path == "":
        log("-> Path vacio, regreso ''")
        return ""

    if path == '""':
        log("-> Path == '\"\"', regreso ''")
        return ""

    # Paso 1: reemplazar delimitadores
    path = re.sub(r'\||->', ',', path)
    log("Reemplazo | y -> por ,:", repr(path))

    # Paso 2: quitar coma inicial
    if path.startswith(','):
        path = path[1:]
        log("Quite coma inicial:", repr(path))
    else:
        log("No inicia con coma")

    # Paso 3: separar tokens
    tokens = path.split(',')
    log("Tokens split:", tokens)

    # Paso 4: filtrar tokens validos
    tokens = [t for t in tokens if re.fullmatch(r'\d{3}|\d{4}|\d{7}', t)]
    log("Tokens validos 3/4/7 digitos:", tokens)

    if not tokens:
        log("-> No hay tokens validos, regreso ''")
        return ""

    # Paso 5: procesar numeros de 7 digitos
    new_tokens = []
    for t in tokens:
        if len(t) == 7:
            if t.startswith('4'):
                new_tokens.append(t)
                log(f"7 digitos inicia en 4: {t}")
            else:
                log(f"7 digitos procesado: {t} -> {t[:3]}, {t[3:]}")
                new_tokens.append(t[:3])
                new_tokens.append(t[3:])
        else:
            new_tokens.append(t)
            log("Token mantenido:", t)
    tokens = new_tokens
    log("Tokens despues de procesar 7 digitos:", tokens)

    # Paso 6: eliminar pares consecutivos duplicados
    cleaned = []
    i = 0
    while i < len(tokens):
        if i + 1 < len(tokens):
            pair_current = (tokens[i], tokens[i + 1])
            if cleaned and len(cleaned) >= 2:
                lastA, lastB = cleaned[-2], cleaned[-1]
                if (lastA, lastB) == pair_current:
                    log(f"Par duplicado consecutivo eliminado: {pair_current}")
                    i += 2
                    continue
        cleaned.append(tokens[i])
        log("Agregado:", tokens[i])
        i += 1

    tokens = cleaned
    log("Tokens tras eliminar pares repetidos:", tokens)

    # Paso 7: eliminar duplicados individuales consecutivos
    final = []
    for t in tokens:
        if final and final[-1] == t:
            log(f"Duplicado individual eliminado: {t}")
            continue
        final.append(t)

    log("FINAL:", final)
    log("===========================\n")

    return "->".join(final)


def procesar_path(path):
    return _procesar_path(path, print if DEBUG_PATH else _noop)


# -----------------------------------------------------
# PROCESAR ARCHIVO CSV COMPLETO (DOCKER / LINUX)
# -----------------------------------------------------

BASE_DATA = "/data"
INCOMING_DIR = os.path.join(BASE_DATA, "incoming")
ORIGINAL_DIR = os.path.join(BASE_DATA, "original")
PROCESADOS_DIR = os.path.join(BASE_DATA, "procesados")

# -----------------------------------------------------
# FILTRO POR ULTIMO REGISTRO EN BD
# -----------------------------------------------------

DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": int(os.getenv("DB_PORT", 5432)),
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASS"),
}


def obtener_ultimo_calldate():
    if not all([DB_CONFIG["host"], DB_CONFIG["dbname"], DB_CONFIG["user"], DB_CONFIG["password"]]):
        raise RuntimeError("Faltan variables de entorno para BD (DB_HOST, DB_NAME, DB_USER, DB_PASS)")

    with psycopg.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT MAX(calldate) FROM llamada;")
            row = cur.fetchone()
            return row[0] if row and row[0] else None


# Crear directorios si no existen
os.makedirs(INCOMING_DIR, exist_ok=True)
os.makedirs(ORIGINAL_DIR, exist_ok=True)
os.makedirs(PROCESADOS_DIR, exist_ok=True)

# Buscar archivos csv con el patron esperado
archivos = glob.glob(os.path.join(INCOMING_DIR, "csv-*.csv"))

if not archivos:
    raise FileNotFoundError("No se encontro ningun archivo csv en /data/incoming")

# Tomar el archivo mas reciente por fecha de modificacion
archivo_origen = max(archivos, key=os.path.getmtime)

# Extraer el nombre base
nombre_archivo = os.path.basename(archivo_origen)

# Extraer la fecha y hora del nombre
# Formato esperado: csv-dd-mm-aaaa_hh-mm-ss.csv
try:
    fecha_str = nombre_archivo.replace("csv-", "").replace(".csv", "")
    fecha_dt = datetime.strptime(fecha_str, "%d-%m-%Y_%H-%M-%S")
except:
    raise ValueError(f"El nombre del archivo no coincide con el formato esperado: {nombre_archivo}")

# Ajustar la hora con offset configurable (por defecto 6 horas)
fecha_corregida = fecha_dt - timedelta(hours=CSV_TIME_OFFSET_HOURS)
fecha_corregida_str = fecha_corregida.strftime("%d-%m-%Y_%H-%M-%S")

# Nombre final corregido
nombre_corregido = f"csv-{fecha_corregida_str}.csv"

# Rutas finales
ruta_original = os.path.join(ORIGINAL_DIR, nombre_corregido)
ruta_procesado = os.path.join(
    PROCESADOS_DIR,
    nombre_corregido.replace(".csv", "_procesado.csv")
)

# Mover archivo a /original
shutil.move(archivo_origen, ruta_original)

# -----------------------------------------------------
# PROCESAMIENTO DEL CSV
# -----------------------------------------------------

ultimo_calldate = None
if FILTRO_BD_ACTIVO:
    ultimo_calldate = obtener_ultimo_calldate()
    if ultimo_calldate:
        print(f"Filtro BD activo. Se omitiran registros con Calldate <= {ultimo_calldate}.")
    else:
        print("Filtro BD activo, pero la tabla llamada esta vacia. No se omitiran registros.")
else:
    print("Filtro BD desactivado. Se procesaran todos los registros del CSV.")

skipped = 0
written = 0
invalid_calldate = 0

with open(ruta_original, newline='', encoding="utf-8") as f_in, \
     open(ruta_procesado, "w", newline='', encoding="utf-8") as f_out:

    reader = csv.DictReader(f_in, delimiter=';')
    print("Columnas detectadas:", reader.fieldnames)

    # Limpiar columnas
    fieldnames_limpias = limpiar_columnas(reader.fieldnames)
    if not fieldnames_limpias:
        raise ValueError("El CSV no tiene columnas validas para procesar")

    writer = csv.DictWriter(
        f_out,
        fieldnames=fieldnames_limpias,
        delimiter=';'
    )

    writer.writeheader()

    for row in reader:
        if ultimo_calldate:
            calldate_str = (row.get("Calldate") or "").strip()
            if not calldate_str:
                invalid_calldate += 1
                continue
            try:
                row_calldate = datetime.strptime(calldate_str, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                invalid_calldate += 1
                continue
            if row_calldate <= ultimo_calldate:
                skipped += 1
                continue

        row_limpio = {k: row.get(k, "") for k in fieldnames_limpias}

        path_value = row_limpio.get("Path", "")
        if path_value and path_value not in ("", '""', " "):
            row_limpio["Path"] = procesar_path(path_value)
        else:
            dst_ext = row_limpio.get("DstExtension")
            if dst_ext and dst_ext not in ("", " "):
                row_limpio["Path"] = dst_ext

        writer.writerow(row_limpio)
        written += 1

print("CSV procesado correctamente")
print("Original :", ruta_original)
print("Procesado:", ruta_procesado)
print(f"Registros omitidos: {skipped}")
print(f"Registros con Calldate invalido: {invalid_calldate}")
print(f"Registros escritos: {written}")
