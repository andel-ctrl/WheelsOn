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


class RecommendationEngine:
    @staticmethod
    def recomendar_contactos(uid, limit=10):
        if not uid:
            return []

        u_principal = UsuarioService.get(uid)
        if not u_principal:
            return []

        if is_neo4j_available() and db:
            try:
                cypher = """
                MATCH (u1:Usuario {uid: $uid})-[:CONECTA_CON]-(amigo:Usuario)-[:CONECTA_CON]-(u2:Usuario)
                WHERE u1 <> u2 AND NOT (u1)-[:CONECTA_CON]-(u2)
                WITH u2, count(DISTINCT amigo) AS amigos_comun, collect(DISTINCT amigo.nombre + ' ' + amigo.apellido) AS nombres_amigos
                OPTIONAL MATCH (u1)-[:TIENE_HABILIDAD]->(h:Habilidad)<-[:TIENE_HABILIDAD]-(u2)
                WITH u2, amigos_comun, nombres_amigos, count(DISTINCT h) AS habs_comun, collect(DISTINCT h.nombre) AS nombres_habs
                OPTIONAL MATCH (u1)-[:TRABAJA_EN]->(emp:Empresa)<-[:TRABAJA_EN]-(u2)
                WITH u2, amigos_comun, nombres_amigos, habs_comun, nombres_habs, count(DISTINCT emp) AS emps_comun
                WITH u2, amigos_comun, nombres_amigos, habs_comun, nombres_habs, emps_comun,
                     (amigos_comun * 4 + habs_comun * 2 + emps_comun * 3) AS score
                ORDER BY score DESC, amigos_comun DESC, u2.nombre ASC
                RETURN u2.uid AS uid, score, amigos_comun, nombres_amigos[..3] AS muestra_amigos,
                       habs_comun, nombres_habs, emps_comun
                LIMIT $limit
                """
                results, _ = db.cypher_query(cypher, {"uid": str(uid), "limit": int(limit)})
                if results:
                    salida = []
                    for row in results:
                        usr = UsuarioService.get(row[0])
                        if usr:
                            salida.append({
                                "usuario": usr,
                                "score": row[1],
                                "amigos_comun": row[2],
                                "muestra_amigos": row[3] or [],
                                "habs_comun": row[4],
                                "nombres_habs": row[5] or [],
                                "emps_comun": row[6],
                                "motivo": f"{row[2]} contacto(s) en común, {row[4]} habilidad(es) afín(es)",
                            })
                    if salida:
                        return salida
            except Exception:
                pass

        amigos_directos = {str(c["usuario"].uid) for c in ConexionService.listar(uid)}
        mis_habilidades = {
            str(h["habilidad"].hid): h["habilidad"].nombre
            for h in HabilidadUsuarioService.listar_por_usuario(uid)
        }
        mis_empresas = {str(e["empresa"].eid) for e in EmpleoService.listar_por_usuario(uid)}

        candidatos = []
        for cand in UsuarioService.all():
            cand_id = str(cand.uid)
            if cand_id == str(uid) or cand_id in amigos_directos:
                continue

            cand_amigos = {str(c["usuario"].uid) for c in ConexionService.listar(cand_id)}
            amigos_comun_ids = amigos_directos & cand_amigos
            amigos_comun_count = len(amigos_comun_ids)

            cand_habs = {
                str(h["habilidad"].hid): h["habilidad"].nombre
                for h in HabilidadUsuarioService.listar_por_usuario(cand_id)
            }
            habs_comun_ids = set(mis_habilidades.keys()) & set(cand_habs.keys())
            habs_comun_count = len(habs_comun_ids)

            cand_emps = {str(e["empresa"].eid) for e in EmpleoService.listar_por_usuario(cand_id)}
            emps_comun_ids = mis_empresas & cand_emps
            emps_comun_count = len(emps_comun_ids)

            score = (amigos_comun_count * 4) + (habs_comun_count * 2) + (emps_comun_count * 3)
            if score > 0 or len(candidatos) < limit:
                amigos_muestra = [
                    u.nombre_completo for u in
                    [UsuarioService.get(i) for i in list(amigos_comun_ids)[:3]]
                    if u
                ]
                habs_muestra = [mis_habilidades[i] for i in habs_comun_ids]

                motivos = []
                if amigos_comun_count > 0:
                    motivos.append(f"{amigos_comun_count} contacto(s) en común")
                if habs_comun_count > 0:
                    motivos.append(f"{habs_comun_count} habilidad(es) compartida(s)")
                if emps_comun_count > 0:
                    motivos.append("Misma empresa o trayectoria")
                if not motivos:
                    motivos.append("Miembro destacado de la red")

                candidatos.append({
                    "usuario": cand,
                    "score": score,
                    "amigos_comun": amigos_comun_count,
                    "muestra_amigos": amigos_muestra,
                    "habs_comun": habs_comun_count,
                    "nombres_habs": habs_muestra,
                    "emps_comun": emps_comun_count,
                    "motivo": ", ".join(motivos),
                })

        candidatos.sort(key=lambda x: (x["score"], x["amigos_comun"], x["habs_comun"]), reverse=True)
        return candidatos[:limit]

    @staticmethod
    def recomendar_empleos(uid, limit=10):
        if not uid:
            return []

        u = UsuarioService.get(uid)
        if not u:
            return []

        if is_neo4j_available() and db:
            try:
                cypher = """
                MATCH (u:Usuario {uid: $uid})
                MATCH (o:Oferta {estado: 'abierta'})
                WHERE NOT (u)-[:POSTULA_A]->(o)
                MATCH (o)-[r:REQUIERE]->(h:Habilidad)
                WITH u, o, collect({hid: h.hid, nombre: h.nombre, prioridad: r.prioridad}) AS requisitos, count(h) AS total_requisitos
                OPTIONAL MATCH (u)-[:TIENE_HABILIDAD]->(h2:Habilidad)
                WHERE h2.hid IN [req IN requisitos | req.hid]
                WITH u, o, requisitos, total_requisitos, collect(h2.nombre) AS habilidades_match, count(h2) AS total_match
                WHERE total_match > 0
                WITH o, total_requisitos, total_match, habilidades_match,
                     round((toFloat(total_match) / toFloat(total_requisitos)) * 100, 1) AS match_pct
                ORDER BY match_pct DESC, total_match DESC, o.fecha_publicacion DESC
                RETURN o.oid AS oid, match_pct, total_match, total_requisitos, habilidades_match
                LIMIT $limit
                """
                results, _ = db.cypher_query(cypher, {"uid": str(uid), "limit": int(limit)})
                if results:
                    salida = []
                    for row in results:
                        oferta = OfertaService.get(row[0])
                        if oferta:
                            empresa = PublicacionOfertaService.obtener_empresa(oferta.oid)
                            salida.append({
                                "oferta": oferta,
                                "empresa": empresa,
                                "match_porcentaje": row[1],
                                "total_match": row[2],
                                "total_requisitos": row[3],
                                "habilidades_match": row[4] or [],
                                "habilidades_faltantes": [],
                            })
                    if salida:
                        return salida
            except Exception:
                pass

        mis_habilidades = {
            str(h["habilidad"].hid): h["habilidad"].nombre
            for h in HabilidadUsuarioService.listar_por_usuario(uid)
        }

        recomendaciones = []
        for oferta in OfertaService.all():
            if oferta.estado != "abierta":
                continue
            if PostulacionService.ha_postulado(uid, oferta.oid):
                continue

            reqs = RequisitoOfertaService.listar_por_oferta(oferta.oid)
            if not reqs:
                continue

            req_dict = {str(r["habilidad"].hid): r for r in reqs}
            matches = []
            faltantes = []
            obligatorias_cubiertas = 0
            total_obligatorias = 0

            for hid, req in req_dict.items():
                es_obligatoria = (req.get("prioridad") == "obligatoria")
                if es_obligatoria:
                    total_obligatorias += 1

                if hid in mis_habilidades:
                    matches.append(req["habilidad"].nombre)
                    if es_obligatoria:
                        obligatorias_cubiertas += 1
                else:
                    faltantes.append(req["habilidad"].nombre)

            if matches:
                pct = round((len(matches) / len(reqs)) * 100, 1)
                empresa = PublicacionOfertaService.obtener_empresa(oferta.oid)
                recomendaciones.append({
                    "oferta": oferta,
                    "empresa": empresa,
                    "match_porcentaje": pct,
                    "total_match": len(matches),
                    "total_requisitos": len(reqs),
                    "habilidades_match": matches,
                    "habilidades_faltantes": faltantes,
                    "obligatorias_cubiertas": obligatorias_cubiertas,
                    "total_obligatorias": total_obligatorias,
                })

        recomendaciones.sort(
            key=lambda x: (x["match_porcentaje"], x["obligatorias_cubiertas"], x["total_match"]),
            reverse=True,
        )
        return recomendaciones[:limit]

    @staticmethod
    def recomendar_colaboradores_proyecto(pid, limit=10):
        if not pid:
            return []

        proyecto = ProyectoService.get(pid)
        if not proyecto:
            return []

        miembros_actuales = {
            str(m["usuario"].uid): m["usuario"]
            for m in ParticipacionProyectoService.listar_por_proyecto(pid)
        }

        # Extraer nombres o palabras clave de tecnologias del proyecto
        tech_val = getattr(proyecto, "tecnologias", "") or ""
        if isinstance(tech_val, list):
            tech_tokens = {str(t).strip().lower() for t in tech_val if str(t).strip()}
        else:
            tech_tokens = {t.strip().lower() for t in str(tech_val).replace(";", ",").split(",") if t.strip()}

        habilidades_clave = []
        for hab in HabilidadService.all():
            if hab.nombre.lower() in tech_tokens or any(tk in hab.nombre.lower() for tk in tech_tokens):
                habilidades_clave.append(hab)

        hab_ids_clave = {str(h.hid): h.nombre for h in habilidades_clave}

        candidatos = []
        for usr in UsuarioService.all():
            uid_str = str(usr.uid)
            if uid_str in miembros_actuales:
                continue

            habs_usr = {
                str(h["habilidad"].hid): h["habilidad"].nombre
                for h in HabilidadUsuarioService.listar_por_usuario(uid_str)
            }

            match_habs = set(hab_ids_clave.keys()) & set(habs_usr.keys())
            conexiones_usr = {str(c["usuario"].uid) for c in ConexionService.listar(uid_str)}
            conexiones_con_equipo = conexiones_usr & set(miembros_actuales.keys())

            score = (len(match_habs) * 5) + (len(conexiones_con_equipo) * 3)

            nombres_coincidentes = [hab_ids_clave[hid] for hid in match_habs]
            companeros_conectados = [
                miembros_actuales[mid].nombre_completo
                for mid in conexiones_con_equipo
                if mid in miembros_actuales
            ]

            if score > 0 or not tech_tokens:
                candidatos.append({
                    "usuario": usr,
                    "score": score,
                    "habilidades_match": nombres_coincidentes,
                    "total_match": len(match_habs),
                    "conexiones_equipo": len(conexiones_con_equipo),
                    "nombres_conexiones": companeros_conectados,
                })

        candidatos.sort(key=lambda x: (x["score"], x["total_match"], x["conexiones_equipo"]), reverse=True)
        return candidatos[:limit]

    @staticmethod
    def recomendar_candidatos_para_empresa(eid, limit=10):
        if not eid:
            return []

        empresa = EmpresaService.get(eid)
        if not empresa:
            return []

        ofertas_empresa = PublicacionOfertaService.listar_por_empresa(eid)
        req_habilidades = {}
        for ofr in ofertas_empresa:
            if ofr.estado == "abierta":
                for req in RequisitoOfertaService.listar_por_oferta(ofr.oid):
                    hid = str(req["habilidad"].hid)
                    req_habilidades[hid] = req["habilidad"].nombre

        empleados_actuales = {
            str(emp["usuario"].uid)
            for emp in EmpleoService.listar_por_empresa(eid)
        }

        candidatos = []
        for usr in UsuarioService.all():
            uid_str = str(usr.uid)
            if uid_str in empleados_actuales:
                continue

            habs_usr = {
                str(h["habilidad"].hid): h["habilidad"].nombre
                for h in HabilidadUsuarioService.listar_por_usuario(uid_str)
            }

            matches = set(req_habilidades.keys()) & set(habs_usr.keys())
            conexiones_usr = {str(c["usuario"].uid) for c in ConexionService.listar(uid_str)}
            conexiones_empleados = conexiones_usr & empleados_actuales

            score = (len(matches) * 4) + (len(conexiones_empleados) * 3)
            if score > 0 or not req_habilidades:
                candidatos.append({
                    "usuario": usr,
                    "score": score,
                    "total_match": len(matches),
                    "habilidades_match": [req_habilidades[h] for h in matches if h in req_habilidades],
                    "conexiones_internas": len(conexiones_empleados),
                })

        candidatos.sort(key=lambda x: (x["score"], x["total_match"]), reverse=True)
        return candidatos[:limit]
