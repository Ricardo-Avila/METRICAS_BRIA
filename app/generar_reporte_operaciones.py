import os
import json
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
WHERE u.departamento = %s
GROUP BY u.extension, u.nombre, u.departamento
ORDER BY llamadas_entrada DESC;
"""

SQL_MENSUAL = """
SELECT
    date_trunc('month', calldate) AS mes,
    COUNT(*) AS total_llamadas,
    COALESCE(SUM(duration), 0) AS total_segundos
FROM llamada
WHERE attended = true
  AND direction IN ('incoming', 'outgoing')
  AND calldate >= %s
  AND calldate < %s
GROUP BY mes
ORDER BY mes;
"""

SQL_MENSUAL_RESUMEN = """
WITH base AS (
  SELECT
    date_trunc('month', l.calldate) AS mes,
    LOWER(COALESCE(l.attended::text, '')) AS attended,
    l.duration,
    l.direction,
    COALESCE(dm.pais, 'SIN PAIS') AS pais
  FROM llamada l
  LEFT JOIN LATERAL (
    SELECT d.pais
    FROM did d
    WHERE (
        l.direction = 'incoming'
        AND l.destination IS NOT NULL
        AND l.destination LIKE '%%' || d.did
      ) OR (
        l.direction = 'outgoing'
        AND l.callerid IS NOT NULL
        AND l.callerid LIKE '%%' || d.did
      )
    ORDER BY LENGTH(d.did) DESC
    LIMIT 1
  ) dm ON true
  WHERE LOWER(COALESCE(l.attended::text, '')) = 'true'
    AND l.direction IN ('incoming', 'outgoing', 'internal')
    AND l.calldate >= %s
    AND l.calldate < %s
)
SELECT
  mes,
  SUM(
    CASE
      WHEN LOWER(COALESCE(attended::text, '')) = 'true'
       AND direction IN ('incoming', 'outgoing')
      THEN 1 ELSE 0
    END
  ) AS total_llamadas,
  COALESCE(
    SUM(
      CASE
        WHEN LOWER(COALESCE(attended::text, '')) = 'true'
         AND direction IN ('incoming', 'outgoing')
        THEN duration ELSE 0
      END
    ),
    0
  ) AS total_segundos,
  SUM(
    CASE
      WHEN LOWER(COALESCE(attended::text, '')) = 'true'
       AND direction = 'incoming'
      THEN 1 ELSE 0
    END
  ) AS llamadas_entrantes,
  SUM(
    CASE
      WHEN LOWER(COALESCE(attended::text, '')) = 'true'
       AND direction = 'outgoing'
      THEN 1 ELSE 0
    END
  ) AS llamadas_salientes,
  COALESCE(
    SUM(
      CASE
        WHEN LOWER(COALESCE(attended::text, '')) = 'true'
         AND direction = 'incoming'
        THEN duration ELSE 0
      END
    ),
    0
  ) AS segundos_entrantes,
  COALESCE(
    SUM(
      CASE
        WHEN LOWER(COALESCE(attended::text, '')) = 'true'
         AND direction = 'outgoing'
        THEN duration ELSE 0
      END
    ),
    0
  ) AS segundos_salientes,
  SUM(
    CASE
      WHEN LOWER(COALESCE(attended::text, '')) = 'true'
       AND direction = 'internal'
      THEN 1 ELSE 0
    END
  ) AS llamadas_internas,
  COALESCE(
    SUM(
      CASE
        WHEN LOWER(COALESCE(attended::text, '')) = 'true'
         AND direction = 'internal'
        THEN duration ELSE 0
      END
    ),
    0
  ) AS segundos_internas
FROM base
GROUP BY mes
ORDER BY mes;
"""

SQL_MENSUAL_POR_PAIS = """
WITH base AS (
  SELECT
    date_trunc('month', l.calldate) AS mes,
    l.direction,
    COALESCE(l.duration, 0) AS duration,
    regexp_replace(
      COALESCE(
        CASE
          WHEN l.direction = 'incoming' THEN l.callerid
          WHEN l.direction = 'outgoing' THEN l.destination
          ELSE NULL
        END,
        ''
      ),
      '\\D',
      '',
      'g'
    ) AS number_raw
  FROM llamada l
  WHERE LOWER(COALESCE(l.attended::text, '')) = 'true'
    AND l.direction IN ('incoming', 'outgoing')
    AND l.calldate >= %s
    AND l.calldate < %s
),
normalized AS (
  SELECT
    mes,
    direction,
    duration,
    CASE
      WHEN number_raw LIKE '00%%' THEN SUBSTRING(number_raw FROM 3)
      ELSE number_raw
    END AS number_norm
  FROM base
),
classified AS (
  SELECT
    mes,
    direction,
    duration,
    CASE
      WHEN number_norm LIKE '52%%' THEN 'MEXICO'
      WHEN (
        LENGTH(number_norm) = 10
        AND (
          SUBSTRING(number_norm FROM 1 FOR 2) IN ('55', '56', '33', '81')
          OR SUBSTRING(number_norm FROM 1 FOR 3) IN (
            '220', '221', '222', '228', '229',
            '246', '311', '312',
            '440', '442', '443', '444', '446', '449',
            '473', '492',
            '618', '662', '667', '686',
            '720', '722', '729', '747', '771', '777',
            '834', '844',
            '951', '961', '983', '990', '999'
          )
        )
      ) THEN 'MEXICO'
      WHEN number_norm LIKE '506%%' THEN 'COSTA RICA'
      WHEN number_norm LIKE '57%%' THEN 'COLOMBIA'
      WHEN number_norm LIKE '504%%' THEN 'HONDURAS'
      WHEN number_norm LIKE '502%%' THEN 'GUATEMALA'
      WHEN number_norm LIKE '507%%' THEN 'PANAMA'
      WHEN number_norm LIKE '593%%' THEN 'ECUADOR'
      WHEN number_norm LIKE '505%%' THEN 'NICARAGUA'
      WHEN number_norm LIKE '503%%' THEN 'EL SALVADOR'
      ELSE 'OTROS'
    END AS pais
  FROM normalized
)
SELECT
  mes,
  pais,
  COALESCE(SUM(CASE WHEN direction = 'incoming' THEN duration ELSE 0 END), 0) AS segundos_entrada,
  COALESCE(SUM(CASE WHEN direction = 'outgoing' THEN duration ELSE 0 END), 0) AS segundos_salida,
  COALESCE(SUM(duration), 0) AS segundos_total
FROM classified
GROUP BY mes, pais
ORDER BY mes, pais;
"""

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>Ranking de Extensiones - Datos Actualizados</title>

<style>
  body {
    font-family: Arial, sans-serif;
    background: #f1f5f9;
    padding: 20px;
  }
  .tabs {
    width: 900px;
    margin: 0 auto 12px;
    display: flex;
    gap: 8px;
  }
  .tab-btn {
    border: none;
    background: #e2e8f0;
    color: #0f172a;
    padding: 8px 12px;
    border-radius: 8px;
    cursor: pointer;
    font-weight: 600;
  }
  .tab-btn.active {
    background: #0d6efd;
    color: white;
  }
  .panel {
    width: 900px;
    margin: 0 auto;
  }
  .hidden {
    display: none;
  }
  table {
    width: 900px;
    margin: auto;
    border-collapse: collapse;
    background: white;
    border-radius: 10px;
    overflow: hidden;
    box-shadow: 0 0 10px #0003;
  }
  th {
    background: #0d6efd;
    color: white;
    padding: 10px;
  }
  td {
    padding: 10px;
    border-bottom: 1px solid #ddd;
    text-align: center;
  }
  .emoji-col {
    width: 56px;
  }
  tr:last-child td { border-bottom: none; }
  .emoji {
    font-size: 22px;
  }
  .controls {
    text-align: center;
    margin: 10px 0 16px;
  }
  .btn {
    border: none;
    background: #198754;
    color: white;
    padding: 8px 14px;
    border-radius: 8px;
    cursor: pointer;
    font-weight: 600;
    margin: 0 6px;
  }
  .btn--alt {
    background: #fd7e14;
  }
  .chart-card {
    background: white;
    border-radius: 10px;
    padding: 16px 18px 14px;
    box-shadow: 0 0 10px #0003;
  }
  .chart-title {
    font-weight: 700;
    margin: 0 0 10px 0;
  }
  .chart-legend {
    display: flex;
    gap: 16px;
    align-items: center;
    font-size: 12px;
    color: #475569;
    margin-bottom: 8px;
  }
  .legend-dot {
    width: 10px;
    height: 10px;
    border-radius: 999px;
    display: inline-block;
    margin-right: 6px;
  }
  .legend-min {
    background: #0d6efd;
  }
  .legend-call {
    background: #f59e0b;
  }
  .chart-wrap {
    overflow-x: auto;
    position: relative;
  }
  .chart-tooltip {
    position: absolute;
    z-index: 30;
    pointer-events: none;
    background: #0f172a;
    color: #f8fafc;
    border: 1px solid #1e293b;
    border-radius: 10px;
    padding: 8px 10px;
    box-shadow: 0 10px 24px rgba(2, 6, 23, 0.35);
    transform: translate(-50%, -110%);
    opacity: 0;
    transition: opacity 0.16s ease;
    min-width: 170px;
  }
  .chart-tooltip.is-visible {
    opacity: 1;
  }
  .tooltip-title {
    font-size: 12px;
    font-weight: 700;
    margin-bottom: 6px;
  }
  .tooltip-row {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 12px;
    line-height: 1.4;
  }
  .tooltip-value {
    margin-left: auto;
    font-weight: 700;
  }
  .tooltip-dot {
    width: 9px;
    height: 9px;
    border-radius: 999px;
    display: inline-block;
  }
  .tooltip-dot-min {
    background: #0d6efd;
  }
  .tooltip-dot-call {
    background: #f59e0b;
  }
  .month-group .chart-bar {
    transition: transform 0.18s ease, opacity 0.18s ease, filter 0.18s ease;
    transform-box: fill-box;
    transform-origin: center bottom;
    cursor: pointer;
  }
  .month-group:hover .chart-bar {
    filter: brightness(1.08);
  }
  .month-group:hover .bar-min,
  .month-group:hover .bar-call {
    transform: translateY(-2px) scaleY(1.03);
  }
  .chart-footnote {
    font-size: 12px;
    color: #64748b;
    margin-top: 8px;
  }
  .monthly-table-card {
    margin-top: 16px;
    background: white;
    border-radius: 10px;
    padding: 16px 18px 12px;
    box-shadow: 0 0 10px #0003;
  }
  .monthly-controls {
    display: flex;
    justify-content: flex-end;
    gap: 8px;
    margin: 8px 0 12px;
  }
  .monthly-select {
    border: 1px solid #cbd5f5;
    border-radius: 8px;
    padding: 6px 10px;
    font-weight: 600;
    color: #0f172a;
    background: #f8fafc;
    cursor: pointer;
  }
  .monthly-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
    margin: 0;
    background: transparent;
    box-shadow: none;
    border-radius: 0;
  }
  .monthly-table th {
    background: #0f172a;
    color: #f8fafc;
    font-weight: 700;
    padding: 8px;
  }
  .monthly-table td {
    padding: 8px;
    border-bottom: 1px solid #e2e8f0;
    vertical-align: top;
    text-align: left;
  }
  .monthly-table tr:last-child td {
    border-bottom: none;
  }
  .col-mes {
    width: 12%;
  }
  .col-promedio {
    width: 13%;
    white-space: nowrap;
  }
  .col-llamadas {
    width: 16%;
  }
  .col-minutos {
    width: 16%;
  }
  .col-pais {
    width: 43%;
  }
  .monthly-metrics {
    display: grid;
    gap: 4px;
  }
  .monthly-metrics span {
    display: flex;
    justify-content: space-between;
    gap: 8px;
  }
  .resolution-wrap {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
  }
  .resolution-value {
    font-weight: 700;
    color: #0f172a;
    white-space: nowrap;
  }
  .trend-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 34px;
    height: 28px;
    border-radius: 6px;
    font-size: 18px;
    font-weight: 700;
    border: 1px solid transparent;
    line-height: 1;
  }
  .trend-good {
    background: #dcfce7;
    color: #166534;
    border-color: #86efac;
  }
  .trend-bad {
    background: #fee2e2;
    color: #991b1b;
    border-color: #fca5a5;
  }
  .trend-neutral {
    background: #e2e8f0;
    color: #334155;
    border-color: #cbd5e1;
  }
  .metric-label {
    color: #475569;
  }
  .metric-value {
    font-weight: 700;
    color: #0f172a;
  }
  .country-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 12px;
    margin: 0;
    background: transparent;
    box-shadow: none;
    border-radius: 0;
  }
  .country-table th {
    background: #e2e8f0;
    color: #0f172a;
    font-weight: 700;
    padding: 6px;
  }
  .country-table td {
    padding: 6px;
    border-bottom: 1px dashed #e2e8f0;
  }
  .country-table tr:last-child td {
    border-bottom: none;
  }
  .empty-note {
    padding: 10px 0;
    color: #64748b;
    font-size: 13px;
    text-align: center;
  }
</style>

</head>
<body>

<h2 style="text-align:center;">&#x1F3C6; Ranking de Llamadas - __MES_NOMBRE__ __ANIO__</h2>

<div class="tabs">
  <button class="tab-btn active" data-target="panel-operaciones">Operaciones</button>
  <button class="tab-btn" data-target="panel-comercial">Comercial</button>
  <button class="tab-btn" data-target="panel-administracion">Administracion</button>
  <button class="tab-btn" data-target="panel-cuentas">Cuentas</button>
  <button class="tab-btn" data-target="panel-desarrollo">Desarrollo</button>
  <button class="tab-btn" data-target="panel-mensual">Resumen</button>
</div>

<div class="panel" id="panel-operaciones">
  <div class="controls">
    <button class="btn" data-sort="entrantes">Ordenar por Entrantes</button>
    <button class="btn btn--alt" data-sort="salientes">Ordenar por Salientes</button>
  </div>

  <table class="ranking-table">
    <tr>
      <th>Lugar</th>
      <th>Extensi&oacute;n</th>
      <th class="emoji-col"></th>
      <th>Nombre</th>
      <th>&Aacute;rea</th>
      <th>Entrantes</th>
      <th>Salientes</th>
    </tr>

__FILAS_OPERACIONES__

  </table>
</div>

<div class="panel hidden" id="panel-comercial">
  <div class="controls">
    <button class="btn" data-sort="entrantes">Ordenar por Entrantes</button>
    <button class="btn btn--alt" data-sort="salientes">Ordenar por Salientes</button>
  </div>
  <table class="ranking-table">
    <tr>
      <th>Lugar</th>
      <th>Extensi&oacute;n</th>
      <th class="emoji-col"></th>
      <th>Nombre</th>
      <th>&Aacute;rea</th>
      <th>Entrantes</th>
      <th>Salientes</th>
    </tr>
__FILAS_COMERCIAL__
  </table>
</div>

<div class="panel hidden" id="panel-administracion">
  <div class="controls">
    <button class="btn" data-sort="entrantes">Ordenar por Entrantes</button>
    <button class="btn btn--alt" data-sort="salientes">Ordenar por Salientes</button>
  </div>
  <table class="ranking-table">
    <tr>
      <th>Lugar</th>
      <th>Extensi&oacute;n</th>
      <th class="emoji-col"></th>
      <th>Nombre</th>
      <th>&Aacute;rea</th>
      <th>Entrantes</th>
      <th>Salientes</th>
    </tr>
__FILAS_ADMINISTRACION__
  </table>
</div>

<div class="panel hidden" id="panel-cuentas">
  <div class="controls">
    <button class="btn" data-sort="entrantes">Ordenar por Entrantes</button>
    <button class="btn btn--alt" data-sort="salientes">Ordenar por Salientes</button>
  </div>
  <table class="ranking-table">
    <tr>
      <th>Lugar</th>
      <th>Extensi&oacute;n</th>
      <th class="emoji-col"></th>
      <th>Nombre</th>
      <th>&Aacute;rea</th>
      <th>Entrantes</th>
      <th>Salientes</th>
    </tr>
__FILAS_CUENTAS__
  </table>
</div>

<div class="panel hidden" id="panel-desarrollo">
  <div class="controls">
    <button class="btn" data-sort="entrantes">Ordenar por Entrantes</button>
    <button class="btn btn--alt" data-sort="salientes">Ordenar por Salientes</button>
  </div>
  <table class="ranking-table">
    <tr>
      <th>Lugar</th>
      <th>Extensi&oacute;n</th>
      <th class="emoji-col"></th>
      <th>Nombre</th>
      <th>&Aacute;rea</th>
      <th>Entrantes</th>
      <th>Salientes</th>
    </tr>
__FILAS_DESARROLLO__
  </table>
</div>

<div class="panel hidden" id="panel-mensual">
  <div class="chart-card">
    <p class="chart-title">Comparativo mensual (desde septiembre 2025)</p>
    <div class="chart-legend">
      <span><span class="legend-dot legend-min"></span>Minutos hablados</span>
      <span><span class="legend-dot legend-call"></span>Llamadas atendidas</span>
    </div>
    <div class="chart-wrap">
      <svg id="chartMensual" width="900" height="320" viewBox="0 0 900 320" role="img" aria-label="Grafica mensual"></svg>
      <div id="chartTooltip" class="chart-tooltip"></div>
    </div>
    <div class="chart-footnote">Incluye llamadas entrantes y salientes con attended=true. Duraci&oacute;n en minutos.</div>
  </div>
  <div class="monthly-table-card">
    <p class="chart-title">Detalle mensual</p>
    <div class="monthly-controls">
      <select id="monthSelect" class="monthly-select" aria-label="Seleccionar mes"></select>
    </div>
    __MONTH_TABLE__
  </div>
</div>

<script>
  (function () {
    function emojiFor(rank) {
      if (rank === 1) return "&#x1F947;";
      if (rank === 2) return "&#x1F948;";
      if (rank === 3) return "&#x1F949;";
      if (rank <= 10) return "&#x2728;";
      return "";
    }

    function renderTable(tableEl, sorted) {
      if (!tableEl) return;
      const tbody = tableEl;
      const staticHeader = tbody.querySelectorAll("tr")[0];
      tbody.innerHTML = "";
      tbody.appendChild(staticHeader);

      if (!sorted.length) {
        const tr = document.createElement("tr");
        tr.innerHTML = '<td colspan="7">Sin datos para el mes actual.</td>';
        tbody.appendChild(tr);
        return;
      }

      sorted.forEach((row, index) => {
        const place = index + 1;
        const emoji = emojiFor(place);
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td>${place}</td>
          <td>${row.extension}</td>
          <td class="emoji">${emoji}</td>
          <td>${row.nombre}</td>
          <td>${row.departamento}</td>
          <td>${row.entrantes}</td>
          <td>${row.salientes}</td>
        `;
        tbody.appendChild(tr);
      });
    }

    function renderPanel(panelId, baseRows, sortKey) {
      const panelEl = document.getElementById(panelId);
      if (!panelEl) return;
      const tableEl = panelEl.querySelector(".ranking-table");
      const sorted = [...baseRows].sort((a, b) => (b[sortKey] ?? 0) - (a[sortKey] ?? 0));
      renderTable(tableEl, sorted);
    }

    function getPanelRows(panelId) {
      return Array.from(document.querySelectorAll(`#${panelId} tr[data-row='1']`))
        .map((tr) => ({
          extension: tr.dataset.extension || "",
          nombre: tr.dataset.nombre || "",
          departamento: tr.dataset.departamento || "",
          entrantes: Number(tr.dataset.llamadas_entrada || 0),
          salientes: Number(tr.dataset.llamadas_salida || 0)
        }));
    }

    const panelConfig = [
      { id: "panel-operaciones" },
      { id: "panel-comercial" },
      { id: "panel-administracion" },
      { id: "panel-cuentas" },
      { id: "panel-desarrollo" },
    ];

    panelConfig.forEach((cfg) => {
      const panelEl = document.getElementById(cfg.id);
      if (!panelEl) return;
      const panelRows = getPanelRows(cfg.id);
      let currentSort = "entrantes";

      renderPanel(cfg.id, panelRows, currentSort);

      panelEl.querySelectorAll("button[data-sort]").forEach((btn) => {
        btn.addEventListener("click", () => {
          currentSort = btn.dataset.sort === "salientes" ? "salientes" : "entrantes";
          renderPanel(cfg.id, panelRows, currentSort);
        });
      });
    });

    const tabs = document.querySelectorAll(".tab-btn");
    const panels = document.querySelectorAll(".panel");
    tabs.forEach((btn) => {
      btn.addEventListener("click", () => {
        tabs.forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        const targetId = btn.dataset.target;
        panels.forEach((panelEl) => {
          panelEl.classList.toggle("hidden", panelEl.id !== targetId);
        });
      });
    });

    const monthlyData = __MONTH_DATA__;
    renderMonthlyChart(monthlyData);
    setupMonthFilter();

    function renderMonthlyChart(data) {
      const svg = document.getElementById("chartMensual");
      const tooltip = document.getElementById("chartTooltip");
      const width = 900;
      const height = 320;
      const padding = { left: 62, right: 24, top: 20, bottom: 48 };
      const plotW = width - padding.left - padding.right;
      const plotH = height - padding.top - padding.bottom;

      const tickCount = 5;
      const axisMin = 0;
      const axisMax = 15000;

      function formatNum(value) {
        return new Intl.NumberFormat("es-MX").format(Math.round(value));
      }

      const step = (axisMax - axisMin) / tickCount;

      const barGroupWidth = data.length ? plotW / data.length : plotW;
      const barWidth = Math.max(10, Math.min(24, barGroupWidth * 0.3));

      const svgParts = [];
      svgParts.push(`<rect x="0" y="0" width="${width}" height="${height}" fill="white" />`);

      for (let i = 0; i <= tickCount; i++) {
        const y = padding.top + (plotH * i) / tickCount;
        const tickValue = axisMax - step * i;
        svgParts.push(`<line x1="${padding.left}" y1="${y}" x2="${width - padding.right}" y2="${y}" stroke="#e5e7eb" />`);
        svgParts.push(`<text x="${padding.left - 8}" y="${y + 4}" text-anchor="end" font-size="11" fill="#64748b">${formatNum(tickValue)}</text>`);
      }

      data.forEach((d, i) => {
        const xCenter = padding.left + barGroupWidth * i + barGroupWidth / 2;
        const minutesH = (Math.min(d.minutes, axisMax) / axisMax) * plotH;
        const callsH = (Math.min(d.calls, axisMax) / axisMax) * plotH;
        const yMinutes = padding.top + (plotH - minutesH);
        const yCalls = padding.top + (plotH - callsH);
        svgParts.push(`<g class="month-group" data-label="${d.label}" data-minutes="${d.minutes}" data-calls="${d.calls}">`);
        svgParts.push(`<rect class="chart-bar bar-min" x="${xCenter - barWidth - 4}" y="${yMinutes}" width="${barWidth}" height="${minutesH}" fill="#0d6efd" rx="3" />`);
        svgParts.push(`<rect class="chart-bar bar-call" x="${xCenter + 4}" y="${yCalls}" width="${barWidth}" height="${callsH}" fill="#f59e0b" rx="3" />`);
        svgParts.push(`<text x="${xCenter}" y="${height - 20}" text-anchor="middle" font-size="11" fill="#334155">${d.label}</text>`);
        svgParts.push(`</g>`);
      });

      svg.innerHTML = svgParts.join("");

      const chartWrap = svg.closest(".chart-wrap");
      if (!chartWrap || !tooltip) return;

      function showTooltip(groupEl, event) {
        const label = groupEl.dataset.label || "";
        const minutes = Number(groupEl.dataset.minutes || 0);
        const calls = Number(groupEl.dataset.calls || 0);
        tooltip.innerHTML = `
          <div class="tooltip-title">${label}</div>
          <div class="tooltip-row"><span class="tooltip-dot tooltip-dot-min"></span><span>Minutos</span><span class="tooltip-value">${formatNum(minutes)}</span></div>
          <div class="tooltip-row"><span class="tooltip-dot tooltip-dot-call"></span><span>Llamadas</span><span class="tooltip-value">${formatNum(calls)}</span></div>
        `;
        tooltip.classList.add("is-visible");
        moveTooltip(event);
      }

      function moveTooltip(event) {
        const rect = chartWrap.getBoundingClientRect();
        const tooltipWidth = tooltip.offsetWidth || 170;
        const minX = tooltipWidth / 2 + 8;
        const maxX = rect.width - tooltipWidth / 2 - 8;
        const x = Math.max(minX, Math.min(event.clientX - rect.left, maxX));
        const y = Math.max(20, event.clientY - rect.top);
        tooltip.style.left = `${x}px`;
        tooltip.style.top = `${y - 8}px`;
      }

      function hideTooltip() {
        tooltip.classList.remove("is-visible");
      }

      const monthGroups = svg.querySelectorAll(".month-group");
      monthGroups.forEach((groupEl) => {
        groupEl.addEventListener("mouseenter", (event) => showTooltip(groupEl, event));
        groupEl.addEventListener("mousemove", moveTooltip);
        groupEl.addEventListener("mouseleave", hideTooltip);
      });
    }

    function setupMonthFilter() {
      const select = document.getElementById("monthSelect");
      const rows = Array.from(document.querySelectorAll("tr[data-month]"));
      if (!select || !rows.length) return;

      const months = rows.map((row) => ({
        value: row.dataset.month,
        label: row.dataset.monthLabel || row.dataset.month
      }));

      select.innerHTML = "";
      const allOption = document.createElement("option");
      allOption.value = "all";
      allOption.textContent = "Todos los meses";
      select.appendChild(allOption);

      months.forEach((m) => {
        const option = document.createElement("option");
        option.value = m.value;
        option.textContent = m.label;
        select.appendChild(option);
      });

      select.addEventListener("change", () => {
        const value = select.value;
        rows.forEach((row) => {
          row.style.display = value === "all" || row.dataset.month === value ? "" : "none";
        });
      });
    }
  })();
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


def remove_surrogates(text):
    # Prevent UnicodeEncodeError when DB values contain isolated surrogate code points.
    return "".join(ch for ch in text if not 0xD800 <= ord(ch) <= 0xDFFF)


def fetch_ranking(start_date, end_date, departamento):
    if not all([DB_CONFIG["host"], DB_CONFIG["dbname"], DB_CONFIG["user"], DB_CONFIG["password"]]):
        raise RuntimeError("Faltan variables de entorno para BD (DB_HOST, DB_NAME, DB_USER, DB_PASS)")

    with psycopg.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:
            cur.execute(SQL_REPORTE, (start_date, end_date, start_date, end_date, departamento))
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


def fetch_monthly(start_date, end_date):
    if not all([DB_CONFIG["host"], DB_CONFIG["dbname"], DB_CONFIG["user"], DB_CONFIG["password"]]):
        raise RuntimeError("Faltan variables de entorno para BD (DB_HOST, DB_NAME, DB_USER, DB_PASS)")

    with psycopg.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:
            cur.execute(SQL_MENSUAL, (start_date, end_date))
            rows = cur.fetchall()

    data = []
    for r in rows:
        mes = r[0]
        total_llamadas = int(r[1]) if r[1] is not None else 0
        total_segundos = int(r[2]) if r[2] is not None else 0
        minutes = round(total_segundos / 60, 1)
        label = f"{MESES.get(mes.month, mes.month)[:3]} {str(mes.year)[-2:]}"
        data.append({
            "label": label,
            "calls": total_llamadas,
            "minutes": minutes,
        })
    return data


def fetch_monthly_summary(start_date, end_date):
    if not all([DB_CONFIG["host"], DB_CONFIG["dbname"], DB_CONFIG["user"], DB_CONFIG["password"]]):
        raise RuntimeError("Faltan variables de entorno para BD (DB_HOST, DB_NAME, DB_USER, DB_PASS)")

    with psycopg.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:
            cur.execute(SQL_MENSUAL_RESUMEN, (start_date, end_date))
            rows = cur.fetchall()

    data = []
    for r in rows:
        mes = r[0]
        data.append({
            "mes": mes,
            "total_llamadas": int(r[1]) if r[1] is not None else 0,
            "total_segundos": int(r[2]) if r[2] is not None else 0,
            "llamadas_entrantes": int(r[3]) if r[3] is not None else 0,
            "llamadas_salientes": int(r[4]) if r[4] is not None else 0,
            "segundos_entrantes": int(r[5]) if r[5] is not None else 0,
            "segundos_salientes": int(r[6]) if r[6] is not None else 0,
            "llamadas_internas": int(r[7]) if r[7] is not None else 0,
            "segundos_internas": int(r[8]) if r[8] is not None else 0,
        })
    return data


def fetch_monthly_by_country(start_date, end_date):
    if not all([DB_CONFIG["host"], DB_CONFIG["dbname"], DB_CONFIG["user"], DB_CONFIG["password"]]):
        raise RuntimeError("Faltan variables de entorno para BD (DB_HOST, DB_NAME, DB_USER, DB_PASS)")

    with psycopg.connect(**DB_CONFIG) as conn:
        with conn.cursor() as cur:
            cur.execute(SQL_MENSUAL_POR_PAIS, (start_date, end_date))
            rows = cur.fetchall()

    data = []
    for r in rows:
        data.append({
            "mes": r[0],
            "pais": r[1],
            "segundos_entrada": int(r[2]) if r[2] is not None else 0,
            "segundos_salida": int(r[3]) if r[3] is not None else 0,
            "segundos_total": int(r[4]) if r[4] is not None else 0,
        })
    return data


def build_rows(data):
    if not data:
        return '<tr><td colspan="7">Sin datos para el mes actual.</td></tr>'

    out = []
    for r in data:
        extension = "" if r["extension"] is None else remove_surrogates(str(r["extension"]))
        nombre = "" if r["nombre"] is None else remove_surrogates(str(r["nombre"]))
        departamento = "" if r["departamento"] is None else remove_surrogates(str(r["departamento"]))
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


def format_number(value, decimals=0):
    if value is None:
        value = 0
    if decimals == 0:
        return f"{int(round(value)):,}"
    text = f"{value:,.1f}"
    return text.rstrip("0").rstrip(".")


def format_mmss(minutes_value):
    total_seconds = int(round((minutes_value or 0) * 60))
    mm = total_seconds // 60
    ss = total_seconds % 60
    return f"{mm:02d}:{ss:02d}"


def build_month_table(summary_data, country_data):
    if not summary_data:
        return '<div class="empty-note">Sin datos para el periodo seleccionado.</div>'

    country_by_month = {}
    for row in country_data:
        month_key = row["mes"].strftime("%Y-%m")
        country_by_month.setdefault(month_key, []).append(row)

    rows = []
    rows.append(
        "<table class=\"monthly-table\">"
        "<tr>"
        "<th class=\"col-mes\">Mes</th>"
        "<th class=\"col-promedio\">Prom. Resol. Entra.</th>"
        "<th class=\"col-llamadas\">Llamadas</th>"
        "<th class=\"col-minutos\">Minutos</th>"
        "<th class=\"col-pais\">Pa&iacute;s</th>"
        "</tr>"
    )

    previous_avg_min = None
    for item in summary_data:
        mes = item["mes"]
        month_key = mes.strftime("%Y-%m")
        label = f"{MESES.get(mes.month, mes.month)} {mes.year}"

        total_llamadas = item["total_llamadas"]
        llamadas_entrantes = item["llamadas_entrantes"]
        llamadas_salientes = item["llamadas_salientes"]
        llamadas_internas = item["llamadas_internas"]
        total_min = item["total_segundos"] / 60
        min_entrantes = item["segundos_entrantes"] / 60
        min_salientes = item["segundos_salientes"] / 60
        min_internas = item["segundos_internas"] / 60
        avg_resolution_min = (min_entrantes / llamadas_entrantes) if llamadas_entrantes > 0 else 0

        if previous_avg_min is None:
            trend_class = "trend-neutral"
            trend_icon = "&#9632;"
            trend_title = "Sin referencia del mes anterior"
        elif avg_resolution_min < previous_avg_min:
            trend_class = "trend-good"
            trend_icon = "&#8595;"
            trend_title = "Disminuy\u00f3 vs mes anterior"
        elif avg_resolution_min > previous_avg_min:
            trend_class = "trend-bad"
            trend_icon = "&#8593;"
            trend_title = "Aument\u00f3 vs mes anterior"
        else:
            trend_class = "trend-neutral"
            trend_icon = "="
            trend_title = "Sin cambio vs mes anterior"

        promedio_html = (
            "<div class=\"resolution-wrap\">"
            f"<span class=\"resolution-value\">{format_mmss(avg_resolution_min)}</span>"
            f"<span class=\"trend-badge {trend_class}\" title=\"{trend_title}\">{trend_icon}</span>"
            "</div>"
        )

        llamadas_html = (
            "<div class=\"monthly-metrics\">"
            f"<span><span class=\"metric-label\">Total</span><span class=\"metric-value\">{format_number(total_llamadas)}</span></span>"
            f"<span><span class=\"metric-label\">Entrantes</span><span class=\"metric-value\">{format_number(llamadas_entrantes)}</span></span>"
            f"<span><span class=\"metric-label\">Salientes</span><span class=\"metric-value\">{format_number(llamadas_salientes)}</span></span>"
            f"<span><span class=\"metric-label\">Internas</span><span class=\"metric-value\">{format_number(llamadas_internas)}</span></span>"
            "</div>"
        )

        minutos_html = (
            "<div class=\"monthly-metrics\">"
            f"<span><span class=\"metric-label\">Total</span><span class=\"metric-value\">{format_number(total_min)}</span></span>"
            f"<span><span class=\"metric-label\">Entrantes</span><span class=\"metric-value\">{format_number(min_entrantes)}</span></span>"
            f"<span><span class=\"metric-label\">Salientes</span><span class=\"metric-value\">{format_number(min_salientes)}</span></span>"
            f"<span><span class=\"metric-label\">Internas</span><span class=\"metric-value\">{format_number(min_internas)}</span></span>"
            "</div>"
        )

        country_rows = country_by_month.get(month_key, [])
        if not country_rows:
            country_html = '<div class="empty-note">Sin datos por pa&iacute;s.</div>'
        else:
            ordered_countries = [
                "MEXICO",
                "COSTA RICA",
                "COLOMBIA",
                "HONDURAS",
                "GUATEMALA",
                "PANAMA",
                "ECUADOR",
                "NICARAGUA",
                "EL SALVADOR",
                "OTROS",
            ]
            country_map = {str(c["pais"]).upper(): c for c in country_rows}
            country_html = [
                "<table class=\"country-table\">",
                "<tr><th>Pa&iacute;s</th><th>Entrada (min)</th><th>Salida (min)</th><th>Total (min)</th></tr>",
            ]
            for country_name in ordered_countries:
                c = country_map.get(country_name, {})
                min_entrada = (c.get("segundos_entrada", 0) or 0) / 60
                min_salida = (c.get("segundos_salida", 0) or 0) / 60
                min_total = (c.get("segundos_total", 0) or 0) / 60
                country_html.append(
                    "<tr>"
                    f"<td>{escape(country_name)}</td>"
                    f"<td>{format_number(min_entrada)}</td>"
                    f"<td>{format_number(min_salida)}</td>"
                    f"<td>{format_number(min_total)}</td>"
                    "</tr>"
                )
            country_html.append("</table>")
            country_html = "".join(country_html)

        rows.append(
            f"<tr data-month=\"{month_key}\" data-month-label=\"{label}\">"
            f"<td class=\"col-mes\">{label}</td>"
            f"<td class=\"col-promedio\">{promedio_html}</td>"
            f"<td class=\"col-llamadas\">{llamadas_html}</td>"
            f"<td class=\"col-minutos\">{minutos_html}</td>"
            f"<td class=\"col-pais\">{country_html}</td>"
            "</tr>"
        )
        previous_avg_min = avg_resolution_min

    rows.append("</table>")
    return "\n".join(rows)


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

    ranking_operaciones = fetch_ranking(start_date, end_date, "Operaciones")
    ranking_comercial = fetch_ranking(start_date, end_date, "Comercial")
    ranking_administracion = fetch_ranking(start_date, end_date, "Administracion")
    ranking_cuentas = fetch_ranking(start_date, end_date, "Cuentas")
    ranking_desarrollo = fetch_ranking(start_date, end_date, "Desarrollo")

    filas_operaciones = build_rows(ranking_operaciones)
    filas_comercial = build_rows(ranking_comercial)
    filas_administracion = build_rows(ranking_administracion)
    filas_cuentas = build_rows(ranking_cuentas)
    filas_desarrollo = build_rows(ranking_desarrollo)

    monthly_start = datetime(2025, 9, 1)
    monthly_data = fetch_monthly(monthly_start, end_date)
    monthly_summary = fetch_monthly_summary(monthly_start, end_date)
    monthly_by_country = fetch_monthly_by_country(monthly_start, end_date)

    report_filename = f"Reporte_Operaciones_{now.year}_{month:02d}.html"
    report_path = os.path.abspath(os.path.join(BASE_DIR, "..", "reports", report_filename))

    html = (
        HTML_TEMPLATE
        .replace("__MES_NOMBRE__", mes_nombre)
        .replace("__ANIO__", str(now.year))
        .replace("__FECHA_GENERACION__", fecha_generacion)
        .replace("__FILAS_OPERACIONES__", filas_operaciones)
        .replace("__FILAS_COMERCIAL__", filas_comercial)
        .replace("__FILAS_ADMINISTRACION__", filas_administracion)
        .replace("__FILAS_CUENTAS__", filas_cuentas)
        .replace("__FILAS_DESARROLLO__", filas_desarrollo)
        .replace("__MONTH_DATA__", json.dumps(monthly_data, ensure_ascii=True))
        .replace("__MONTH_TABLE__", build_month_table(monthly_summary, monthly_by_country))
    )
    html = remove_surrogates(html)

    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"Reporte generado: {report_path}")


if __name__ == "__main__":
    main()
