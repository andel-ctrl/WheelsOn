// ==============================================================================
// WheelsOn - Datos iniciales del grafo (Neo4j 5.x)
// ==============================================================================
// Este script es la UNICA fuente de datos de ejemplo: la app no trae datos propios.
//
// Requisito: ejecutar antes scripts/init_db.cypher (restricciones e indices).
// Para recargar desde cero, descomenta la limpieza del paso 1.
//
// Todos los usuarios de ejemplo tienen la contrasena: WheelsOn2026*
//
// Las fechas se guardan como texto ISO (AAAA-MM-DD) porque es el formato con el
// que neomodel, el ORM de la app, lee y escribe sus propiedades de tipo fecha.

// 1. Limpieza opcional
// MATCH (n) DETACH DELETE n;


// 2. Usuarios
CREATE (:Usuario {uid: "usr_carlos001", nombre: "Carlos", apellido: "Calabria", email: "carlos@wheelson.com", password_hash: "pbkdf2_sha256$1500000$Ef7e8qk0uV6rF4POSxkisx$FOa8FWls+ZRN+6eZuC+8w62sP2qudem3NppGhjfNorc=", titulo_profesional: "Senior Backend & Graph Engineer", ubicacion: "Bogota, Colombia", biografia: "Especialista en bases de datos de grafos, modelado Cypher y arquitectura distribuida en Python.", fecha_registro: "2026-10-01"});
CREATE (:Usuario {uid: "usr_angelo002", nombre: "Angelo", apellido: "Caneda", email: "angelo@wheelson.com", password_hash: "pbkdf2_sha256$1500000$Ef7e8qk0uV6rF4POSxkisx$FOa8FWls+ZRN+6eZuC+8w62sP2qudem3NppGhjfNorc=", titulo_profesional: "Senior Backend & Distributed Systems", ubicacion: "Medellin, Colombia", biografia: "Ingeniero backend enfocado en microservicios de alto rendimiento, concurrencia y FastAPI.", fecha_registro: "2026-10-05"});
CREATE (:Usuario {uid: "usr_dubal003", nombre: "Dubal", apellido: "Aguilar", email: "dubal@wheelson.com", password_hash: "pbkdf2_sha256$1500000$Ef7e8qk0uV6rF4POSxkisx$FOa8FWls+ZRN+6eZuC+8w62sP2qudem3NppGhjfNorc=", titulo_profesional: "Data Architect & Big Data Specialist", ubicacion: "Barranquilla, Colombia", biografia: "Arquitecto de datos especializado en pipelines distribuidos, Spark y almacenamiento analitico.", fecha_registro: "2026-10-08"});
CREATE (:Usuario {uid: "usr_luis004", nombre: "Luis", apellido: "Angel", email: "luis.angel@wheelson.com", password_hash: "pbkdf2_sha256$1500000$Ef7e8qk0uV6rF4POSxkisx$FOa8FWls+ZRN+6eZuC+8w62sP2qudem3NppGhjfNorc=", titulo_profesional: "Fullstack Engineer & Cloud Native", ubicacion: "Cali, Colombia", biografia: "Desarrollador fullstack con experiencia en ecosistemas React, TypeScript, Python y despliegues en la nube.", fecha_registro: "2026-10-10"});
CREATE (:Usuario {uid: "usr_mateo005", nombre: "Mateo", apellido: "Cisneros", email: "mateo@wheelson.com", password_hash: "pbkdf2_sha256$1500000$Ef7e8qk0uV6rF4POSxkisx$FOa8FWls+ZRN+6eZuC+8w62sP2qudem3NppGhjfNorc=", titulo_profesional: "Tech Lead & Graph Architect", ubicacion: "Bucaramanga, Colombia", biografia: "Tech Lead de WheelsOn, especialista en modelado de grafos complejos, algoritmos de recomendacion y arquitectura distribuida.", fecha_registro: "2026-10-12"});
CREATE (:Usuario {uid: "usr_juan006", nombre: "Juan", apellido: "Arrieta", email: "juan@wheelson.com", password_hash: "pbkdf2_sha256$1500000$Ef7e8qk0uV6rF4POSxkisx$FOa8FWls+ZRN+6eZuC+8w62sP2qudem3NppGhjfNorc=", titulo_profesional: "DevOps & Site Reliability Engineer", ubicacion: "Cartagena, Colombia", biografia: "Especialista en observabilidad, automatizacion CI/CD, clusters Kubernetes y seguridad en la nube.", fecha_registro: "2026-10-14"});
CREATE (:Usuario {uid: "usr_jeronimo007", nombre: "Jeronimo", apellido: "Castro", email: "jeronimo@wheelson.com", password_hash: "pbkdf2_sha256$1500000$Ef7e8qk0uV6rF4POSxkisx$FOa8FWls+ZRN+6eZuC+8w62sP2qudem3NppGhjfNorc=", titulo_profesional: "Frontend Architect & UI/UX Specialist", ubicacion: "Pereira, Colombia", biografia: "Apasionado por el diseno de interfaces modernas, estetica minimalista y rendimiento web.", fecha_registro: "2026-10-15"});
CREATE (:Usuario {uid: "usr_wilson008", nombre: "Wilson", apellido: "Estrada", email: "wilson@wheelson.com", password_hash: "pbkdf2_sha256$1500000$Ef7e8qk0uV6rF4POSxkisx$FOa8FWls+ZRN+6eZuC+8w62sP2qudem3NppGhjfNorc=", titulo_profesional: "Cybersecurity & Infrastructure Lead", ubicacion: "Manizales, Colombia", biografia: "Lider de seguridad informatica enfocado en proteccion de infraestructuras criticas y hardening.", fecha_registro: "2026-10-18"});
CREATE (:Usuario {uid: "usr_maria009", nombre: "Maria", apellido: "Sanchez", email: "maria.sanchez@wheelson.com", password_hash: "pbkdf2_sha256$1500000$Ef7e8qk0uV6rF4POSxkisx$FOa8FWls+ZRN+6eZuC+8w62sP2qudem3NppGhjfNorc=", titulo_profesional: "Product Manager & Tech Strategist", ubicacion: "Bogota, Colombia", biografia: "Lider de producto orientada a impacto en el usuario, metodologias agiles y vision estrategica de negocio.", fecha_registro: "2026-10-20"});
CREATE (:Usuario {uid: "usr_miguel010", nombre: "Miguel", apellido: "Carrizosa", email: "miguel@wheelson.com", password_hash: "pbkdf2_sha256$1500000$Ef7e8qk0uV6rF4POSxkisx$FOa8FWls+ZRN+6eZuC+8w62sP2qudem3NppGhjfNorc=", titulo_profesional: "Mobile Developer & Flutter Lead", ubicacion: "Medellin, Colombia", biografia: "Desarrollador de aplicaciones moviles multiplataforma con Flutter, Dart y arquitecturas offline-first.", fecha_registro: "2026-10-22"});
CREATE (:Usuario {uid: "usr_santiago011", nombre: "Santiago", apellido: "Vieira", email: "santiago.vieira@wheelson.com", password_hash: "pbkdf2_sha256$1500000$Ef7e8qk0uV6rF4POSxkisx$FOa8FWls+ZRN+6eZuC+8w62sP2qudem3NppGhjfNorc=", titulo_profesional: "Database Administrator & Neo4j Expert", ubicacion: "Barranquilla, Colombia", biografia: "DBA con amplia trayectoria en administracion, clustering y tuning de Neo4j y PostgreSQL.", fecha_registro: "2026-10-25"});
CREATE (:Usuario {uid: "usr_jose012", nombre: "Jose", apellido: "Villa", email: "jose@wheelson.com", password_hash: "pbkdf2_sha256$1500000$Ef7e8qk0uV6rF4POSxkisx$FOa8FWls+ZRN+6eZuC+8w62sP2qudem3NppGhjfNorc=", titulo_profesional: "Software Engineer & Microservices", ubicacion: "Cali, Colombia", biografia: "Desarrollador backend enfocado en APIs RESTful escalables, colas de mensajeria y contenedores.", fecha_registro: "2026-10-26"});
CREATE (:Usuario {uid: "usr_luisc013", nombre: "Luis", apellido: "Cortes", email: "luis.cortes@wheelson.com", password_hash: "pbkdf2_sha256$1500000$Ef7e8qk0uV6rF4POSxkisx$FOa8FWls+ZRN+6eZuC+8w62sP2qudem3NppGhjfNorc=", titulo_profesional: "QA Automation & Performance Engineer", ubicacion: "Bogota, Colombia", biografia: "Ingeniero de pruebas automatizadas, pruebas de carga y aseguramiento de calidad de software.", fecha_registro: "2026-10-27"});
CREATE (:Usuario {uid: "usr_santiagoa014", nombre: "Santiago", apellido: "Arenas", email: "santiago.arenas@wheelson.com", password_hash: "pbkdf2_sha256$1500000$Ef7e8qk0uV6rF4POSxkisx$FOa8FWls+ZRN+6eZuC+8w62sP2qudem3NppGhjfNorc=", titulo_profesional: "Solutions Architect & Cloud DevOps", ubicacion: "Medellin, Colombia", biografia: "Arquitecto de soluciones en la nube con enfasis en Terraform, Serverless y alta disponibilidad.", fecha_registro: "2026-10-28"});
CREATE (:Usuario {uid: "usr_andres015", nombre: "Andres", apellido: "Castillo", email: "andres@wheelson.com", password_hash: "pbkdf2_sha256$1500000$Ef7e8qk0uV6rF4POSxkisx$FOa8FWls+ZRN+6eZuC+8w62sP2qudem3NppGhjfNorc=", titulo_profesional: "Data Scientist & NLP Specialist", ubicacion: "Bucaramanga, Colombia", biografia: "Cientifico de datos enfocado en procesamiento de lenguaje natural y analitica predictiva.", fecha_registro: "2026-10-30"});

// 3. Empresas
CREATE (:Empresa {eid: "emp_nexus01", nombre: "Nexus Corp", industria: "Fintech", ubicacion: "Bogota, Colombia", descripcion: "Empresa lider en soluciones tecnologicas financieras impulsadas por grafos.", tamano: "grande"});
CREATE (:Empresa {eid: "emp_techin02", nombre: "Tech Innovators", industria: "Software", ubicacion: "Medellin, Colombia", descripcion: "Hub de investigacion y desarrollo de productos digitales avanzados.", tamano: "mediana"});
CREATE (:Empresa {eid: "emp_globant03", nombre: "Globant Latam", industria: "Consultoria IT", ubicacion: "Bogota, Colombia", descripcion: "Transformacion digital y arquitectura de software de clase mundial.", tamano: "grande"});

// 4. Habilidades
CREATE (:Habilidad {hid: "hab_py01", nombre: "Python", categoria: "tecnica", descripcion: "Lenguaje principal de desarrollo backend y analitica."});
CREATE (:Habilidad {hid: "hab_neo02", nombre: "Neo4j", categoria: "tecnica", descripcion: "Base de datos orientada a grafos y motor Bolt."});
CREATE (:Habilidad {hid: "hab_cyp03", nombre: "Cypher", categoria: "tecnica", descripcion: "Lenguaje declarativo de consulta sobre nodos y aristas."});
CREATE (:Habilidad {hid: "hab_doc04", nombre: "Docker", categoria: "tecnica", descripcion: "Contenerizacion y despliegue de microservicios."});
CREATE (:Habilidad {hid: "hab_lid05", nombre: "Liderazgo", categoria: "blanda", descripcion: "Gestion de equipos de alto rendimiento y coordinacion."});
CREATE (:Habilidad {hid: "hab_ing06", nombre: "Ingles Tecnico", categoria: "idioma", descripcion: "Comunicacion fluida en entornos internacionales."});
CREATE (:Habilidad {hid: "hab_rea07", nombre: "React", categoria: "tecnica", descripcion: "Libreria declarativa para interfaces de usuario modernas."});
CREATE (:Habilidad {hid: "hab_ts08", nombre: "TypeScript", categoria: "tecnica", descripcion: "Superconjunto tipado de JavaScript para aplicaciones robustas."});
CREATE (:Habilidad {hid: "hab_ml09", nombre: "Machine Learning", categoria: "tecnica", descripcion: "Modelos estadisticos, prediccion y embeddings."});
CREATE (:Habilidad {hid: "hab_aws10", nombre: "AWS Cloud", categoria: "tecnica", descripcion: "Infraestructura, computo distribuido y storage en la nube."});
CREATE (:Habilidad {hid: "hab_k8s11", nombre: "Kubernetes", categoria: "tecnica", descripcion: "Orquestacion de contenedores en clusters de produccion."});
CREATE (:Habilidad {hid: "hab_sql12", nombre: "PostgreSQL", categoria: "tecnica", descripcion: "Base de datos relacional y soporte de extensiones avanzadas."});

// 5. Proyectos
CREATE (:Proyecto {pid: "proy_graph01", nombre: "Motor de Grafos WheelsOn", descripcion: "Plataforma de investigacion y desarrollo para navegacion y analisis de redes complejas.", estado: "activo", fecha_inicio: "2026-10-01", tecnologias: ["Python", "Django", "Neo4j", "Cypher", "Vis.js"]});
CREATE (:Proyecto {pid: "proy_fintech02", nombre: "Plataforma Fintech AI", descripcion: "Deteccion de patrones anomalos y analisis de comunidades en redes de pago.", estado: "activo", fecha_inicio: "2026-09-01", tecnologias: ["Python", "Docker", "Neo4j", "Machine Learning"]});

// 6. Ofertas
CREATE (:Oferta {oid: "ofr_dataeng01", titulo: "Senior Data Engineer", descripcion: "Buscamos especialista en modelos de grafos para optimizar almacenamiento y consultas analiticas.", salario_min: 8000000.0, salario_max: 12000000.0, modalidad: "remoto", ubicacion: "Colombia", estado: "abierta", fecha_publicacion: "2026-11-01"});
CREATE (:Oferta {oid: "ofr_arch02", titulo: "Lead Graph Architect", descripcion: "Liderazgo en diseno de ontologias de grafos y algoritmos de recomendacion colaborativa.", salario_min: 14000000.0, salario_max: 18000000.0, modalidad: "hibrido", ubicacion: "Bogota", estado: "abierta", fecha_publicacion: "2026-11-02"});

// 7. Conexiones profesionales [:CONECTA_CON]
MATCH (a:Usuario {uid: "usr_mateo005"}), (b:Usuario {uid: "usr_carlos001"}) CREATE (a)-[:CONECTA_CON {mensaje: "Gran colaboracion en el motor de grafos y arquitectura backend.", estado: "aceptada", fecha: "2026-11-01"}]->(b);
MATCH (a:Usuario {uid: "usr_mateo005"}), (b:Usuario {uid: "usr_angelo002"}) CREATE (a)-[:CONECTA_CON {mensaje: "Revisemos la integracion de los endpoints y microservicios.", estado: "aceptada", fecha: "2026-11-01"}]->(b);
MATCH (a:Usuario {uid: "usr_mateo005"}), (b:Usuario {uid: "usr_dubal003"}) CREATE (a)-[:CONECTA_CON {mensaje: "Excelente avance en el pipeline de datos y particionado.", estado: "aceptada", fecha: "2026-11-01"}]->(b);
MATCH (a:Usuario {uid: "usr_mateo005"}), (b:Usuario {uid: "usr_luis004"}) CREATE (a)-[:CONECTA_CON {mensaje: "El frontend reactivo de WheelsOn quedo impecable.", estado: "aceptada", fecha: "2026-11-01"}]->(b);
MATCH (a:Usuario {uid: "usr_mateo005"}), (b:Usuario {uid: "usr_jeronimo007"}) CREATE (a)-[:CONECTA_CON {mensaje: "La estetica y usabilidad de la plataforma esta genial.", estado: "aceptada", fecha: "2026-11-01"}]->(b);
MATCH (a:Usuario {uid: "usr_mateo005"}), (b:Usuario {uid: "usr_wilson008"}) CREATE (a)-[:CONECTA_CON {mensaje: "Revisemos las politicas de seguridad del cluster.", estado: "aceptada", fecha: "2026-11-01"}]->(b);
MATCH (a:Usuario {uid: "usr_mateo005"}), (b:Usuario {uid: "usr_maria009"}) CREATE (a)-[:CONECTA_CON {mensaje: "Alineemos los entregables tecnicos del proximo sprint.", estado: "aceptada", fecha: "2026-11-01"}]->(b);
MATCH (a:Usuario {uid: "usr_mateo005"}), (b:Usuario {uid: "usr_santiago011"}) CREATE (a)-[:CONECTA_CON {mensaje: "Optimizamos los indices y restricciones en Neo4j.", estado: "aceptada", fecha: "2026-11-01"}]->(b);
MATCH (a:Usuario {uid: "usr_mateo005"}), (b:Usuario {uid: "usr_andres015"}) CREATE (a)-[:CONECTA_CON {mensaje: "Comparativa de embeddings de nodos relacionales finalizada.", estado: "aceptada", fecha: "2026-11-01"}]->(b);
MATCH (a:Usuario {uid: "usr_carlos001"}), (b:Usuario {uid: "usr_angelo002"}) CREATE (a)-[:CONECTA_CON {mensaje: "Gran debate sobre concurrencia y FastAPI.", estado: "aceptada", fecha: "2026-11-01"}]->(b);
MATCH (a:Usuario {uid: "usr_carlos001"}), (b:Usuario {uid: "usr_dubal003"}) CREATE (a)-[:CONECTA_CON {mensaje: "Excelente debate sobre particionado en grafos distribuidos.", estado: "aceptada", fecha: "2026-11-01"}]->(b);
MATCH (a:Usuario {uid: "usr_carlos001"}), (b:Usuario {uid: "usr_luis004"}) CREATE (a)-[:CONECTA_CON {mensaje: "El frontend reactivo de WheelsOn quedo impecable.", estado: "aceptada", fecha: "2026-11-01"}]->(b);
MATCH (a:Usuario {uid: "usr_carlos001"}), (b:Usuario {uid: "usr_santiago011"}) CREATE (a)-[:CONECTA_CON {mensaje: "Optimizamos los indices y restricciones en Neo4j.", estado: "aceptada", fecha: "2026-11-01"}]->(b);
MATCH (a:Usuario {uid: "usr_angelo002"}), (b:Usuario {uid: "usr_dubal003"}) CREATE (a)-[:CONECTA_CON {mensaje: "Conectemos el pipeline de ingestion con los microservicios.", estado: "aceptada", fecha: "2026-11-01"}]->(b);
MATCH (a:Usuario {uid: "usr_angelo002"}), (b:Usuario {uid: "usr_juan006"}) CREATE (a)-[:CONECTA_CON {mensaje: "Listo el manifiesto de despliegue en Kubernetes.", estado: "aceptada", fecha: "2026-11-01"}]->(b);
MATCH (a:Usuario {uid: "usr_angelo002"}), (b:Usuario {uid: "usr_jose012"}) CREATE (a)-[:CONECTA_CON {mensaje: "Estandaricemos las interfaces de la API.", estado: "aceptada", fecha: "2026-11-01"}]->(b);
MATCH (a:Usuario {uid: "usr_dubal003"}), (b:Usuario {uid: "usr_santiago011"}) CREATE (a)-[:CONECTA_CON {mensaje: "Validemos las particiones de la base de datos.", estado: "aceptada", fecha: "2026-11-01"}]->(b);
MATCH (a:Usuario {uid: "usr_dubal003"}), (b:Usuario {uid: "usr_andres015"}) CREATE (a)-[:CONECTA_CON {mensaje: "El dataset analitico ya esta limpio y normalizado.", estado: "aceptada", fecha: "2026-11-01"}]->(b);
MATCH (a:Usuario {uid: "usr_jeronimo007"}), (b:Usuario {uid: "usr_luis004"}) CREATE (a)-[:CONECTA_CON {mensaje: "Integracion fluida de los componentes Alpine.", estado: "aceptada", fecha: "2026-11-01"}]->(b);
MATCH (a:Usuario {uid: "usr_jeronimo007"}), (b:Usuario {uid: "usr_miguel010"}) CREATE (a)-[:CONECTA_CON {mensaje: "Compartamos el sistema de diseno para mobile.", estado: "aceptada", fecha: "2026-11-01"}]->(b);
MATCH (a:Usuario {uid: "usr_jeronimo007"}), (b:Usuario {uid: "usr_maria009"}) CREATE (a)-[:CONECTA_CON {mensaje: "Feedback de experiencia de usuario implementado.", estado: "aceptada", fecha: "2026-11-01"}]->(b);
MATCH (a:Usuario {uid: "usr_luis004"}), (b:Usuario {uid: "usr_miguel010"}) CREATE (a)-[:CONECTA_CON {mensaje: "Unificando endpoints para la app y la web.", estado: "aceptada", fecha: "2026-11-01"}]->(b);
MATCH (a:Usuario {uid: "usr_luis004"}), (b:Usuario {uid: "usr_luisc013"}) CREATE (a)-[:CONECTA_CON {mensaje: "Listos los tests e2e para el flujo de publicacion.", estado: "aceptada", fecha: "2026-11-01"}]->(b);
MATCH (a:Usuario {uid: "usr_juan006"}), (b:Usuario {uid: "usr_wilson008"}) CREATE (a)-[:CONECTA_CON {mensaje: "Auditoria de red interna aprobada sin hallazgos.", estado: "aceptada", fecha: "2026-11-01"}]->(b);
MATCH (a:Usuario {uid: "usr_juan006"}), (b:Usuario {uid: "usr_santiagoa014"}) CREATE (a)-[:CONECTA_CON {mensaje: "Infraestructura como codigo en Terraform desplegada.", estado: "aceptada", fecha: "2026-11-01"}]->(b);
MATCH (a:Usuario {uid: "usr_juan006"}), (b:Usuario {uid: "usr_luisc013"}) CREATE (a)-[:CONECTA_CON {mensaje: "Pipeline de pruebas automatizadas integrado en CI/CD.", estado: "aceptada", fecha: "2026-11-01"}]->(b);
MATCH (a:Usuario {uid: "usr_wilson008"}), (b:Usuario {uid: "usr_santiagoa014"}) CREATE (a)-[:CONECTA_CON {mensaje: "Configuracion de VPC y grupos de seguridad lista.", estado: "aceptada", fecha: "2026-11-01"}]->(b);
MATCH (a:Usuario {uid: "usr_maria009"}), (b:Usuario {uid: "usr_santiagoa014"}) CREATE (a)-[:CONECTA_CON {mensaje: "Estimacion de costos de infraestructura aprobada.", estado: "aceptada", fecha: "2026-11-01"}]->(b);
MATCH (a:Usuario {uid: "usr_jose012"}), (b:Usuario {uid: "usr_luisc013"}) CREATE (a)-[:CONECTA_CON {mensaje: "Casos de prueba de regresion ejecutados al 100%.", estado: "aceptada", fecha: "2026-11-01"}]->(b);
MATCH (a:Usuario {uid: "usr_santiago011"}), (b:Usuario {uid: "usr_jose012"}) CREATE (a)-[:CONECTA_CON {mensaje: "Pool de conexiones a base de datos ajustado.", estado: "aceptada", fecha: "2026-11-01"}]->(b);

// 8. Experiencia laboral [:TRABAJA_EN]
MATCH (a:Usuario {uid: "usr_mateo005"}), (b:Empresa {eid: "emp_nexus01"}) CREATE (a)-[:TRABAJA_EN {cargo: "Tech Lead & Graph Architect", fecha_inicio: "2024-01-15", actual: true}]->(b);
MATCH (a:Usuario {uid: "usr_carlos001"}), (b:Empresa {eid: "emp_nexus01"}) CREATE (a)-[:TRABAJA_EN {cargo: "Senior Backend & Graph Engineer", fecha_inicio: "2024-02-01", actual: true}]->(b);
MATCH (a:Usuario {uid: "usr_angelo002"}), (b:Empresa {eid: "emp_techin02"}) CREATE (a)-[:TRABAJA_EN {cargo: "Senior Backend Engineer", fecha_inicio: "2023-03-01", actual: true}]->(b);
MATCH (a:Usuario {uid: "usr_dubal003"}), (b:Empresa {eid: "emp_globant03"}) CREATE (a)-[:TRABAJA_EN {cargo: "Principal Data Architect", fecha_inicio: "2022-06-10", actual: true}]->(b);
MATCH (a:Usuario {uid: "usr_luis004"}), (b:Empresa {eid: "emp_techin02"}) CREATE (a)-[:TRABAJA_EN {cargo: "Fullstack Developer", fecha_inicio: "2023-08-15", actual: true}]->(b);
MATCH (a:Usuario {uid: "usr_juan006"}), (b:Empresa {eid: "emp_globant03"}) CREATE (a)-[:TRABAJA_EN {cargo: "DevOps & SRE Lead", fecha_inicio: "2023-01-10", actual: true}]->(b);
MATCH (a:Usuario {uid: "usr_jeronimo007"}), (b:Empresa {eid: "emp_nexus01"}) CREATE (a)-[:TRABAJA_EN {cargo: "Frontend Architect", fecha_inicio: "2023-11-01", actual: true}]->(b);
MATCH (a:Usuario {uid: "usr_wilson008"}), (b:Empresa {eid: "emp_techin02"}) CREATE (a)-[:TRABAJA_EN {cargo: "Cybersecurity Specialist", fecha_inicio: "2022-09-01", actual: true}]->(b);
MATCH (a:Usuario {uid: "usr_maria009"}), (b:Empresa {eid: "emp_globant03"}) CREATE (a)-[:TRABAJA_EN {cargo: "Senior Product Manager", fecha_inicio: "2023-04-15", actual: true}]->(b);
MATCH (a:Usuario {uid: "usr_miguel010"}), (b:Empresa {eid: "emp_techin02"}) CREATE (a)-[:TRABAJA_EN {cargo: "Mobile Tech Lead", fecha_inicio: "2023-10-01", actual: true}]->(b);
MATCH (a:Usuario {uid: "usr_santiago011"}), (b:Empresa {eid: "emp_nexus01"}) CREATE (a)-[:TRABAJA_EN {cargo: "Senior Database Administrator", fecha_inicio: "2023-05-01", actual: true}]->(b);
MATCH (a:Usuario {uid: "usr_jose012"}), (b:Empresa {eid: "emp_techin02"}) CREATE (a)-[:TRABAJA_EN {cargo: "Backend Software Engineer", fecha_inicio: "2024-03-01", actual: true}]->(b);
MATCH (a:Usuario {uid: "usr_luisc013"}), (b:Empresa {eid: "emp_globant03"}) CREATE (a)-[:TRABAJA_EN {cargo: "QA Automation Lead", fecha_inicio: "2023-07-01", actual: true}]->(b);
MATCH (a:Usuario {uid: "usr_santiagoa014"}), (b:Empresa {eid: "emp_nexus01"}) CREATE (a)-[:TRABAJA_EN {cargo: "Solutions Architect", fecha_inicio: "2023-12-01", actual: true}]->(b);
MATCH (a:Usuario {uid: "usr_andres015"}), (b:Empresa {eid: "emp_globant03"}) CREATE (a)-[:TRABAJA_EN {cargo: "Data Scientist", fecha_inicio: "2024-04-01", actual: true}]->(b);

// 9. Habilidades de cada usuario [:TIENE_HABILIDAD]
MATCH (a:Usuario {uid: "usr_mateo005"}), (b:Habilidad {hid: "hab_py01"}) CREATE (a)-[:TIENE_HABILIDAD {nivel: "experto", anios_experiencia: 7}]->(b);
MATCH (a:Usuario {uid: "usr_mateo005"}), (b:Habilidad {hid: "hab_neo02"}) CREATE (a)-[:TIENE_HABILIDAD {nivel: "experto", anios_experiencia: 5}]->(b);
MATCH (a:Usuario {uid: "usr_mateo005"}), (b:Habilidad {hid: "hab_cyp03"}) CREATE (a)-[:TIENE_HABILIDAD {nivel: "avanzado", anios_experiencia: 5}]->(b);
MATCH (a:Usuario {uid: "usr_mateo005"}), (b:Habilidad {hid: "hab_lid05"}) CREATE (a)-[:TIENE_HABILIDAD {nivel: "experto", anios_experiencia: 6}]->(b);
MATCH (a:Usuario {uid: "usr_mateo005"}), (b:Habilidad {hid: "hab_ml09"}) CREATE (a)-[:TIENE_HABILIDAD {nivel: "experto", anios_experiencia: 5}]->(b);
MATCH (a:Usuario {uid: "usr_mateo005"}), (b:Habilidad {hid: "hab_doc04"}) CREATE (a)-[:TIENE_HABILIDAD {nivel: "avanzado", anios_experiencia: 4}]->(b);
MATCH (a:Usuario {uid: "usr_carlos001"}), (b:Habilidad {hid: "hab_py01"}) CREATE (a)-[:TIENE_HABILIDAD {nivel: "experto", anios_experiencia: 7}]->(b);
MATCH (a:Usuario {uid: "usr_carlos001"}), (b:Habilidad {hid: "hab_neo02"}) CREATE (a)-[:TIENE_HABILIDAD {nivel: "experto", anios_experiencia: 5}]->(b);
MATCH (a:Usuario {uid: "usr_carlos001"}), (b:Habilidad {hid: "hab_cyp03"}) CREATE (a)-[:TIENE_HABILIDAD {nivel: "avanzado", anios_experiencia: 4}]->(b);
MATCH (a:Usuario {uid: "usr_carlos001"}), (b:Habilidad {hid: "hab_doc04"}) CREATE (a)-[:TIENE_HABILIDAD {nivel: "avanzado", anios_experiencia: 4}]->(b);
MATCH (a:Usuario {uid: "usr_angelo002"}), (b:Habilidad {hid: "hab_py01"}) CREATE (a)-[:TIENE_HABILIDAD {nivel: "experto", anios_experiencia: 6}]->(b);
MATCH (a:Usuario {uid: "usr_angelo002"}), (b:Habilidad {hid: "hab_doc04"}) CREATE (a)-[:TIENE_HABILIDAD {nivel: "avanzado", anios_experiencia: 5}]->(b);
MATCH (a:Usuario {uid: "usr_angelo002"}), (b:Habilidad {hid: "hab_sql12"}) CREATE (a)-[:TIENE_HABILIDAD {nivel: "avanzado", anios_experiencia: 4}]->(b);
MATCH (a:Usuario {uid: "usr_angelo002"}), (b:Habilidad {hid: "hab_cyp03"}) CREATE (a)-[:TIENE_HABILIDAD {nivel: "intermedio", anios_experiencia: 3}]->(b);
MATCH (a:Usuario {uid: "usr_dubal003"}), (b:Habilidad {hid: "hab_py01"}) CREATE (a)-[:TIENE_HABILIDAD {nivel: "avanzado", anios_experiencia: 5}]->(b);
MATCH (a:Usuario {uid: "usr_dubal003"}), (b:Habilidad {hid: "hab_neo02"}) CREATE (a)-[:TIENE_HABILIDAD {nivel: "avanzado", anios_experiencia: 4}]->(b);
MATCH (a:Usuario {uid: "usr_dubal003"}), (b:Habilidad {hid: "hab_aws10"}) CREATE (a)-[:TIENE_HABILIDAD {nivel: "avanzado", anios_experiencia: 4}]->(b);
MATCH (a:Usuario {uid: "usr_luis004"}), (b:Habilidad {hid: "hab_rea07"}) CREATE (a)-[:TIENE_HABILIDAD {nivel: "experto", anios_experiencia: 5}]->(b);
MATCH (a:Usuario {uid: "usr_luis004"}), (b:Habilidad {hid: "hab_ts08"}) CREATE (a)-[:TIENE_HABILIDAD {nivel: "avanzado", anios_experiencia: 4}]->(b);
MATCH (a:Usuario {uid: "usr_luis004"}), (b:Habilidad {hid: "hab_py01"}) CREATE (a)-[:TIENE_HABILIDAD {nivel: "intermedio", anios_experiencia: 3}]->(b);
MATCH (a:Usuario {uid: "usr_juan006"}), (b:Habilidad {hid: "hab_doc04"}) CREATE (a)-[:TIENE_HABILIDAD {nivel: "experto", anios_experiencia: 6}]->(b);
MATCH (a:Usuario {uid: "usr_juan006"}), (b:Habilidad {hid: "hab_k8s11"}) CREATE (a)-[:TIENE_HABILIDAD {nivel: "avanzado", anios_experiencia: 4}]->(b);
MATCH (a:Usuario {uid: "usr_juan006"}), (b:Habilidad {hid: "hab_aws10"}) CREATE (a)-[:TIENE_HABILIDAD {nivel: "avanzado", anios_experiencia: 5}]->(b);
MATCH (a:Usuario {uid: "usr_jeronimo007"}), (b:Habilidad {hid: "hab_rea07"}) CREATE (a)-[:TIENE_HABILIDAD {nivel: "experto", anios_experiencia: 5}]->(b);
MATCH (a:Usuario {uid: "usr_jeronimo007"}), (b:Habilidad {hid: "hab_ts08"}) CREATE (a)-[:TIENE_HABILIDAD {nivel: "avanzado", anios_experiencia: 4}]->(b);
MATCH (a:Usuario {uid: "usr_wilson008"}), (b:Habilidad {hid: "hab_doc04"}) CREATE (a)-[:TIENE_HABILIDAD {nivel: "avanzado", anios_experiencia: 4}]->(b);
MATCH (a:Usuario {uid: "usr_wilson008"}), (b:Habilidad {hid: "hab_py01"}) CREATE (a)-[:TIENE_HABILIDAD {nivel: "avanzado", anios_experiencia: 4}]->(b);
MATCH (a:Usuario {uid: "usr_maria009"}), (b:Habilidad {hid: "hab_lid05"}) CREATE (a)-[:TIENE_HABILIDAD {nivel: "experto", anios_experiencia: 8}]->(b);
MATCH (a:Usuario {uid: "usr_maria009"}), (b:Habilidad {hid: "hab_ing06"}) CREATE (a)-[:TIENE_HABILIDAD {nivel: "avanzado", anios_experiencia: 6}]->(b);
MATCH (a:Usuario {uid: "usr_miguel010"}), (b:Habilidad {hid: "hab_ts08"}) CREATE (a)-[:TIENE_HABILIDAD {nivel: "avanzado", anios_experiencia: 4}]->(b);
MATCH (a:Usuario {uid: "usr_miguel010"}), (b:Habilidad {hid: "hab_rea07"}) CREATE (a)-[:TIENE_HABILIDAD {nivel: "intermedio", anios_experiencia: 3}]->(b);
MATCH (a:Usuario {uid: "usr_santiago011"}), (b:Habilidad {hid: "hab_neo02"}) CREATE (a)-[:TIENE_HABILIDAD {nivel: "experto", anios_experiencia: 7}]->(b);
MATCH (a:Usuario {uid: "usr_santiago011"}), (b:Habilidad {hid: "hab_cyp03"}) CREATE (a)-[:TIENE_HABILIDAD {nivel: "experto", anios_experiencia: 6}]->(b);
MATCH (a:Usuario {uid: "usr_santiago011"}), (b:Habilidad {hid: "hab_sql12"}) CREATE (a)-[:TIENE_HABILIDAD {nivel: "avanzado", anios_experiencia: 5}]->(b);
MATCH (a:Usuario {uid: "usr_jose012"}), (b:Habilidad {hid: "hab_py01"}) CREATE (a)-[:TIENE_HABILIDAD {nivel: "avanzado", anios_experiencia: 4}]->(b);
MATCH (a:Usuario {uid: "usr_jose012"}), (b:Habilidad {hid: "hab_doc04"}) CREATE (a)-[:TIENE_HABILIDAD {nivel: "intermedio", anios_experiencia: 3}]->(b);
MATCH (a:Usuario {uid: "usr_luisc013"}), (b:Habilidad {hid: "hab_py01"}) CREATE (a)-[:TIENE_HABILIDAD {nivel: "avanzado", anios_experiencia: 4}]->(b);
MATCH (a:Usuario {uid: "usr_luisc013"}), (b:Habilidad {hid: "hab_doc04"}) CREATE (a)-[:TIENE_HABILIDAD {nivel: "intermedio", anios_experiencia: 3}]->(b);
MATCH (a:Usuario {uid: "usr_santiagoa014"}), (b:Habilidad {hid: "hab_aws10"}) CREATE (a)-[:TIENE_HABILIDAD {nivel: "experto", anios_experiencia: 6}]->(b);
MATCH (a:Usuario {uid: "usr_santiagoa014"}), (b:Habilidad {hid: "hab_k8s11"}) CREATE (a)-[:TIENE_HABILIDAD {nivel: "avanzado", anios_experiencia: 4}]->(b);
MATCH (a:Usuario {uid: "usr_andres015"}), (b:Habilidad {hid: "hab_py01"}) CREATE (a)-[:TIENE_HABILIDAD {nivel: "experto", anios_experiencia: 6}]->(b);
MATCH (a:Usuario {uid: "usr_andres015"}), (b:Habilidad {hid: "hab_ml09"}) CREATE (a)-[:TIENE_HABILIDAD {nivel: "avanzado", anios_experiencia: 4}]->(b);

// 10. Participacion en proyectos [:PARTICIPA_EN]
MATCH (a:Usuario {uid: "usr_mateo005"}), (b:Proyecto {pid: "proy_graph01"}) CREATE (a)-[:PARTICIPA_EN {rol: "Tech Director & Lead Architect", fecha_inicio: "2026-10-01", activo: true}]->(b);
MATCH (a:Usuario {uid: "usr_carlos001"}), (b:Proyecto {pid: "proy_graph01"}) CREATE (a)-[:PARTICIPA_EN {rol: "Senior Graph Engineer", fecha_inicio: "2026-10-01", activo: true}]->(b);
MATCH (a:Usuario {uid: "usr_angelo002"}), (b:Proyecto {pid: "proy_graph01"}) CREATE (a)-[:PARTICIPA_EN {rol: "Backend Lead", fecha_inicio: "2026-10-05", activo: true}]->(b);
MATCH (a:Usuario {uid: "usr_jeronimo007"}), (b:Proyecto {pid: "proy_graph01"}) CREATE (a)-[:PARTICIPA_EN {rol: "Frontend Architect", fecha_inicio: "2026-10-10", activo: true}]->(b);
MATCH (a:Usuario {uid: "usr_luis004"}), (b:Proyecto {pid: "proy_graph01"}) CREATE (a)-[:PARTICIPA_EN {rol: "Fullstack Developer", fecha_inicio: "2026-10-12", activo: true}]->(b);
MATCH (a:Usuario {uid: "usr_santiago011"}), (b:Proyecto {pid: "proy_graph01"}) CREATE (a)-[:PARTICIPA_EN {rol: "Database DBA", fecha_inicio: "2026-10-15", activo: true}]->(b);
MATCH (a:Usuario {uid: "usr_dubal003"}), (b:Proyecto {pid: "proy_fintech02"}) CREATE (a)-[:PARTICIPA_EN {rol: "Data Architect", fecha_inicio: "2026-09-05", activo: true}]->(b);
MATCH (a:Usuario {uid: "usr_andres015"}), (b:Proyecto {pid: "proy_fintech02"}) CREATE (a)-[:PARTICIPA_EN {rol: "Lead Data Scientist", fecha_inicio: "2026-09-10", activo: true}]->(b);

// 11. Publicacion de ofertas [:PUBLICA]
MATCH (a:Empresa {eid: "emp_nexus01"}), (b:Oferta {oid: "ofr_dataeng01"}) CREATE (a)-[:PUBLICA {fecha_publicacion: "2026-11-01"}]->(b);
MATCH (a:Empresa {eid: "emp_globant03"}), (b:Oferta {oid: "ofr_arch02"}) CREATE (a)-[:PUBLICA {fecha_publicacion: "2026-11-02"}]->(b);

// 12. Requisitos de ofertas [:REQUIERE]
MATCH (a:Oferta {oid: "ofr_dataeng01"}), (b:Habilidad {hid: "hab_py01"}) CREATE (a)-[:REQUIERE {nivel_minimo: "avanzado", prioridad: "obligatoria"}]->(b);
MATCH (a:Oferta {oid: "ofr_dataeng01"}), (b:Habilidad {hid: "hab_neo02"}) CREATE (a)-[:REQUIERE {nivel_minimo: "intermedio", prioridad: "obligatoria"}]->(b);
MATCH (a:Oferta {oid: "ofr_dataeng01"}), (b:Habilidad {hid: "hab_aws10"}) CREATE (a)-[:REQUIERE {nivel_minimo: "intermedio", prioridad: "deseable"}]->(b);
MATCH (a:Oferta {oid: "ofr_arch02"}), (b:Habilidad {hid: "hab_cyp03"}) CREATE (a)-[:REQUIERE {nivel_minimo: "avanzado", prioridad: "obligatoria"}]->(b);
MATCH (a:Oferta {oid: "ofr_arch02"}), (b:Habilidad {hid: "hab_neo02"}) CREATE (a)-[:REQUIERE {nivel_minimo: "avanzado", prioridad: "obligatoria"}]->(b);
MATCH (a:Oferta {oid: "ofr_arch02"}), (b:Habilidad {hid: "hab_lid05"}) CREATE (a)-[:REQUIERE {nivel_minimo: "avanzado", prioridad: "deseable"}]->(b);

// 13. Postulaciones [:POSTULA_A]
MATCH (a:Usuario {uid: "usr_dubal003"}), (b:Oferta {oid: "ofr_dataeng01"}) CREATE (a)-[:POSTULA_A {fecha: "2026-11-03", estado: "enviada", carta_presentacion: "Cuento con experiencia solida en pipelines de datos distribuidos y grafos de conocimiento."}]->(b);
MATCH (a:Usuario {uid: "usr_santiago011"}), (b:Oferta {oid: "ofr_arch02"}) CREATE (a)-[:POSTULA_A {fecha: "2026-11-04", estado: "enviada", carta_presentacion: "Especialista en administracion y optimizacion de grafos Neo4j a gran escala."}]->(b);
