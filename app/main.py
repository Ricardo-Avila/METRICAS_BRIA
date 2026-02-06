import subprocess
import sys
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def ejecutar_script(script):
    ruta = os.path.join(BASE_DIR, script)

    if not os.path.exists(ruta):
        print(f"ERROR: No existe el archivo: {script}")
        sys.exit(1)

    print(f"Ejecutando {script} ...")
    resultado = subprocess.run(
        [sys.executable, ruta],
        cwd=BASE_DIR
    )

    if resultado.returncode != 0:
        print(f"ERROR: Error al ejecutar {script}")
        sys.exit(1)

    print(f"OK: {script} finalizado correctamente\n")

def main():
    print("INICIANDO PIPELINE METRICAS_BRIA\n")

    # 1 Login + descarga CSV (selenium)
    ejecutar_script("issabel_login.py")

    #2 Procesar CSV
    ejecutar_script("procesar.py")

    # 3 Subir a Postgres
    ejecutar_script("csv_a_postgres.py")

    # Aqui luego agregas:
    # ejecutar_script("enviar_correo.py")
    # ejecutar_script("limpieza.py")

    print("PROCESO COMPLETO FINALIZADO CON EXITO")

if __name__ == "__main__":
    main()


