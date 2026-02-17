import os
import smtplib
from datetime import datetime
from email.message import EmailMessage
import re
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

def parse_addresses(raw):
    if not raw:
        return []
    parts = re.split(r"[;,]", raw)
    return [p.strip() for p in parts if p and p.strip()]


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
    mail_to = os.getenv("MAIL_TO")
    mail_to_cc = os.getenv("MAIL_YO_CC") or os.getenv("MAIL_TO_CC")
    mail_to_error = os.getenv("MAIL_TO_ERROR")
    log_path = os.getenv("METRICAS_LOG_PATH", "/var/log/metricas.log")

    if not all([smtp_host, smtp_user, smtp_pass, mail_from]):
        raise RuntimeError("Faltan variables de entorno SMTP (SMTP_HOST, SMTP_USER, SMTP_PASS, MAIL_FROM opcional)")

    now = datetime.now()
    subject = build_subject(now)

    report_filename = f"Reporte_Operaciones_{now.year}_{now.month:02d}.html"
    report_path = os.path.abspath(os.path.join(BASE_DIR, "..", "reports", report_filename))
    report_exists = os.path.exists(report_path)
    attach_error_log = False
    error_detail = ""

    msg = EmailMessage()
    msg["From"] = mail_from
    if report_exists:
        msg["To"] = ", ".join(parse_addresses(mail_to)) or mail_to
        cc_list = parse_addresses(mail_to_cc)
        if cc_list:
            msg["Cc"] = ", ".join(cc_list)
        msg["Subject"] = subject
        msg.set_content("Ricardo Avila Laguna | B2B Negocios | Correo Automatizado")
        try:
            with open(report_path, "rb") as f:
                msg.add_attachment(
                    f.read(),
                    maintype="text",
                    subtype="html",
                    filename=report_filename,
                )
        except Exception as exc:
            report_exists = False
            attach_error_log = True
            error_detail = f"No se pudo adjuntar el reporte: {exc}"

    if not report_exists:
        msg["To"] = ", ".join(parse_addresses(mail_to_error)) or mail_to_error
        msg["Subject"] = f"Fallo reporte Operaciones {now.month:02d}-{now.year}"
        msg.set_content(
            "No se encontro el reporte mensual de Operaciones.\n"
            f"Se esperaba el archivo: {report_path}\n"
            + (f"{error_detail}\n" if error_detail else "")
            + "Ricardo Avila Laguna | B2B Negocios | Correo Automatizado"
        )
        attach_error_log = True
        if attach_error_log and os.path.exists(log_path):
            with open(log_path, "rb") as f:
                msg.add_attachment(
                    f.read(),
                    maintype="text",
                    subtype="plain",
                    filename=os.path.basename(log_path),
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
