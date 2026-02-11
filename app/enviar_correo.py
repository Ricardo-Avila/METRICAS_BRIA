import os
import smtplib
from datetime import datetime
from email.message import EmailMessage
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

MESES = {
    1: "Enero",
    2: "Febrero",
    3: "Marzo",
    4: "Abril",
    5: "Mayo",
    6: "Junio",
    7: "Julio",
    8: "Agosto",
    9: "Septiembre",
    10: "Octubre",
    11: "Noviembre",
    12: "Diciembre",
}


def build_subject(now):
    mes_nombre = MESES.get(now.month, str(now.month))
    return f"Metricas Bria {mes_nombre} {now.year} Area Operaciones"


def main():
    load_dotenv()
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASS")
    smtp_ssl_env = os.getenv("SMTP_SSL")
    if smtp_ssl_env is None:
        smtp_ssl = smtp_port == 465
    else:
        smtp_ssl = smtp_ssl_env.strip().lower() in {"1", "true", "yes", "y"}
    smtp_tls = os.getenv("SMTP_TLS", "true").strip().lower() in {"1", "true", "yes", "y"}
    mail_from = os.getenv("MAIL_FROM", smtp_user)
    mail_to = os.getenv("MAIL_TO", "ravila@b2bservicios.com")
    mail_to_cc = os.getenv("MAIL_TO_CC")
    mail_to_error = os.getenv("MAIL_TO_ERROR", "error@b2bservicios.com")

    if not all([smtp_host, smtp_user, smtp_pass, mail_from]):
        raise RuntimeError("Faltan variables de entorno SMTP (SMTP_HOST, SMTP_USER, SMTP_PASS, MAIL_FROM opcional)")

    now = datetime.now()
    subject = build_subject(now)

    report_filename = f"Reporte_Operaciones_{now.year}_{now.month:02d}.html"
    report_path = os.path.abspath(os.path.join(BASE_DIR, "..", "reports", report_filename))
    report_exists = os.path.exists(report_path)

    msg = EmailMessage()
    msg["From"] = mail_from
    if report_exists:
        msg["To"] = mail_to
        if mail_to_cc:
            msg["Cc"] = mail_to_cc
        msg["Subject"] = subject
        msg.set_content("Ricardo Avila Laguna | B2B Negocios | Correo Automatizado")
        with open(report_path, "rb") as f:
            msg.add_attachment(
                f.read(),
                maintype="text",
                subtype="html",
                filename=report_filename,
            )
    else:
        msg["To"] = mail_to_error
        msg["Subject"] = f"Fallo reporte Operaciones {now.month:02d}-{now.year}"
        msg.set_content(
            "No se encontro el reporte mensual de Operaciones.\n"
            f"Se esperaba el archivo: {report_path}\n"
            "Ricardo Avila Laguna | B2B Negocios | Correo Automatizado"
        )

    if smtp_ssl:
        with smtplib.SMTP_SSL(smtp_host, smtp_port) as server:
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
    else:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            if smtp_tls:
                server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)

    if report_exists:
        print("Correo enviado correctamente.")
    else:
        print("Correo de error enviado correctamente.")


if __name__ == "__main__":
    main()
