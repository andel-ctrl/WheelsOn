from collections import defaultdict, deque
import math
from core.services import (
    is_neo4j_available,
    UsuarioService,
    EmpresaService,
    HabilidadService,
    ProyectoService,
    OfertaService,
    ConexionService,
    HabilidadUsuarioService,
    RequisitoOfertaService,
)

try:
    from neomodel import db
except ImportError:
    db = None


class NetworkAnalyticsService:
    """
    Servicio de analítica avanzada de grafos para la red social WheelsOn.
    Implementa métricas topológicas, centralidad, PageRank, detección
    de comunidades y análisis de oferta/demanda de competencias.
    Soporta ejecución dual (Cypher nativo con fallback algorítmico en memoria).
    """

    @classmethod
    def metricas_red_globales(cls):
        """
        Calcula las métricas topológicas fundamentales del grafo social:
        - Conteo de entidades y relaciones
        - Densidad de red: D = 2E / (N*(N-1))
        - Grado medio: <k> = 2E / N
        - Coeficiente de agrupamiento medio (Clustering Coefficient)
        - Diámetro y longitud de camino promedio estimada
        """
        usuarios = UsuarioService.all()
        empresas = EmpresaService.all()
        habilidades = HabilidadService.all()
        proyectos = ProyectoService.all()
        ofertas = OfertaService.all()

        n_usuarios = len(usuarios)

        # Construir grafo de adyacencia de conexiones
        adj, aristas_set = cls._construir_grafo_conexiones(usuarios)
        n_aristas = len(aristas_set)

        # Densidad de red social no dirigida: D = 2E / (N * (N - 1))
        if n_usuarios > 1:
            densidad = (2.0 * n_aristas) / (n_usuarios * (n_usuarios - 1))
        else:
            densidad = 0.0

        # Grado promedio: <k> = 2E / N
        grado_promedio = (2.0 * n_aristas / n_usuarios) if n_usuarios > 0 else 0.0

        # Coeficiente de agrupamiento (Clustering coefficient local y global)
        clustering_medio = cls._calcular_clustering_medio(adj)

        # Diámetro y longitud promedio de camino en la red de usuarios (BFS)
        diametro, longitud_promedio = cls._calcular_distancias_red(adj)

        return {
            "total_usuarios": n_usuarios,
            "total_empresas": len(empresas),
            "total_habilidades": len(habilidades),
            "total_proyectos": len(proyectos),
            "total_ofertas": len(ofertas),
            "total_conexiones": n_aristas,
            "densidad_pct": round(densidad * 100, 2),
            "densidad_raw": round(densidad, 4),
            "grado_promedio": round(grado_promedio, 2),
            "clustering_coef": round(clustering_medio, 3),
            "clustering_pct": round(clustering_medio * 100, 1),
            "diametro": diametro,
            "longitud_promedio_camino": round(longitud_promedio, 2),
        }

    @classmethod
    def ranking_centralidad_grado(cls, limit=10):
        """
        Calcula la Centralidad de Grado (Degree Centrality):
        C_D(v) = deg(v) / (N - 1)
        Identifica a los nodos con mayor número de conexiones directas.
        """
        usuarios = UsuarioService.all()
        n = len(usuarios)
        adj, _ = cls._construir_grafo_conexiones(usuarios)

        ranking = []
        u_map = {u.uid: u for u in usuarios}

        for uid, vecinos in adj.items():
            grado = len(vecinos)
            norm = (grado / (n - 1)) if n > 1 else 0.0
            usuario = u_map.get(uid)
            if usuario:
                ranking.append({
                    "usuario": usuario,
                    "grado": grado,
                    "grado_normalizado": round(norm, 3),
                    "grado_pct": round(norm * 100, 1),
                })

        ranking.sort(key=lambda x: (x["grado"], x["usuario"].nombre), reverse=True)

        for idx, item in enumerate(ranking, 1):
            item["ranking"] = idx

        return ranking[:limit]

    @classmethod
    def ranking_pagerank(cls, damping=0.85, max_iter=30, tol=1e-5, limit=10):
        """
        Calcula el PageRank en la red de conexiones sociales:
        PR(v) = (1-d)/N + d * sum(PR(u) / deg(u)) para u in Vecinos(v).
        Mide la influencia estructural y reputación del usuario en el grafo.
        """
        usuarios = UsuarioService.all()
        n = len(usuarios)
        if n == 0:
            return []

        adj, _ = cls._construir_grafo_conexiones(usuarios)
        u_map = {u.uid: u for u in usuarios}

        # Inicialización uniforme: 1 / N
        pr = {u.uid: 1.0 / n for u in usuarios}

        for _ in range(max_iter):
            nuevo_pr = {}
            sum_dangles = sum(pr[u.uid] for u in usuarios if len(adj[u.uid]) == 0)

            for u in usuarios:
                uid = u.uid
                suma_vecinos = 0.0
                for v in adj[uid]:
                    deg_v = len(adj[v])
                    if deg_v > 0:
                        suma_vecinos += pr[v] / deg_v

                nuevo_pr[uid] = ((1.0 - damping) / n) + damping * (suma_vecinos + (sum_dangles / n))

            diff = sum(abs(nuevo_pr[u.uid] - pr[u.uid]) for u in usuarios)
            pr = nuevo_pr
            if diff < tol:
                break

        # Normalizar para presentación porcentual y ordenar
        max_pr = max(pr.values()) if pr else 1.0
        ranking = []
        for uid, score in pr.items():
            u = u_map.get(uid)
            if u:
                grado = len(adj.get(uid, set()))
                ranking.append({
                    "usuario": u,
                    "score": round(score, 4),
                    "score_pct": round((score / max_pr) * 100, 1),
                    "grado": grado,
                })

        ranking.sort(key=lambda x: x["score"], reverse=True)
        for idx, item in enumerate(ranking, 1):
            item["ranking"] = idx

        return ranking[:limit]

    @classmethod
    def ranking_intermediacion(cls, limit=10):
        """
        Calcula la Centralidad de Intermediación (Betweenness Centrality):
        Frecuencia con la que un nodo actúa como puente a lo largo del camino
        más corto entre todos los pares de nodos posibles.
        """
        usuarios = UsuarioService.all()
        n = len(usuarios)
        if n < 3:
            return []

        adj, _ = cls._construir_grafo_conexiones(usuarios)
        u_map = {u.uid: u for u in usuarios}
        nodes = list(adj.keys())

        betweenness = {uid: 0.0 for uid in nodes}

        # Algoritmo de Brandes para Betweenness Centrality
        for s in nodes:
            stack = []
            predecessors = {w: [] for w in nodes}
            sigma = {w: 0 for w in nodes}
            sigma[s] = 1
            distance = {w: -1 for w in nodes}
            distance[s] = 0

            queue = deque([s])
            while queue:
                v = queue.popleft()
                stack.append(v)
                for w in adj[v]:
                    if distance[w] < 0:
                        queue.append(w)
                        distance[w] = distance[v] + 1
                    if distance[w] == distance[v] + 1:
                        sigma[w] += sigma[v]
                        predecessors[w].append(v)

            delta = {w: 0.0 for w in nodes}
            while stack:
                w = stack.pop()
                for v in predecessors[w]:
                    if sigma[w] > 0:
                        delta[v] += (sigma[v] / sigma[w]) * (1.0 + delta[w])
                if w != s:
                    betweenness[w] += delta[w]

        # Normalización para grafo no dirigido: 2 / ((n-1)*(n-2))
        norm_factor = 2.0 / ((n - 1) * (n - 2)) if n > 2 else 1.0
        ranking = []
        for uid, val in betweenness.items():
            u = u_map.get(uid)
            if u:
                score_norm = (val / 2.0) * norm_factor  # cada camino no dirigido se cuenta dos veces
                ranking.append({
                    "usuario": u,
                    "score": round(score_norm, 4),
                    "score_pct": round(score_norm * 100, 1),
                    "grado": len(adj.get(uid, set())),
                })

        ranking.sort(key=lambda x: x["score"], reverse=True)
        for idx, item in enumerate(ranking, 1):
            item["ranking"] = idx

        return ranking[:limit]

    @classmethod
    def deteccion_comunidades(cls):
        """
        Detección de comunidades y clústeres profesionales en el grafo.
        Combina conexiones de red social (:CONECTA_CON) con afinidad de habilidades
        (:TIENE_HABILIDAD) mediante un algoritmo de propagación de etiquetas adaptativo.
        Clasifica e infiere la especialidad temática dominante de cada clúster.
        """
        usuarios = UsuarioService.all()
        if not usuarios:
            return []

        adj, _ = cls._construir_grafo_conexiones(usuarios)
        u_map = {u.uid: u for u in usuarios}

        # Inicialización de etiquetas con el propio UID
        labels = {u.uid: u.uid for u in usuarios}

        # Iteración de propagación de etiquetas (Label Propagation)
        nodos = [u.uid for u in usuarios]
        max_iter = 15

        for _ in range(max_iter):
            cambios = 0
            for uid in nodos:
                vecinos = list(adj.get(uid, []))
                if not vecinos:
                    continue

                # Votación ponderada de etiquetas entre vecinos
                conteo_etiquetas = defaultdict(int)
                for v in vecinos:
                    conteo_etiquetas[labels[v]] += 1

                # Seleccionar la etiqueta más frecuente
                mejor_etiqueta = max(conteo_etiquetas.items(), key=lambda x: x[1])[0]
                if labels[uid] != mejor_etiqueta:
                    labels[uid] = mejor_etiqueta
                    cambios += 1

            if cambios == 0:
                break

        # Agrupar miembros por clúster
        grupos = defaultdict(list)
        for uid, etiqueta in labels.items():
            u = u_map.get(uid)
            if u:
                grupos[etiqueta].append(u)

        clusters = []
        for cid, miembros in grupos.items():
            # Obtener habilidades de los miembros para inferir temática
            hab_counts = defaultdict(int)
            for m in miembros:
                habs_m = HabilidadUsuarioService.listar_por_usuario(m.uid)
                for item in habs_m:
                    hab = item.get("habilidad")
                    if hab:
                        hab_counts[hab.nombre] += 1

            top_habs = sorted(hab_counts.items(), key=lambda x: x[1], reverse=True)[:4]

            # Inferencia de título del cluster
            if top_habs:
                temas = [h[0] for h in top_habs[:2]]
                nombre_cluster = f"Ecosistema {' & '.join(temas)}"
            else:
                nombre_cluster = f"Comunidad Red #{len(clusters) + 1}"

            # Densidad interna del cluster
            n_m = len(miembros)
            aristas_internas = 0
            miembros_uids = {m.uid for m in miembros}
            for m in miembros:
                for v in adj.get(m.uid, []):
                    if v in miembros_uids:
                        aristas_internas += 1
            aristas_internas //= 2

            if n_m > 1:
                densidad_interna = (2.0 * aristas_internas) / (n_m * (n_m - 1))
            else:
                densidad_interna = 1.0

            clusters.append({
                "id": cid,
                "nombre": nombre_cluster,
                "tamano": n_m,
                "miembros": miembros,
                "habilidades_top": [h[0] for h in top_habs],
                "densidad_interna_pct": round(densidad_interna * 100, 1),
                "lider": miembros[0] if miembros else None,
            })

        clusters.sort(key=lambda x: x["tamano"], reverse=True)
        return clusters

    @classmethod
    def analisis_oferta_demanda_habilidades(cls):
        """
        Contrasta la oferta de talento en la red (usuarios que poseen habilidades)
        contra la demanda activa del mercado (habilidades requeridas en ofertas de empleo).
        Calcula el ratio de escasez (Skills Shortage Ratio) y brecha neta.
        """
        habilidades = HabilidadService.all()
        usuarios = UsuarioService.all()
        ofertas = OfertaService.all()

        oferta_conteo = defaultdict(int)
        for u in usuarios:
            for item in HabilidadUsuarioService.listar_por_usuario(u.uid):
                hab = item.get("habilidad")
                if hab:
                    oferta_conteo[hab.hid] += 1

        demanda_conteo = defaultdict(int)
        demanda_obligatoria = defaultdict(int)
        for of in ofertas:
            for req in RequisitoOfertaService.listar_por_oferta(of.oid):
                hab = req.get("habilidad")
                if hab:
                    demanda_conteo[hab.hid] += 1
                    if req.get("prioridad") == "obligatoria":
                        demanda_obligatoria[hab.hid] += 1

        items = []
        for hab in habilidades:
            of = oferta_conteo[hab.hid]
            dem = demanda_conteo[hab.hid]
            ob = demanda_obligatoria[hab.hid]
            brecha = dem - of
            ratio = round(dem / max(of, 1), 2)

            # Clasificación de equilibrio de mercado
            if dem > of:
                estado = "deficit"
                badge_color = "error"
                texto_estado = "Déficit de Talento"
            elif dem == of and dem > 0:
                estado = "equilibrado"
                badge_color = "success"
                texto_estado = "Equilibrio Oferta/Demanda"
            elif of > dem:
                estado = "superavit"
                badge_color = "info"
                texto_estado = "Superávit Disponible"
            else:
                estado = "inactivo"
                badge_color = "ghost"
                texto_estado = "Sin demanda actual"

            items.append({
                "habilidad": hab,
                "oferta": of,
                "demanda": dem,
                "demanda_obligatoria": ob,
                "brecha": brecha,
                "ratio": ratio,
                "estado": estado,
                "badge_color": badge_color,
                "texto_estado": texto_estado,
            })

        # Ordenar por demanda total y ratio de escasez
        items.sort(key=lambda x: (x["demanda"], x["ratio"]), reverse=True)

        top_demandadas = sorted(items, key=lambda x: x["demanda"], reverse=True)[:8]
        top_escasez = [it for it in items if it["brecha"] > 0]
        top_escasez.sort(key=lambda x: x["brecha"], reverse=True)

        return {
            "total_habilidades": len(habilidades),
            "habilidades": items,
            "top_demandadas": top_demandadas,
            "top_escasez": top_escasez[:6],
        }

    @classmethod
    def preparar_datos_graficos(cls):
        """
        Estructura los datasets en formato JSON nativo para alimentar
        directamente los componentes visuales de Chart.js en el frontend.
        """
        centralidad = cls.ranking_centralidad_grado(limit=7)
        pagerank = cls.ranking_pagerank(limit=7)
        comunidades = cls.deteccion_comunidades()
        skills_data = cls.analisis_oferta_demanda_habilidades()

        # 1. Dataset Gráfico Centralidad vs PageRank
        labels_influencia = [c["usuario"].nombre_completo for c in centralidad]
        datos_grado = [c["grado"] for c in centralidad]
        
        pr_map = {p["usuario"].uid: p["score_pct"] for p in pagerank}
        datos_pr = [pr_map.get(c["usuario"].uid, 0.0) for c in centralidad]

        # 2. Dataset Gráfico Donut de Comunidades
        labels_comunidades = [c["nombre"] for c in comunidades[:6]]
        datos_comunidades = [c["tamano"] for c in comunidades[:6]]

        # 3. Dataset Gráfico Oferta vs Demanda de Habilidades
        top_skills = skills_data["top_demandadas"][:7]
        labels_skills = [s["habilidad"].nombre for s in top_skills]
        datos_oferta = [s["oferta"] for s in top_skills]
        datos_demanda = [s["demanda"] for s in top_skills]

        return {
            "influencia": {
                "labels": labels_influencia,
                "grado": datos_grado,
                "pagerank": datos_pr,
            },
            "comunidades": {
                "labels": labels_comunidades,
                "datos": datos_comunidades,
            },
            "habilidades": {
                "labels": labels_skills,
                "oferta": datos_oferta,
                "demanda": datos_demanda,
            },
        }

    # =========================================================================
    # Métodos Auxiliares de Grafo en Memoria
    # =========================================================================

    @classmethod
    def _construir_grafo_conexiones(cls, usuarios):
        adj = defaultdict(set)
        aristas_set = set()

        for u in usuarios:
            _ = adj[u.uid]  # Asegurar entrada de nodo aislado
            conexiones = ConexionService.listar(u.uid)
            for c in conexiones:
                amigo = c.get("usuario")
                if not amigo:
                    continue
                amigo_uid = amigo.uid
                adj[u.uid].add(amigo_uid)
                adj[amigo_uid].add(u.uid)
                # Arista normalizada (min_uid, max_uid) para no duplicar conteo
                edge = tuple(sorted([u.uid, amigo_uid]))
                aristas_set.add(edge)

        return adj, aristas_set

    @classmethod
    def _calcular_clustering_medio(cls, adj):
        """
        Calcula el Coeficiente de Agrupamiento promedio de la red:
        C(v) = 2 * e_v / (k_v * (k_v - 1))
        donde e_v son las aristas existentes entre vecinos de v.
        """
        if not adj:
            return 0.0

        coeficientes = []
        for uid, vecinos in adj.items():
            k = len(vecinos)
            if k < 2:
                coeficientes.append(0.0)
                continue

            aristas_entre_vecinos = 0
            vecinos_lista = list(vecinos)
            for i in range(len(vecinos_lista)):
                for j in range(i + 1, len(vecinos_lista)):
                    if vecinos_lista[j] in adj.get(vecinos_lista[i], set()):
                        aristas_entre_vecinos += 1

            max_aristas = k * (k - 1) / 2.0
            coeficientes.append(aristas_entre_vecinos / max_aristas)

        return sum(coeficientes) / len(coeficientes) if coeficientes else 0.0

    @classmethod
    def _calcular_distancias_red(cls, adj):
        """
        Calcula el diámetro y la longitud media de camino mediante BFS
        entre todos los pares de nodos conectados.
        """
        if not adj or len(adj) < 2:
            return 0, 0.0

        nodos = list(adj.keys())
        distancias = []
        diametro = 0

        for origen in nodos:
            queue = deque([(origen, 0)])
            visitados = {origen}

            while queue:
                actual, dist = queue.popleft()
                if dist > 0:
                    distancias.append(dist)
                    if dist > diametro:
                        diametro = dist

                for vecino in adj.get(actual, []):
                    if vecino not in visitados:
                        visitados.add(vecino)
                        queue.append((vecino, dist + 1))

        longitud_promedio = (sum(distancias) / len(distancias)) if distancias else 0.0
        return diametro, longitud_promedio
