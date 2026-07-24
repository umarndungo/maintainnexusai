# MaintainNexus ETL Pipeline Overview

MaintainNexus demonstrates a practical, automated ETL foundation for ingesting and operationalizing noisy maintenance data. The solution is designed to accept raw equipment signals, apply basic quality control, enrich those signals with contextual data, and transform them into actionable work-order dispatch decisions.

The implemented flow is:

1. Ingest raw maintenance alerts
2. Validate the minimum required field structure and severity rules
3. Enrich the alert with inventory and technician context
4. Transform the result into a dispatchable work order
5. Load the work order into the operational system
6. Persist audit records so the data path remains traceable and documented

## 1. Ingesting noisy operational inputs

Operational alert data enters the system through the FastAPI maintenance ingestion endpoint:

- `POST /api/v1/alerts/maintenance`
- Implemented in `api/maintenance.py`

The API accepts alert payloads containing fields such as:

- `equipment_id`
- `part_number`
- `severity`
- `failure_code`
- `risk_probability`
- `telemetry`

On ingestion, each alert is assigned a unique `task_id` and written to the audit log. This preserved record ensures that even messy or incomplete upstream inputs remain traceable and auditable within the platform.

## 2. Cleaning through basic validation rules

The first ETL safeguard is a lightweight validation gate in `etl/validate.py`.

The validation layer enforces the following rules:

- required keys must be present and non-empty
- `severity` must be one of `HIGH`, `CRITICAL`, or `MEDIUM`

If an alert fails these checks, the pipeline halts early and logs the rejection. This is the core cleaning layer used to remove malformed or incomplete operational inputs before the system spends downstream resources on them.

## 3. Documenting the flow

The system documents the ETL lifecycle through a combination of repository documentation and module-level implementation structure:

- `README.md` provides the overall product and architecture summary
- `pipeline.md` provides the end-to-end ETL explanation
- the ETL modules are documented in code and separated by responsibility

The modular design is intentionally clear:

- `etl/extract.py` retrieves contextual data from inventory and technician services
- `etl/validate.py` applies the minimum quality checks
- `etl/transform.py` assembles the work-order payload
- `etl/load.py` dispatches the payload to the downstream work-order API
- `etl/pipeline.py` orchestrates the complete sequence

This modularity makes the data flow understandable, maintainable, and easy to extend.

## 4. Automating the process with a scheduler and pipeline orchestration

The automation layer is implemented using Celery and task orchestration:

- `tasks.py` defines the alert-processing task entry point
- the scheduler is used to enqueue sample or recurring maintenance jobs
- `process_alert_pipeline()` coordinates the full ETL lifecycle in a single, repeatable execution path

### End-to-end automated sequence

1. A raw alert is accepted by the API.
2. The alert is persisted in `audit_logs` with its generated `task_id`.
3. Celery queues the processing task asynchronously.
4. The worker runs the validation, extraction, transformation, and loading stages.
5. Inventory availability is checked for the required replacement part.
6. A certified technician is queried from the HR/technician service.
7. The alert and technician context are transformed into a work-order payload.
8. The work order is dispatched and correlated back to its originating alert using `alert_task_id`.

## 5. Data lineage and correlation

One of the key integration features is event correlation. The system carries `alert_task_id` through the ETL workflow and persists it inside the `work_orders` table.

This provides a lightweight but meaningful lineage mechanism:

- the original alert can be traced from ingestion to downstream action
- the created work order can be tied back to the alert that triggered it

## 6. Operational outcome

The result is a structured operational workflow that converts noisy sensor or maintenance input into a more actionable dispatch process:

- malformed or incomplete input is rejected early
- valid alerts are enriched with inventory and technician context
- the output is a clean, auditable, and traceable work-order dispatch record

## 7. Delivery statement

The current implementation successfully delivers a clean, documented, and automated ETL foundation for predictive maintenance operations. It demonstrates the core components expected of an operational ETL workflow:

- ingestion of noisy domain inputs
- basic data cleaning through validation
- documented flow across modular ETL stages
- orchestration through automated background task execution and scheduling

This provides a solid baseline for further refinement into a more comprehensive enterprise-grade ETL system with deeper normalization, richer data quality checks, and more advanced lineage and observability controls.
