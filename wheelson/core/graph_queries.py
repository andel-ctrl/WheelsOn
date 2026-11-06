"""
Consultas de grafo de WheelsOn. Todas se ejecutan como Cypher en Neo4j y están
documentadas también en scripts/queries.cypher.
"""

from core.models import Proyecto, Usuario
from core.services import consulta


class GraphAnalyticsService:
    @staticmethod
    def shortest_path_usuarios(uid1, uid2):
        if not uid1 or not uid2 or uid1 == uid2:
            return {"camino": [], "grados": 0, "encontrado": False}

        filas = consulta(
            """
            MATCH (u1:Usuario {uid: $uid1}), (u2:Usuario {uid: $uid2})
            MATCH p = shortestPath((u1)-[:CONECTA_CON*..6]-(u2))
            RETURN nodes(p), length(p)
            """,
            uid1=str(uid1), uid2=str(uid2),
        )
        if not filas:
            return {"camino": [], "grados": 0, "encontrado": False}
        nodos, grados = filas[0]
        return {"camino": [Usuario.inflate(n) for n in nodos], "grados": grados, "encontrado": True}

    @staticmethod
    def contactos_en_comun(uid1, uid2):
        if not uid1 or not uid2 or uid1 == uid2:
            return []
        filas = consulta(
            """
            MATCH (:Usuario {uid: $uid1})-[:CONECTA_CON]-(comun:Usuario)-[:CONECTA_CON]-(:Usuario {uid: $uid2})
            RETURN DISTINCT comun
            ORDER BY comun.nombre ASC
            """,
            uid1=str(uid1), uid2=str(uid2),
        )
        return [Usuario.inflate(fila[0]) for fila in filas]

    @staticmethod
    def usuarios_con_habilidades_similares(uid, limit=10):
        if not uid:
            return []
        filas = consulta(
            """
            MATCH (u1:Usuario {uid: $uid})-[:TIENE_HABILIDAD]->(h:Habilidad)<-[:TIENE_HABILIDAD]-(u2:Usuario)
            WHERE u1 <> u2
            WITH u2, count(h) AS total_compartidas, collect(h.nombre) AS habilidades_comunes
            ORDER BY total_compartidas DESC, u2.nombre ASC
            RETURN u2, total_compartidas, habilidades_comunes
            LIMIT $limit
            """,
            uid=str(uid), limit=int(limit),
        )
        return [
            {
                "usuario": Usuario.inflate(usuario),
                "total_compartidas": total,
                "habilidades_comunes": comunes,
            }
            for usuario, total, comunes in filas
        ]

    @staticmethod
    def ruta_usuario_empresa(uid, eid):
        if not uid or not eid:
            return {"camino": [], "longitud": 0, "encontrado": False}

        # Solo pasa por contactos y empleos: compartir una habilidad con alguien
        # no acerca a una persona a una empresa.
        filas = consulta(
            """
            MATCH (u:Usuario {uid: $uid}), (e:Empresa {eid: $eid})
            MATCH p = shortestPath((u)-[:CONECTA_CON|TRABAJA_EN*..6]-(e))
            WHERE all(r IN relationships(p) WHERE type(r) <> 'TRABAJA_EN' OR coalesce(r.actual, true))
            RETURN [n IN nodes(p) | {
                tipo: labels(n)[0],
                id: coalesce(n.uid, n.eid),
                nombre: CASE WHEN n:Usuario THEN n.nombre + ' ' + n.apellido ELSE n.nombre END
            }], length(p)
            """,
            uid=str(uid), eid=str(eid),
        )
        if not filas:
            return {"camino": [], "longitud": 0, "encontrado": False}
        return {"camino": filas[0][0], "longitud": filas[0][1], "encontrado": True}

    @staticmethod
    def habilidades_mas_demandadas(limit=10):
        filas = consulta(
            """
            MATCH (h:Habilidad)<-[r:REQUIERE]-(o:Oferta {estado: 'abierta'})
            RETURN h.hid, h.nombre, h.categoria,
                   count(o) AS total_ofertas,
                   count(CASE WHEN r.prioridad = 'obligatoria' THEN 1 END) AS obligatorias,
                   count(CASE WHEN r.prioridad = 'deseable' THEN 1 END) AS deseables
            ORDER BY total_ofertas DESC, obligatorias DESC
            LIMIT $limit
            """,
            limit=int(limit),
        )
        return [
            {
                "hid": hid,
                "habilidad": nombre,
                "categoria": categoria,
                "total_ofertas": total,
                "obligatorias": obligatorias,
                "deseables": deseables,
            }
            for hid, nombre, categoria, total, obligatorias, deseables in filas
        ]

    @staticmethod
    def ruta_usuario_oferta(uid, oid):
        """
        Camino más corto de un usuario a una oferta: contactos y empleos hasta la
        empresa que la publica. Postularse no cuenta como camino, porque la pregunta
        es cómo llegar a la oportunidad; por eso se informa aparte en ya_postulado.
        """
        vacio = {"camino": [], "longitud": 0, "encontrado": False, "ya_postulado": False}
        if not uid or not oid:
            return vacio

        postulado = consulta(
            "RETURN EXISTS { (:Usuario {uid: $uid})-[:POSTULA_A]->(:Oferta {oid: $oid}) }",
            uid=str(uid), oid=str(oid),
        )[0][0]

        # Hasta 6 saltos para llegar a la empresa, como en la ruta a empresa, y 1 más a la oferta.
        filas = consulta(
            """
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
            }], [r IN relationships(p) | type(r)], length(p)
            """,
            uid=str(uid), oid=str(oid),
        )
        if not filas:
            return {**vacio, "ya_postulado": postulado}

        pasos, relaciones, longitud = filas[0]
        for paso, relacion in zip(pasos, relaciones + [None]):
            paso["relacion_siguiente"] = relacion
        return {"camino": pasos, "longitud": longitud, "encontrado": True, "ya_postulado": postulado}

    @staticmethod
    def proyectos_relacionados(pid, limit=10):
        """
        Otros proyectos que comparten con este tecnologías o miembros, o cuyos
        equipos tienen personas conectadas entre sí (miembros relacionados).
        """
        if not pid:
            return []

        filas = consulta(
            """
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
            RETURN otro, tecnologias, miembros_comunes, conectados, score
            ORDER BY score DESC, otro.nombre ASC
            LIMIT $limit
            """,
            pid=str(pid), limit=int(limit),
        )
        return [
            {
                "proyecto": Proyecto.inflate(otro),
                "tecnologias_comunes": tecnologias,
                "miembros_comunes": miembros,
                "miembros_conectados": conectados,
                "score": score,
            }
            for otro, tecnologias, miembros, conectados, score in filas
        ]

    @staticmethod
    def candidatos_para_oferta(oid, limit=10):
        """
        Candidatos según competencias y conexiones. Debe cumplir al menos un requisito;
        tener contactos en la empresa sube su puesto, pero no basta por sí solo.
        Quienes ya trabajan en la empresa que publica la oferta no se consideran.
        """
        if not oid:
            return []
        filas = consulta(
            """
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
            RETURN u, total_coincidencias, obligatorias_cubiertas, habilidades_match, contactos,
                   total_coincidencias * 3 + obligatorias_cubiertas * 2 + size(contactos) * 2 AS score,
                   EXISTS { (u)-[:POSTULA_A]->(o) } AS ya_postulado
            ORDER BY score DESC, total_coincidencias DESC, u.nombre ASC
            LIMIT $limit
            """,
            oid=str(oid), limit=int(limit),
        )
        return [
            {
                "usuario": Usuario.inflate(usuario),
                "total_coincidencias": total,
                "obligatorias_cubiertas": obligatorias,
                "habilidades_match": habilidades,
                "contactos_en_empresa": contactos,
                "score": score,
                "ya_postulado": postulado,
            }
            for usuario, total, obligatorias, habilidades, contactos, score, postulado in filas
        ]
