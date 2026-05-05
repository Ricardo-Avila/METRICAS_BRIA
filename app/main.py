import subprocess
import sys
import os
from datetime import datetime
import calendar

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
    #ejecutar_script("issabel_login.py")

    #2 Procesar CSV
    #ejecutar_script("procesar.py")

    # 3 Subir a Postgres
    #ejecutar_script("csv_a_postgres.py")

    # 4 Generar Reporte (solo el ultimo dia del mes)
    #ejecutar_script("generar_reporte_operaciones.py")
    #today = datetime.now().date()
    #last_day = calendar.monthrange(today.year, today.month)[1]
    #if today.day == last_day:
    #    ejecutar_script("generar_reporte_operaciones.py")
    #else:
    #    print("INFO: generar_reporte_operaciones.py se omite (no es el ultimo dia del mes).")

    # 5 Enviar correo (solo el ultimo dia del mes)
    #ejecutar_script("enviar_correo.py")
    #if today.day == last_day:
    #    ejecutar_script("enviar_correo.py")
    #else:
    #    print("INFO: enviar_correo.py se omite (no es el ultimo dia del mes).")

    #ejecutar_script("limpieza.py")

    print("PROCESO COMPLETO FINALIZADO CON EXITO")

if __name__ == "__main__":
    main()


