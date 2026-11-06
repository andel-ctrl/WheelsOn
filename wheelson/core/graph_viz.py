# -*- coding: utf-8 -*-
"""
Servicio de Visualizacion de Grafos Interactiva (Fase 9)
Proyecto WheelsOn - Red Social Profesional con Base de Datos de Grafos
Genera estructuras optimizadas para Vis.js Network con compatibilidad Dual-Mode.
"""

from core.services import (
    UsuarioService, EmpresaService, HabilidadService, ProyectoService, OfertaService,
    _memory_conexiones, _memory_empleos, _memory_habilidades_usuario,
    _memory_participaciones, _memory_publicaciones, _memory_requisitos,
    _memory_postulaciones, is_neo4j_available
)


class GrafoVisualizacionService:
    """
    Servicio encargado de extraer la topología completa o subgrafos
    de la red social y transformarlos al formato de nodos y aristas de Vis.js.
    """

    COLOR_MAP = {
        "Usuario": {
            "background": "#00b84c",
            "border": "#34d399",
            "highlight": {"background": "#059669", "border": "#6ee7b7"},
            "font": {"color": "#ffffff"}
        },
        "UsuarioActivo": {
            "background": "#059669",
            "border": "#10b981",
            "highlight": {"background": "#047857", "border": "#34d399"},
            "font": {"color": "#ffffff"}
        },
        "Empresa": {
            "background": "#06b6d4",
            "border": "#22d3ee",
            "highlight": {"background": "#0891b2", "border": "#a5f3fc"},
            "font": {"color": "#ffffff"}
        },
        "Habilidad": {
            "background": "#f59e0b",
            "border": "#fbbf24",
            "highlight": {"background": "#d97706", "border": "#fde68a"},
            "font": {"color": "#ffffff"}
        },
        "Proyecto": {
            "background": "#8b5cf6",
            "border": "#a78bfa",
            "highlight": {"background": "#7c3aed", "border": "#ddd6fe"},
            "font": {"color": "#ffffff"}
        },
        "Oferta": {
            "background": "#f43f5e",
            "border": "#fb7185",
            "highlight": {"background": "#e11d48", "border": "#fecdd3"},
            "font": {"color": "#ffffff"}
        }
    }

    @classmethod
    def obtener_datos_grafo(cls, subgrafo_uid=None, tipos_nodo=None, busqueda=None, max_nodos=150):
        """
        Extrae y compila nodos y aristas para Vis.js.
        Soporta filtrado por tipo de entidad, búsqueda y extracción de subgrafos egocéntricos.
        """
        # 1. Obtener entidades del backend (Online / Offline)
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
                "color": {"color": color_edge, "highlight": "#00b84c", "hover": "#ffffff"},
                "arrows": "to" if dirigida else "",
                "font": {"color": "#94a3b8", "size": 9, "face": "monospace", "align": "middle", "strokeWidth": 0},
                "smooth": {"type": "continuous", "roundness": 0.2},
                "datos": datos or {}
            }
            edges_raw.append(edge)

        # 2.1 Conexiones sociales (:CONECTADO_CON)
        for e in _memory_conexiones._edges:
            agregar_arista(e.get("source_id"), e.get("target_id"), "CONECTADO_CON", "#334155", dirigida=False, datos=e)

        # 2.2 Experiencia laboral (:TRABAJA_EN)
        for e in _memory_empleos._edges:
            agregar_arista(e.get("source_id"), e.get("target_id"), "TRABAJA_EN", "#1e293b", dirigida=True, datos=e)

        # 2.3 Habilidades de usuarios (:TIENE_HABILIDAD)
        for e in _memory_habilidades_usuario._edges:
            agregar_arista(e.get("source_id"), e.get("target_id"), "TIENE_HABILIDAD", "#1e293b", dirigida=True, datos=e)

        # 2.4 Proyectos desarrollados (:DESARROLLO)
        for e in _memory_participaciones._edges:
            agregar_arista(e.get("source_id"), e.get("target_id"), "DESARROLLO", "#1e293b", dirigida=True, datos=e)

        # 2.5 Empresas publican ofertas (:PUBLICA)
        for e in _memory_publicaciones._edges:
            agregar_arista(e.get("source_id"), e.get("target_id"), "PUBLICA", "#1e293b", dirigida=True, datos=e)

        # 2.6 Requisitos de ofertas (:REQUIERE)
        for e in _memory_requisitos._edges:
            agregar_arista(e.get("source_id"), e.get("target_id"), "REQUIERE", "#1e293b", dirigida=True, datos=e)

        # 2.7 Postulaciones laborales (:APLICO_A)
        for e in _memory_postulaciones._edges:
            agregar_arista(e.get("source_id"), e.get("target_id"), "APLICO_A", "#1e293b", dirigida=True, datos=e)

        # 3. Compilar Nodos
        nodes_raw = []

        # Usuarios
        for u in usuarios:
            k = grados.get(str(u.uid), 0)
            es_central = (str(u.uid) == str(subgrafo_uid)) or (str(u.uid) == "usr_mateo005")
            color_scheme = cls.COLOR_MAP["UsuarioActivo"] if es_central else cls.COLOR_MAP["Usuario"]
            node_size = 28 if es_central else max(16, min(24, 16 + (k * 1.5)))
            
            nodes_raw.append({
                "id": str(u.uid),
                "label": u.nombre_completo,
                "group": "Usuario",
                "shape": "dot",
                "size": node_size,
                "color": color_scheme,
                "font": {"color": "#f8fafc", "size": 11, "face": "Helvetica", "strokeWidth": 2, "strokeColor": "#0d0f12"},
                "title": f"<b>{u.nombre_completo}</b><br>{u.titulo_profesional or 'Profesional'}<br>Conexiones: {k}",
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
                "shape": "dot",
                "size": max(18, min(26, 18 + k)),
                "color": cls.COLOR_MAP["Empresa"],
                "font": {"color": "#a5f3fc", "size": 11, "face": "Helvetica", "strokeWidth": 2, "strokeColor": "#0d0f12"},
                "title": f"<b>Empresa: {emp.nombre}</b><br>{emp.industria}<br>{emp.ubicacion}",
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
                "shape": "dot",
                "size": max(14, min(22, 14 + k)),
                "color": cls.COLOR_MAP["Habilidad"],
                "font": {"color": "#fde68a", "size": 10, "face": "Helvetica", "strokeWidth": 2, "strokeColor": "#0d0f12"},
                "title": f"<b>Habilidad: {h.nombre}</b><br>Categoría: {h.categoria}<br>Adoptada por {k} nodos",
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
                "shape": "dot",
                "size": max(17, min(25, 17 + k)),
                "color": cls.COLOR_MAP["Proyecto"],
                "font": {"color": "#ddd6fe", "size": 11, "face": "Helvetica", "strokeWidth": 2, "strokeColor": "#0d0f12"},
                "title": f"<b>Proyecto: {p.nombre}</b><br>Estado: {p.estado}<br>Colaboradores: {k}",
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
                "shape": "dot",
                "size": max(16, min(23, 16 + k)),
                "color": cls.COLOR_MAP["Oferta"],
                "font": {"color": "#fecdd3", "size": 10, "face": "Helvetica", "strokeWidth": 2, "strokeColor": "#0d0f12"},
                "title": f"<b>Vacante: {o.titulo}</b><br>Modalidad: {o.modalidad}<br>Salario: ${o.salario_min}-${o.salario_max}",
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
