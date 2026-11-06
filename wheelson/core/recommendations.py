"""
Motor de recomendaciones de WheelsOn. Cada recomendación es una consulta Cypher
que recorre el grafo en Neo4j; están documentadas en scripts/queries.cypher.
"""

from core.models import Empresa, Oferta, Usuario
from core.services import consulta


class RecommendationEngine:
    @staticmethod
    def recomendar_contactos(uid, limit=10):
        """Personas con las que no estás conectado: pesan contactos, habilidades y empresas en común."""
        if not uid:
            return []

        filas = consulta(
            """
            MATCH (yo:Usuario {uid: $uid}), (otro:Usuario)
            WHERE otro <> yo AND NOT (yo)-[:CONECTA_CON]-(otro) AND NOT (yo)-[:SOLICITA_CONEXION]-(otro)
            OPTIONAL MATCH (yo)-[:CONECTA_CON]-(amigo:Usuario)-[:CONECTA_CON]-(otro)
            WITH yo, otro,
                 count(DISTINCT amigo) AS amigos_comun,
                 collect(DISTINCT amigo.nombre + ' ' + amigo.apellido) AS nombres_amigos
            OPTIONAL MATCH (yo)-[:TIENE_HABILIDAD]->(h:Habilidad)<-[:TIENE_HABILIDAD]-(otro)
            WITH yo, otro, amigos_comun, nombres_amigos,
                 count(DISTINCT h) AS habs_comun,
                 collect(DISTINCT h.nombre) AS nombres_habs
            OPTIONAL MATCH (yo)-[t1:TRABAJA_EN]->(e:Empresa)<-[t2:TRABAJA_EN]-(otro)
            WHERE coalesce(t1.actual, true) AND coalesce(t2.actual, true)
            WITH otro, amigos_comun, nombres_amigos, habs_comun, nombres_habs,
                 count(DISTINCT e) AS emps_comun
            WITH otro, amigos_comun, nombres_amigos, habs_comun, nombres_habs, emps_comun,
                 amigos_comun * 4 + habs_comun * 2 + emps_comun * 3 AS score
            WHERE score > 0
            RETURN otro, score, amigos_comun, nombres_amigos[..3], habs_comun, nombres_habs, emps_comun
            ORDER BY score DESC, amigos_comun DESC, otro.nombre ASC
            LIMIT $limit
            """,
            uid=str(uid), limit=int(limit),
        )

        recomendaciones = []
        for otro, score, amigos, muestra, habs, nombres_habs, emps in filas:
            motivos = []
            if amigos:
                motivos.append(f"{amigos} contacto{'s' if amigos != 1 else ''} en común")
            if habs:
                motivos.append("1 habilidad compartida" if habs == 1 else f"{habs} habilidades compartidas")
            if emps:
                motivos.append("Misma empresa")
            recomendaciones.append({
                "usuario": Usuario.inflate(otro),
                "score": score,
                "amigos_comun": amigos,
                "muestra_amigos": muestra,
                "habs_comun": habs,
                "nombres_habs": nombres_habs,
                "emps_comun": emps,
                "motivo": ", ".join(motivos),
            })
        return recomendaciones

    @staticmethod
    def recomendar_empleos(uid, limit=10):
        """Ofertas abiertas de otras empresas, a las que no te has postulado y con habilidades en común."""
        if not uid:
            return []

        filas = consulta(
            """
            MATCH (u:Usuario {uid: $uid}), (o:Oferta {estado: 'abierta'})
            WHERE NOT (u)-[:POSTULA_A]->(o) AND NOT (u)-[:ADMINISTRA]->(:Empresa)-[:PUBLICA]->(o)
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
            LIMIT $limit
            """,
            uid=str(uid), limit=int(limit),
        )
        return [
            {
                "oferta": Oferta.inflate(oferta),
                "empresa": Empresa.inflate(empresa) if empresa else None,
                "match_porcentaje": round(proporcion * 100, 1),
                "total_match": len(coinciden),
                "total_requisitos": total_requisitos,
                "habilidades_match": coinciden,
                "habilidades_faltantes": faltan,
                "obligatorias_cubiertas": obligatorias_cubiertas,
                "total_obligatorias": total_obligatorias,
            }
            for oferta, empresa, total_requisitos, coinciden, faltan, total_obligatorias,
                obligatorias_cubiertas, proporcion in filas
        ]

    @staticmethod
    def recomendar_colaboradores_proyecto(pid, limit=10):
        """Personas fuera del proyecto con habilidades de su stack o contactos dentro del equipo."""
        if not pid:
            return []

        filas = consulta(
            """
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
            LIMIT $limit
            """,
            pid=str(pid), limit=int(limit),
        )
        return [
            {
                "usuario": Usuario.inflate(usuario),
                "score": score,
                "habilidades_match": habilidades,
                "total_match": len(habilidades),
                "conexiones_equipo": len(companeros),
                "nombres_conexiones": companeros,
            }
            for usuario, score, habilidades, companeros in filas
        ]

    @staticmethod
    def recomendar_candidatos_para_empresa(eid, limit=10):
        """Personas externas con habilidades pedidas en sus ofertas abiertas o contactos en la empresa."""
        if not eid:
            return []

        filas = consulta(
            """
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
            LIMIT $limit
            """,
            eid=str(eid), limit=int(limit),
        )
        return [
            {
                "usuario": Usuario.inflate(usuario),
                "score": score,
                "total_match": len(habilidades),
                "habilidades_match": habilidades,
                "conexiones_internas": conexiones,
            }
            for usuario, score, habilidades, conexiones in filas
        ]
