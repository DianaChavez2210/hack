

HealthSignal LATAM | Hackathon Internacional | ParticipantesPagina 1
## HACKATHON INTERNACIONAL - NIVEL AVANZADO
## HEALTHSIGNAL LATAM
Guia tecnica oficial del participante - RISA Data V1.0
Entidad retadora: Talento TECH
Escenario: Red Integrada de Salud Avanzada - RISA (ficticia)
Dataset: RISA Data V1.0
Reto: HealthSignal LATAM - Anticiparse al riesgo

HealthSignal LATAM | Hackathon Internacional | ParticipantesPagina 2
Proposito del documento
Esta guia acompana el desafio oficial y el dataset RISA Data V1.0. Define el escenario, la logica de los datos, las
dificultades tecnicas, las capacidades que debe demostrar la solucion, la estructura de entrega y las reglas de
trazabilidad. No contiene respuestas de evaluacion, Gold Standard ni casos ocultos.
Principio central
Transformar datos heterogeneos de salud en senales oportunas y priorizadas, sustentadas en evidencia disponible en
el momento de decision, robustas frente a calidad y contexto, y trazables hasta los registros fuente.
- Escenario RISA y problema operativo
## •
RISA es una red de salud ficticia latinoamericana que integra hospital de mayor complejidad, clinica especializada,
atencion primaria, monitoreo domiciliario, laboratorios y telemonitoreo.
## •
El problema no es la ausencia de datos, sino su fragmentacion, heterogeneidad, frecuencia variable, latencia y
calidad desigual.
## •
La pregunta operativa es: como reconocer a tiempo que una combinacion de datos merece atencion, sin convertir
cada variacion en una alerta.
## •
Todos los pacientes y registros son sinteticos; no representan personas reales.
- Arquitectura conceptual de RISA Data V1.0
## •
La data combina maestros, informacion clinica, observaciones fisiologicas, wearables, laboratorio, contexto,
dispositivos y conectividad.
## •
Las fuentes no necesariamente comparten granularidad ni frecuencia. Los equipos deben reconstruir la historia
temporal del paciente a partir de multiples tablas.
## •
Los identificadores originales deben conservarse para permitir joins, auditoria y trazabilidad.
## •
Los catalogos de variables, unidades y fuentes deben revisarse antes de modelar.
- Semantica temporal y operacional
## •
Debe distinguirse entre el momento en que ocurre un evento y el momento en que la informacion esta disponible
para el sistema.
## •
En laboratorio, la muestra puede existir antes de que el resultado este disponible; en wearable, la observacion puede
sincronizarse despues.
## •
Para una decision en T solo puede utilizarse informacion con T_available <= T.
## •
Una buena solucion diferencia timeline fisiologico y timeline operacional cuando sea pertinente.
- Calidad de datos, temporalidad y trampas tecnicas
## •
RISA no es un dataset perfectamente limpio por diseno. La limpieza forma parte del problema analitico.
## •
El equipo debe considerar missingness, ruido/artefactos, duplicados/retransmisiones, unidades, calidad de senal,
contexto y desalineacion temporal.
## •
Missing no equivale a cero ni a normal. La imputacion debe ser defendible y debe diferenciar dato observado de dato
estimado.
## •
Un outlier no equivale automaticamente a riesgo: debe contrastarse con persistencia, contexto, calidad, historico y
otras variables.
## •
Debe evitarse temporal leakage tanto en features como en baselines y validacion.
- Estrategia tecnica recomendada

HealthSignal LATAM | Hackathon Internacional | ParticipantesPagina 3
## •
Ruta sugerida: comprender -> ingerir -> validar -> normalizar -> ordenar temporalmente -> contextualizar -> construir
evidencia -> detectar -> priorizar -> explicar -> validar.
## •
No es obligatorio cargar todo simultaneamente. Es valido desarrollar primero un pipeline correcto sobre una muestra
y luego escalarlo.
## •
Se recomienda separar RAW, CLEAN, FEATURES y MODEL para preservar auditabilidad.
## •
Las features pueden incluir agregaciones, pendientes, persistencia, desviaciones respecto al baseline, contexto y
calidad.
## •
RISA no impone machine learning: reglas, estadistica, ML, deep learning, modelos temporales o sistemas hibridos
son validos si estan justificados.
- Capacidades que debe demostrar la solucion
## •
Deteccion: identificar senales relevantes, no solo valores fuera de rango.
## •
Anticipacion: producir una decision en un momento util sin utilizar informacion futura.
## •
Priorizacion: ordenar pacientes/senales de forma operativa y justificar por que A esta antes que B.
## •
Explicabilidad y trazabilidad: mostrar que ocurrio, cuando, con que evidencia y por que se asigno esa prioridad.
## •
Robustez: gestionar razonablemente ruido, missingness, calidad, contexto, latencias y heterogeneidad.
## •
Resultado observable: el evaluador debe poder inspeccionar paciente, momento, prioridad/score, evidencia y
explicacion.
- Requisitos tecnicos de entrega
## •
Componentes obligatorios: solucion funcional; codigo fuente o artefacto ejecutable; README.md; results/signals.csv;
results/evidence.csv; arquitectura tecnica de maximo 5 paginas; dependencias/configuracion reproducible.
## •
Debe existir un punto de entrada claro y las rutas de datos no deben depender de una ruta rigida del computador del
participante.
## •
Los CSV de salida deben ser UTF-8, separados por coma y corresponder a la misma version final de la solucion.
## •
El pitch final no forma parte de la metrica tecnica oficial.
- Evidencia, explicabilidad y trazabilidad
## •
La cadena esperada es dato -> evidencia -> senal -> prioridad -> explicacion, manteniendo tambien la ruta inversa
para auditoria.
## •
Cada senal debe vincularse con evidencia concreta. La evidencia puede tener rol PRIMARY, SUPPORTING,
CONTEXT o QUALITY.
## •
Las features derivadas son validas, pero las senales importantes deben poder trazarse razonablemente hacia
registros originales.
## •
Los LLM pueden transformar evidencia estructurada en explicaciones, pero no inventar hechos, mediciones ni
antecedentes.
## •
Una explicacion fuerte conecta comportamiento observado, tiempo, contexto, calidad y decision.
- Reglas de uso y limites
## •
Los archivos oficiales de RISA Data V1.0 se consideran inmutables. Pueden crearse copias, bases derivadas,
Parquet, features, indices o embeddings.
## •
Modelos preentrenados, APIs y servicios externos pueden utilizarse si las reglas generales del evento lo permiten y
su funcion se documenta.
## •
El reto no exige diagnostico ni prescripcion. La solucion apoya identificacion, priorizacion y revision.

HealthSignal LATAM | Hackathon Internacional | ParticipantesPagina 4
## •
El Gold Standard, casos CORE, hard negatives oficiales, ventanas y rankings esperados son confidenciales.
## •
No existe numero obligatorio de senales, pacientes prioritarios, threshold oficial ni algoritmo obligatorio.
## •
La entrega final debe ser reproducible y los resultados estructurados deben provenir del pipeline presentado.
7.1 Esquema oficial de signals.csv
CampoOblig.Regla principal
signal_idSiIdentificador unico de la senal
patient_idSiID existente en RISA
decision_datetimeSiInstante en que existe evidencia suficiente
risk_scoreSiNumerico entre 0 y 1
priority_levelSiLOW / MEDIUM / HIGH / CRITICAL
confidence_scoreNoSi se usa, entre 0 y 1
evidence_startSiInicio de ventana principal
evidence_endSiFin de ventana; <= decision_datetime
explanationSiJustificacion breve y verificable
model_versionSiVersion que produjo el resultado
7.2 Esquema oficial de evidence.csv
CampoOblig.Regla principal
signal_idSiFK hacia signals.csv
source_fileSiArchivo fuente de RISA
record_idSiIdentificador original del registro
variable_codeNoVariable relacionada cuando aplique
event_datetimeSiMomento del fenomeno
available_datetimeSiMomento en que la evidencia estaba disponible
evidence_roleSiPRIMARY / SUPPORTING / CONTEXT / QUALITY
contributionNoPeso o contribucion documentada
- Checklist final del participante
## •
[ ] Uso la version oficial de RISA Data V1.0 y conservo IDs originales.
## •
[ ] Revise unidades, missingness, duplicados, calidad y heterogeneidad temporal.
## •
[ ] Mi pipeline evita temporal leakage y no usa evidencia disponible despues de decision_datetime.
## •
[ ] Cada senal tiene score, prioridad, ventana, explicacion, version y evidencia asociada.
## •
[ ] Cada available_datetime de evidence.csv es menor o igual al decision_datetime de su senal.
## •
[ ] Puedo explicar por que un paciente aparece antes que otro.
## •
[ ] Existe una solucion funcional y un punto de entrada claro.
## •
[ ] README, dependencias, arquitectura, signals.csv y evidence.csv estan completos.
## •
[ ] Ejecute validate_submission.py y el formato finaliza sin errores.
## •
[ ] Una persona ajena al desarrollo puede comprender que paciente priorizamos, cuando, por que y con que
evidencia.

HealthSignal LATAM | Hackathon Internacional | ParticipantesPagina 5
Regla de cierre
Si un evaluador no puede ejecutar, reconstruir o verificar una senal, esa senal no esta completamente demostrada.