from collections import defaultdict, deque
from core.services import (
    UsuarioService,
    EmpresaService,
    HabilidadService,
    ProyectoService,
    OfertaService,
    HabilidadUsuarioService,
    RequisitoOfertaService,
    consulta,
)


class NetworkAnalyticsService:
    """
    Servicio de analítica avanzada de grafos para la red social WheelsOn.
    Implementa métricas topológicas, centralidad, PageRank, detección
    de comunidades y análisis de oferta/demanda de competencias.
    Los datos se leen de Neo4j y las métricas se calculan aquí, en Python.
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
        Agrupa a los usuarios según sus conexiones (:CONECTA_CON) con el algoritmo
        de Louvain y nombra cada clúster según sus habilidades más frecuentes.
        """
        usuarios = UsuarioService.all()
        if not usuarios:
            return []

        adj, _ = cls._construir_grafo_conexiones(usuarios)
        u_map = {u.uid: u for u in usuarios}

        grupos = defaultdict(list)
        for uid, comunidad in cls._louvain(adj).items():
            grupos[comunidad].append(u_map[uid])

        # Las habilidades de toda la red en una sola consulta, no una por persona
        habilidades_de = defaultdict(list)
        for uid, nombre in consulta("MATCH (u:Usuario)-[:TIENE_HABILIDAD]->(h:Habilidad) RETURN u.uid, h.nombre"):
            habilidades_de[uid].append(nombre)

        clusters = []
        nombres_usados = defaultdict(int)
        for cid, miembros in grupos.items():
            # Obtener habilidades de los miembros para inferir temática
            hab_counts = defaultdict(int)
            for m in miembros:
                for nombre in habilidades_de[m.uid]:
                    hab_counts[nombre] += 1

            top_habs = sorted(hab_counts.items(), key=lambda x: (-x[1], x[0]))[:4]

            # Inferencia de título del cluster
            if top_habs:
                temas = [h[0] for h in top_habs[:2]]
                nombre_cluster = f"Ecosistema {' & '.join(temas)}"
            else:
                nombre_cluster = "Comunidad de la red"

            # Dos comunidades distintas pueden compartir habilidades principales
            nombres_usados[nombre_cluster] += 1
            if nombres_usados[nombre_cluster] > 1:
                nombre_cluster = f"{nombre_cluster} ({nombres_usados[nombre_cluster]})"

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
                "lider": max(miembros, key=lambda m: (len(adj[m.uid] & miembros_uids), m.uid)),
            })

        clusters.sort(key=lambda x: (-x["tamano"], x["nombre"]))
        return clusters

    @classmethod
    def _louvain(cls, adj):
        """
        Algoritmo de Louvain: mueve cada nodo a la comunidad vecina donde más
        aumenta la modularidad (cuántas conexiones quedan dentro de los grupos,
        comparado con lo esperable al azar). Luego trata cada comunidad como un
        solo nodo y repite hasta que no haya mejora. Los nodos se recorren
        ordenados para que el resultado sea siempre el mismo.

        Devuelve un diccionario {uid: identificador de su comunidad}.
        """
        grafo = {n: {v: 1.0 for v in adj[n]} for n in adj}
        miembros = {n: [n] for n in adj}

        while True:
            comunidad = cls._agrupar_por_modularidad(grafo)
            if len(set(comunidad.values())) == len(grafo):
                break

            nuevo_grafo = defaultdict(lambda: defaultdict(float))
            for n, vecinos in grafo.items():
                # Cuenta también los pesos internos: quedan como un lazo del nuevo nodo
                _ = nuevo_grafo[comunidad[n]]
                for v, peso in vecinos.items():
                    nuevo_grafo[comunidad[n]][comunidad[v]] += peso

            nuevos_miembros = defaultdict(list)
            for n, integrantes in miembros.items():
                nuevos_miembros[comunidad[n]].extend(integrantes)

            grafo = {n: dict(vecinos) for n, vecinos in nuevo_grafo.items()}
            miembros = nuevos_miembros

        return {uid: c for c, integrantes in miembros.items() for uid in integrantes}

    @staticmethod
    def _agrupar_por_modularidad(grafo):
        grado = {n: sum(vecinos.values()) for n, vecinos in grafo.items()}
        total = sum(grado.values())
        comunidad = {n: n for n in grafo}
        if not total:
            return comunidad

        peso_comunidad = dict(grado)
        hubo_cambios = True
        while hubo_cambios:
            hubo_cambios = False
            for n in sorted(grafo):
                actual = comunidad[n]
                peso_comunidad[actual] -= grado[n]

                peso_hacia = defaultdict(float)
                for v, peso in grafo[n].items():
                    if v != n:
                        peso_hacia[comunidad[v]] += peso

                ganancia = lambda c: peso_hacia[c] - peso_comunidad[c] * grado[n] / total
                mejor = actual
                for c in sorted(peso_hacia):
                    if ganancia(c) > ganancia(mejor) + 1e-9:
                        mejor = c

                peso_comunidad[mejor] += grado[n]
                if mejor != actual:
                    comunidad[n] = mejor
                    hubo_cambios = True

        return comunidad

    @classmethod
    def analisis_oferta_demanda_habilidades(cls):
        """
        Contrasta la oferta de talento en la red (usuarios que poseen habilidades)
        contra la demanda activa del mercado (habilidades requeridas en ofertas de empleo).
        Calcula el ratio de escasez (Skills Shortage Ratio) y brecha neta.
        """
        habilidades = HabilidadService.all()

        # Oferta y demanda se cuentan en Neo4j: dos consultas en vez de una por persona y por empleo
        oferta_conteo = defaultdict(int, consulta(
            "MATCH (:Usuario)-[:TIENE_HABILIDAD]->(h:Habilidad) RETURN h.hid, count(*)"
        ))
        demanda_conteo, demanda_obligatoria = defaultdict(int), defaultdict(int)
        for hid, total, obligatorias in consulta(
            """
            MATCH (:Oferta {estado: 'abierta'})-[r:REQUIERE]->(h:Habilidad)
            RETURN h.hid, count(*), sum(CASE WHEN r.prioridad = 'obligatoria' THEN 1 ELSE 0 END)
            """
        ):
            demanda_conteo[hid], demanda_obligatoria[hid] = total, obligatorias

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

        top_demandadas = [it for it in items if it["demanda"] > 0][:8]
        top_escasez = [it for it in items if it["brecha"] > 0]
        top_escasez.sort(key=lambda x: x["brecha"], reverse=True)

        return {
            "total_habilidades": len(habilidades),
            "habilidades": items,
            "top_demandadas": top_demandadas,
            "top_escasez": top_escasez[:6],
        }

    @classmethod
    def preparar_datos_graficos(cls, comunidades=None, skills_data=None):
        """
        Estructura los datasets en formato JSON nativo para alimentar
        directamente los componentes visuales de Chart.js en el frontend.
        Recibe comunidades y habilidades si ya se calcularon, para no repetirlas.
        """
        centralidad = cls.ranking_centralidad_grado(limit=7)
        # Sin límite: una persona del top de conexiones puede no estar en el top de PageRank.
        pagerank = cls.ranking_pagerank(limit=None)
        if comunidades is None:
            comunidades = cls.deteccion_comunidades()
        if skills_data is None:
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
        uids = {u.uid for u in usuarios}

        for uid in uids:
            _ = adj[uid]  # Asegurar entrada de nodo aislado

        for origen, destino in consulta(
            "MATCH (a:Usuario)-[:CONECTA_CON]->(b:Usuario) RETURN a.uid, b.uid"
        ):
            if origen in uids and destino in uids and origen != destino:
                adj[origen].add(destino)
                adj[destino].add(origen)
                # Arista normalizada (min_uid, max_uid) para no duplicar conteo
                aristas_set.add(tuple(sorted([origen, destino])))

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
