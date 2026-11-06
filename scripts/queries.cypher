// ==============================================================================
// WHEELSON - RED PROFESIONAL BASADA EN BASE DE DATOS DE GRAFOS
// SCRIPT DE CONSULTAS AVANZADAS EN LENGUAJE CYPHER (FASE 6)
// ==============================================================================

// ------------------------------------------------------------------------------
// CONSULTA 1: Ruta mas corta entre dos usuarios (Shortest Path / Grados de Separacion)
// Encuentra la cadena minima de intermediarios entre dos profesionales en la red.
// ------------------------------------------------------------------------------
MATCH (u1:Usuario {uid: $uid1}), (u2:Usuario {uid: $uid2})
MATCH p = shortestPath((u1)-[:CONECTA_CON*..6]-(u2))
RETURN [n IN nodes(p) | {uid: n.uid, nombre: n.nombre, apellido: n.apellido, titulo: n.titulo_profesional}] AS ruta_nodos,
       length(p) AS grados_separacion;

// ------------------------------------------------------------------------------
// CONSULTA 2: Contactos en comun entre dos usuarios (Mutual Connections)
// Identifica profesionales compartidos conectados directamente con ambos usuarios.
// ------------------------------------------------------------------------------
MATCH (u1:Usuario {uid: $uid1})-[:CONECTA_CON]-(comun:Usuario)-[:CONECTA_CON]-(u2:Usuario {uid: $uid2})
WHERE u1 <> u2
RETURN DISTINCT comun.uid AS uid,
       comun.nombre + ' ' + comun.apellido AS nombre_completo,
       comun.titulo_profesional AS titulo,
       comun.ubicacion AS ubicacion
ORDER BY nombre_completo ASC;

// ------------------------------------------------------------------------------
// CONSULTA 3: Usuarios con habilidades tecnicas similares (Similitud por Habilidades)
// Recomienda colegas profesionales con base en la interseccion de habilidades que dominan.
// ------------------------------------------------------------------------------
MATCH (u1:Usuario {uid: $uid1})-[:TIENE_HABILIDAD]->(h:Habilidad)<-[:TIENE_HABILIDAD]-(u2:Usuario)
WHERE u1 <> u2
WITH u2, count(h) AS total_compartidas, collect(h.nombre) AS habilidades_comunes
ORDER BY total_compartidas DESC, u2.nombre ASC
RETURN u2.uid AS uid,
       u2.nombre + ' ' + u2.apellido AS nombre_completo,
       u2.titulo_profesional AS titulo,
       total_compartidas,
       habilidades_comunes
LIMIT $limit;

// ------------------------------------------------------------------------------
// CONSULTA 4: Ruta usuario -> empresa (Networking para Referidos)
// Traza el camino mas corto desde un usuario hacia una empresa a traves de contactos y colegas.
// ------------------------------------------------------------------------------
MATCH (u:Usuario {uid: $uid}), (e:Empresa {eid: $eid})
MATCH p = shortestPath((u)-[:CONECTA_CON|TRABAJA_EN*..6]-(e))
WHERE all(r IN relationships(p) WHERE type(r) <> 'TRABAJA_EN' OR coalesce(r.actual, true))
RETURN [n IN nodes(p) | {
    tipo: labels(n)[0],
    id: coalesce(n.uid, n.eid),
    nombre: CASE WHEN n:Usuario THEN n.nombre + ' ' + n.apellido ELSE n.nombre END
}] AS pasos_ruta,
length(p) AS longitud_camino;

// ------------------------------------------------------------------------------
// CONSULTA 5: Habilidades mas demandadas por el mercado laboral
// Agrupa y contabiliza las habilidades requeridas por vacantes abiertas, discriminando obligatorias.
// ------------------------------------------------------------------------------
MATCH (h:Habilidad)<-[r:REQUIERE]-(o:Oferta {estado: 'abierta'})
RETURN h.hid AS hid,
       h.nombre AS habilidad,
       h.categoria AS categoria,
       count(o) AS total_ofertas,
       count(CASE WHEN r.prioridad = 'obligatoria' THEN 1 END) AS obligatorias,
       count(CASE WHEN r.prioridad = 'deseable' THEN 1 END) AS deseables
ORDER BY total_ofertas DESC, obligatorias DESC
LIMIT $limit;

// ------------------------------------------------------------------------------
// CONSULTA 6: Candidatos recomendados para una oferta segun competencias y conexiones
// Debe cumplir al menos un requisito; los contactos en la empresa suben su puesto.
// Excluye a quienes ya trabajan en la empresa que publica la oferta.
// ------------------------------------------------------------------------------
MATCH (o:Oferta {oid: $oid})-[r:REQUIERE]->(h:Habilidad)<-[:TIENE_HABILIDAD]-(u:Usuario)
WHERE NOT EXISTS {
    MATCH (u)-[t:TRABAJA_EN]->(:Empresa)-[:PUBLICA]->(o)
    WHERE coalesce(t.actual, true)
}
WITH o, u,
     count(DISTINCT h) AS total_coincidencias,
     collect(DISTINCT h.nombre) AS habilidades_match,
     count(DISTINCT CASE WHEN r.prioridad = 'obligatoria' THEN h END) AS obligatorias_cubiertas
OPTIONAL MATCH (u)-[:CONECTA_CON]-(c:Usuario)-[t:TRABAJA_EN]->(:Empresa)-[:PUBLICA]->(o)
WHERE coalesce(t.actual, true)
WITH o, u, total_coincidencias, habilidades_match, obligatorias_cubiertas,
     collect(DISTINCT c.nombre + ' ' + c.apellido) AS contactos
RETURN u.uid AS uid,
       u.nombre + ' ' + u.apellido AS nombre_completo,
       total_coincidencias, obligatorias_cubiertas, habilidades_match, contactos,
       total_coincidencias * 3 + obligatorias_cubiertas * 2 + size(contactos) * 2 AS score,
       EXISTS { (u)-[:POSTULA_A]->(o) } AS ya_postulado
ORDER BY score DESC, total_coincidencias DESC, nombre_completo ASC
LIMIT $limit;

// ------------------------------------------------------------------------------
// CONSULTA 7: Recomendar contactos
// Personas sin conexion directa, puntuadas por contactos, habilidades y empresas en comun.
// ------------------------------------------------------------------------------
MATCH (yo:Usuario {uid: $uid}), (otro:Usuario)
WHERE otro <> yo AND NOT (yo)-[:CONECTA_CON]-(otro)
OPTIONAL MATCH (yo)-[:CONECTA_CON]-(amigo:Usuario)-[:CONECTA_CON]-(otro)
WITH yo, otro, count(DISTINCT amigo) AS amigos_comun,
     collect(DISTINCT amigo.nombre + ' ' + amigo.apellido) AS nombres_amigos
OPTIONAL MATCH (yo)-[:TIENE_HABILIDAD]->(h:Habilidad)<-[:TIENE_HABILIDAD]-(otro)
WITH yo, otro, amigos_comun, nombres_amigos, count(DISTINCT h) AS habs_comun,
     collect(DISTINCT h.nombre) AS nombres_habs
OPTIONAL MATCH (yo)-[t1:TRABAJA_EN]->(e:Empresa)<-[t2:TRABAJA_EN]-(otro)
WHERE coalesce(t1.actual, true) AND coalesce(t2.actual, true)
WITH otro, amigos_comun, nombres_amigos, habs_comun, nombres_habs, count(DISTINCT e) AS emps_comun
WITH otro, amigos_comun, nombres_amigos, habs_comun, nombres_habs, emps_comun,
     amigos_comun * 4 + habs_comun * 2 + emps_comun * 3 AS score
WHERE score > 0
RETURN otro, score, amigos_comun, nombres_amigos[..3], habs_comun, nombres_habs, emps_comun
ORDER BY score DESC, amigos_comun DESC, otro.nombre ASC
LIMIT $limit;

// ------------------------------------------------------------------------------
// CONSULTA 8: Recomendar empleos
// Ofertas abiertas sin postulacion, con el porcentaje de habilidades que ya se cumplen.
// ------------------------------------------------------------------------------
MATCH (u:Usuario {uid: $uid}), (o:Oferta {estado: 'abierta'})
WHERE NOT (u)-[:POSTULA_A]->(o)
MATCH (o)-[r:REQUIERE]->(h:Habilidad)
WITH u, o, r, h, EXISTS { (u)-[:TIENE_HABILIDAD]->(h) } AS la_tiene
WITH o,
     count(h) AS total_requisitos,
     [n IN collect(CASE WHEN la_tiene THEN h.nombre END) WHERE n IS NOT NULL] AS coinciden,
     [n IN collect(CASE WHEN NOT la_tiene THEN h.nombre END) WHERE n IS NOT NULL] AS faltan,
     count(CASE WHEN r.prioridad = 'obligatoria' THEN 1 END) AS total_obligatorias,
     count(CASE WHEN r.prioridad = 'obligatoria' AND la_tiene THEN 1 END) AS obligatorias_cubiertas
WHERE size(coinciden) > 0
OPTIONAL MATCH (e:Empresa)-[:PUBLICA]->(o)
RETURN o, e, total_requisitos, coinciden, faltan, total_obligatorias, obligatorias_cubiertas,
       toFloat(size(coinciden)) / total_requisitos AS proporcion
ORDER BY proporcion DESC, obligatorias_cubiertas DESC, o.fecha_publicacion DESC
LIMIT $limit;

// ------------------------------------------------------------------------------
// CONSULTA 9: Recomendar colaboradores para un proyecto
// Personas externas con habilidades del stack del proyecto o contactos en su equipo.
// ------------------------------------------------------------------------------
MATCH (p:Proyecto {pid: $pid}), (u:Usuario)
WHERE NOT (u)-[:PARTICIPA_EN]->(p)
OPTIONAL MATCH (u)-[:TIENE_HABILIDAD]->(h:Habilidad)
WHERE any(t IN coalesce(p.tecnologias, []) WHERE toLower(h.nombre) CONTAINS toLower(t))
WITH p, u, collect(DISTINCT h.nombre) AS habilidades
OPTIONAL MATCH (u)-[:CONECTA_CON]-(m:Usuario)-[:PARTICIPA_EN]->(p)
WITH u, habilidades, collect(DISTINCT m.nombre + ' ' + m.apellido) AS companeros
WITH u, habilidades, companeros, size(habilidades) * 5 + size(companeros) * 3 AS score
WHERE score > 0
RETURN u, score, habilidades, companeros
ORDER BY score DESC, size(habilidades) DESC, size(companeros) DESC, u.nombre ASC
LIMIT $limit;

// ------------------------------------------------------------------------------
// CONSULTA 10: Recomendar talento para una empresa
// Personas externas con habilidades pedidas en sus ofertas abiertas o contactos internos.
// ------------------------------------------------------------------------------
MATCH (e:Empresa {eid: $eid})
OPTIONAL MATCH (e)-[:PUBLICA]->(:Oferta {estado: 'abierta'})-[:REQUIERE]->(req:Habilidad)
WITH e, collect(DISTINCT req) AS requeridas
MATCH (u:Usuario)
WHERE NOT EXISTS { (u)-[t:TRABAJA_EN]->(e) WHERE coalesce(t.actual, true) }
OPTIONAL MATCH (u)-[:TIENE_HABILIDAD]->(h:Habilidad)
WHERE h IN requeridas
WITH e, u, collect(DISTINCT h.nombre) AS habilidades
OPTIONAL MATCH (u)-[:CONECTA_CON]-(c:Usuario)-[t:TRABAJA_EN]->(e)
WHERE coalesce(t.actual, true)
WITH u, habilidades, count(DISTINCT c) AS conexiones
WITH u, habilidades, conexiones, size(habilidades) * 4 + conexiones * 3 AS score
WHERE score > 0
RETURN u, score, habilidades, conexiones
ORDER BY score DESC, size(habilidades) DESC, u.nombre ASC
LIMIT $limit;

// ------------------------------------------------------------------------------
// CONSULTA 11: Red de conexiones para la analitica
// Devuelve las aristas; centralidad, PageRank y comunidades se calculan con ellas en Python.
// ------------------------------------------------------------------------------
MATCH (a:Usuario)-[:CONECTA_CON]->(b:Usuario)
RETURN a.uid, b.uid;

// ------------------------------------------------------------------------------
// CONSULTA 12: Relaciones del grafo interactivo
// ------------------------------------------------------------------------------
MATCH (a)-[r:CONECTA_CON|TRABAJA_EN|TIENE_HABILIDAD|PARTICIPA_EN|PUBLICA|REQUIERE|POSTULA_A|ADMINISTRA|LIDERA]->(b)
RETURN coalesce(a.uid, a.eid, a.hid, a.pid, a.oid) AS origen,
       coalesce(b.uid, b.eid, b.hid, b.pid, b.oid) AS destino,
       type(r) AS tipo,
       properties(r) AS propiedades;

// ------------------------------------------------------------------------------
// CONSULTA 13: Camino de un usuario a una oferta
// Pasa por contactos y empleos hasta la empresa que publica la oferta.
// ------------------------------------------------------------------------------
MATCH (u:Usuario {uid: $uid}), (o:Oferta {oid: $oid})
MATCH p = shortestPath((u)-[:CONECTA_CON|TRABAJA_EN|PUBLICA*..7]-(o))
WHERE all(r IN relationships(p) WHERE type(r) <> 'TRABAJA_EN' OR coalesce(r.actual, true))
RETURN [n IN nodes(p) | {
    tipo: labels(n)[0],
    id: coalesce(n.uid, n.eid, n.oid),
    nombre: CASE
        WHEN n:Usuario THEN n.nombre + ' ' + n.apellido
        WHEN n:Oferta THEN n.titulo
        ELSE n.nombre
    END
}] AS pasos_ruta,
[r IN relationships(p) | type(r)] AS relaciones,
length(p) AS longitud_camino;

// ------------------------------------------------------------------------------
// CONSULTA 14: Proyectos que comparten tecnologias o miembros relacionados
// Miembros relacionados: personas de ambos equipos conectadas entre si.
// ------------------------------------------------------------------------------
MATCH (p:Proyecto {pid: $pid}), (otro:Proyecto)
WHERE otro <> p
WITH p, otro,
     [t IN coalesce(p.tecnologias, [])
      WHERE toLower(t) IN [x IN coalesce(otro.tecnologias, []) | toLower(x)]] AS tecnologias
OPTIONAL MATCH (p)<-[:PARTICIPA_EN]-(m:Usuario)-[:PARTICIPA_EN]->(otro)
WITH p, otro, tecnologias, collect(DISTINCT m) AS comunes
OPTIONAL MATCH (p)<-[:PARTICIPA_EN]-(a:Usuario)-[:CONECTA_CON]-(b:Usuario)-[:PARTICIPA_EN]->(otro)
WHERE NOT a IN comunes AND NOT b IN comunes
WITH otro, tecnologias, comunes,
     collect(DISTINCT a.nombre + ' ' + a.apellido + ' - ' + b.nombre + ' ' + b.apellido) AS conectados
WITH otro, tecnologias, conectados,
     [m IN comunes | m.nombre + ' ' + m.apellido] AS miembros_comunes,
     size(tecnologias) * 2 + size(comunes) * 3 + size(conectados) AS score
WHERE score > 0
RETURN otro.pid AS pid, otro.nombre AS nombre, tecnologias, miembros_comunes, conectados, score
ORDER BY score DESC, nombre ASC
LIMIT $limit;

// ------------------------------------------------------------------------------
// CONSULTA 15: Lo que administra un usuario
// Empresas, proyectos y ofertas sobre los que tiene permiso de gestion.
// ------------------------------------------------------------------------------
MATCH (u:Usuario {uid: $uid})
OPTIONAL MATCH (u)-[:ADMINISTRA]->(e:Empresa)
OPTIONAL MATCH (e)-[:PUBLICA]->(o:Oferta)
OPTIONAL MATCH (u)-[:LIDERA]->(p:Proyecto)
RETURN u.rol AS rol,
       collect(DISTINCT e.nombre) AS empresas,
       collect(DISTINCT o.titulo) AS ofertas,
       collect(DISTINCT p.nombre) AS proyectos;

// ------------------------------------------------------------------------------
// CONSULTA 16: Dueno de cada empresa y proyecto
// ------------------------------------------------------------------------------
MATCH (u:Usuario)-[r:ADMINISTRA|LIDERA]->(recurso)
RETURN u.nombre + ' ' + u.apellido AS dueno,
       type(r) AS relacion,
       labels(recurso)[0] AS tipo,
       recurso.nombre AS nombre
ORDER BY tipo, nombre;

// ------------------------------------------------------------------------------
// Cupos y postulaciones de un empleo
// Aceptar una postulación crea (:Usuario)-[:TRABAJA_EN]->(:Empresa) con el título del
// empleo como cargo. Al llenarse los cupos, el empleo se cierra y quienes seguían en
// proceso quedan como 'no_seleccionada'.
// ------------------------------------------------------------------------------
MATCH (e:Empresa)-[:PUBLICA]->(o:Oferta {oid: $oid})
RETURN o.titulo AS empleo, e.nombre AS empresa, o.estado AS estado,
       coalesce(o.cupos, 1) AS cupos,
       COUNT { (:Usuario)-[:POSTULA_A]->(o) } AS postulaciones,
       COUNT { (:Usuario)-[r:POSTULA_A]->(o) WHERE r.estado = 'aceptada' } AS contratados;
