-- =============================================================================
-- ESQUEMA DE BASE DE DATOS POSTGRESQL 18 — RISA DATA V1.0
-- Proyecto: HealthSignal LATAM (Red Integrada de Salud Avanzada)
-- Propósito: Carga e integración de la base de datos original RISA V1.0
-- =============================================================================

-- Crear Esquema dedicado opcional (si se prefiere aislar del esquema public)
CREATE SCHEMA IF NOT EXISTS risa_raw;
SET search_path TO risa_raw, public;

-- -----------------------------------------------------------------------------
-- DOMINIO 01: TABLAS MAESTRAS (01_master)
-- -----------------------------------------------------------------------------

-- 1. Instaciones / Centros de Salud
CREATE TABLE IF NOT EXISTS healthcare_facilities (
    facility_id VARCHAR(50) PRIMARY KEY,
    facility_name VARCHAR(255) NOT NULL,
    facility_type VARCHAR(100) NOT NULL,
    region_type VARCHAR(50),
    digital_maturity VARCHAR(50),
    connectivity_profile VARCHAR(50),
    monitoring_capability VARCHAR(50),
    laboratory_capability VARCHAR(50)
);

COMMENT ON TABLE healthcare_facilities IS 'Catálogo maestro de instituciones y centros de salud de la red RISA';

-- 2. Pacientes
CREATE TABLE IF NOT EXISTS patients (
    patient_id VARCHAR(50) PRIMARY KEY,
    sex_at_birth VARCHAR(10),
    age_years INT,
    age_group VARCHAR(50),
    region_type VARCHAR(50),
    care_program VARCHAR(100),
    baseline_risk_profile VARCHAR(100),
    enrollment_date DATE,
    active BOOLEAN DEFAULT TRUE
);

COMMENT ON TABLE patients IS 'Registro maestro canónico de pacientes sintéticos RISA';
CREATE INDEX IF NOT EXISTS idx_patients_active ON patients(active);
CREATE INDEX IF NOT EXISTS idx_patients_care_program ON patients(care_program);

-- 3. Dispositivos y Monitores
CREATE TABLE IF NOT EXISTS devices (
    device_id VARCHAR(50) PRIMARY KEY,
    device_type VARCHAR(100) NOT NULL,
    manufacturer_class VARCHAR(100),
    model_family VARCHAR(100),
    measurement_domain VARCHAR(100),
    sampling_profile VARCHAR(100),
    reliability_class VARCHAR(50),
    facility_id VARCHAR(50) REFERENCES healthcare_facilities(facility_id) ON DELETE SET NULL,
    patient_assignment_type VARCHAR(50),
    active BOOLEAN DEFAULT TRUE,
    assigned_patient_id VARCHAR(50) REFERENCES patients(patient_id) ON DELETE SET NULL
);

COMMENT ON TABLE devices IS 'Monitores clínicos de cabecera y pulseras wearables';
CREATE INDEX IF NOT EXISTS idx_devices_assigned_patient ON devices(assigned_patient_id);
CREATE INDEX IF NOT EXISTS idx_devices_facility ON devices(facility_id);

-- 4. Encuentros / Episodios Clínicos
CREATE TABLE IF NOT EXISTS encounters (
    encounter_id VARCHAR(50) PRIMARY KEY,
    patient_id VARCHAR(50) NOT NULL REFERENCES patients(patient_id) ON DELETE CASCADE,
    facility_id VARCHAR(50) REFERENCES healthcare_facilities(facility_id) ON DELETE SET NULL,
    encounter_type VARCHAR(100) NOT NULL,
    start_datetime TIMESTAMP WITH TIME ZONE NOT NULL,
    end_datetime TIMESTAMP WITH TIME ZONE,
    care_setting VARCHAR(50),
    reason_category VARCHAR(100),
    source_system VARCHAR(100),
    status VARCHAR(50)
);

COMMENT ON TABLE encounters IS 'Episodios de hospitalización, observación o monitoreo en casa';
CREATE INDEX IF NOT EXISTS idx_encounters_patient ON encounters(patient_id);
CREATE INDEX IF NOT EXISTS idx_encounters_dates ON encounters(start_datetime, end_datetime);

-- -----------------------------------------------------------------------------
-- DOMINIO 02: HISTORIA CLÍNICA Y LABORATORIO (02_clinical)
-- -----------------------------------------------------------------------------

-- 5. Diagnósticos y Antecedentes
CREATE TABLE IF NOT EXISTS conditions (
    condition_id VARCHAR(50) PRIMARY KEY,
    patient_id VARCHAR(50) NOT NULL REFERENCES patients(patient_id) ON DELETE CASCADE,
    condition_category VARCHAR(100) NOT NULL,
    onset_date DATE,
    status VARCHAR(50),
    severity_context VARCHAR(100),
    source_system VARCHAR(100),
    recorded_datetime TIMESTAMP WITH TIME ZONE
);

COMMENT ON TABLE conditions IS 'Antecedentes patológicos y condiciones clínicas registradas';
CREATE INDEX IF NOT EXISTS idx_conditions_patient ON conditions(patient_id);

-- 6. Catálogo de Medicamentos
CREATE TABLE IF NOT EXISTS medications (
    medication_id VARCHAR(50) PRIMARY KEY,
    medication_class VARCHAR(100) NOT NULL,
    generic_category VARCHAR(100),
    administration_route VARCHAR(50)
);

COMMENT ON TABLE medications IS 'Catálogo maestro de clases farmacológicas';

-- 7. Administraciones de Medicamentos
CREATE TABLE IF NOT EXISTS medication_administrations (
    administration_id VARCHAR(50) PRIMARY KEY,
    patient_id VARCHAR(50) NOT NULL REFERENCES patients(patient_id) ON DELETE CASCADE,
    encounter_id VARCHAR(50) REFERENCES encounters(encounter_id) ON DELETE SET NULL,
    medication_id VARCHAR(50) REFERENCES medications(medication_id) ON DELETE SET NULL,
    start_datetime TIMESTAMP WITH TIME ZONE NOT NULL,
    end_datetime TIMESTAMP WITH TIME ZONE,
    dose_value NUMERIC(10, 4),
    dose_unit VARCHAR(50),
    administration_status VARCHAR(50),
    source_system VARCHAR(100)
);

COMMENT ON TABLE medication_administrations IS 'Eventos de administración de medicamentos a pacientes';
CREATE INDEX IF NOT EXISTS idx_med_admin_patient ON medication_administrations(patient_id);
CREATE INDEX IF NOT EXISTS idx_med_admin_encounter ON medication_administrations(encounter_id);
CREATE INDEX IF NOT EXISTS idx_med_admin_dates ON medication_administrations(start_datetime, end_datetime);

-- 8. Resultados de Laboratorio
CREATE TABLE IF NOT EXISTS laboratory_results (
    lab_result_id VARCHAR(50) PRIMARY KEY,
    patient_id VARCHAR(50) NOT NULL REFERENCES patients(patient_id) ON DELETE CASCADE,
    encounter_id VARCHAR(50) REFERENCES encounters(encounter_id) ON DELETE SET NULL,
    test_code VARCHAR(100) NOT NULL,
    test_name VARCHAR(255),
    result_value NUMERIC(12, 4),
    unit VARCHAR(50),
    reference_low NUMERIC(12, 4),
    reference_high NUMERIC(12, 4),
    sample_datetime TIMESTAMP WITH TIME ZONE NOT NULL,
    result_datetime TIMESTAMP WITH TIME ZONE NOT NULL,
    facility_id VARCHAR(50) REFERENCES healthcare_facilities(facility_id) ON DELETE SET NULL,
    source_system VARCHAR(100),
    quality_flag VARCHAR(50) DEFAULT 'OK'
);

COMMENT ON TABLE laboratory_results IS 'Resultados analíticos con semántica temporal (sample vs result datetime)';
CREATE INDEX IF NOT EXISTS idx_lab_patient ON laboratory_results(patient_id);
CREATE INDEX IF NOT EXISTS idx_lab_encounter ON laboratory_results(encounter_id);
CREATE INDEX IF NOT EXISTS idx_lab_result_datetime ON laboratory_results(result_datetime);
CREATE INDEX IF NOT EXISTS idx_lab_test_code ON laboratory_results(test_code);

-- -----------------------------------------------------------------------------
-- DOMINIO 03: MONITOREO Y TELEMETRÍA (03_monitoring)
-- -----------------------------------------------------------------------------

-- 9. Signos Vitales (Series Temporales Continuas / Periódicas)
CREATE TABLE IF NOT EXISTS vital_signs (
    observation_id VARCHAR(50) PRIMARY KEY,
    patient_id VARCHAR(50) NOT NULL REFERENCES patients(patient_id) ON DELETE CASCADE,
    encounter_id VARCHAR(50) REFERENCES encounters(encounter_id) ON DELETE SET NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    variable_code VARCHAR(50) NOT NULL,
    value NUMERIC(12, 4),
    unit VARCHAR(50),
    device_id VARCHAR(50) REFERENCES devices(device_id) ON DELETE SET NULL,
    source_system VARCHAR(100),
    quality_flag VARCHAR(50) DEFAULT 'OK'
);

COMMENT ON TABLE vital_signs IS 'Telemetría de signos vitales (HR, SpO2, RR, SBP, DBP, TEMP)';
CREATE INDEX IF NOT EXISTS idx_vitals_patient_ts ON vital_signs(patient_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_vitals_variable ON vital_signs(variable_code);
CREATE INDEX IF NOT EXISTS idx_vitals_device ON vital_signs(device_id);

-- 10. Observaciones de Wearables
CREATE TABLE IF NOT EXISTS wearable_observations (
    wearable_observation_id VARCHAR(50) PRIMARY KEY,
    patient_id VARCHAR(50) NOT NULL REFERENCES patients(patient_id) ON DELETE CASCADE,
    device_id VARCHAR(50) REFERENCES devices(device_id) ON DELETE SET NULL,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    variable_code VARCHAR(50) NOT NULL,
    value VARCHAR(100),
    unit VARCHAR(50),
    measurement_quality VARCHAR(50) DEFAULT 'OK',
    sync_datetime TIMESTAMP WITH TIME ZONE NOT NULL
);

COMMENT ON TABLE wearable_observations IS 'Series temporales de pulseras inteligentes con sync diferido';
CREATE INDEX IF NOT EXISTS idx_wearables_patient_ts ON wearable_observations(patient_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_wearables_sync ON wearable_observations(sync_datetime);
CREATE INDEX IF NOT EXISTS idx_wearables_variable ON wearable_observations(variable_code);

-- 11. Calidad de Señal y Dispositivo
CREATE TABLE IF NOT EXISTS device_observations (
    device_observation_id VARCHAR(50) PRIMARY KEY,
    patient_id VARCHAR(50) REFERENCES patients(patient_id) ON DELETE CASCADE,
    encounter_id VARCHAR(50) REFERENCES encounters(encounter_id) ON DELETE SET NULL,
    device_id VARCHAR(50) NOT NULL REFERENCES devices(device_id) ON DELETE CASCADE,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    variable_code VARCHAR(50) DEFAULT 'SIGNAL_QUALITY_INDEX',
    value NUMERIC(10, 4),
    unit VARCHAR(50) DEFAULT 'ratio',
    signal_quality NUMERIC(10, 4),
    source_system VARCHAR(100)
);

COMMENT ON TABLE device_observations IS 'Métricas de calidad de señal y telemetría de monitores';
CREATE INDEX IF NOT EXISTS idx_dev_obs_device_ts ON device_observations(device_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_dev_obs_patient ON device_observations(patient_id);

-- -----------------------------------------------------------------------------
-- DOMINIO 04: CONTEXTO Y CONECTIVIDAD (04_context)
-- -----------------------------------------------------------------------------

-- 12. Contexto de Paciente (Sueño / Actividad)
CREATE TABLE IF NOT EXISTS patient_context (
    context_id VARCHAR(50) PRIMARY KEY,
    patient_id VARCHAR(50) NOT NULL REFERENCES patients(patient_id) ON DELETE CASCADE,
    start_datetime TIMESTAMP WITH TIME ZONE NOT NULL,
    end_datetime TIMESTAMP WITH TIME ZONE NOT NULL,
    context_type VARCHAR(100) NOT NULL,
    context_value VARCHAR(100) NOT NULL,
    source VARCHAR(100),
    confidence NUMERIC(5, 2)
);

COMMENT ON TABLE patient_context IS 'Intervalos de estado contextual (ej. SLEEP_STATE, AWAKE)';
CREATE INDEX IF NOT EXISTS idx_context_patient_dates ON patient_context(patient_id, start_datetime, end_datetime);

-- 13. Eventos de Conectividad de Red
CREATE TABLE IF NOT EXISTS connectivity_events (
    event_id VARCHAR(50) PRIMARY KEY,
    device_id VARCHAR(50) REFERENCES devices(device_id) ON DELETE SET NULL,
    patient_id VARCHAR(50) REFERENCES patients(patient_id) ON DELETE CASCADE,
    start_datetime TIMESTAMP WITH TIME ZONE NOT NULL,
    end_datetime TIMESTAMP WITH TIME ZONE NOT NULL,
    connectivity_status VARCHAR(50) NOT NULL,
    delayed_records INT DEFAULT 0,
    packet_loss_estimate NUMERIC(5, 2) DEFAULT 0.0
);

COMMENT ON TABLE connectivity_events IS 'Incidentes de desconexión de red, retrasos y pérdida de paquetes';
CREATE INDEX IF NOT EXISTS idx_conn_patient_dates ON connectivity_events(patient_id, start_datetime, end_datetime);
CREATE INDEX IF NOT EXISTS idx_conn_device ON connectivity_events(device_id);

-- -----------------------------------------------------------------------------
-- DOMINIO 05: METADATOS Y CATÁLOGOS (05_metadata)
-- -----------------------------------------------------------------------------

-- 14. Diccionario de Datos
CREATE TABLE IF NOT EXISTS data_dictionary (
    file VARCHAR(255) NOT NULL,
    field VARCHAR(100) NOT NULL,
    type VARCHAR(50),
    key_role VARCHAR(50),
    description TEXT,
    PRIMARY KEY (file, field)
);

COMMENT ON TABLE data_dictionary IS 'Diccionario oficial de metadatos de los archivos de RISA';

-- 15. Catálogo de Fuentes
CREATE TABLE IF NOT EXISTS source_catalog (
    source_system VARCHAR(100) PRIMARY KEY,
    source_name VARCHAR(255) NOT NULL,
    source_type VARCHAR(50),
    update_frequency VARCHAR(50),
    interoperability_level VARCHAR(50),
    typical_latency VARCHAR(50),
    description TEXT
);

COMMENT ON TABLE source_catalog IS 'Sistemas de origen con latencias típicas y nivel de interoperabilidad';

-- 16. Catálogo de Unidades
CREATE TABLE IF NOT EXISTS units_catalog (
    unit_code VARCHAR(50) PRIMARY KEY,
    unit_name VARCHAR(100) NOT NULL,
    dimension VARCHAR(50),
    canonical_unit VARCHAR(50) NOT NULL,
    conversion_factor NUMERIC(12, 6) DEFAULT 1.0,
    conversion_offset NUMERIC(12, 6) DEFAULT 0.0
);

COMMENT ON TABLE units_catalog IS 'Unidades de medida con factores y offsets de conversión';

-- 17. Catálogo de Variables
CREATE TABLE IF NOT EXISTS variable_catalog (
    variable_code VARCHAR(50) PRIMARY KEY,
    variable_name VARCHAR(255) NOT NULL,
    domain VARCHAR(50) NOT NULL,
    canonical_unit VARCHAR(50),
    plausibility_min NUMERIC(12, 4),
    plausibility_max NUMERIC(12, 4),
    nominal_sampling VARCHAR(50),
    analysis_role VARCHAR(100)
);

COMMENT ON TABLE variable_catalog IS 'Catálogo de variables clínicas con rangos biológicos plausibles';
