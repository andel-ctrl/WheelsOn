// ==============================================================================
// WheelsOn - Datos Semilla Oficiales (15 Usuarios de nombres.txt)
// Base de Datos de Grafos Neo4j 5.x
// ==============================================================================

// 1. Limpieza de datos previos (opcional)
// MATCH (n) DETACH DELETE n;

// 2. Creacion de 15 Nodos de Usuarios (nombres.txt)
CREATE (u1:Usuario {
    uid: "usr_carlos001",
    nombre: "Carlos",
    apellido: "Calabria",
    email: "carlos@wheelson.com",
    password_hash: "pbkdf2_sha256$hashed",
    titulo_profesional: "Senior Backend & Graph Engineer",
    ubicacion: "Bogota, Colombia",
    biografia: "Especialista en bases de datos de grafos, modelado Cypher y arquitectura distribuida en Python.",
    fecha_registro: date("2026-10-01")
})
CREATE (u2:Usuario {
    uid: "usr_angelo002",
    nombre: "Angelo",
    apellido: "Caneda",
    email: "angelo@wheelson.com",
    password_hash: "pbkdf2_sha256$hashed",
    titulo_profesional: "Senior Backend & Distributed Systems",
    ubicacion: "Medellin, Colombia",
    biografia: "Ingeniero backend enfocado en microservicios de alto rendimiento, concurrencia y FastAPI.",
    fecha_registro: date("2026-10-05")
})
CREATE (u3:Usuario {
    uid: "usr_dubal003",
    nombre: "Dubal",
    apellido: "Aguilar",
    email: "dubal@wheelson.com",
    password_hash: "pbkdf2_sha256$hashed",
    titulo_profesional: "Data Architect & Big Data Specialist",
    ubicacion: "Barranquilla, Colombia",
    biografia: "Arquitecto de datos especializado en pipelines distribuidos, Spark y almacenamiento analitico.",
    fecha_registro: date("2026-10-08")
})
CREATE (u4:Usuario {
    uid: "usr_luis004",
    nombre: "Luis",
    apellido: "Angel",
    email: "luis.angel@wheelson.com",
    password_hash: "pbkdf2_sha256$hashed",
    titulo_profesional: "Fullstack Engineer & Cloud Native",
    ubicacion: "Cali, Colombia",
    biografia: "Desarrollador fullstack con experiencia en ecosistemas React, TypeScript, Python y despliegues en la nube.",
    fecha_registro: date("2026-10-10")
})
CREATE (u5:Usuario {
    uid: "usr_mateo005",
    nombre: "Mateo",
    apellido: "Cisneros",
    email: "mateo@wheelson.com",
    password_hash: "pbkdf2_sha256$hashed",
    titulo_profesional: "Tech Lead & Graph Architect",
    ubicacion: "Bucaramanga, Colombia",
    biografia: "Tech Lead de WheelsOn, especialista en modelado de grafos complejos, algoritmos de recomendacion y arquitectura distribuida.",
    fecha_registro: date("2026-10-12")
})
CREATE (u6:Usuario {
    uid: "usr_juan006",
    nombre: "Juan",
    apellido: "Arrieta",
    email: "juan@wheelson.com",
    password_hash: "pbkdf2_sha256$hashed",
    titulo_profesional: "DevOps & Site Reliability Engineer",
    ubicacion: "Cartagena, Colombia",
    biografia: "Especialista en observabilidad, automatizacion CI/CD, clusters Kubernetes y seguridad en la nube.",
    fecha_registro: date("2026-10-14")
})
CREATE (u7:Usuario {
    uid: "usr_jeronimo007",
    nombre: "Jeronimo",
    apellido: "Castro",
    email: "jeronimo@wheelson.com",
    password_hash: "pbkdf2_sha256$hashed",
    titulo_profesional: "Frontend Architect & UI/UX Specialist",
    ubicacion: "Pereira, Colombia",
    biografia: "Apasionado por el diseno de interfaces modernas, estetica minimalista y rendimiento web.",
    fecha_registro: date("2026-10-15")
})
CREATE (u8:Usuario {
    uid: "usr_wilson008",
    nombre: "Wilson",
    apellido: "Estrada",
    email: "wilson@wheelson.com",
    password_hash: "pbkdf2_sha256$hashed",
    titulo_profesional: "Cybersecurity & Infrastructure Lead",
    ubicacion: "Manizales, Colombia",
    biografia: "Lider de seguridad informatica enfocado en proteccion de infraestructuras criticas y hardening.",
    fecha_registro: date("2026-10-18")
})
CREATE (u9:Usuario {
    uid: "usr_maria009",
    nombre: "Maria",
    apellido: "Sanchez",
    email: "maria.sanchez@wheelson.com",
    password_hash: "pbkdf2_sha256$hashed",
    titulo_profesional: "Product Manager & Tech Strategist",
    ubicacion: "Bogota, Colombia",
    biografia: "Lider de producto orientada a impacto en el usuario, metodologias agiles y vision estrategica de negocio.",
    fecha_registro: date("2026-10-20")
})
CREATE (u10:Usuario {
    uid: "usr_miguel010",
    nombre: "Miguel",
    apellido: "Carrizosa",
    email: "miguel@wheelson.com",
    password_hash: "pbkdf2_sha256$hashed",
    titulo_profesional: "Mobile Developer & Flutter Lead",
    ubicacion: "Medellin, Colombia",
    biografia: "Desarrollador de aplicaciones moviles multiplataforma con Flutter, Dart y arquitecturas offline-first.",
    fecha_registro: date("2026-10-22")
})
CREATE (u11:Usuario {
    uid: "usr_santiago011",
    nombre: "Santiago",
    apellido: "Vieira",
    email: "santiago.vieira@wheelson.com",
    password_hash: "pbkdf2_sha256$hashed",
    titulo_profesional: "Database Administrator & Neo4j Expert",
    ubicacion: "Barranquilla, Colombia",
    biografia: "DBA con amplia trayectoria en administracion, clustering y tuning de Neo4j y PostgreSQL.",
    fecha_registro: date("2026-10-25")
})
CREATE (u12:Usuario {
    uid: "usr_jose012",
    nombre: "Jose",
    apellido: "Villa",
    email: "jose@wheelson.com",
    password_hash: "pbkdf2_sha256$hashed",
    titulo_profesional: "Software Engineer & Microservices",
    ubicacion: "Cali, Colombia",
    biografia: "Desarrollador backend enfocado en APIs RESTful escalables, colas de mensajeria y contenedores.",
    fecha_registro: date("2026-10-26")
})
CREATE (u13:Usuario {
    uid: "usr_luisc013",
    nombre: "Luis",
    apellido: "Cortes",
    email: "luis.cortes@wheelson.com",
    password_hash: "pbkdf2_sha256$hashed",
    titulo_profesional: "QA Automation & Performance Engineer",
    ubicacion: "Bogota, Colombia",
    biografia: "Ingeniero de pruebas automatizadas, pruebas de carga y aseguramiento de calidad de software.",
    fecha_registro: date("2026-10-27")
})
CREATE (u14:Usuario {
    uid: "usr_santiagoa014",
    nombre: "Santiago",
    apellido: "Arenas",
    email: "santiago.arenas@wheelson.com",
    password_hash: "pbkdf2_sha256$hashed",
    titulo_profesional: "Solutions Architect & Cloud DevOps",
    ubicacion: "Medellin, Colombia",
    biografia: "Arquitecto de soluciones en la nube con enfasis en Terraform, Serverless y alta disponibilidad.",
    fecha_registro: date("2026-10-28")
})
CREATE (u15:Usuario {
    uid: "usr_andres015",
    nombre: "Andres",
    apellido: "Castillo",
    email: "andres@wheelson.com",
    password_hash: "pbkdf2_sha256$hashed",
    titulo_profesional: "Data Scientist & NLP Specialist",
    ubicacion: "Bucaramanga, Colombia",
    biografia: "Cientifico de datos enfocado en procesamiento de lenguaje natural y analitica predictiva.",
    fecha_registro: date("2026-10-30")
);

// 3. Creacion de Nodos de Empresas
CREATE (e1:Empresa {
    eid: "emp_nexus01",
    nombre: "Nexus Corp",
    industria: "Fintech",
    ubicacion: "Bogota, Colombia",
    descripcion: "Empresa lider en soluciones tecnologicas financieras impulsadas por grafos.",
    tamano: "grande"
})
CREATE (e2:Empresa {
    eid: "emp_techin02",
    nombre: "Tech Innovators",
    industria: "Software",
    ubicacion: "Medellin, Colombia",
    descripcion: "Hub de investigacion y desarrollo de productos digitales avanzados.",
    tamano: "mediana"
})
CREATE (e3:Empresa {
    eid: "emp_globant03",
    nombre: "Globant Latam",
    industria: "Consultoria IT",
    ubicacion: "Bogota, Colombia",
    descripcion: "Transformacion digital y arquitectura de software de clase mundial.",
    tamano: "grande"
});

// 4. Creacion de Habilidades
CREATE (h1:Habilidad {hid: "hab_py01", nombre: "Python", categoria: "tecnica", descripcion: "Lenguaje principal backend y analitica."})
CREATE (h2:Habilidad {hid: "hab_neo02", nombre: "Neo4j", categoria: "tecnica", descripcion: "Base de datos orientada a grafos y motor Bolt."})
CREATE (h3:Habilidad {hid: "hab_cyp03", nombre: "Cypher", categoria: "tecnica", descripcion: "Lenguaje de consulta declarativo sobre grafos."})
CREATE (h4:Habilidad {hid: "hab_doc04", nombre: "Docker", categoria: "tecnica", descripcion: "Contenerizacion y microservicios."})
CREATE (h5:Habilidad {hid: "hab_lid05", nombre: "Liderazgo", categoria: "blanda", descripcion: "Gestion de equipos tecnicos y coordinacion."})
CREATE (h6:Habilidad {hid: "hab_ing06", nombre: "Ingles Tecnico", categoria: "idioma", descripcion: "Comunicacion fluida internacional."})
CREATE (h7:Habilidad {hid: "hab_rea07", nombre: "React", categoria: "tecnica", descripcion: "Interfaces de usuario web modernas."})
CREATE (h8:Habilidad {hid: "hab_ts08", nombre: "TypeScript", categoria: "tecnica", descripcion: "JavaScript tipado estaticamente."})
CREATE (h9:Habilidad {hid: "hab_ml09", nombre: "Machine Learning", categoria: "tecnica", descripcion: "Modelos predictivos y embeddings."})
CREATE (h10:Habilidad {hid: "hab_aws10", nombre: "AWS Cloud", categoria: "tecnica", descripcion: "Infraestructura cloud y servicios gestionados."})
CREATE (h11:Habilidad {hid: "hab_k8s11", nombre: "Kubernetes", categoria: "tecnica", descripcion: "Orquestacion de contenedores en cluster."})
CREATE (h12:Habilidad {hid: "hab_sql12", nombre: "PostgreSQL", categoria: "tecnica", descripcion: "Motor relacional y datos estructurados."});

// 5. Creacion de Proyectos
CREATE (p1:Proyecto {
    pid: "proy_graph01",
    nombre: "Motor de Grafos WheelsOn",
    descripcion: "Plataforma de investigacion y desarrollo para navegacion y analisis de redes complejas.",
    estado: "activo",
    fecha_inicio: date("2026-10-01"),
    tecnologias: ["Python", "Django", "Neo4j", "Cypher", "Vis.js"]
})
CREATE (p2:Proyecto {
    pid: "proy_fintech02",
    nombre: "Plataforma Fintech AI",
    descripcion: "Deteccion de patrones anomalos y analisis de comunidades en redes de pago.",
    estado: "activo",
    fecha_inicio: date("2026-09-01"),
    tecnologias: ["Python", "Docker", "Neo4j", "Machine Learning"]
});

// 6. Creacion de Ofertas
CREATE (o1:Oferta {
    oid: "ofr_dataeng01",
    titulo: "Senior Data Engineer",
    descripcion: "Buscamos especialista en modelos de grafos para optimizar almacenamiento y consultas analiticas.",
    salario_min: 8000000.0,
    salario_max: 12000000.0,
    modalidad: "remoto",
    ubicacion: "Colombia",
    estado: "abierta"
})
CREATE (o2:Oferta {
    oid: "ofr_arch02",
    titulo: "Lead Graph Architect",
    descripcion: "Liderazgo en diseno de ontologias de grafos y algoritmos de recomendacion colaborativa.",
    salario_min: 14000000.0,
    salario_max: 18000000.0,
    modalidad: "hibrido",
    ubicacion: "Bogota",
    estado: "abierta"
});

// 7. Relaciones de Conexión Mutua [:CONECTA_CON]
MATCH (u1:Usuario {uid: "usr_carlos001"}), (u2:Usuario {uid: "usr_angelo002"}) CREATE (u1)-[:CONECTA_CON {estado: "aceptada", fecha: date("2026-11-01")}]->(u2);
MATCH (u1:Usuario {uid: "usr_carlos001"}), (u3:Usuario {uid: "usr_dubal003"}) CREATE (u1)-[:CONECTA_CON {estado: "aceptada", fecha: date("2026-11-01")}]->(u3);
MATCH (u1:Usuario {uid: "usr_carlos001"}), (u4:Usuario {uid: "usr_luis004"}) CREATE (u1)-[:CONECTA_CON {estado: "aceptada", fecha: date("2026-11-01")}]->(u4);
MATCH (u1:Usuario {uid: "usr_carlos001"}), (u5:Usuario {uid: "usr_mateo005"}) CREATE (u1)-[:CONECTA_CON {estado: "aceptada", fecha: date("2026-11-01")}]->(u5);
MATCH (u1:Usuario {uid: "usr_carlos001"}), (u7:Usuario {uid: "usr_jeronimo007"}) CREATE (u1)-[:CONECTA_CON {estado: "aceptada", fecha: date("2026-11-01")}]->(u7);
MATCH (u1:Usuario {uid: "usr_carlos001"}), (u8:Usuario {uid: "usr_wilson008"}) CREATE (u1)-[:CONECTA_CON {estado: "aceptada", fecha: date("2026-11-01")}]->(u8);
MATCH (u1:Usuario {uid: "usr_carlos001"}), (u9:Usuario {uid: "usr_maria009"}) CREATE (u1)-[:CONECTA_CON {estado: "aceptada", fecha: date("2026-11-01")}]->(u9);
MATCH (u1:Usuario {uid: "usr_carlos001"}), (u11:Usuario {uid: "usr_santiago011"}) CREATE (u1)-[:CONECTA_CON {estado: "aceptada", fecha: date("2026-11-01")}]->(u11);

MATCH (u2:Usuario {uid: "usr_angelo002"}), (u3:Usuario {uid: "usr_dubal003"}) CREATE (u2)-[:CONECTA_CON {estado: "aceptada", fecha: date("2026-11-01")}]->(u3);
MATCH (u2:Usuario {uid: "usr_angelo002"}), (u6:Usuario {uid: "usr_juan006"}) CREATE (u2)-[:CONECTA_CON {estado: "aceptada", fecha: date("2026-11-01")}]->(u6);
MATCH (u2:Usuario {uid: "usr_angelo002"}), (u12:Usuario {uid: "usr_jose012"}) CREATE (u2)-[:CONECTA_CON {estado: "aceptada", fecha: date("2026-11-01")}]->(u12);

MATCH (u3:Usuario {uid: "usr_dubal003"}), (u11:Usuario {uid: "usr_santiago011"}) CREATE (u3)-[:CONECTA_CON {estado: "aceptada", fecha: date("2026-11-01")}]->(u11);
MATCH (u3:Usuario {uid: "usr_dubal003"}), (u15:Usuario {uid: "usr_andres015"}) CREATE (u3)-[:CONECTA_CON {estado: "aceptada", fecha: date("2026-11-01")}]->(u15);

MATCH (u7:Usuario {uid: "usr_jeronimo007"}), (u4:Usuario {uid: "usr_luis004"}) CREATE (u7)-[:CONECTA_CON {estado: "aceptada", fecha: date("2026-11-01")}]->(u4);
MATCH (u7:Usuario {uid: "usr_jeronimo007"}), (u10:Usuario {uid: "usr_miguel010"}) CREATE (u7)-[:CONECTA_CON {estado: "aceptada", fecha: date("2026-11-01")}]->(u10);
MATCH (u7:Usuario {uid: "usr_jeronimo007"}), (u9:Usuario {uid: "usr_maria009"}) CREATE (u7)-[:CONECTA_CON {estado: "aceptada", fecha: date("2026-11-01")}]->(u9);

MATCH (u4:Usuario {uid: "usr_luis004"}), (u10:Usuario {uid: "usr_miguel010"}) CREATE (u4)-[:CONECTA_CON {estado: "aceptada", fecha: date("2026-11-01")}]->(u10);
MATCH (u4:Usuario {uid: "usr_luis004"}), (u13:Usuario {uid: "usr_luisc013"}) CREATE (u4)-[:CONECTA_CON {estado: "aceptada", fecha: date("2026-11-01")}]->(u13);

MATCH (u5:Usuario {uid: "usr_mateo005"}), (u15:Usuario {uid: "usr_andres015"}) CREATE (u5)-[:CONECTA_CON {estado: "aceptada", fecha: date("2026-11-01")}]->(u15);
MATCH (u5:Usuario {uid: "usr_mateo005"}), (u9:Usuario {uid: "usr_maria009"}) CREATE (u5)-[:CONECTA_CON {estado: "aceptada", fecha: date("2026-11-01")}]->(u9);
MATCH (u5:Usuario {uid: "usr_mateo005"}), (u11:Usuario {uid: "usr_santiago011"}) CREATE (u5)-[:CONECTA_CON {estado: "aceptada", fecha: date("2026-11-01")}]->(u11);

MATCH (u6:Usuario {uid: "usr_juan006"}), (u8:Usuario {uid: "usr_wilson008"}) CREATE (u6)-[:CONECTA_CON {estado: "aceptada", fecha: date("2026-11-01")}]->(u8);
MATCH (u6:Usuario {uid: "usr_juan006"}), (u14:Usuario {uid: "usr_santiagoa014"}) CREATE (u6)-[:CONECTA_CON {estado: "aceptada", fecha: date("2026-11-01")}]->(u14);
MATCH (u6:Usuario {uid: "usr_juan006"}), (u13:Usuario {uid: "usr_luisc013"}) CREATE (u6)-[:CONECTA_CON {estado: "aceptada", fecha: date("2026-11-01")}]->(u13);

MATCH (u8:Usuario {uid: "usr_wilson008"}), (u14:Usuario {uid: "usr_santiagoa014"}) CREATE (u8)-[:CONECTA_CON {estado: "aceptada", fecha: date("2026-11-01")}]->(u14);
MATCH (u9:Usuario {uid: "usr_maria009"}), (u14:Usuario {uid: "usr_santiagoa014"}) CREATE (u9)-[:CONECTA_CON {estado: "aceptada", fecha: date("2026-11-01")}]->(u14);
MATCH (u12:Usuario {uid: "usr_jose012"}), (u13:Usuario {uid: "usr_luisc013"}) CREATE (u12)-[:CONECTA_CON {estado: "aceptada", fecha: date("2026-11-01")}]->(u13);
MATCH (u11:Usuario {uid: "usr_santiago011"}), (u12:Usuario {uid: "usr_jose012"}) CREATE (u11)-[:CONECTA_CON {estado: "aceptada", fecha: date("2026-11-01")}]->(u12);

// 8. Relaciones Laborales [:TRABAJA_EN]
MATCH (u:Usuario {uid: "usr_mateo005"}), (e:Empresa {eid: "emp_nexus01"}) CREATE (u)-[:TRABAJA_EN {cargo: "Tech Lead & Graph Architect", actual: true, fecha_inicio: date("2024-01-15")}]->(e);
MATCH (u:Usuario {uid: "usr_angelo002"}), (e:Empresa {eid: "emp_techin02"}) CREATE (u)-[:TRABAJA_EN {cargo: "Senior Backend Engineer", actual: true, fecha_inicio: date("2023-03-01")}]->(e);
MATCH (u:Usuario {uid: "usr_dubal003"}), (e:Empresa {eid: "emp_globant03"}) CREATE (u)-[:TRABAJA_EN {cargo: "Principal Data Architect", actual: true, fecha_inicio: date("2022-06-10")}]->(e);
MATCH (u:Usuario {uid: "usr_luis004"}), (e:Empresa {eid: "emp_techin02"}) CREATE (u)-[:TRABAJA_EN {cargo: "Fullstack Developer", actual: true, fecha_inicio: date("2023-08-15")}]->(e);
MATCH (u:Usuario {uid: "usr_carlos001"}), (e:Empresa {eid: "emp_nexus01"}) CREATE (u)-[:TRABAJA_EN {cargo: "Senior Backend & Graph Engineer", actual: true, fecha_inicio: date("2024-02-01")}]->(e);
MATCH (u:Usuario {uid: "usr_juan006"}), (e:Empresa {eid: "emp_globant03"}) CREATE (u)-[:TRABAJA_EN {cargo: "DevOps & SRE Lead", actual: true, fecha_inicio: date("2023-01-10")}]->(e);
MATCH (u:Usuario {uid: "usr_jeronimo007"}), (e:Empresa {eid: "emp_nexus01"}) CREATE (u)-[:TRABAJA_EN {cargo: "Frontend Architect", actual: true, fecha_inicio: date("2023-11-01")}]->(e);
MATCH (u:Usuario {uid: "usr_wilson008"}), (e:Empresa {eid: "emp_techin02"}) CREATE (u)-[:TRABAJA_EN {cargo: "Cybersecurity Specialist", actual: true, fecha_inicio: date("2022-09-01")}]->(e);
MATCH (u:Usuario {uid: "usr_maria009"}), (e:Empresa {eid: "emp_globant03"}) CREATE (u)-[:TRABAJA_EN {cargo: "Senior Product Manager", actual: true, fecha_inicio: date("2023-04-15")}]->(e);
MATCH (u:Usuario {uid: "usr_miguel010"}), (e:Empresa {eid: "emp_techin02"}) CREATE (u)-[:TRABAJA_EN {cargo: "Mobile Tech Lead", actual: true, fecha_inicio: date("2023-10-01")}]->(e);
MATCH (u:Usuario {uid: "usr_santiago011"}), (e:Empresa {eid: "emp_nexus01"}) CREATE (u)-[:TRABAJA_EN {cargo: "Senior Database Administrator", actual: true, fecha_inicio: date("2023-05-01")}]->(e);
MATCH (u:Usuario {uid: "usr_jose012"}), (e:Empresa {eid: "emp_techin02"}) CREATE (u)-[:TRABAJA_EN {cargo: "Backend Software Engineer", actual: true, fecha_inicio: date("2024-03-01")}]->(e);
MATCH (u:Usuario {uid: "usr_luisc013"}), (e:Empresa {eid: "emp_globant03"}) CREATE (u)-[:TRABAJA_EN {cargo: "QA Automation Lead", actual: true, fecha_inicio: date("2023-07-01")}]->(e);
MATCH (u:Usuario {uid: "usr_santiagoa014"}), (e:Empresa {eid: "emp_nexus01"}) CREATE (u)-[:TRABAJA_EN {cargo: "Solutions Architect", actual: true, fecha_inicio: date("2023-12-01")}]->(e);
MATCH (u:Usuario {uid: "usr_andres015"}), (e:Empresa {eid: "emp_globant03"}) CREATE (u)-[:TRABAJA_EN {cargo: "Data Scientist", actual: true, fecha_inicio: date("2024-04-01")}]->(e);

// 9. Publicaciones de Ofertas [:PUBLICA]
MATCH (e:Empresa {eid: "emp_nexus01"}), (o:Oferta {oid: "ofr_dataeng01"}) CREATE (e)-[:PUBLICA {fecha_publicacion: date("2026-11-01")}]->(o);
MATCH (e:Empresa {eid: "emp_globant03"}), (o:Oferta {oid: "ofr_arch02"}) CREATE (e)-[:PUBLICA {fecha_publicacion: date("2026-11-02")}]->(o);

// 10. Requisitos de Ofertas [:REQUIERE]
MATCH (o:Oferta {oid: "ofr_dataeng01"}), (h:Habilidad {hid: "hab_py01"}) CREATE (o)-[:REQUIERE {prioridad: "obligatoria", nivel_minimo: "avanzado"}]->(h);
MATCH (o:Oferta {oid: "ofr_dataeng01"}), (h:Habilidad {hid: "hab_neo02"}) CREATE (o)-[:REQUIERE {prioridad: "obligatoria", nivel_minimo: "intermedio"}]->(h);
MATCH (o:Oferta {oid: "ofr_dataeng01"}), (h:Habilidad {hid: "hab_aws10"}) CREATE (o)-[:REQUIERE {prioridad: "deseable", nivel_minimo: "intermedio"}]->(h);

MATCH (o:Oferta {oid: "ofr_arch02"}), (h:Habilidad {hid: "hab_cyp03"}) CREATE (o)-[:REQUIERE {prioridad: "obligatoria", nivel_minimo: "avanzado"}]->(h);
MATCH (o:Oferta {oid: "ofr_arch02"}), (h:Habilidad {hid: "hab_neo02"}) CREATE (o)-[:REQUIERE {prioridad: "obligatoria", nivel_minimo: "avanzado"}]->(h);
MATCH (o:Oferta {oid: "ofr_arch02"}), (h:Habilidad {hid: "hab_lid05"}) CREATE (o)-[:REQUIERE {prioridad: "deseable", nivel_minimo: "avanzado"}]->(h);
