# Decisiones de Ingeniería

Este documento resume las principales decisiones técnicas tomadas durante el desarrollo de **ChileCompra Data Platform** y el razonamiento detrás de cada una.

---

## 1. Batch en lugar de streaming

La plataforma utiliza procesamiento **batch diario**.

### Motivo

Los datos de ChileCompra no requieren latencia de segundos o minutos. El objetivo principal es mantener información actualizada diariamente.

Elegir streaming habría agregado:

- mayor complejidad operacional;
- más componentes;
- mayor costo;
- necesidad de administrar procesamiento continuo.

Para este caso, un pipeline batch diario satisface el requerimiento con menor complejidad.

---

## 2. Separar carga histórica e incremental

Se utilizan dos estrategias de ingesta:

```text
Histórico
→ archivos CSV masivos

Incremental
→ API Mercado Público
```

### Motivo

Los archivos masivos son apropiados para construir el estado histórico inicial, mientras que la API permite continuar incorporando información diariamente.

Se definió una frontera temporal clara para evitar que ambas fuentes procesen el mismo período de forma independiente.

---

## 3. Landing conserva todas las ejecuciones

La Landing Zone utiliza:

```text
process_date
run_id
```

Ejemplo:

```text
process_date=2026-09-01/
    run_id=<ADF_RUN_ID>/
```

### Motivo

`process_date` representa qué fecha lógica se está procesando.

`run_id` identifica una ejecución física específica.

Esto permite realizar varias ejecuciones de una misma fecha sin perder evidencia del dato recibido originalmente.

La trazabilidad de ejecución se conserva en Landing, mientras el lakehouse mantiene un estado lógico determinístico.

---

## 4. Idempotencia como requisito del pipeline

El pipeline fue diseñado para que una misma fecha pueda procesarse nuevamente sin generar duplicados.

Esto permite:

- reruns;
- recuperación ante fallos;
- backfills;
- reprocesamiento manual.

### Bronze

Los datos incrementales utilizan reemplazo determinístico de la partición correspondiente a `process_date`.

### Silver

Las entidades se consolidan mediante `MERGE`.

### Gold

Las tablas se reconstruyen desde Silver.

El objetivo es que:

```text
ejecutar dos veces la misma fecha
≈
mismo estado final
```

---

## 5. No asumir CDC donde no existe

La API de Mercado Público es mutable, pero no entrega eventos explícitos de:

```text
INSERT
UPDATE
DELETE
```

Por este motivo no se implementó CDC tradicional.

### Decisión

La ausencia de una entidad en una respuesta posterior de la API **no se interpreta como eliminación**.

Se utiliza una estrategia de:

```text
upsert-only
```

Una entidad nueva se inserta y una versión más reciente puede actualizar la existente.

### Motivo

Eliminar registros únicamente porque dejaron de aparecer en una consulta podría provocar pérdida de datos válidos.

---

## 6. Freshness antes de actualizar Silver

Cuando una entidad ya existe en Silver, una nueva versión de la API solo debe reemplazarla si realmente es más reciente.

Para esto se utilizan metadatos como:

```text
process_date
source_created_at
ingestion_timestamp
```

### Motivo

Una ejecución tardía o un backfill no debería sobrescribir accidentalmente una versión más nueva ya almacenada.

---

## 7. MERGE en Silver

Silver representa el estado consolidado de las entidades.

Se utiliza Delta Lake `MERGE` porque permite:

```text
MATCHED     → UPDATE
NOT MATCHED → INSERT
```

### Motivo

Esto simplifica la incorporación incremental y mantiene una sola entidad consolidada por clave de negocio.

Además permite implementar reglas de freshness antes de actualizar.

---

## 8. Duplicados no siempre significan mala calidad

Durante el análisis de la API de licitaciones se encontraron códigos repetidos dentro de una misma respuesta.

Inicialmente podría parecer un error de calidad.

Sin embargo, el análisis mostró que estos duplicados podían representar registros legítimos con diferencias en atributos como la fecha de cierre.

### Decisión

No se impuso unicidad en Bronze para licitaciones.

En cambio:

```text
Bronze
→ conserva comportamiento de la fuente

Silver
→ selecciona versión representativa por código
```

### Motivo

Una regla de Data Quality debe basarse en el contrato real de la fuente, no en una suposición.

---

## 9. Data Quality antes y después de escribir

Se implementaron validaciones en dos etapas.

### Pre-write

Valida que el dataset que será escrito cumpla condiciones críticas.

Ejemplos:

- claves no nulas;
- ausencia de duplicados inesperados;
- estados reconocidos;
- relaciones válidas.

### Post-write

Comprueba que la escritura produjo el resultado esperado.

### Motivo

Una transformación puede ser correcta antes de escribir, pero fallar durante una operación de persistencia o `MERGE`.

Validar ambos lados entrega una garantía más fuerte.

---

## 10. Fallar ante errores críticos

Las violaciones críticas de Data Quality generan:

```python
raise ValueError(...)
```

Esto provoca el fallo de la tarea Databricks.

El error se propaga hacia:

```text
Databricks Job
      ↓
Azure Data Factory
```

### Motivo

Un pipeline no debería continuar produciendo Gold o refrescando dashboards si una capa previa contiene datos inválidos.

---

## 11. Silver como estado consolidado

Silver no fue diseñado como histórico completo de cambios.

Por ejemplo:

```text
silver.licitaciones
```

representa la última versión conocida de cada licitación.

### Consecuencia

No es posible reconstruir desde Silver todas las transiciones históricas de estado.

Para eso sería necesario implementar:

- snapshots;
- SCD Type 2;
- o una tabla de eventos/historial.

### Motivo

Ese nivel de historial no era necesario para los objetivos actuales del proyecto y habría aumentado considerablemente el alcance.

---

## 12. Gold reconstruido completamente

Las tablas Gold se generan mediante overwrite desde Silver.

### Motivo

Gold contiene agregaciones mucho más pequeñas que las capas anteriores.

Implementar lógica incremental adicional habría aumentado la complejidad sin entregar un beneficio significativo.

Para este volumen:

```text
reconstrucción completa
```

es simple, determinística y suficientemente eficiente.

---

## 13. Gold en paralelo

Las cinco transformaciones Gold no dependen entre sí.

Por esta razón se ejecutan en paralelo dentro del mismo Databricks Job.

```text
Gold 1 ─┐
Gold 2 ─┤
Gold 3 ─┤
Gold 4 ─┤
Gold 5 ─┘
         ↓
 Dashboard
```

### Motivo

Agregar dependencias secuenciales artificiales aumentaría el tiempo total del pipeline.

La única dependencia necesaria es que todas terminen correctamente antes de actualizar el dashboard.

---

## 14. ADF como orquestador externo

Azure Data Factory coordina el flujo general y Databricks Jobs gestiona las transformaciones internas.

### Separación de responsabilidades

```text
ADF
→ fuentes
→ secretos
→ Landing
→ ejecución de workloads
→ dependencias entre dominios

Databricks Jobs
→ Bronze
→ Silver
→ Gold
→ dashboard
```

### Motivo

ADF es adecuado para integrar servicios externos y Azure, mientras Databricks es el entorno natural para procesamiento Spark y Delta.

---

## 15. Managed Identity en lugar de credenciales

Se evitó utilizar:

- storage account keys;
- credenciales embebidas;
- secretos escritos directamente en notebooks.

Se utilizaron:

```text
Azure Key Vault
Managed Identity
RBAC
Databricks Access Connector
Unity Catalog
```

### Motivo

Las identidades administradas reducen el manejo manual de credenciales y representan una arquitectura más cercana a un entorno productivo.

---

## 16. Serverless compute

Los Jobs Databricks utilizan compute Serverless.

### Motivo

Para este workload permite:

- evitar administración de clusters;
- reducir tiempos de provisión;
- simplificar la operación;
- pagar principalmente por el compute utilizado durante las ejecuciones.

No se requieren configuraciones especiales que justifiquen clusters clásicos.

---

## 17. Refresh del dashboard dependiente de Gold

El dashboard no utiliza un schedule independiente.

El flujo es:

```text
Gold exitoso
      ↓
Dashboard Task
      ↓
Refresh
```

### Motivo

Un refresh basado solo en horario podría ejecutarse mientras Gold todavía está procesándose o después de un fallo.

Al hacerlo dependiente del Job, el dashboard solo se actualiza cuando los datos están listos.

---

## 18. Diseño consciente de costos

El proyecto fue desarrollado bajo un presupuesto limitado.

Se evitaron componentes innecesarios como:

- streaming continuo;
- clusters permanentemente activos;
- refreshes frecuentes;
- pipelines duplicados.

La arquitectura prioriza:

```text
simplicidad
automatización
costo controlado
capacidad de recuperación
```

---

## Conclusión

Las decisiones del proyecto no buscan maximizar la cantidad de tecnologías utilizadas.

El objetivo fue construir una arquitectura que pudiera defenderse bajo criterios de:

```text
correctitud
idempotencia
trazabilidad
mantenibilidad
seguridad
costo
```

y que pudiera evolucionar posteriormente si aumentaran el volumen, la frecuencia o los requerimientos del sistema.
