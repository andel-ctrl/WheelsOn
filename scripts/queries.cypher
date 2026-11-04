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
MATCH p = shortestPath((u)-[*..6]-(e))
RETURN [n IN nodes(p) | {
    tipo: labels(n)[0],
    id: coalesce(n.uid, n.eid, n.pid, n.oid, n.hid),
    nombre: coalesce(n.nombre_completo, n.nombre, n.titulo)
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
// CONSULTA 6: Candidatos recomendados para una oferta laboral (Match Semantico)
// Cruza los requerimientos obligatorios y deseables de una oferta con las habilidades de los usuarios.
// ------------------------------------------------------------------------------
MATCH (o:Oferta {oid: $oid})-[r:REQUIERE]->(h:Habilidad)<-[t:TIENE_HABILIDAD]-(u:Usuario)
WITH u,
     count(h) AS total_coincidencias,
     collect(h.nombre) AS habilidades_match,
     count(CASE WHEN r.prioridad = 'obligatoria' THEN 1 END) AS obligatorias_cubiertas
ORDER BY total_coincidencias DESC, obligatorias_cubiertas DESC
RETURN u.uid AS uid,
       u.nombre + ' ' + u.apellido AS nombre_completo,
       u.titulo_profesional AS titulo,
       u.ubicacion AS ubicacion,
       total_coincidencias,
       obligatorias_cubiertas,
       habilidades_match
LIMIT $limit;
