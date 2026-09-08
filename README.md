# ChileCompra Data Platform

Plataforma de datos **batch end-to-end** construida en Azure y Databricks para procesar datos públicos de compras del Estado de Chile provenientes de ChileCompra / Mercado Público.

Integra carga histórica e ingesta incremental diaria mediante una arquitectura **Medallion**, con procesamiento idempotente, Data Quality, orquestación automatizada, seguridad cloud y una capa analítica actualizada automáticamente.

---

## Arquitectura

![Arquitectura ChileCompra Data Platform](docs/images/architecture.png)

```text
ChileCompra / Mercado Público
        ↓
Azure Data Factory
        ↓
ADLS Gen2 - Landing
        ↓
Azure Databricks
Bronze → Silver → Gold
        ↓
Databricks AI/BI Dashboard
```

---

## Resultados

- **+1.1M órdenes de compra** procesadas.
- **+2.8M ítems** procesados.
- Carga histórica + **ingesta incremental diaria**.
- Pipelines preparados para **reruns y backfills**.
- Procesamiento idempotente con `process_date`, `replaceWhere` y Delta `MERGE`.
- Controles de **Data Quality** con propagación de fallos.
- Flujo automatizado desde la fuente hasta el **refresh del dashboard**.

---

## Stack

`Azure Data Factory` · `ADLS Gen2` · `Azure Databricks` · `PySpark` · `SQL` · `Delta Lake` · `Unity Catalog` · `Key Vault` · `GitHub`

---

## Qué construí

- Arquitectura **Landing → Bronze → Silver → Gold**.
- Ingesta histórica desde archivos masivos de ChileCompra.
- Ingesta incremental diaria desde la API de Mercado Público.
- Manejo de una **fuente API mutable** sin asumir CDC inexistente.
- Upserts mediante **Delta Lake MERGE**.
- Ejecuciones idempotentes y soporte para backfills.
- Procesamiento paralelo mediante ADF y Databricks Jobs.
- Autenticación mediante **Managed Identity**, Key Vault y Access Connector.
- Gold orientado a métricas de negocio.
- Dashboard AI/BI con refresh automático después de Gold.

---

## Pipeline

```text
Trigger diario
     ↓
Azure Data Factory
     ↓
Landing
     ↓
Bronze
     ↓
Silver
     ↓
Gold
     ↓
ChileCompra Analytics
```

Las ramas de **órdenes de compra** y **licitaciones** se procesan en paralelo.  
Gold comienza únicamente después de que ambas terminan correctamente.

---

## Analytics

### Órdenes de Compra

![Dashboard Órdenes de Compra](docs/images/dashboard-orders.png)

Incluye evolución mensual, KPIs de compras públicas y rankings de organismos y proveedores.

### Licitaciones

![Dashboard Licitaciones](docs/images/dashboard-licitaciones.png)

Incluye distribución por estado, mes de cierre y relación entre órdenes de compra y licitaciones.

---

## Documentación técnica

Para mantener este README enfocado en una lectura rápida, el detalle técnico está separado:

- [Arquitectura](docs/architecture.md)
- [Decisiones de ingeniería](docs/engineering-decisions.md)
- [Operación, observabilidad y costos](docs/operations.md)

---

## Estado

El pipeline está actualmente **automatizado de extremo a extremo** y se mantiene operativo durante un período de observación para registrar comportamiento real, costos e incidentes.

---

## Autor

**Nicolás Rojas**

Proyecto de portafolio orientado a **Data Engineering** utilizando datos públicos de ChileCompra / Mercado Público.
