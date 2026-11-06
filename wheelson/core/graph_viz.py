# -*- coding: utf-8 -*-
"""
Servicio de Visualizacion de Grafos Interactiva (Fase 9)
Proyecto WheelsOn - Red Social Profesional con Base de Datos de Grafos
Genera estructuras optimizadas para Vis.js Network a partir de los datos de Neo4j.
"""

from core.services import (
    UsuarioService, EmpresaService, HabilidadService, ProyectoService, OfertaService,
    consulta,
)


class GrafoVisualizacionService:
    """
    Servicio encargado de extraer la topología completa o subgrafos
    de la red social y transformarlos al formato de nodos y aristas de Vis.js.
    """

    # Cada tipo de nodo tiene color y forma propios, para distinguirlos también con daltonismo.
    COLOR_MAP = {
        "Usuario": {"background": "#455DD1", "border": "#3448AE", "highlight": {"background": "#3448AE", "border": "#2A1A2E"}},
        "UsuarioActivo": {"background": "#2F3F9E", "border": "#232F78", "highlight": {"background": "#232F78", "border": "#2A1A2E"}},
        "Empresa": {"background": "#14A3B0", "border": "#0A7C87", "highlight": {"background": "#0A7C87", "border": "#2A1A2E"}},
        "Habilidad": {"background": "#9A831C", "border": "#7A6815", "highlight": {"background": "#7A6815", "border": "#2A1A2E"}},
        "Proyecto": {"background": "#9B3096", "border": "#7C2678", "highlight": {"background": "#7C2678", "border": "#2A1A2E"}},
        "Oferta": {"background": "#A33A20", "border": "#832E19", "highlight": {"background": "#832E19", "border": "#2A1A2E"}},
    }
    FUENTE_NODO = {"color": "#2A1A2E", "face": "Manrope, sans-serif", "strokeWidth": 3, "strokeColor": "#FFFFFF"}

    @classmethod
    def obtener_datos_grafo(cls, subgrafo_uid=None, tipos_nodo=None, busqueda=None, max_nodos=150, permisos=None):
        """
        Extrae y compila nodos y aristas para Vis.js.
        Soporta filtrado por tipo de entidad, búsqueda y extracción de subgrafos egocéntricos.
        Las postulaciones son privadas: solo se incluyen las que `permisos` autoriza a ver.
        """
        # 1. Obtener entidades de Neo4j
        usuarios = UsuarioService.all(limit=max_nodos)
        empresas = EmpresaService.all(limit=max_nodos)
        habilidades = HabilidadService.all(limit=max_nodos)
        proyectos = ProyectoService.all(limit=max_nodos)
        ofertas = OfertaService.all(limit=max_nodos)

        # Mapeo de grados de conexión para escalado dinámico de nodos
        grados = {}
        def inc_grado(nid):
            grados[str(nid)] = grados.get(str(nid), 0) + 1

        # 2. Compilar Aristas
        edges_raw = []
        seen_edges = set()

        def agregar_arista(origen, destino, label, color_edge, dirigida=True, datos=None):
            if not origen or not destino or origen == destino:
                return
            s_id, t_id = str(origen), str(destino)
            key = (s_id, t_id, label) if dirigida else tuple(sorted([s_id, t_id])) + (label,)
            if key in seen_edges:
                return
            seen_edges.add(key)
            inc_grado(s_id)
            inc_grado(t_id)

            edge = {
                "id": f"e_{len(edges_raw)+1}",
                "from": s_id,
                "to": t_id,
                "label": label,
                "title": f"Relación: {label}",
                "color": {"color": color_edge, "highlight": "#D9483B", "hover": "#D9483B"},
                "arrows": "to" if dirigida else "",
                "font": {"color": "#756578", "size": 9, "face": "JetBrains Mono, monospace", "align": "middle", "strokeWidth": 3, "strokeColor": "#FFFFFF"},
                "smooth": {"type": "continuous", "roundness": 0.2},
                "datos": datos or {}
            }
            edges_raw.append(edge)

        # Las relaciones se leen de Neo4j, con los mismos nombres que tienen en el modelo.
        relaciones = consulta(
            """
            MATCH (a)-[r:CONECTA_CON|TRABAJA_EN|TIENE_HABILIDAD|PARTICIPA_EN|PUBLICA|REQUIERE|POSTULA_A|ADMINISTRA|LIDERA]->(b)
            RETURN coalesce(a.uid, a.eid, a.hid, a.pid, a.oid),
                   coalesce(b.uid, b.eid, b.hid, b.pid, b.oid),
                   type(r),
                   properties(r)
            """
        )
        for origen, destino, tipo, propiedades in relaciones:
            if tipo == "POSTULA_A" and not (permisos and permisos.ver_postulacion(origen, destino)):
                continue
            agregar_arista(
                origen,
                destino,
                tipo,
                "#A99AAA" if tipo == "CONECTA_CON" else "#C9BEC9",
                dirigida=tipo != "CONECTA_CON",
                datos={clave: str(valor) for clave, valor in propiedades.items()},
            )

        # 3. Compilar Nodos
        nodes_raw = []

        # Usuarios
        for u in usuarios:
            k = grados.get(str(u.uid), 0)
            es_central = str(u.uid) in (str(subgrafo_uid), str(permisos.uid if permisos else None))
            color_scheme = cls.COLOR_MAP["UsuarioActivo"] if es_central else cls.COLOR_MAP["Usuario"]
            node_size = 28 if es_central else max(16, min(24, 16 + (k * 1.5)))
            
            nodes_raw.append({
                "id": str(u.uid),
                "label": u.nombre_completo,
                "group": "Usuario",
                "shape": "dot",
                "size": node_size,
                "color": color_scheme,
                "font": {**cls.FUENTE_NODO, "size": 11},
                "title": f"{u.nombre_completo}\n{u.titulo_profesional or 'Profesional'}\nConexiones: {k}",
                "properties": {
                    "tipo": "Usuario",
                    "uid": str(u.uid),
                    "nombre": u.nombre_completo,
                    "rol": u.titulo_profesional or "Profesional de Software",
                    "email": u.email,
                    "ubicacion": u.ubicacion or "No especificada",
                    "bio": u.biografia or "Sin biografía registrada.",
                    "conexiones_count": k,
                    "url": f"/usuarios/{u.uid}/"
                }
            })

        # Empresas
        for emp in empresas:
            k = grados.get(str(emp.eid), 0)
            nodes_raw.append({
                "id": str(emp.eid),
                "label": emp.nombre,
                "group": "Empresa",
                "shape": "square",
                "size": max(18, min(26, 18 + k)),
                "color": cls.COLOR_MAP["Empresa"],
                "font": {**cls.FUENTE_NODO, "size": 11},
                "title": f"Empresa: {emp.nombre}\n{emp.industria}\n{emp.ubicacion}",
                "properties": {
                    "tipo": "Empresa",
                    "eid": str(emp.eid),
                    "nombre": emp.nombre,
                    "industria": emp.industria,
                    "ubicacion": emp.ubicacion,
                    "tamano": getattr(emp, "tamano", "Mediana"),
                    "url": f"/empresas/{emp.eid}/"
                }
            })

        # Habilidades
        for h in habilidades:
            k = grados.get(str(h.hid), 0)
            nodes_raw.append({
                "id": str(h.hid),
                "label": h.nombre,
                "group": "Habilidad",
                "shape": "diamond",
                "size": max(14, min(22, 14 + k)),
                "color": cls.COLOR_MAP["Habilidad"],
                "font": {**cls.FUENTE_NODO, "size": 10},
                "title": f"Habilidad: {h.nombre}\nCategoría: {h.categoria}\nAdoptada por {k} nodos",
                "properties": {
                    "tipo": "Habilidad",
                    "hid": str(h.hid),
                    "nombre": h.nombre,
                    "categoria": h.categoria,
                    "demanda_count": k
                }
            })

        # Proyectos
        for p in proyectos:
            k = grados.get(str(p.pid), 0)
            nodes_raw.append({
                "id": str(p.pid),
                "label": p.nombre,
                "group": "Proyecto",
                "shape": "hexagon",
                "size": max(17, min(25, 17 + k)),
                "color": cls.COLOR_MAP["Proyecto"],
                "font": {**cls.FUENTE_NODO, "size": 11},
                "title": f"Proyecto: {p.nombre}\nEstado: {p.estado}\nColaboradores: {k}",
                "properties": {
                    "tipo": "Proyecto",
                    "pid": str(p.pid),
                    "nombre": p.nombre,
                    "estado": p.estado,
                    "descripcion": p.descripcion,
                    "tecnologias": p.tecnologias if isinstance(p.tecnologias, list) else [],
                    "url": f"/proyectos/{p.pid}/"
                }
            })

        # Ofertas de Empleo
        for o in ofertas:
            k = grados.get(str(o.oid), 0)
            nodes_raw.append({
                "id": str(o.oid),
                "label": o.titulo,
                "group": "Oferta",
                "shape": "triangle",
                "size": max(16, min(23, 16 + k)),
                "color": cls.COLOR_MAP["Oferta"],
                "font": {**cls.FUENTE_NODO, "size": 10},
                "title": f"Vacante: {o.titulo}\nModalidad: {o.modalidad}\nSalario: ${o.salario_min}-${o.salario_max}",
                "properties": {
                    "tipo": "Oferta",
                    "oid": str(o.oid),
                    "titulo": o.titulo,
                    "modalidad": o.modalidad,
                    "salario_min": o.salario_min,
                    "salario_max": o.salario_max,
                    "ubicacion": o.ubicacion,
                    "url": f"/ofertas/{o.oid}/"
                }
            })

        # 4. Filtrado por Tipo de Nodo si se especificó
        if tipos_nodo:
            tipos_set = set(tipos_nodo)
            nodes_raw = [n for n in nodes_raw if n["group"] in tipos_set]

        # 5. Filtrado por Subgrafo Egocéntrico si se solicitó
        if subgrafo_uid:
            s_uid = str(subgrafo_uid)
            # Nodos directamente conectados al usuario (1 salto)
            vecinos_ids = {s_uid}
            for e in edges_raw:
                if e["from"] == s_uid:
                    vecinos_ids.add(e["to"])
                elif e["to"] == s_uid:
                    vecinos_ids.add(e["from"])

            nodes_raw = [n for n in nodes_raw if n["id"] in vecinos_ids]

        # 6. Filtrado de Aristas para mantener solo aquellas cuyos nodos extremos existan
        node_ids_validos = {n["id"] for n in nodes_raw}
        edges_final = [
            e for e in edges_raw
            if e["from"] in node_ids_validos and e["to"] in node_ids_validos
        ]

        # 7. Filtrado por Búsqueda (resaltar o aislar)
        if busqueda:
            b_lower = busqueda.strip().lower()
            for n in nodes_raw:
                if b_lower in n["label"].lower():
                    n["size"] = n["size"] + 8
                    n["borderWidth"] = 3

        stats = {
            "total_nodos": len(nodes_raw),
            "total_aristas": len(edges_final),
            "usuarios": sum(1 for n in nodes_raw if n["group"] == "Usuario"),
            "empresas": sum(1 for n in nodes_raw if n["group"] == "Empresa"),
            "habilidades": sum(1 for n in nodes_raw if n["group"] == "Habilidad"),
            "proyectos": sum(1 for n in nodes_raw if n["group"] == "Proyecto"),
            "ofertas": sum(1 for n in nodes_raw if n["group"] == "Oferta")
        }

        return {
            "nodes": nodes_raw,
            "edges": edges_final,
            "stats": stats
        }
