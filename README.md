# ChileCompra Data Platform

End-to-end batch data platform built on Azure and Databricks to ingest, process, model, and analyze Chilean public procurement data from Mercado Público.

The project combines historical bulk files with daily API ingestion and implements an automated Medallion Architecture with incremental processing, idempotent reruns, data quality controls, Delta Lake MERGE operations, cloud security, orchestration, business aggregates, and an automatically refreshed analytics dashboard.

---

## Project Overview

ChileCompra publishes public procurement information through bulk datasets and the Mercado Público API.

The goal of this project was not only to analyze the data, but to design a production-oriented data engineering platform capable of:

- loading historical procurement data;
- ingesting new data every day;
- supporting reruns and backfills;
- handling a mutable API source;
- validating data before and after writes;
- separating raw, curated, and business-ready data;
- securely accessing Azure resources without embedded credentials;
- orchestrating dependencies and failures;
- exposing business metrics through an analytics layer;
- automatically refreshing dashboards after successful processing.

The platform currently processes more than **1.1 million purchase orders** and more than **2.8 million purchase-order items**, with new API data incorporated through the daily pipeline.

---

## Architecture

The platform follows this high-level flow:

```text
Mercado Público
 Bulk CSV + REST API
        |
        v
Azure Data Factory
 Historical + Incremental orchestration
        |
        v
ADLS Gen2
 Landing Zone
        |
        v
Azure Databricks
        |
        +--> Bronze
        |
        +--> Silver
        |
        +--> Gold
        |
        v
Databricks AI/BI
ChileCompra Analytics
```

The final architecture also uses:

- **Azure Key Vault** for API credentials;
- **Managed Identity** for Azure Data Factory;
- **Databricks Access Connector** for storage access;
- **Azure RBAC** for service permissions;
- **Unity Catalog** for data governance;
- **Delta Lake** for transactional tables;
- **Lakeflow Jobs / Databricks Jobs** for transformation workflows;
- **GitHub** for source control;
- **Databricks AI/BI Dashboards** for analytics.

> A detailed architecture diagram will be added to this repository.

---

## Technology Stack

| Layer | Technology |
|---|---|
| Source | Mercado Público API, ChileCompra bulk CSV |
| Orchestration | Azure Data Factory |
| Storage | Azure Data Lake Storage Gen2 |
| Processing | Azure Databricks |
| Compute | Databricks Serverless |
| Language | Python, PySpark, SQL |
| Storage Format | Delta Lake |
| Governance | Unity Catalog |
| Secrets | Azure Key Vault |
| Identity | Managed Identities / Databricks Access Connector |
| Analytics | Databricks AI/BI Dashboards |
| Version Control | GitHub |

---

## Data Sources

### Historical Purchase Orders

Historical purchase orders are loaded from ChileCompra bulk CSV files.

The historical bootstrap covers:

```text
January 2026 → August 2026
```

The bulk source has item-level granularity:

```text
1 row = 1 purchase-order item
```

The purchase-order code is therefore repeated across items, while the item identifier is used as the natural key for the item-level Silver table.

### Incremental Purchase Orders

Starting from September 2026, purchase-order updates are ingested daily from the Mercado Público API.

### Licitaciones

Licitaciones are also ingested daily through the Mercado Público API.

Their API coverage begins with the incremental pipeline and therefore does **not** represent a complete historical snapshot of all previous licitaciones.

---

## Landing Zone

Azure Data Factory stores immutable source executions in ADLS Gen2.

```text
landing/
└── chilecompra/
    ├── ordenes_compra/
    │   ├── historical/
    │   │   └── year=YYYY/month=MM/
    │   └── incremental/
    │       └── process_date=YYYY-MM-DD/
    │           └── run_id=<ADF_RUN_ID>/
    │
    └── licitaciones/
        └── incremental/
            └── process_date=YYYY-MM-DD/
                └── run_id=<ADF_RUN_ID>/
```

Two identifiers are deliberately separated:

- `process_date`: business date being processed;
- `run_id`: unique execution identifier.

This allows the same business date to be rerun without overwriting the original Landing execution.

---

## Medallion Architecture

### Bronze

Bronze preserves source-level records while adding ingestion metadata.

Main responsibilities:

- ingest historical CSV files;
- ingest daily API JSON responses;
- preserve source information;
- normalize column naming;
- attach ingestion metadata;
- validate basic source contracts;
- provide deterministic partition replacement for reruns.

Examples of metadata stored in Bronze include:

```text
_ingestion_timestamp
_source_file
_process_date
_pipeline_run_id
```

Historical and incremental ingestion use different strategies because the source contracts are different.

---

### Silver

Silver contains typed, standardized and deduplicated business entities.

Main tables include:

```text
chilecompra.silver.ordenes_compra
chilecompra.silver.ordenes_compra_items
chilecompra.silver.licitaciones
```

Transformations include:

- type casting;
- date normalization;
- decimal normalization;
- state mapping;
- deduplication;
- entity-level keys;
- foreign-key validation;
- API freshness handling;
- Delta Lake MERGE operations.

#### Mutable API handling

The Mercado Público API is mutable and does not expose true CDC semantics.

For this reason, the pipeline uses an **upsert strategy** rather than interpreting missing records as deletes.

When several API versions of the same entity exist, the newest version is selected using source and processing timestamps.

This avoids deleting valid historical entities only because they disappear from a later API response.

---

## Incremental Processing and Idempotency

The daily pipeline receives a controlled parameter:

```text
process_date
```

The same pipeline can therefore be used for:

- normal daily processing;
- reruns;
- backfills.

No code modification is required to process another date.

### Bronze

Incremental Bronze writes replace only the partition associated with the requested `process_date`.

### Silver

Silver uses Delta Lake `MERGE` to insert new entities and update entities only when the incoming API version is newer than the existing version.

### Gold

Gold tables contain relatively small business aggregates and are rebuilt deterministically from Silver.

Running the same `process_date` again therefore produces the same final business state.

---

## Data Quality

Data Quality checks are executed both **before and after writes**.

Critical violations fail the Databricks task and propagate the failure to the orchestrator.

Examples include:

- null purchase-order codes;
- null item identifiers;
- unexpected duplicate keys;
- invalid state mappings;
- broken item-to-order relationships;
- inconsistent source row counts;
- failed post-write verification.

Not every anomaly is treated as an error.

For example, duplicate licitacion codes inside the same API response were observed to be legitimate source behavior and are handled during Silver deduplication rather than causing Bronze ingestion to fail.

This separates:

```text
critical data contract violations
```

from:

```text
valid but unusual source behavior
```

---

## Orchestration

Azure Data Factory acts as the outer orchestrator.

Two main pipelines are versioned in the repository:

```text
pl_chilecompra_historial
pl_chilecompra_incremental
```

### Historical Pipeline

The historical pipeline is manually parameterized and supports loading a specific year/month source file.

It performs:

```text
Source validation
      ↓
Historical Bronze ingestion
      ↓
Purchase Orders Silver
      ↓
Purchase Order Items Silver
```

### Incremental Pipeline

The incremental pipeline runs daily and processes the previous Chilean business date.

Conceptually:

```text
                 ┌─ Purchase Orders API
                 │        ↓
Key Vault ──> ADF│     Landing
                 │        ↓
                 │    Bronze → Silver
                 │
                 └─ Licitaciones API
                          ↓
                       Landing
                          ↓
                     Bronze → Silver
                          │
             both branches succeeded
                          ↓
                        Gold
                          ↓
                  Dashboard Refresh
```

Purchase orders and licitaciones are processed in parallel.

Gold starts only after both branches finish successfully.

---

## Gold Layer

The Gold layer exposes business-ready monthly aggregates.

### Monthly Purchase Orders

```text
chilecompra.gold.compras_mensuales
```

Metrics include:

- purchase-order count;
- total ordered amount in CLP;
- average order amount;
- distinct suppliers;
- distinct public organizations.

### Purchase Orders by Organization

```text
chilecompra.gold.ordenes_por_organismo_mensual
```

Used to analyze procurement concentration by public organization.

### Purchase Orders by Supplier

```text
chilecompra.gold.ordenes_por_proveedor_mensual
```

Used to analyze supplier concentration and monthly procurement amounts.

### Licitaciones by Closing Month and State

```text
chilecompra.gold.licitaciones_por_mes_cierre_estado
```

Groups the currently observed licitaciones using their closing month and current state.

This dataset should **not** be interpreted as historical state-transition tracking because Silver stores the latest observed licitacion state rather than an SCD history.

### Purchase Order / Licitacion Relationship

```text
chilecompra.gold.oc_licitaciones_mensual
```

Measures:

- total purchase orders;
- orders containing a licitacion code;
- orders without a licitacion code;
- API matches where temporal coverage allows it;
- percentage of purchase orders associated with a licitacion.

Because historical purchase orders and API licitaciones have different temporal coverage, a low API match rate is not treated as a broken relationship.

---

## Analytics Dashboard

The project includes the version-controlled Databricks AI/BI dashboard:

```text
ChileCompra Analytics
```

It contains two pages.

### Purchase Orders

Includes:

- total purchase orders;
- total purchase-order amount;
- distinct suppliers;
- distinct public organizations;
- monthly order amount;
- monthly order count;
- Top 10 public organizations;
- Top 10 suppliers;
- interactive period filtering.

### Licitaciones

Includes:

- observed licitaciones;
- published licitaciones;
- awarded licitaciones;
- deserted licitaciones;
- licitaciones by state;
- licitaciones by closing month;
- monthly state composition;
- percentage of purchase orders containing a licitacion code;
- closing-month filtering.

The dashboard is automatically refreshed only after all Gold tasks complete successfully.

This keeps analytics synchronized with the final data layer without using an independent high-frequency refresh schedule.

---

## Security

Credentials are not embedded in notebooks or pipelines.

The platform uses:

- **Azure Key Vault** for the Mercado Público API credential;
- **Azure Data Factory Managed Identity** for service authentication;
- **Azure RBAC** for storage permissions;
- **Databricks Access Connector** instead of storage account keys;
- **Unity Catalog Storage Credentials and External Locations** for lakehouse access;
- `.gitignore` to prevent local secrets from being committed.

The architecture intentionally avoids storing API keys, storage account keys, or credentials in source code.

---

## Operational Behavior

The pipeline has been executed successfully through its automated daily trigger across multiple consecutive days.

Operational visibility is currently provided through:

- Azure Data Factory pipeline run history;
- Databricks Job run history;
- task-level status and dependencies;
- Data Quality failures propagated as task failures;
- dependency-based Gold execution;
- dashboard refresh only after successful Gold completion.

The project is being left operational for an observation period so that real failures, if they occur, can be analyzed and documented rather than artificially simulated.

---

## Cost-Aware Design

The project was designed under a limited Azure development budget.

Cost-conscious decisions include:

- batch instead of streaming;
- one daily incremental execution;
- Serverless Databricks compute;
- parallel Gold tasks;
- small Gold aggregate tables;
- dashboard refresh only after new Gold data is available;
- no unnecessary continuously running infrastructure.

A final cost summary will be documented after the operational observation period.

---

## Repository Structure

```text
chilecompra-data-platform/
│
├── adf/
│   ├── dataset/
│   ├── factory/
│   ├── linkedService/
│   ├── pipeline/
│   │   ├── pl_chilecompra_historial.json
│   │   └── pl_chilecompra_incremental.json
│   ├── trigger/
│   └── publish_config.json
│
├── databricks/
│   ├── setup/
│   │
│   ├── bronze/
│   │   ├── 01_load_oc_historical.ipynb
│   │   ├── 02_load_oc_api.ipynb
│   │   └── 03_load_licitaciones_api.ipynb
│   │
│   ├── silver/
│   │   ├── 01_transform_ordenes_compra.ipynb
│   │   ├── 02_transform_ordenes_compra_items.ipynb
│   │   ├── 03_transform_licitaciones_api.ipynb
│   │   └── 04_merge_ordenes_compra_api.ipynb
│   │
│   ├── gold/
│   │   ├── 01_compras_mensuales.ipynb
│   │   ├── 02_compras_mensuales_organismo.ipynb
│   │   ├── 03_ordenes_por_proveedor_mensual.ipynb
│   │   ├── 04_licitaciones_por_estado_mensual.ipynb
│   │   └── 05_oc_licitaciones_mensual.ipynb
│   │
│   └── Dashboard/
│       └── ChileCompra Analytics.lvdash.json
│
├── exploration/
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

---

## Key Engineering Decisions

### Batch instead of streaming

ChileCompra data does not require sub-minute processing, so a scheduled batch architecture provides lower complexity and cost while satisfying the business requirement.

### Historical and incremental sources are separated

Historical CSV files provide the initial dataset, while the API provides ongoing updates.

A clear temporal boundary prevents both sources from independently loading the same period.

### No inferred deletes

Absence from a later API response is not considered proof of deletion.

The Silver layer therefore follows an upsert-only strategy unless explicit delete semantics are available from the source.

### Idempotency over execution uniqueness

Landing preserves every execution using `run_id`, while lakehouse tables use deterministic `process_date` and business keys.

This provides both execution traceability and safe reruns.

### Full rebuild for small Gold tables

Gold aggregates are small compared with Silver and can be deterministically regenerated.

This reduces incremental-state complexity in the serving layer.

---

## Current Limitations

- Historical licitacion data is not available for the same period as historical purchase orders.
- Licitacion state transitions are not modeled as SCD history.
- API responses are mutable and do not provide complete CDC semantics.
- The current platform is optimized for batch analytical workloads rather than real-time processing.
- Infrastructure was provisioned manually rather than through Infrastructure as Code.

These limitations are deliberate and documented rather than hidden.

---

## Possible Future Improvements

Potential extensions include:

- Infrastructure as Code with Terraform or Bicep;
- Databricks Asset Bundles for deployment;
- historical licitacion backfill if a suitable source becomes available;
- SCD/event history for licitacion state transitions;
- centralized monitoring and alerting;
- automated data-quality metrics reporting;
- CI/CD validation for notebooks and ADF artifacts.

---

## What This Project Demonstrates

This project demonstrates practical experience with:

- Azure cloud data architecture;
- Data Lake design;
- Medallion Architecture;
- PySpark and Spark SQL;
- Delta Lake;
- incremental batch processing;
- idempotent pipelines;
- MERGE/upsert patterns;
- historical backfills;
- data-quality gates;
- DAG orchestration;
- parallel task execution;
- source-system analysis;
- cloud identity and secret management;
- Unity Catalog;
- analytics serving layers;
- dashboard automation;
- Git-based development.

---

## Author

**Nicolás Rojas**

Data Engineering portfolio project built using public ChileCompra / Mercado Público data.
