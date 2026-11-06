"""
Consultas de grafo de WheelsOn. Todas se ejecutan como Cypher en Neo4j y están
documentadas también en scripts/queries.cypher.
"""

from core.models import Usuario
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
    def candidatos_para_oferta(oid, limit=10):
        if not oid:
            return []
        filas = consulta(
            """
            MATCH (:Oferta {oid: $oid})-[r:REQUIERE]->(h:Habilidad)<-[:TIENE_HABILIDAD]-(u:Usuario)
            WITH u,
                 count(h) AS total_coincidencias,
                 collect(h.nombre) AS habilidades_match,
                 count(CASE WHEN r.prioridad = 'obligatoria' THEN 1 END) AS obligatorias_cubiertas
            ORDER BY total_coincidencias DESC, obligatorias_cubiertas DESC
            RETURN u, total_coincidencias, obligatorias_cubiertas, habilidades_match
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
            }
            for usuario, total, obligatorias, habilidades in filas
        ]
