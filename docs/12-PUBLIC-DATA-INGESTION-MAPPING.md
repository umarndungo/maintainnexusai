# Public Dataset Ingestion & Canonical Mapping

## Purpose

This document defines how external public predictive-maintenance datasets are ingested without pretending that they are KPC telemetry.

## Provenance rules

| Dataset | Provenance | Primary use | Target semantics |
|---|---|---|---|
| UCI AI4I 2020 | EXTERNAL_PUBLIC / synthetic benchmark | Generic failure-classification baseline and feature engineering | `machine_failure` at the recorded observation; **not** a 24-hour failure label |
| UCI Hydraulic Systems | EXTERNAL_PUBLIC / experimental test rig | Pump leakage + valve condition modelling and sensor feature engineering | Cycle-wise component condition; **not** a 24-hour failure label |
| KPC-style generated data | SYNTHETIC | End-to-end prototype, loading-arm coverage, operational automation simulation | `failure_within_24h` in the prototype generator only |
| Internal KPC telemetry (future) | INTERNAL | Production model training/validation | Must be defined from actual failure/maintenance timestamps |

## Canonical feature mapping

### AI4I 2020

| Source field | Canonical concept | Transformation | Limitation |
|---|---|---|---|
| Type | asset/product context | categorical encode | not a KPC equipment type |
| Air temperature | ambient/process context | K -> C optional | not necessarily depot ambient temperature |
| Process temperature | temperature | retain/convert | single process temperature |
| Rotational speed | rpm | rename | generic machine |
| Torque | load/torque | rename | no motor current/voltage |
| Tool wear | wear proxy | rename | not directly equivalent to maintenance age |
| Machine failure | `machine_failure` | binary target | observation-level failure, not 24h horizon |
| TWF/HDF/PWF/OSF/RNF | failure mode flags | preserve separately | benchmark-specific failure modes |

### UCI Hydraulic Systems

The dataset contains 2,205 cycles and raw multivariate sensor matrices. Pressures PS1–PS6 and motor power EPS1 are sampled at 100 Hz; flow FS1/FS2 at 10 Hz; temperatures TS1–TS4 and vibration VS1 at 1 Hz. The cycle-level profile contains valve condition, internal pump leakage and other component-condition labels. citeturn0search0

| Source | Canonical concept | Transformation |
|---|---|---|
| PS1–PS6 | pressure | per-cycle mean/std/min/max/slope |
| EPS1 | motor power | per-cycle mean/std/min/max |
| FS1–FS2 | flow | per-cycle mean/std/min/max |
| TS1–TS4 | temperature | per-cycle mean/std/min/max |
| VS1 | vibration | per-cycle mean/std/max/std |
| profile valve condition | `valve_condition` | preserve ordinal percentage |
| profile internal pump leakage | `pump_leakage_level` | preserve 0/1/2 |
| stable flag | `stable_flag` | preserve |

### Synthetic operational data

Synthetic data remains the only current source covering the combined KPC-style domain of pumps + loading arms + valves + truck schedules + loading points + spare parts. It is explicitly labelled `SYNTHETIC` and must never be presented as historical KPC telemetry.

## Target separation

Do not force every dataset into `failure_within_24h`.

- `failure_within_24h`: only use where an actual future failure horizon can be established.
- `machine_failure`: AI4I benchmark target.
- `valve_condition`: hydraulic benchmark target.
- `pump_leakage_level`: hydraulic benchmark target.
- `failure_event`: synthetic prototype event label.

This prevents target leakage and avoids claiming that a cycle-level condition label represents a future failure horizon.
