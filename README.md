# ChileCompra Data Platform

Plataforma de datos **batch end-to-end** construida en Azure y Databricks para ingerir, procesar y analizar datos públicos de compras del Estado de Chile provenientes de ChileCompra / Mercado Público.

El proyecto integra carga histórica e ingesta incremental diaria mediante una arquitectura **Medallion**, con procesamiento idempotente, controles de calidad, orquestación automatizada, seguridad basada en identidades administradas y una capa analítica con dashboard actualizado automáticamente.

---

## Resultados

- **+1.1 millones de órdenes de compra** procesadas.
- **+2.8 millones de ítems** procesados.
- Ingesta histórica de órdenes de compra desde archivos masivos.
- Ingesta incremental diaria desde la API de Mercado Público.
- Pipelines preparados para **reruns y backfills** mediante `process_date`.
- Procesamiento incremental con **Delta Lake MERGE** y reemplazo determinístico de particiones.
- Controles de **Data Quality** antes y después de las escrituras.
- Pipeline automatizado desde la fuente hasta el dashboard analítico.
- Ejecuciones diarias operando exitosamente durante el período de observación.

---

## Arquitectura

<!--
Descomentar cuando agreguemos el diagrama:

![Arquitectura ChileCompra Data Platform](docs/images/architecture.png)
-->

```text
ChileCompra / Mercado Público
        │
        ├── CSV históricos
        └── REST API
                │
                ▼
        Azure Data Factory
                │
                ▼
          ADLS Gen2 Landing
                │
                ▼
        Azure Databricks
                │
        ┌───────┼───────┐
        ▼       ▼       ▼
      Bronze  Silver   Gold
                        │
                        ▼
              Databricks AI/BI
              ChileCompra Analytics
```

La arquitectura se complementa con **Azure Key Vault**, **Managed Identities**, **Databricks Access Connector**, **RBAC** y **Unity Catalog** para evitar credenciales embebidas y gobernar el acceso a los datos.

---

## Stack tecnológico

| Área | Tecnología |
|---|---|
| Orquestación | Azure Data Factory |
| Data Lake | Azure Data Lake Storage Gen2 |
| Procesamiento | Azure Databricks |
| Lenguajes | Python, PySpark, SQL |
| Formato | Delta Lake |
| Arquitectura | Medallion: Bronze / Silver / Gold |
| Gobierno | Unity Catalog |
| Secretos | Azure Key Vault |
| Identidad | Managed Identity / Access Connector |
| Compute | Databricks Serverless |
| Analytics | Databricks AI/BI Dashboards |
| Versionamiento | Git + GitHub |

---

## Qué construí

### Ingesta histórica + incremental

Se implementaron dos estrategias de entrada:

- **Histórica:** archivos masivos CSV de órdenes de compra.
- **Incremental:** API diaria de órdenes de compra y licitaciones.

La separación permite realizar el bootstrap histórico una vez y continuar posteriormente mediante cargas incrementales controladas.

### Arquitectura Medallion

```text
Landing
   ↓
Bronze
   ↓
Silver
   ↓
Gold
   ↓
Dashboard
```

**Bronze** conserva los datos de origen junto con metadatos de ingesta.

**Silver** normaliza tipos, resuelve duplicados, aplica reglas de negocio y consolida entidades mediante `MERGE`.

**Gold** genera agregaciones orientadas al consumo analítico.

### Procesamiento idempotente

Cada ejecución incremental utiliza:

```text
process_date → fecha lógica procesada
run_id       → ejecución física de ADF
```

Esto permite repetir una fecha o realizar un backfill sin modificar el código del pipeline.

Landing conserva cada ejecución mediante `run_id`, mientras Bronze y Silver mantienen un estado final determinístico.

### Data Quality

Se implementaron validaciones críticas como:

- claves nulas;
- duplicados inesperados;
- estados no mapeados;
- relaciones padre/hijo inválidas;
- discrepancias de conteos;
- verificaciones posteriores a escrituras y `MERGE`.

Una violación crítica genera una excepción y provoca el fallo de la tarea, propagándose hacia la orquestación.

---

## Pipeline automatizado

Azure Data Factory actúa como orquestador principal.

```text
Trigger diario
     │
     ▼
Obtención del secreto desde Key Vault
     │
     ├───────────────┐
     ▼               ▼
Órdenes de Compra   Licitaciones
     │               │
     ▼               ▼
   Landing         Landing
     │               │
     ▼               ▼
Bronze → Silver  Bronze → Silver
     │               │
     └───────┬───────┘
             ▼
            Gold
             │
             ▼
      Refresh Dashboard
```

Las ramas de órdenes de compra y licitaciones se procesan en paralelo.

La capa Gold solo comienza cuando ambas ramas terminan correctamente y el dashboard se actualiza únicamente después de que todas las tareas Gold finalizan con éxito.

---

## Principales decisiones de ingeniería

**Batch en lugar de streaming**  
Los datos no requieren procesamiento en tiempo real. Un pipeline diario reduce complejidad y costo operacional.

**No inferir eliminaciones desde la API**  
La API es mutable y no entrega semántica CDC completa. La ausencia de un registro en una respuesta posterior no se interpreta automáticamente como un `DELETE`.

**MERGE en Silver**  
Las entidades provenientes de la API se actualizan únicamente cuando la versión recibida es más reciente que la almacenada.

**Idempotencia separada de trazabilidad**  
`run_id` conserva evidencia de cada ejecución en Landing, mientras `process_date` controla el estado lógico procesado.

**Gold determinístico**  
Las tablas Gold son pequeñas comparadas con Silver, por lo que pueden reconstruirse completamente reduciendo complejidad incremental.

**Ejecución paralela**  
Las transformaciones Gold independientes se ejecutan simultáneamente y convergen antes del refresh analítico.

---

## Analytics

El proyecto incluye el dashboard versionado:

**ChileCompra Analytics**

con dos páginas principales.

### Órdenes de Compra

- total de órdenes;
- monto total de órdenes;
- proveedores y organismos distintos;
- evolución mensual;
- cantidad mensual de órdenes;
- Top 10 organismos;
- Top 10 proveedores;
- filtro interactivo por período.

<!--
![Dashboard Órdenes](docs/images/dashboard-orders.png)
-->

### Licitaciones

- total de licitaciones observadas;
- publicadas, adjudicadas y desiertas;
- distribución por estado;
- distribución por mes de cierre;
- composición mensual por estado;
- porcentaje de órdenes con código de licitación;
- filtro por mes de cierre.

<!--
![Dashboard Licitaciones](docs/images/dashboard-licitaciones.png)
-->

El dashboard forma parte del flujo automatizado y se refresca después de la actualización exitosa de Gold.

---

## Seguridad

La plataforma evita almacenar credenciales directamente en código.

Se utilizan:

- **Azure Key Vault** para el ticket de Mercado Público;
- **Managed Identity** para Azure Data Factory;
- **RBAC** para acceso a ADLS Gen2;
- **Databricks Access Connector** para autenticación contra Storage;
- **Unity Catalog** para gobierno del lakehouse;
- `.gitignore` para excluir secretos locales.

No se utilizan storage keys ni credenciales embebidas en notebooks.

---

## Estructura del repositorio

```text
chilecompra-data-platform/
│
├── adf/
│   ├── dataset/
│   ├── linkedService/
│   ├── pipeline/
│   └── trigger/
│
├── databricks/
│   ├── setup/
│   ├── bronze/
│   ├── silver/
│   ├── gold/
│   └── Dashboard/
│
├── exploration/
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

---

## Estado del proyecto

Actualmente el flujo se encuentra automatizado de extremo a extremo:

```text
Fuente
→ ADF
→ Landing
→ Bronze
→ Silver
→ Gold
→ Dashboard
```

El pipeline se mantiene operativo durante un período de observación para registrar comportamiento real, costos e incidentes antes del cierre definitivo del proyecto.

---

## Documentación técnica

La documentación detallada del proyecto se dividirá en:

```text
docs/
├── architecture.md
├── engineering-decisions.md
└── operations.md
```

Estos documentos profundizan en la arquitectura, decisiones técnicas, operación, backfills, observabilidad y costos sin sobrecargar este README principal.

---

## Autor

**Nicolás Rojas**

Proyecto de portafolio orientado a **Data Engineering**, construido utilizando datos públicos de ChileCompra / Mercado Público.
