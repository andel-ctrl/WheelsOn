from collections import deque, Counter
from datetime import date
from core.services import (
    is_neo4j_available,
    UsuarioService,
    EmpresaService,
    HabilidadService,
    ProyectoService,
    OfertaService,
    ConexionService,
    EmpleoService,
    HabilidadUsuarioService,
    ParticipacionProyectoService,
    PublicacionOfertaService,
    RequisitoOfertaService,
    PostulacionService,
)

try:
    from neomodel import db
except ImportError:
    db = None


class GraphAnalyticsService:
    @staticmethod
    def shortest_path_usuarios(uid1, uid2):
        if not uid1 or not uid2 or uid1 == uid2:
            return {"camino": [], "grados": 0, "encontrado": False}

        if is_neo4j_available() and db:
            try:
                cypher = """
                MATCH (u1:Usuario {uid: $uid1}), (u2:Usuario {uid: $uid2})
                MATCH p = shortestPath((u1)-[:CONECTA_CON*..6]-(u2))
                RETURN [n IN nodes(p) | {uid: n.uid, nombre: n.nombre, apellido: n.apellido, titulo: n.titulo_profesional}] AS ruta_nodos,
                       length(p) AS grados
                """
                results, _ = db.cypher_query(cypher, {"uid1": str(uid1), "uid2": str(uid2)})
                if results and results[0]:
                    nodes_data = results[0][0]
                    grados = results[0][1]
                    camino_objs = [UsuarioService.get(n["uid"]) or n for n in nodes_data]
                    return {"camino": camino_objs, "grados": grados, "encontrado": True}
            except Exception:
                pass

        # Algoritmo BFS en memoria
        queue = deque([[str(uid1)]])
        visited = {str(uid1)}
        while queue:
            path = queue.popleft()
            curr = path[-1]
            if curr == str(uid2):
                camino = [UsuarioService.get(uid) for uid in path if UsuarioService.get(uid)]
                return {"camino": camino, "grados": len(path) - 1, "encontrado": True}

            for c in ConexionService.listar(curr):
                next_uid = str(c["usuario"].uid)
                if next_uid not in visited and len(path) <= 6:
                    visited.add(next_uid)
                    queue.append(path + [next_uid])

        return {"camino": [], "grados": 0, "encontrado": False}

    @staticmethod
    def contactos_en_comun(uid1, uid2):
        if not uid1 or not uid2 or uid1 == uid2:
            return []

        if is_neo4j_available() and db:
            try:
                cypher = """
                MATCH (u1:Usuario {uid: $uid1})-[:CONECTA_CON]-(comun:Usuario)-[:CONECTA_CON]-(u2:Usuario {uid: $uid2})
                WHERE u1 <> u2
                RETURN DISTINCT comun.uid AS uid
                ORDER BY comun.nombre ASC
                """
                results, _ = db.cypher_query(cypher, {"uid1": str(uid1), "uid2": str(uid2)})
                if results:
                    return [UsuarioService.get(row[0]) for row in results if UsuarioService.get(row[0])]
            except Exception:
                pass

        con1 = {str(c["usuario"].uid) for c in ConexionService.listar(uid1)}
        con2 = {str(c["usuario"].uid) for c in ConexionService.listar(uid2)}
        comunes_ids = con1 & con2
        return [UsuarioService.get(cid) for cid in comunes_ids if UsuarioService.get(cid)]

    @staticmethod
    def usuarios_con_habilidades_similares(uid, limit=10):
        if not uid:
            return []

        if is_neo4j_available() and db:
            try:
                cypher = """
                MATCH (u1:Usuario {uid: $uid})-[:TIENE_HABILIDAD]->(h:Habilidad)<-[:TIENE_HABILIDAD]-(u2:Usuario)
                WHERE u1 <> u2
                WITH u2, count(h) AS total_compartidas, collect(h.nombre) AS habilidades_comunes
                ORDER BY total_compartidas DESC, u2.nombre ASC
                RETURN u2.uid AS uid, total_compartidas, habilidades_comunes
                LIMIT $limit
                """
                results, _ = db.cypher_query(cypher, {"uid": str(uid), "limit": int(limit)})
                if results:
                    resultado = []
                    for row in results:
                        u = UsuarioService.get(row[0])
                        if u:
                            resultado.append({
                                "usuario": u,
                                "total_compartidas": row[1],
                                "habilidades_comunes": row[2],
                            })
                    return resultado
            except Exception:
                pass

        mis_habilidades = {
            str(item["habilidad"].hid): item["habilidad"].nombre
            for item in HabilidadUsuarioService.listar_por_usuario(uid)
        }
        if not mis_habilidades:
            return []

        ranking = []
        for otro_usuario in UsuarioService.all():
            if str(otro_usuario.uid) == str(uid):
                continue
            otras_habs = {
                str(item["habilidad"].hid): item["habilidad"].nombre
                for item in HabilidadUsuarioService.listar_por_usuario(otro_usuario.uid)
            }
            compartidas_ids = set(mis_habilidades.keys()) & set(otras_habs.keys())
            if compartidas_ids:
                nombres_comunes = [mis_habilidades[hid] for hid in compartidas_ids]
                ranking.append({
                    "usuario": otro_usuario,
                    "total_compartidas": len(compartidas_ids),
                    "habilidades_comunes": nombres_comunes,
                })

        ranking.sort(key=lambda x: x["total_compartidas"], reverse=True)
        return ranking[:limit]

    @staticmethod
    def ruta_usuario_empresa(uid, eid):
        if not uid or not eid:
            return {"camino": [], "longitud": 0, "encontrado": False}

        if is_neo4j_available() and db:
            try:
                cypher = """
                MATCH (u:Usuario {uid: $uid}), (e:Empresa {eid: $eid})
                MATCH p = shortestPath((u)-[*..6]-(e))
                RETURN [n IN nodes(p) | {
                    tipo: labels(n)[0],
                    id: coalesce(n.uid, n.eid, n.pid, n.oid, n.hid),
                    nombre: coalesce(n.nombre_completo, n.nombre, n.titulo)
                }] AS pasos, length(p) AS longitud
                """
                results, _ = db.cypher_query(cypher, {"uid": str(uid), "eid": str(eid)})
                if results and results[0]:
                    return {"camino": results[0][0], "longitud": results[0][1], "encontrado": True}
            except Exception:
                pass

        # Verificacion directa: ¿El usuario ya trabaja allí?
        empleos = EmpleoService.listar_por_usuario(uid)
        for emp in empleos:
            if str(emp["empresa"].eid) == str(eid):
                u = UsuarioService.get(uid)
                return {
                    "camino": [
                        {"tipo": "Usuario", "id": uid, "nombre": u.nombre_completo},
                        {"tipo": "Empresa", "id": eid, "nombre": emp["empresa"].nombre},
                    ],
                    "longitud": 1,
                    "encontrado": True,
                }

        # BFS buscando intermediarios que trabajen en la empresa
        queue = deque([[("Usuario", str(uid))]])
        visited = {("Usuario", str(uid))}

        while queue:
            path = queue.popleft()
            curr_type, curr_id = path[-1]

            if curr_type == "Empresa" and curr_id == str(eid):
                camino_formateado = []
                for t, i in path:
                    if t == "Usuario":
                        usr = UsuarioService.get(i)
                        camino_formateado.append({"tipo": t, "id": i, "nombre": usr.nombre_completo if usr else i})
                    else:
                        emp = EmpresaService.get(i)
                        camino_formateado.append({"tipo": t, "id": i, "nombre": emp.nombre if emp else i})
                return {"camino": camino_formateado, "longitud": len(path) - 1, "encontrado": True}

            if curr_type == "Usuario" and len(path) < 6:
                # 1. Contactos del usuario
                for c in ConexionService.listar(curr_id):
                    nxt = ("Usuario", str(c["usuario"].uid))
                    if nxt not in visited:
                        visited.add(nxt)
                        queue.append(path + [nxt])

                # 2. Empresas donde trabaja el usuario
                for emp in EmpleoService.listar_por_usuario(curr_id):
                    nxt = ("Empresa", str(emp["empresa"].eid))
                    if nxt not in visited:
                        visited.add(nxt)
                        queue.append(path + [nxt])

            elif curr_type == "Empresa" and len(path) < 6:
                # Empleados de la empresa
                for emp_usr in EmpleoService.listar_por_empresa(curr_id):
                    nxt = ("Usuario", str(emp_usr["usuario"].uid))
                    if nxt not in visited:
                        visited.add(nxt)
                        queue.append(path + [nxt])

        return {"camino": [], "longitud": 0, "encontrado": False}

    @staticmethod
    def habilidades_mas_demandadas(limit=10):
        if is_neo4j_available() and db:
            try:
                cypher = """
                MATCH (h:Habilidad)<-[r:REQUIERE]-(o:Oferta {estado: 'abierta'})
                RETURN h.hid AS hid,
                       h.nombre AS habilidad,
                       h.categoria AS categoria,
                       count(o) AS total_ofertas,
                       count(CASE WHEN r.prioridad = 'obligatoria' THEN 1 END) AS obligatorias,
                       count(CASE WHEN r.prioridad = 'deseable' THEN 1 END) AS deseables
                ORDER BY total_ofertas DESC, obligatorias DESC
                LIMIT $limit
                """
                results, _ = db.cypher_query(cypher, {"limit": int(limit)})
                if results:
                    return [
                        {
                            "hid": row[0],
                            "habilidad": row[1],
                            "categoria": row[2],
                            "total_ofertas": row[3],
                            "obligatorias": row[4],
                            "deseables": row[5],
                        }
                        for row in results
                    ]
            except Exception:
                pass

        conteo_total = Counter()
        conteo_obligatorias = Counter()
        conteo_deseables = Counter()
        hab_info = {}

        for oferta in OfertaService.all():
            if oferta.estado == "abierta":
                reqs = RequisitoOfertaService.listar_por_oferta(oferta.oid)
                for req in reqs:
                    hid = str(req["habilidad"].hid)
                    hab_info[hid] = req["habilidad"]
                    conteo_total[hid] += 1
                    if req.get("prioridad") == "obligatoria":
                        conteo_obligatorias[hid] += 1
                    else:
                        conteo_deseables[hid] += 1

        resultado = []
        for hid, total in conteo_total.most_common(limit):
            hab = hab_info.get(hid)
            resultado.append({
                "hid": hid,
                "habilidad": hab.nombre if hab else hid,
                "categoria": getattr(hab, "categoria", "tecnica") if hab else "tecnica",
                "total_ofertas": total,
                "obligatorias": conteo_obligatorias[hid],
                "deseables": conteo_deseables[hid],
            })
        return resultado

    @staticmethod
    def candidatos_para_oferta(oid, limit=10):
        if not oid:
            return []

        if is_neo4j_available() and db:
            try:
                cypher = """
                MATCH (o:Oferta {oid: $oid})-[r:REQUIERE]->(h:Habilidad)<-[t:TIENE_HABILIDAD]-(u:Usuario)
                WITH u,
                     count(h) AS total_coincidencias,
                     collect(h.nombre) AS habilidades_match,
                     count(CASE WHEN r.prioridad = 'obligatoria' THEN 1 END) AS obligatorias_cubiertas
                ORDER BY total_coincidencias DESC, obligatorias_cubiertas DESC
                RETURN u.uid AS uid, total_coincidencias, obligatorias_cubiertas, habilidades_match
                LIMIT $limit
                """
                results, _ = db.cypher_query(cypher, {"oid": str(oid), "limit": int(limit)})
                if results:
                    resultado = []
                    for row in results:
                        u = UsuarioService.get(row[0])
                        if u:
                            resultado.append({
                                "usuario": u,
                                "total_coincidencias": row[1],
                                "obligatorias_cubiertas": row[2],
                                "habilidades_match": row[3],
                            })
                    return resultado
            except Exception:
                pass

        reqs = RequisitoOfertaService.listar_por_oferta(oid)
        if not reqs:
            return []

        req_ids = {str(r["habilidad"].hid): r for r in reqs}
        candidatos = []

        for usuario in UsuarioService.all():
            habs_usuario = HabilidadUsuarioService.listar_por_usuario(usuario.uid)
            coincidencias = []
            obligatorias_count = 0

            for h in habs_usuario:
                hid = str(h["habilidad"].hid)
                if hid in req_ids:
                    coincidencias.append(h["habilidad"].nombre)
                    if req_ids[hid].get("prioridad") == "obligatoria":
                        obligatorias_count += 1

            if coincidencias:
                candidatos.append({
                    "usuario": usuario,
                    "total_coincidencias": len(coincidencias),
                    "obligatorias_cubiertas": obligatorias_count,
                    "habilidades_match": coincidencias,
                })

        candidatos.sort(key=lambda x: (x["total_coincidencias"], x["obligatorias_cubiertas"]), reverse=True)
        return candidatos[:limit]
