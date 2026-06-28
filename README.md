# ProcureAI Insights

ProcureAI Insights es un chatbot en Streamlit para analizar archivos estructurados de negocio como CSV, Excel o Google Sheets exportados. Está pensado para equipos de procurement, finanzas, dirección y usuarios de negocio que necesitan consultar KPIs con preguntas en lenguaje natural.

## Funcionalidades principales

- Carga de archivos CSV, XLSX o XLS.
- Detección básica de columnas principales como `provider`, `product`, `revenue`, `cost` y `spend`.
- Vista previa del dataset cargado.
- Validación previa de columnas críticas y advertencias sobre columnas recomendadas.
- Preguntas en lenguaje natural para obtener insights de negocio, incluyendo consultas abiertas que GPT traduce a código pandas.
- Cálculo de KPIs mínimos:
  - Profit.
  - Spend.
  - Revenue.
  - Spend agrupado por proveedor.
  - Productos con mejor desempeño por revenue.
  - Filtros temporales como “profit de marzo” o “revenue de 2026”.
- Con OpenAI, generación de código pandas para extraer la información solicitada, ejecución validada de ese código y redacción final del insight. Sin API key, fallback determinístico para KPIs comunes.
- Mensajes de error claros y accionables cuando el archivo o la pregunta no puedan procesarse.
- Gráficas rápidas de tendencia mensual y gasto por proveedor, más visualización de resultados cuando la pregunta solicita tendencia o comparación.

## Estructura del proyecto

```text
ProcureAI/
├── app.py                         # Aplicación principal de Streamlit
├── data/
│   └── sample_procurement_data.csv # Dataset de prueba
├── src/
│   ├── ai_client.py               # Generación de código con OpenAI y redacción ejecutiva
│   ├── code_executor.py           # Validador/ejecutor del código pandas generado
│   ├── error_messages.py          # Catálogo de errores claros para usuario
│   ├── config.py                  # Lectura de secrets/env vars
│   ├── data_loader.py             # Carga y perfilado de datos
│   ├── kpi_engine.py              # Interpretación simple y cálculo de KPIs
│   ├── validation.py              # Validación automática del dataset
│   └── visualizations.py          # Gráficas básicas de tendencias/comparaciones
├── .streamlit/
│   └── secrets.toml.example       # Plantilla para API key
├── .env.example                   # Alternativa local para variables de entorno
└── requirements.txt
```

## Cómo ejecutar localmente

1. Crea un entorno virtual e instala dependencias:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Opcional: configura la API key de OpenAI para mejorar las respuestas:

```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

Luego edita `.streamlit/secrets.toml` y reemplaza `pega_tu_api_key_aqui` con tu API key.

3. Ejecuta Streamlit:

```bash
streamlit run app.py
```

4. Carga el archivo de prueba incluido:

```text
data/sample_procurement_data.csv
```

## Configuración en Streamlit Cloud

1. Sube este repositorio a GitHub.
2. En Streamlit Cloud crea una nueva app apuntando a `app.py`.
3. En **App settings > Secrets**, agrega:

```toml
OPENAI_API_KEY = "pega_tu_api_key_aqui"
OPENAI_MODEL = "gpt-4o-mini"
```

> La app también funciona sin API key usando el motor local de KPIs. Con OpenAI, GPT genera código pandas específico para la pregunta, la app valida que no use imports, archivos, red, funciones/clases ni nombres peligrosos, y luego ejecuta ese código contra una copia del DataFrame cargado.

## Troubleshooting

### Error `Client.__init__() got an unexpected keyword argument 'proxies'`

Este error suele ocurrir cuando `openai` se instala junto con una versión incompatible de `httpx`. El proyecto fija `httpx==0.27.2` en `requirements.txt` para mantener compatibilidad con la versión de `openai` usada por la app.

Si ya habías instalado dependencias antes del cambio, ejecuta:

```bash
pip install -r requirements.txt --upgrade --force-reinstall
```

### Warnings de fechas en pandas

La detección de fechas solo intenta parsear columnas cuyo nombre parece representar una fecha, como `date`, `fecha` o `invoice_date`, para evitar warnings innecesarios al analizar columnas de texto como proveedores o productos.

## Preguntas de prueba sugeridas

- ¿Cuál fue el profit de marzo?
- ¿Cuál fue el revenue de abril?
- ¿Qué proveedor tuvo mayor gasto en mayo?
- ¿Cuál fue el profit total?
- ¿Cuál fue el spend total?
- ¿Qué proveedor tuvo mayor gasto?
- ¿Cuál fue el revenue total?
- ¿Cuáles fueron los productos con mejor desempeño?

## Historias de usuario cubiertas

| ID | Cobertura |
| --- | --- |
| HU-01 | Carga CSV/Excel, validación de extensión, reconocimiento de columnas y preview. |
| HU-02 | Campo de pregunta, preguntas de prueba y generación de código pandas con OpenAI, con fallback por palabras clave/plan local. |
| HU-03 | Cálculo de profit, spend, revenue y gasto por proveedor. |
| HU-04 | Respuestas breves, claras y orientadas a decisiones de negocio. |
| HU-05 | Validación automática de columnas mínimas, errores bloqueantes y advertencias de columnas recomendadas. |
| HU-06 | Catálogo de errores claros, breves y accionables para archivo, API key, columnas y preguntas. |
| HU-07 | Gráficas rápidas de tendencia mensual y gasto por proveedor; visualización de resultados comparativos solicitados. |
| HU-04R | Prompt de respuesta refinado con respuesta directa, insight de negocio y recomendación accionable. |
