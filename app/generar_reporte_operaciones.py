import os
from datetime import datetime
from html import escape
import psycopg

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": int(os.getenv("DB_PORT", 5432)),
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASS"),
}

SQL_REPORTE = """
SELECT
    u.extension,
    u.nombre,
    u.departamento,
    COUNT(DISTINCT l.uuid) AS llamadas_salida,
    COUNT(DISTINCT li.uuid) AS llamadas_entrada
FROM usuario u
LEFT JOIN llamada l ON u.extension = l.srcextension
    AND l.attended = true
    AND l.direction = 'outgoing'
    AND l.calldate >= %s
    AND l.calldate < %s
LEFT JOIN ruta_path r ON u.extension = r.extension
LEFT JOIN llamada li ON r.id_llamada = li.uuid
    AND li.direction = 'incoming'
    AND li.attended = true
    AND li.calldate >= %s
    AND li.calldate < %s
WHERE u.departamento = 'Operaciones'
GROUP BY u.extension, u.nombre, u.departamento
ORDER BY llamadas_entrada DESC;
"""

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>Ranking de Extensiones - Datos Actualizados</title>

<style>
  body {{
    font-family: Arial, sans-serif;
    background: #f1f5f9;
    padding: 20px;
  }}
  table {{
    width: 900px;
    margin: auto;
    border-collapse: collapse;
    background: white;
    border-radius: 10px;
    overflow: hidden;
    box-shadow: 0 0 10px #0003;
  }}
  th {{
    background: #0d6efd;
    color: white;
    padding: 10px;
  }}
  td {{
    padding: 10px;
    border-bottom: 1px solid #ddd;
    text-align: center;
  }}
  .emoji-col {{
    width: 56px;
  }}
  tr:last-child td {{ border-bottom: none; }}
  .emoji {{
    font-size: 22px;
  }}
  .controls {{
    text-align: center;
    margin: 10px 0 16px;
  }}
  .btn {{
    border: none;
    background: #198754;
    color: white;
    padding: 8px 14px;
    border-radius: 8px;
    cursor: pointer;
    font-weight: 600;
    margin: 0 6px;
  }}
  .btn--alt {{
    background: #fd7e14;
  }}
</style>

</head>
<body>

<h2 style="text-align:center;">🏆 Ranking de Llamadas - {mes_nombre} {anio}</h2>

<div class="controls">
  <button class="btn" id="sortEntrantes">Ordenar por Entrantes</button>
  <button class="btn btn--alt" id="sortSalientes">Ordenar por Salientes</button>
</div>

<table>
  
  <tr>
    <th>Lugar</th>
    <th>Extensión</th>
    <th class="emoji-col"></th>
    <th>Nombre</th>
    <th>Área</th>
    <th>Entrantes</th>
    <th>Salientes</th>
  </tr>

{filas}

</table>

<script>
  (function () {{
    const rows = Array.from(document.querySelectorAll("tr[data-row='1']"))
      .map((tr) => ({{
        tr,
        extension: tr.dataset.extension || "",
        nombre: tr.dataset.nombre || "",
        departamento: tr.dataset.departamento || "",
        entrantes: Number(tr.dataset.llamadas_entrada || 0),
        salientes: Number(tr.dataset.llamadas_salida || 0)
      }}));

    function emojiFor(rank) {{
      if (rank === 1) return "🥇";
      if (rank === 2) return "🥈";
      if (rank === 3) return "🥉";
      if (rank <= 10) return "✨";
      return "";
    }}

    function render(sorted) {{
      const tbody = document.querySelector("table");
      const staticHeader = tbody.querySelectorAll("tr")[0];
      tbody.innerHTML = "";
      tbody.appendChild(staticHeader);

      if (!sorted.length) {{
        const tr = document.createElement("tr");
        tr.innerHTML = '<td colspan="7">Sin datos para el mes actual.</td>';
        tbody.appendChild(tr);
        return;
      }}

      sorted.forEach((row, index) => {{
        const place = index + 1;
        const emoji = emojiFor(place);
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td>${{place}}</td>
          <td>${{row.extension}}</td>
          <td class="emoji">${{emoji}}</td>
          <td>${{row.nombre}}</td>
          <td>${{row.departamento}}</td>
          <td>${{row.entrantes}}</td>
          <td>${{row.salientes}}</td>
        `;
        tbody.appendChild(tr);
      }});
    }}

    function sortBy(key) {{
      const sorted = [...rows].sort((a, b) => (b[key] ?? 0) - (a[key] ?? 0));
      render(sorted);
    }}

    document.getElementById("sortEntrantes").addEventListener("click", () => sortBy("entrantes"));
    document.getElementById("sortSalientes").addEventListener("click", () => sortBy("salientes"));

    sortBy("entrantes");
  }})();
</script>

</body>
</html>
"""

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


def fetch_data(start_date, end_date):
    if not all([DB_CONFIG["host"], DB_CONFIG["dbname"], DB_CONFIG["user"], DB_CONFIG["password"]]):
        raise RuntimeError("Faltan variables de entorno para BD (DB_HOST, DB_NAME, DB_USER, DB_PASS)")

    with psycopg.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:
            cur.execute(SQL_REPORTE, (start_date, end_date, start_date, end_date))
            rows = cur.fetchall()

    data = []
    for r in rows:
        data.append({
            "extension": r[0],
            "nombre": r[1],
            "departamento": r[2],
            "llamadas_salida": r[3],
            "llamadas_entrada": r[4],
        })
    return data


def build_rows(data):
    if not data:
        return '<tr><td colspan="7">Sin datos para el mes actual.</td></tr>'

    out = []
    for r in data:
        extension = "" if r["extension"] is None else str(r["extension"])
        nombre = "" if r["nombre"] is None else str(r["nombre"])
        departamento = "" if r["departamento"] is None else str(r["departamento"])
        llamadas_salida = 0 if r["llamadas_salida"] is None else r["llamadas_salida"]
        llamadas_entrada = 0 if r["llamadas_entrada"] is None else r["llamadas_entrada"]
        out.append(
            "<tr data-row=\"1\" "
            f"data-extension=\"{escape(extension, quote=True)}\" "
            f"data-nombre=\"{escape(nombre, quote=True)}\" "
            f"data-departamento=\"{escape(departamento, quote=True)}\" "
            f"data-llamadas_salida=\"{llamadas_salida}\" "
            f"data-llamadas_entrada=\"{llamadas_entrada}\">"
            "</tr>"
        )
    return "\n".join(out)


def main():
    now = datetime.now()
    month = now.month
    mes_nombre = MESES.get(month, str(month))
    fecha_generacion = now.strftime("%Y-%m-%d %H:%M:%S")
    start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if month == 12:
        end_date = start_date.replace(year=start_date.year + 1, month=1)
    else:
        end_date = start_date.replace(month=month + 1)

    data = fetch_data(start_date, end_date)
    filas = build_rows(data)

    report_filename = f"Reporte_Operaciones_{now.year}_{month:02d}.html"
    report_path = os.path.abspath(os.path.join(BASE_DIR, "..", "reports", report_filename))

    html = HTML_TEMPLATE.format(
        mes_nombre=mes_nombre,
        anio=now.year,
        titulo_metrica="ENTRANTES",
        fecha_generacion=fecha_generacion,
        filas=filas,
    )

    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Reporte generado: {report_path}")


if __name__ == "__main__":
    main()
