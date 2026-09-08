# Operación, Observabilidad y Costos

Este documento describe cómo se opera **ChileCompra Data Platform**, cómo se monitorean sus ejecuciones y cómo se realizan reruns y backfills ante reprocesamientos o fallos.

---

## 1. Operación diaria

La plataforma ejecuta automáticamente un pipeline incremental diario.

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
Dashboard Refresh
```

Azure Data Factory actúa como orquestador principal, mientras que Databricks Jobs ejecuta las transformaciones del lakehouse.

El trigger procesa la información correspondiente al **día anterior en horario de Chile**.

---

## 2. Fecha lógica de procesamiento

Cada ejecución incremental recibe el parámetro:

```text
process_date
```

Este valor representa la fecha lógica que debe procesarse y es independiente de la fecha física en que se ejecuta el pipeline.

Ejemplo:

```text
Ejecución:    2026-09-08
process_date: 2026-09-07
```

Esta separación permite repetir fechas anteriores sin modificar notebooks ni pipelines.

---

## 3. Reruns

Una fecha puede volver a ejecutarse utilizando el mismo:

```text
process_date
```

Cada ejecución de Azure Data Factory genera un nuevo:

```text
run_id
```

Por lo tanto:

```text
misma process_date
+
nuevo run_id
```

Landing conserva cada ejecución física para mantener trazabilidad.

Las capas posteriores utilizan estrategias idempotentes para evitar duplicar el estado lógico de los datos.

---

## 4. Backfills

El mismo diseño permite reprocesar fechas anteriores manualmente.

Por ejemplo:

```text
process_date = 2026-09-03
```

Esto permite recuperar:

- ejecuciones fallidas;
- días omitidos;
- fechas que requieran reprocesamiento.

La carga histórica dispone además de un pipeline independiente parametrizado por año y mes.

---

## 5. Idempotencia operacional

Cada capa utiliza una estrategia diferente.

### Landing

Cada ejecución se conserva mediante `run_id`.

```text
process_date=YYYY-MM-DD/
└── run_id=<ADF_RUN_ID>/
```

### Bronze

Las cargas incrementales reemplazan de forma determinística los datos correspondientes a la `process_date`.

Esto permite repetir una fecha sin acumular duplicados.

### Silver

Las entidades incrementales se consolidan mediante Delta Lake `MERGE`.

Las reglas de freshness evitan que una ejecución antigua sobrescriba información más reciente.

### Gold

Las tablas analíticas se reconstruyen desde Silver.

Dado que su volumen es pequeño en comparación con las capas anteriores, esta estrategia mantiene el procesamiento simple y determinístico.

---

## 6. Observabilidad operacional

Actualmente la plataforma utiliza principalmente las capacidades nativas de:

```text
Azure Data Factory Monitor
Databricks Jobs
Logs de Tasks
Data Quality Checks
```

No se implementó una plataforma externa o centralizada de observabilidad como Azure Monitor o Log Analytics.

### Azure Data Factory

ADF permite revisar:

- estado de cada pipeline;
- duración de ejecuciones;
- actividades ejecutadas;
- parámetros;
- errores;
- historial del trigger diario.

Esto permite observar el flujo completo de orquestación.

### Databricks Jobs

Databricks permite revisar:

- estado del Job;
- estado de cada Task;
- duración;
- dependencias;
- logs;
- excepciones.

De esta forma es posible identificar en qué etapa ocurrió un problema:

```text
Bronze
Silver
Gold
Dashboard
```

---

## 7. Data Quality como mecanismo de control

Los controles de Data Quality forman parte del comportamiento operacional del pipeline.

Se validan condiciones críticas como:

- claves naturales nulas;
- duplicados inesperados;
- estados no reconocidos;
- relaciones inválidas entre entidades;
- discrepancias de conteos.

Ante una violación crítica, el notebook genera una excepción.

Ejemplo conceptual:

```python
if critical_error:
    raise ValueError("Data Quality check failed")
```

El fallo se propaga por la cadena de ejecución:

```text
Data Quality Failure
        ↓
Databricks Task Failed
        ↓
Databricks Job Failed
        ↓
ADF Activity Failed
```

Esto evita continuar hacia capas posteriores con datos que no cumplen los contratos definidos.

---

## 8. Dependencias del pipeline

Órdenes de compra y licitaciones se procesan mediante ramas independientes.

```text
Órdenes de Compra ─────┐
                       ├── Gold
Licitaciones ──────────┘
```

Gold comienza únicamente cuando ambas ramas terminan correctamente.

Dentro del Gold Job existen cinco transformaciones independientes que se ejecutan en paralelo.

```text
Gold 1 ─┐
Gold 2 ─┤
Gold 3 ─┤
Gold 4 ─┤
Gold 5 ─┘
         ↓
Dashboard Refresh
```

El dashboard se actualiza únicamente después de que todas las transformaciones Gold finalizan exitosamente.

---

## 9. Recuperación ante fallos

La estrategia de recuperación depende de la etapa donde ocurra el problema.

### Extracción o Landing

Se vuelve a ejecutar la misma `process_date`.

El nuevo `run_id` conserva la nueva ejecución sin eliminar la anterior.

### Bronze

La fecha puede reprocesarse nuevamente.

La partición correspondiente a `process_date` se reemplaza de forma determinística.

### Silver

El `MERGE` puede ejecutarse nuevamente sin duplicar las entidades.

Las reglas de freshness evitan que datos antiguos reemplacen versiones más recientes.

### Gold

Las tablas pueden reconstruirse nuevamente desde Silver.

### Dashboard

Si solamente falla el refresh del dashboard, los datos Gold permanecen disponibles y el refresh puede volver a ejecutarse.

---

## 10. Estado operacional

El pipeline incremental se encuentra automatizado y actualmente está siendo ejecutado diariamente durante un período de observación.

Hasta el momento se han observado múltiples ejecuciones automáticas exitosas.

No se establece un SLA ni se asume confiabilidad de largo plazo a partir de este período limitado de pruebas.

---

## 11. Evidencia operacional

Al finalizar el período de observación se incorporarán capturas como:

```text
docs/images/
├── adf-run-history.png
├── gold-job.png
└── dashboard-refresh.png
```

Estas capturas buscarán demostrar:

- ejecuciones automáticas consecutivas;
- estado del pipeline en ADF;
- DAG de Databricks Jobs;
- transformaciones Gold en paralelo;
- refresh automático del dashboard.

---

## 12. Costos

La arquitectura fue diseñada considerando un presupuesto limitado de desarrollo.

Las principales decisiones orientadas al control de costos fueron:

- procesamiento batch diario;
- ausencia de streaming;
- Databricks Serverless;
- ausencia de clusters permanentemente activos;
- transformaciones Gold pequeñas;
- refresh del dashboard una vez finalizado Gold;
- evitar componentes que no aportaran valor al caso de uso.

### Costo final

> Pendiente de completar al finalizar el período de observación.

Se documentará el consumo real observado en Azure y Databricks una vez finalizada la ejecución continua del proyecto.

---

## 13. Incidentes

Durante el período de observación se documentarán únicamente incidentes que ocurran realmente.

Si aparece alguno, se registrará utilizando la siguiente estructura:

```text
Síntoma
   ↓
Diagnóstico
   ↓
Causa raíz
   ↓
Solución
   ↓
Prevención
```

No se simularán incidentes únicamente con fines de documentación.

---

## Pendientes antes del cierre

Al finalizar el período de observación se actualizará este documento con:

- cantidad de días observados;
- cantidad de ejecuciones automáticas;
- ejecuciones exitosas y fallidas;
- incidentes reales, si existen;
- costo final;
- capturas de observabilidad;
- conclusiones operacionales.
