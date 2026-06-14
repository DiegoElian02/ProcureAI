# ProcureAI Insights

ProcureAI Insights es un chatbot en Streamlit para analizar archivos estructurados de negocio como CSV, Excel o Google Sheets exportados. Está pensado para equipos de procurement, finanzas, dirección y usuarios de negocio que necesitan consultar KPIs con preguntas en lenguaje natural.

## Funcionalidades principales

- Carga de archivos CSV, XLSX o XLS.
- Detección básica de columnas principales como `provider`, `product`, `revenue`, `cost` y `spend`.
- Vista previa del dataset cargado.
- Preguntas en lenguaje natural para obtener insights de negocio.
- Cálculo de KPIs mínimos:
  - Profit.
  - Spend.
  - Revenue.
  - Spend agrupado por proveedor.
  - Productos con mejor desempeño por revenue.
- Respuestas determinísticas sin API key y respuestas mejoradas con OpenAI cuando se configura una key.

## Estructura del proyecto

```text
ProcureAI/
├── app.py                         # Aplicación principal de Streamlit
├── data/
│   └── sample_procurement_data.csv # Dataset de prueba
├── src/
│   ├── ai_client.py               # Integración opcional con OpenAI
│   ├── config.py                  # Lectura de secrets/env vars
│   ├── data_loader.py             # Carga y perfilado de datos
│   └── kpi_engine.py              # Interpretación simple y cálculo de KPIs
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

> La app también funciona sin API key usando el motor local de KPIs, pero la integración con OpenAI ayuda a redactar respuestas más naturales y ejecutivas.

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

- ¿Cuál fue el profit total?
- ¿Cuál fue el spend total?
- ¿Qué proveedor tuvo mayor gasto?
- ¿Cuál fue el revenue total?
- ¿Cuáles fueron los productos con mejor desempeño?

## Historias de usuario cubiertas

| ID | Cobertura |
| --- | --- |
| HU-01 | Carga CSV/Excel, validación de extensión, reconocimiento de columnas y preview. |
| HU-02 | Campo de pregunta, preguntas de prueba e interpretación por palabras clave. |
| HU-03 | Cálculo de profit, spend, revenue y gasto por proveedor. |
| HU-04 | Respuestas breves, claras y orientadas a decisiones de negocio. |
