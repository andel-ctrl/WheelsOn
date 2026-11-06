"""
Capa de servicios de WheelsOn.

Toda lectura y escritura se hace contra Neo4j. Si Neo4j no responde, el error
se propaga a propósito y core.middleware.Neo4jNoDisponibleMiddleware muestra
una página clara, para que la app nunca presente datos que no están en la base.
"""

import unicodedata
from contextlib import contextmanager
from datetime import date
from functools import wraps
from random import random
from time import sleep, time
from uuid import uuid4

from django.contrib.auth.hashers import make_password, check_password
from neo4j.exceptions import TransientError
from neomodel import UniqueProperty, db

from core.models import ESTADOS_FINALES, ESTADOS_POSTULACION, ESTADOS_PROYECTO, Avance, Publicacion, Usuario, Empresa, Habilidad, Proyecto, Oferta


def consulta(cypher, **parametros):
    """Ejecuta una consulta Cypher y devuelve sus filas."""
    filas, _ = db.cypher_query(cypher, parametros)
    return filas


@contextmanager
def _transaccion():
    """Abre una transacción, o se suma a la que ya esté abierta."""
    if db._active_transaction is not None:
        yield
    else:
        with db.transaction:
            yield


def atomico(funcion):
    """
    Todo o nada. Si dos personas actúan a la vez, Neo4j puede detectar un bloqueo mutuo
    (deadlock) y cancelar a una: se reintenta sola, en vez de mostrarle un error.
    """
    @wraps(funcion)
    def envoltura(*args, **kwargs):
        if db._active_transaction is not None:
            return funcion(*args, **kwargs)
        for intento in range(8):
            try:
                with db.transaction:
                    return funcion(*args, **kwargs)
            except TransientError:
                if intento == 7:
                    raise
                sleep(0.03 * (intento + 1) + random() * 0.05)
    return envoltura


def bloquear(etiqueta, clave, *valores):
    """
    Toma el bloqueo de escritura de estos nodos hasta terminar la transacción, para que
    comprobar y escribir sea una sola operación: quien llega después espera y ve el
    resultado de quien llegó antes. Se bloquean siempre en el mismo orden.
    """
    for valor in sorted(str(v) for v in valores):
        consulta(f"MATCH (n:{etiqueta} {{{clave}: $valor}}) SET n._bloqueo = true REMOVE n._bloqueo", valor=valor)


def pagina_de_nodos(modelo, condicion, orden, skip, limit, **parametros):
    """
    Trae desde Neo4j solo una página de nodos y el total, para no cargar el catálogo completo.
    `condicion` y `orden` son Cypher fijo del código, nunca texto de quien usa la app:
    lo que viene del usuario siempre va en `parametros`.
    """
    etiqueta = modelo.__name__
    donde = f"WHERE {condicion}" if condicion else ""
    total = consulta(f"MATCH (n:{etiqueta}) {donde} RETURN count(n)", **parametros)[0][0]
    filas = consulta(
        f"MATCH (n:{etiqueta}) {donde} RETURN n ORDER BY {orden} SKIP $skip LIMIT $limit",
        skip=int(skip), limit=int(limit), **parametros,
    )
    return [modelo.inflate(fila[0]) for fila in filas], total


def a_fecha(valor):
    """
    Convierte el valor recibido en un objeto date, que es lo único que acepta
    neomodel. Los formularios HTML envían las fechas como texto "AAAA-MM-DD".
    Lanza ValueError si el texto no es una fecha válida.
    """
    if not valor:
        return None
    if isinstance(valor, date):
        return valor
    return date.fromisoformat(str(valor).strip())


def _clave_nombre(nombre):
    """Compara nombres sin distinguir mayúsculas, tildes ni espacios: 'Diseño  UX' y 'diseno ux' son iguales."""
    sin_tildes = unicodedata.normalize("NFKD", nombre).encode("ascii", "ignore").decode()
    return " ".join(sin_tildes.casefold().split())


def _exigir_nombre_libre(etiqueta, identificador, nombre, excepto=None):
    filas = consulta(f"MATCH (n:{etiqueta}) RETURN n.{identificador}, n.nombre")
    clave = _clave_nombre(nombre)
    if any(_clave_nombre(existente) == clave and actual != excepto for actual, existente in filas):
        raise UniqueProperty(f"Ya existe {etiqueta} con el nombre {nombre}")


def _limpiar(valor, por_defecto=""):
    return valor.strip() if valor else por_defecto


def _actualizar(nodo, **campos):
    for campo, valor in campos.items():
        if hasattr(nodo, campo) and valor is not None:
            setattr(nodo, campo, valor)
    return nodo.save()


def _guardar_relacion(relacion, destino, propiedades):
    """
    Crea la relación o reemplaza la existente. neomodel crearía una segunda
    relación entre los mismos nodos si cambian sus propiedades, y eso duplicaría
    los conteos de las consultas.
    """
    with _transaccion():
        relacion.disconnect(destino)
        return relacion.connect(destino, propiedades)


def _a_lista_tecnologias(tecnologias):
    if isinstance(tecnologias, str):
        return [t.strip() for t in tecnologias.split(",") if t.strip()]
    return tecnologias or []


# ==============================================================================
# SERVICIOS DE NODOS
# ==============================================================================

class UsuarioService:
    @staticmethod
    def create(nombre, apellido, email, password=None, titulo_profesional="Profesional",
               ubicacion="No especificada", biografia="", foto_url="/static/img/default-avatar.svg"):
        return Usuario(
            nombre=nombre.strip(),
            apellido=apellido.strip(),
            email=email.strip().lower(),
            password_hash=make_password(password),  # sin contraseña queda una cuenta que no puede entrar
            titulo_profesional=_limpiar(titulo_profesional, "Profesional"),
            ubicacion=_limpiar(ubicacion, "No especificada"),
            biografia=_limpiar(biografia),
            foto_url=foto_url,
        ).save()

    @staticmethod
    def get(uid):
        return Usuario.nodes.get_or_none(uid=uid) if uid else None

    @staticmethod
    def get_by_email(email):
        if not email:
            return None
        return Usuario.nodes.get_or_none(email=email.strip().lower())

    @staticmethod
    def autenticar(email, password):
        user = UsuarioService.get_by_email(email)
        if not user or not password:
            return None
        try:
            return user if user.password_hash and check_password(password, user.password_hash) else None
        except ValueError:  # hash con formato inválido: nunca concede acceso
            return None

    @staticmethod
    def all(limit=100):
        return list(Usuario.nodes.all()[:limit])

    @staticmethod
    def update(uid, **kwargs):
        user = UsuarioService.get(uid)
        if not user:
            return None
        password = kwargs.pop("password", None)
        if password:
            user.password_hash = make_password(password)
        if kwargs.get("email"):
            kwargs["email"] = kwargs["email"].strip().lower()
        return _actualizar(user, **kwargs)

    @staticmethod
    def pagina(q="", skip=0, limit=8):
        return pagina_de_nodos(
            Usuario,
            """$q = '' OR toLower(coalesce(n.nombre, '') + ' ' + coalesce(n.apellido, '')) CONTAINS $q
               OR toLower(coalesce(n.titulo_profesional, '')) CONTAINS $q
               OR toLower(coalesce(n.ubicacion, '')) CONTAINS $q""",
            "toLower(n.nombre), toLower(n.apellido)", skip, limit, q=q,
        )

    @staticmethod
    def grados():
        """Grado de cada persona en el grafo: con cuántas está conectada."""
        filas = consulta("MATCH (u:Usuario) RETURN u.uid, COUNT { (u)-[:CONECTA_CON]-(:Usuario) }")
        return dict(filas)

    @staticmethod
    def es_ultimo_admin(uid):
        filas = consulta("MATCH (u:Usuario {rol: 'admin'}) RETURN collect(u.uid)")
        return filas[0][0] == [str(uid)]

    @staticmethod
    def delete(uid):
        user = UsuarioService.get(uid)
        if not user:
            return False
        user.delete()
        return True


class EmpresaService:
    @staticmethod
    def create(nombre, industria, ubicacion="No especificada", descripcion="",
               sitio_web="", tamano="mediana", logo_url="/static/img/default-company.svg"):
        _exigir_nombre_libre("Empresa", "eid", nombre)
        return Empresa(
            nombre=" ".join(nombre.split()),
            industria=industria.strip(),
            ubicacion=_limpiar(ubicacion, "No especificada"),
            descripcion=_limpiar(descripcion),
            sitio_web=_limpiar(sitio_web),
            tamano=tamano,
            logo_url=logo_url,
        ).save()

    @staticmethod
    def get(eid):
        return Empresa.nodes.get_or_none(eid=eid) if eid else None

    @staticmethod
    def all(limit=100):
        return list(Empresa.nodes.all()[:limit])

    @staticmethod
    def update(eid, **kwargs):
        empresa = EmpresaService.get(eid)
        if not empresa:
            return None
        if kwargs.get("nombre"):
            _exigir_nombre_libre("Empresa", "eid", kwargs["nombre"], excepto=str(eid))
            kwargs["nombre"] = " ".join(kwargs["nombre"].split())
        return _actualizar(empresa, **kwargs)

    @staticmethod
    def delete(eid):
        """Elimina la empresa y sus ofertas: una oferta no puede existir sin quien la publica."""
        empresa = EmpresaService.get(eid)
        if not empresa:
            return False
        consulta("MATCH (:Empresa {eid: $eid})-[:PUBLICA]->(o:Oferta) DETACH DELETE o", eid=str(eid))
        consulta("MATCH (:Empresa {eid: $eid})-[:AUTOR_DE]->(p:Publicacion) DETACH DELETE p", eid=str(eid))
        empresa.delete()
        return True

    @staticmethod
    def pagina(q="", skip=0, limit=6):
        return pagina_de_nodos(
            Empresa,
            """$q = '' OR toLower(coalesce(n.nombre, '')) CONTAINS $q
               OR toLower(coalesce(n.industria, '')) CONTAINS $q
               OR toLower(coalesce(n.ubicacion, '')) CONTAINS $q""",
            "toLower(n.nombre)", skip, limit, q=q,
        )

    @staticmethod
    def resumen_edificios(ids=None):
        filas = consulta(
            """
            MATCH (e:Empresa)
            WHERE $ids IS NULL OR e.eid IN $ids
            RETURN e.eid,
                   COUNT { (:Usuario)-[t:TRABAJA_EN]->(e) WHERE coalesce(t.actual, true) },
                   COUNT { (e)-[:PUBLICA]->(:Oferta {estado: 'abierta'}) }
            """,
            ids=ids,
        )
        return {eid: {"empleados": a, "ofertas": b} for eid, a, b in filas}

    @staticmethod
    def impacto_de_eliminar(eid):
        """Lo que desaparece junto con la empresa, para avisarlo antes de confirmar."""
        filas = consulta(
            """
            MATCH (e:Empresa {eid: $eid})
            RETURN COUNT { (:Usuario)-[:TRABAJA_EN]->(e) },
                   COUNT { (e)-[:PUBLICA]->(:Oferta) },
                   COUNT { (e)-[:PUBLICA]->(:Oferta)<-[:POSTULA_A]-(:Usuario) },
                   COUNT { (e)-[:AUTOR_DE]->(:Publicacion) }
            """,
            eid=str(eid),
        )
        empleados, ofertas, postulaciones, publicaciones = filas[0] if filas else (0, 0, 0, 0)
        return {"empleados": empleados, "ofertas": ofertas, "postulaciones": postulaciones, "publicaciones": publicaciones}


class HabilidadService:
    @staticmethod
    def pagina(q="", categoria="", skip=0, limit=12):
        """Las más usadas primero: es lo primero que alguien busca en el catálogo."""
        return pagina_de_nodos(
            Habilidad,
            "($q = '' OR toLower(n.nombre) CONTAINS $q) AND ($categoria = '' OR n.categoria = $categoria)",
            "COUNT { (:Usuario)-[:TIENE_HABILIDAD]->(n) } DESC, toLower(n.nombre)",
            skip, limit, q=q, categoria=categoria,
        )

    @staticmethod
    def resumen_catalogo(ids):
        """Cuántas personas tienen cada habilidad y cuántos empleos abiertos la piden."""
        filas = consulta(
            """
            MATCH (h:Habilidad) WHERE h.hid IN $ids
            RETURN h.hid,
                   COUNT { (:Usuario)-[:TIENE_HABILIDAD]->(h) },
                   COUNT { (:Oferta {estado: 'abierta'})-[:REQUIERE]->(h) }
            """,
            ids=ids,
        )
        return {hid: {"personas": a, "empleos": b} for hid, a, b in filas}

    @staticmethod
    def conteo_por_categoria():
        return dict(consulta("MATCH (h:Habilidad) RETURN h.categoria, count(h)"))

    @staticmethod
    def create(nombre, categoria="tecnica", descripcion=""):
        _exigir_nombre_libre("Habilidad", "hid", nombre)
        return Habilidad(
            nombre=" ".join(nombre.split()),
            categoria=categoria,
            descripcion=_limpiar(descripcion),
        ).save()

    @staticmethod
    def get(hid):
        return Habilidad.nodes.get_or_none(hid=hid) if hid else None

    @staticmethod
    def all(limit=100):
        return list(Habilidad.nodes.all()[:limit])

    @staticmethod
    def update(hid, **kwargs):
        habilidad = HabilidadService.get(hid)
        return _actualizar(habilidad, **kwargs) if habilidad else None

    @staticmethod
    def delete(hid):
        habilidad = HabilidadService.get(hid)
        if not habilidad:
            return False
        habilidad.delete()
        return True


class ProyectoService:
    @staticmethod
    def pagina(q="", estado="", skip=0, limit=6):
        """Los activos primero; dentro de cada estado, los más recientes."""
        return pagina_de_nodos(
            Proyecto,
            """($estado = '' OR n.estado = $estado)
               AND ($q = '' OR toLower(n.nombre) CONTAINS $q
                    OR toLower(coalesce(n.descripcion, '')) CONTAINS $q
                    OR any(t IN coalesce(n.tecnologias, []) WHERE toLower(t) CONTAINS $q))""",
            "CASE n.estado WHEN 'activo' THEN 0 WHEN 'pausado' THEN 1 ELSE 2 END, n.fecha_inicio DESC, toLower(n.nombre)",
            skip, limit, q=q, estado=estado,
        )

    @staticmethod
    def resumen_carpetas(ids=None):
        """Miembros y avances de cada proyecto, para dibujar sus carpetas."""
        miembros = consulta(
            """
            MATCH (u:Usuario)-[:PARTICIPA_EN]->(p:Proyecto)
            WHERE $ids IS NULL OR p.pid IN $ids
            WITH p, u ORDER BY u.nombre
            RETURN p.pid, collect(left(u.nombre, 1) + left(u.apellido, 1))
            """,
            ids=ids,
        )
        avances = consulta(
            """
            MATCH (p:Proyecto)-[:TIENE_AVANCE]->(a:Avance)
            WHERE $ids IS NULL OR p.pid IN $ids
            WITH p, a ORDER BY a.fecha DESC, a.creada DESC
            WITH p, collect(a.texto) AS textos
            RETURN p.pid, size(textos), textos[0]
            """,
            ids=ids,
        )
        return dict(miembros), {pid: (total, texto) for pid, total, texto in avances}

    @staticmethod
    def create(nombre, descripcion="", fecha_inicio=None, fecha_fin=None,
               estado="activo", tecnologias=None):
        return Proyecto(
            nombre=nombre.strip(),
            descripcion=_limpiar(descripcion),
            fecha_inicio=a_fecha(fecha_inicio),
            fecha_fin=a_fecha(fecha_fin),
            estado=estado,
            tecnologias=_a_lista_tecnologias(tecnologias),
        ).save()

    @staticmethod
    def get(pid):
        return Proyecto.nodes.get_or_none(pid=pid) if pid else None

    @staticmethod
    def all(limit=100):
        return list(Proyecto.nodes.all()[:limit])

    @staticmethod
    def update(pid, **kwargs):
        proyecto = ProyectoService.get(pid)
        if not proyecto:
            return None
        if kwargs.get("tecnologias") is not None:
            kwargs["tecnologias"] = _a_lista_tecnologias(kwargs["tecnologias"])
        for campo in ("fecha_inicio", "fecha_fin"):
            if campo in kwargs:
                kwargs[campo] = a_fecha(kwargs[campo])
        return _actualizar(proyecto, **kwargs)

    @staticmethod
    def delete(pid):
        proyecto = ProyectoService.get(pid)
        if not proyecto:
            return False
        consulta("MATCH (:Proyecto {pid: $pid})-[:TIENE_AVANCE]->(a:Avance) DETACH DELETE a", pid=str(pid))
        proyecto.delete()
        return True


class OfertaService:
    @staticmethod
    def pagina(q="", modalidad="", skip=0, limit=6):
        """Las abiertas primero; dentro de cada estado, las más recientes."""
        return pagina_de_nodos(
            Oferta,
            """($modalidad = '' OR toLower(coalesce(n.modalidad, '')) = $modalidad)
               AND ($q = '' OR toLower(n.titulo) CONTAINS $q
                    OR toLower(coalesce(n.descripcion, '')) CONTAINS $q
                    OR toLower(coalesce(n.ubicacion, '')) CONTAINS $q)""",
            "CASE n.estado WHEN 'abierta' THEN 0 ELSE 1 END, n.fecha_publicacion DESC, toLower(n.titulo)",
            skip, limit, q=q, modalidad=modalidad,
        )

    @staticmethod
    def resumen_boletos(uid, ids=None):
        """Empresa, compatibilidad y relación de esta persona con cada oferta."""
        filas = consulta(
            """
            MATCH (o:Oferta)
            WHERE $ids IS NULL OR o.oid IN $ids
            OPTIONAL MATCH (e:Empresa)-[:PUBLICA]->(o)
            RETURN o.oid, e,
                   COUNT { (o)-[:REQUIERE]->(:Habilidad) },
                   COUNT { (o)-[:REQUIERE]->(:Habilidad)<-[:TIENE_HABILIDAD]-(:Usuario {uid: $uid}) },
                   EXISTS { (:Usuario {uid: $uid})-[:POSTULA_A]->(o) },
                   EXISTS { (:Usuario {uid: $uid})-[:ADMINISTRA]->(:Empresa)-[:PUBLICA]->(o) }
            """,
            uid=str(uid),
            ids=ids,
        )
        return {
            oid: {
                "empresa": Empresa.inflate(empresa) if empresa else None,
                "pct": round(coinciden * 100 / total) if total else None,
                "postulado": postulado,
                "propia": propia,
            }
            for oid, empresa, total, coinciden, postulado, propia in filas
        }

    @staticmethod
    def create(titulo, descripcion="", salario_min=0.0, salario_max=0.0,
               modalidad="remoto", ubicacion="No especificada", estado="abierta", cupos=1):
        return Oferta(
            titulo=titulo.strip(),
            descripcion=_limpiar(descripcion),
            salario_min=float(salario_min or 0.0),
            salario_max=float(salario_max or 0.0),
            modalidad=modalidad,
            ubicacion=_limpiar(ubicacion, "No especificada"),
            estado=estado,
            cupos=int(cupos or 1),
        ).save()

    @staticmethod
    def get(oid):
        return Oferta.nodes.get_or_none(oid=oid) if oid else None

    @staticmethod
    def all(limit=100):
        return list(Oferta.nodes.all()[:limit])

    @staticmethod
    def update(oid, **kwargs):
        oferta = OfertaService.get(oid)
        if not oferta:
            return None
        for campo in ("salario_min", "salario_max"):
            if kwargs.get(campo) is not None:
                kwargs[campo] = float(kwargs[campo] or 0.0)
        return _actualizar(oferta, **kwargs)

    @staticmethod
    def delete(oid):
        oferta = OfertaService.get(oid)
        if not oferta:
            return False
        oferta.delete()
        return True


class PublicacionService:
    """
    Publicaciones del feed. El autor es una persona o una empresa (AUTOR_DE); si es una
    empresa, REDACTA guarda qué persona la escribió. La reacción es la percepción de cada
    persona: una relación PERCIBE por publicación, buena o mala, que se puede cambiar o retirar.
    """

    PERCEPCIONES = ("buena", "mala")

    @staticmethod
    def crear(uid, texto, eid=None):
        """Con `eid` se publica a nombre de esa empresa. Quién puede hacerlo lo decide la vista."""
        autor = UsuarioService.get(uid)
        empresa = EmpresaService.get(eid) if eid else None
        if not autor or (eid and not empresa):
            return None
        publicacion = Publicacion(texto=texto.strip(), fecha=date.today(), creada=time()).save()
        if empresa:
            consulta(
                """
                MATCH (e:Empresa {eid: $eid}), (u:Usuario {uid: $uid}), (p:Publicacion {pubid: $pubid})
                CREATE (e)-[:AUTOR_DE]->(p), (u)-[:REDACTA]->(p)
                """,
                eid=str(eid), uid=str(uid), pubid=publicacion.pubid,
            )
        else:
            autor.publicaciones.connect(publicacion)
        return publicacion

    @staticmethod
    def autor_de(pubid):
        """Devuelve {'uid': ..., 'eid': ...}: uno de los dos es None. None si no existe."""
        filas = consulta("MATCH (a)-[:AUTOR_DE]->(:Publicacion {pubid: $pubid}) RETURN a.uid, a.eid", pubid=str(pubid))
        return {"uid": filas[0][0], "eid": filas[0][1]} if filas else None

    @staticmethod
    def _listar(filtro, uid_visor, limite, **parametros):
        filas = consulta(
            f"""
            MATCH (autor)-[:AUTOR_DE]->(p:Publicacion)
            {filtro}
            OPTIONAL MATCH (:Usuario {{uid: $visor}})-[mia:PERCIBE]->(p)
            RETURN p, autor,
                   COUNT {{ (:Usuario)-[:PERCIBE {{tipo: 'buena'}}]->(p) }},
                   COUNT {{ (:Usuario)-[:PERCIBE {{tipo: 'mala'}}]->(p) }},
                   mia.tipo,
                   autor.uid = $visor OR EXISTS {{ (:Usuario {{uid: $visor}})-[:ADMINISTRA]->(autor) }}
            ORDER BY p.fecha DESC, p.creada DESC
            LIMIT $limite
            """,
            visor=str(uid_visor), limite=int(limite), **parametros,
        )
        resultado = []
        for publicacion, autor, buenas, malas, mia, es_mia in filas:
            total = buenas + malas
            es_empresa = "Empresa" in autor.labels
            resultado.append({
                "publicacion": Publicacion.inflate(publicacion),
                "autor": None if es_empresa else Usuario.inflate(autor),
                "empresa": Empresa.inflate(autor) if es_empresa else None,
                "buenas": buenas,
                "malas": malas,
                "total": total,
                "pct_buena": round(buenas * 100 / total) if total else 0,
                "mi_percepcion": mia,
                "es_mia": bool(es_mia),
            })
        return resultado

    @staticmethod
    def recientes(uid_visor, limite=20):
        return PublicacionService._listar("", uid_visor, limite)

    @staticmethod
    def de_usuario(uid, uid_visor, limite=20):
        return PublicacionService._listar("WHERE autor.uid = $autor", uid_visor, limite, autor=str(uid))

    @staticmethod
    def de_empresa(eid, uid_visor, limite=20):
        return PublicacionService._listar("WHERE autor.eid = $autor", uid_visor, limite, autor=str(eid))

    @staticmethod
    @atomico
    def percibir(uid, pubid, tipo):
        """Elegir la misma opción otra vez la retira. Nadie opina sobre lo que publicó él o su empresa."""
        bloquear("Publicacion", "pubid", pubid)
        autor = PublicacionService.autor_de(pubid)
        if tipo not in PublicacionService.PERCEPCIONES or not autor or autor["uid"] == uid or not UsuarioService.get(uid):
            return False
        if autor["eid"]:
            administrador = PropiedadService.administrador_de(autor["eid"])
            if administrador and administrador.uid == uid:
                return False
        anterior = consulta(
            """
            MATCH (:Usuario {uid: $uid})-[r:PERCIBE]->(:Publicacion {pubid: $pubid})
            WITH r, r.tipo AS tipo
            DELETE r
            RETURN tipo
            """,
            uid=str(uid), pubid=str(pubid),
        )
        if not anterior or anterior[0][0] != tipo:
            consulta(
                """
                MATCH (u:Usuario {uid: $uid}), (p:Publicacion {pubid: $pubid})
                CREATE (u)-[:PERCIBE {tipo: $tipo, fecha: $hoy}]->(p)
                """,
                uid=str(uid), pubid=str(pubid), tipo=tipo, hoy=date.today().isoformat(),
            )
        return True

    @staticmethod
    def contar_de(uid):
        return consulta("RETURN COUNT { (:Usuario {uid: $uid})-[:AUTOR_DE]->(:Publicacion) }", uid=str(uid))[0][0]

    @staticmethod
    def delete(pubid):
        filas = consulta("MATCH (p:Publicacion {pubid: $pubid}) DETACH DELETE p RETURN 1", pubid=str(pubid))
        return bool(filas)


class AvanceService:
    """Novedades de un proyecto. Registrar un avance también actualiza el estado del proyecto."""

    @staticmethod
    def crear(uid, pid, texto, estado):
        autor = UsuarioService.get(uid)
        proyecto = ProyectoService.get(pid)
        if not autor or not proyecto or estado not in ESTADOS_PROYECTO:
            return None
        avance = Avance(texto=texto.strip(), estado=estado, fecha=date.today(), creada=time()).save()
        consulta(
            """
            MATCH (u:Usuario {uid: $uid}), (p:Proyecto {pid: $pid}), (a:Avance {aid: $aid})
            CREATE (p)-[:TIENE_AVANCE]->(a), (u)-[:REGISTRA]->(a)
            SET p.estado = $estado
            """,
            uid=str(uid), pid=str(pid), aid=avance.aid, estado=estado,
        )
        return avance

    @staticmethod
    def _listar(filtro, limite, **parametros):
        filas = consulta(
            f"""
            MATCH (p:Proyecto)-[:TIENE_AVANCE]->(a:Avance)
            {filtro}
            OPTIONAL MATCH (autor:Usuario)-[:REGISTRA]->(a)
            RETURN a, p, autor
            ORDER BY a.fecha DESC, a.creada DESC
            LIMIT $limite
            """,
            limite=int(limite), **parametros,
        )
        return [
            {
                "avance": Avance.inflate(avance),
                "proyecto": Proyecto.inflate(proyecto),
                "autor": Usuario.inflate(autor) if autor else None,
                "estado_texto": ESTADOS_PROYECTO.get(avance["estado"], avance["estado"]),
            }
            for avance, proyecto, autor in filas
        ]

    @staticmethod
    def recientes(limite=10):
        return AvanceService._listar("", limite)

    @staticmethod
    def de_proyecto(pid, limite=50):
        return AvanceService._listar("WHERE p.pid = $pid", limite, pid=str(pid))

    @staticmethod
    def proyecto_de(aid):
        filas = consulta("MATCH (p:Proyecto)-[:TIENE_AVANCE]->(:Avance {aid: $aid}) RETURN p.pid", aid=str(aid))
        return filas[0][0] if filas else None

    @staticmethod
    def delete(aid):
        filas = consulta("MATCH (a:Avance {aid: $aid}) DETACH DELETE a RETURN 1", aid=str(aid))
        return bool(filas)


# ==============================================================================
# SERVICIOS DE RELACIONES
# ==============================================================================

class ConexionService:
    """
    CONECTA_CON se guarda con una dirección porque Neo4j lo exige, pero significa
    una relación mutua. Por eso estas consultas la recorren en ambos sentidos.
    """

    @staticmethod
    def saltos_a_empresas(uid):
        """
        A cuántos saltos está cada empresa: 0 si ya trabajas ahí; 1 si un contacto directo
        trabaja ahí. Las empresas sin camino no aparecen.
        """
        filas = consulta(
            """
            MATCH (yo:Usuario {uid: $uid}), (t:Usuario)-[r:TRABAJA_EN]->(e:Empresa)
            WHERE t <> yo AND coalesce(r.actual, true)
            MATCH camino = shortestPath((yo)-[:CONECTA_CON*..6]-(t))
            RETURN e.eid, min(length(camino))
            """,
            uid=str(uid),
        )
        saltos = dict(filas)
        propias = consulta("MATCH (:Usuario {uid: $uid})-[r:TRABAJA_EN]->(e:Empresa) WHERE coalesce(r.actual, true) RETURN e.eid", uid=str(uid))
        saltos.update({fila[0]: 0 for fila in propias})
        return saltos

    @staticmethod
    @atomico
    def conectar(uid_origen, uid_destino, mensaje="", estado="aceptada"):
        bloquear("Usuario", "uid", uid_origen, uid_destino)
        if uid_origen == uid_destino:
            return None
        u1 = UsuarioService.get(uid_origen)
        u2 = UsuarioService.get(uid_destino)
        if not u1 or not u2:
            return None
        if ConexionService.estan_conectados(uid_origen, uid_destino):
            return True
        u1.conexiones.connect(u2, {"mensaje": mensaje, "estado": estado, "fecha": date.today()})
        return True

    @staticmethod
    def desconectar(uid_origen, uid_destino):
        filas = consulta(
            """
            MATCH (:Usuario {uid: $a})-[r:CONECTA_CON]-(:Usuario {uid: $b})
            DELETE r
            RETURN count(r)
            """,
            a=str(uid_origen), b=str(uid_destino),
        )
        return filas[0][0] > 0

    @staticmethod
    def estan_conectados(uid_origen, uid_destino):
        filas = consulta(
            """
            MATCH (:Usuario {uid: $a})-[r:CONECTA_CON]-(:Usuario {uid: $b})
            RETURN count(r)
            """,
            a=str(uid_origen), b=str(uid_destino),
        )
        return filas[0][0] > 0

    @staticmethod
    def listar(uid):
        filas = consulta(
            """
            MATCH (:Usuario {uid: $uid})-[r:CONECTA_CON]-(otro:Usuario)
            RETURN otro, r.mensaje, r.estado, r.fecha
            ORDER BY otro.nombre, otro.apellido
            """,
            uid=str(uid),
        )
        return [
            {
                "usuario": Usuario.inflate(otro),
                "mensaje": mensaje or "",
                "estado": estado or "aceptada",
                "fecha": str(fecha) if fecha else "",
            }
            for otro, mensaje, estado, fecha in filas
        ]


class EmpleoService:
    """
    TRABAJA_EN solo existe si la empresa lo confirmó. Mientras tanto, lo que la persona
    declara vive en SOLICITA_EMPLEO, y no cuenta en la página de la empresa, las
    sugerencias ni "¿Quién te puede referir?".
    """

    @staticmethod
    @atomico
    def solicitar(uid, eid, cargo, fecha_inicio=None, fecha_fin=None, actual=True):
        bloquear("Empresa", "eid", eid)
        if not UsuarioService.get(uid) or not EmpresaService.get(eid):
            return False
        inicio, fin = a_fecha(fecha_inicio), a_fecha(fecha_fin)
        consulta(
            """
            MATCH (u:Usuario {uid: $uid}), (e:Empresa {eid: $eid})
            MERGE (u)-[r:SOLICITA_EMPLEO]->(e)
            SET r.cargo = $cargo, r.fecha_inicio = $inicio, r.fecha_fin = $fin, r.actual = $actual, r.fecha = $hoy
            """,
            uid=str(uid), eid=str(eid), cargo=cargo.strip(), actual=bool(actual), hoy=date.today().isoformat(),
            inicio=inicio.isoformat() if inicio else None, fin=fin.isoformat() if fin else None,
        )
        return True

    @staticmethod
    @atomico
    def responder(uid, eid, aceptar):
        bloquear("Empresa", "eid", eid)
        filas = consulta(
            """
            MATCH (:Usuario {uid: $uid})-[r:SOLICITA_EMPLEO]->(:Empresa {eid: $eid})
            WITH r, r.cargo AS cargo, r.fecha_inicio AS inicio, r.fecha_fin AS fin, r.actual AS actual
            DELETE r
            RETURN cargo, inicio, fin, actual
            """,
            uid=str(uid), eid=str(eid),
        )
        if not filas:
            return False
        if aceptar:
            cargo, inicio, fin, actual = filas[0]
            EmpleoService.vincular(uid, eid, cargo=cargo, fecha_inicio=inicio, fecha_fin=fin, actual=actual)
        return True

    @staticmethod
    @atomico
    def invitar(uid, eid, cargo):
        """
        La empresa invita a alguien a su equipo. Devuelve 'enviada', 'aceptada' (la persona ya
        lo había pedido), 'empleado', 'ya_enviada' o None si no existe.
        """
        bloquear("Empresa", "eid", eid)
        if not UsuarioService.get(uid) or not EmpresaService.get(eid):
            return None
        if EmpleoService.es_empleado(uid, eid):
            return "empleado"
        if EmpleoService.tiene_solicitud(uid, eid):
            EmpleoService.responder(uid, eid, aceptar=True)
            return "aceptada"
        if EmpleoService.invitacion_de(uid, eid):
            return "ya_enviada"
        consulta(
            """
            MATCH (u:Usuario {uid: $uid}), (e:Empresa {eid: $eid})
            CREATE (u)-[:INVITADO_A_TRABAJAR {cargo: $cargo, fecha: $hoy}]->(e)
            """,
            uid=str(uid), eid=str(eid), cargo=cargo.strip(), hoy=date.today().isoformat(),
        )
        return "enviada"

    @staticmethod
    def invitacion_de(uid, eid):
        filas = consulta(
            "MATCH (:Usuario {uid: $uid})-[r:INVITADO_A_TRABAJAR]->(:Empresa {eid: $eid}) RETURN r.cargo",
            uid=str(uid), eid=str(eid),
        )
        return {"cargo": filas[0][0]} if filas else None

    @staticmethod
    @atomico
    def responder_invitacion(uid, eid, aceptar):
        """También sirve para que la empresa cancele su invitación."""
        bloquear("Empresa", "eid", eid)
        filas = consulta(
            """
            MATCH (:Usuario {uid: $uid})-[r:INVITADO_A_TRABAJAR]->(:Empresa {eid: $eid})
            WITH r, r.cargo AS cargo
            DELETE r
            RETURN cargo
            """,
            uid=str(uid), eid=str(eid),
        )
        if not filas:
            return False
        if aceptar:
            EmpleoService.vincular(uid, eid, cargo=filas[0][0], fecha_inicio=date.today(), actual=True)
        return True

    @staticmethod
    def invitaciones_de_usuario(uid):
        filas = consulta(
            "MATCH (:Usuario {uid: $uid})-[r:INVITADO_A_TRABAJAR]->(e:Empresa) RETURN e, r.cargo, r.fecha ORDER BY r.fecha DESC",
            uid=str(uid),
        )
        return [{"empresa": Empresa.inflate(e), "cargo": cargo, "fecha": str(fecha or "")} for e, cargo, fecha in filas]

    @staticmethod
    def invitaciones_de_empresa(eid):
        filas = consulta(
            "MATCH (u:Usuario)-[r:INVITADO_A_TRABAJAR]->(:Empresa {eid: $eid}) RETURN u, r.cargo ORDER BY r.fecha DESC",
            eid=str(eid),
        )
        return [{"usuario": Usuario.inflate(u), "cargo": cargo} for u, cargo in filas]

    @staticmethod
    def tiene_solicitud(uid, eid):
        filas = consulta(
            "RETURN EXISTS { (:Usuario {uid: $uid})-[:SOLICITA_EMPLEO]->(:Empresa {eid: $eid}) }",
            uid=str(uid), eid=str(eid),
        )
        return filas[0][0]

    @staticmethod
    @atomico
    def terminar(uid, eid):
        """Sale del equipo, pero el empleo queda en su trayectoria como experiencia anterior."""
        bloquear("Empresa", "eid", eid)
        filas = consulta(
            """
            MATCH (:Usuario {uid: $uid})-[r:TRABAJA_EN]->(:Empresa {eid: $eid})
            WHERE coalesce(r.actual, true)
            SET r.actual = false, r.fecha_fin = $hoy
            RETURN count(r)
            """,
            uid=str(uid), eid=str(eid), hoy=date.today().isoformat(),
        )
        if not filas or not filas[0][0]:
            return False
        # Quien ya no es miembro no puede recibir la empresa
        consulta("MATCH (:Usuario {uid: $uid})-[r:INVITADO_A_ADMINISTRAR]->(:Empresa {eid: $eid}) DELETE r", uid=str(uid), eid=str(eid))
        return True

    @staticmethod
    def es_empleado(uid, eid):
        filas = consulta(
            """
            RETURN EXISTS {
                MATCH (:Usuario {uid: $uid})-[r:TRABAJA_EN]->(:Empresa {eid: $eid})
                WHERE coalesce(r.actual, true)
            }
            """,
            uid=str(uid), eid=str(eid),
        )
        return filas[0][0]

    @staticmethod
    def solicitudes_de_empresa(eid):
        filas = consulta(
            "MATCH (u:Usuario)-[r:SOLICITA_EMPLEO]->(:Empresa {eid: $eid}) RETURN u, r.cargo, r.fecha ORDER BY r.fecha DESC",
            eid=str(eid),
        )
        return [{"usuario": Usuario.inflate(u), "cargo": cargo, "fecha": str(fecha or "")} for u, cargo, fecha in filas]

    @staticmethod
    def solicitudes_de_usuario(uid):
        filas = consulta(
            "MATCH (:Usuario {uid: $uid})-[r:SOLICITA_EMPLEO]->(e:Empresa) RETURN e, r.cargo ORDER BY r.fecha DESC",
            uid=str(uid),
        )
        return [{"empresa": Empresa.inflate(e), "cargo": cargo} for e, cargo in filas]

    @staticmethod
    def solicitudes_para_administrador(uid):
        filas = consulta(
            """
            MATCH (:Usuario {uid: $uid})-[:ADMINISTRA]->(e:Empresa)<-[r:SOLICITA_EMPLEO]-(u:Usuario)
            RETURN u, e, r.cargo, r.fecha ORDER BY r.fecha DESC
            """,
            uid=str(uid),
        )
        return [
            {"usuario": Usuario.inflate(u), "empresa": Empresa.inflate(e), "cargo": cargo, "fecha": str(fecha or "")}
            for u, e, cargo, fecha in filas
        ]

    @staticmethod
    def vincular(uid, eid, cargo, fecha_inicio=None, fecha_fin=None, actual=True):
        u = UsuarioService.get(uid)
        e = EmpresaService.get(eid)
        if not u or not e:
            return None
        return _guardar_relacion(u.empleos, e, {
            "cargo": cargo.strip(),
            "fecha_inicio": a_fecha(fecha_inicio),
            "fecha_fin": a_fecha(fecha_fin),
            "actual": bool(actual),
        })

    @staticmethod
    def desvincular(uid, eid):
        u = UsuarioService.get(uid)
        e = EmpresaService.get(eid)
        if not u or not e:
            return False
        u.empleos.disconnect(e)
        # Quien ya no es miembro no puede recibir la empresa
        consulta("MATCH (:Usuario {uid: $uid})-[r:INVITADO_A_ADMINISTRAR]->(:Empresa {eid: $eid}) DELETE r", uid=str(uid), eid=str(eid))
        return True

    @staticmethod
    def listar_por_usuario(uid):
        u = UsuarioService.get(uid)
        if not u:
            return []
        resultado = []
        for empresa in u.empleos.all():
            rel = u.empleos.relationship(empresa)
            resultado.append({
                "empresa": empresa,
                "cargo": rel.cargo or "Colaborador",
                "fecha_inicio": str(rel.fecha_inicio or ""),
                "fecha_fin": str(rel.fecha_fin or ""),
                "actual": rel.actual,
            })
        return resultado

    @staticmethod
    def listar_por_empresa(eid):
        empresa = EmpresaService.get(eid)
        if not empresa:
            return []
        resultado = []
        for usuario in empresa.empleados.all():
            rel = empresa.empleados.relationship(usuario)
            resultado.append({
                "usuario": usuario,
                "cargo": rel.cargo or "Colaborador",
                "fecha_inicio": str(rel.fecha_inicio or ""),
                "fecha_fin": str(rel.fecha_fin or ""),
                "actual": rel.actual,
            })
        return resultado


class HabilidadUsuarioService:
    @staticmethod
    def vincular(uid, hid, nivel="intermedio", anios_experiencia=0):
        u = UsuarioService.get(uid)
        h = HabilidadService.get(hid)
        if not u or not h:
            return None
        return _guardar_relacion(u.habilidades, h, {
            "nivel": nivel,
            "anios_experiencia": int(anios_experiencia or 0),
        })

    @staticmethod
    def desvincular(uid, hid):
        u = UsuarioService.get(uid)
        h = HabilidadService.get(hid)
        if not u or not h:
            return False
        u.habilidades.disconnect(h)
        return True

    @staticmethod
    def listar_por_usuario(uid):
        u = UsuarioService.get(uid)
        if not u:
            return []
        resultado = []
        for habilidad in u.habilidades.all():
            rel = u.habilidades.relationship(habilidad)
            resultado.append({
                "habilidad": habilidad,
                "nivel": rel.nivel,
                "anios_experiencia": rel.anios_experiencia,
            })
        return resultado


class ParticipacionProyectoService:
    @staticmethod
    def vincular(uid, pid, rol="Colaborador", fecha_inicio=None, activo=True):
        u = UsuarioService.get(uid)
        p = ProyectoService.get(pid)
        if not u or not p:
            return None
        return _guardar_relacion(u.proyectos, p, {
            "rol": rol.strip(),
            "fecha_inicio": a_fecha(fecha_inicio),
            "activo": bool(activo),
        })

    @staticmethod
    def es_miembro(uid, pid):
        filas = consulta(
            "RETURN EXISTS { (:Usuario {uid: $uid})-[:PARTICIPA_EN]->(:Proyecto {pid: $pid}) }",
            uid=str(uid), pid=str(pid),
        )
        return filas[0][0]

    @staticmethod
    def desvincular(uid, pid):
        u = UsuarioService.get(uid)
        p = ProyectoService.get(pid)
        if not u or not p:
            return False
        u.proyectos.disconnect(p)
        # Quien ya no es miembro no puede recibir el proyecto
        consulta("MATCH (:Usuario {uid: $uid})-[r:INVITADO_A {tipo: 'liderar'}]->(:Proyecto {pid: $pid}) DELETE r", uid=str(uid), pid=str(pid))
        return True

    @staticmethod
    def listar_por_usuario(uid):
        u = UsuarioService.get(uid)
        if not u:
            return []
        resultado = []
        for proyecto in u.proyectos.all():
            rel = u.proyectos.relationship(proyecto)
            resultado.append({
                "proyecto": proyecto,
                "rol": rel.rol,
                "fecha_inicio": str(rel.fecha_inicio or ""),
                "activo": rel.activo,
            })
        return resultado

    @staticmethod
    def listar_por_proyecto(pid):
        p = ProyectoService.get(pid)
        if not p:
            return []
        resultado = []
        for usuario in p.miembros.all():
            rel = p.miembros.relationship(usuario)
            resultado.append({
                "usuario": usuario,
                "rol": rel.rol,
                "fecha_inicio": str(rel.fecha_inicio or ""),
                "activo": rel.activo,
            })
        return resultado


class PublicacionOfertaService:
    @staticmethod
    def vincular(eid, oid, fecha_publicacion=None):
        e = EmpresaService.get(eid)
        o = OfertaService.get(oid)
        if not e or not o:
            return None
        return _guardar_relacion(e.ofertas, o, {"fecha_publicacion": a_fecha(fecha_publicacion) or date.today()})

    @staticmethod
    def desvincular(eid, oid):
        e = EmpresaService.get(eid)
        o = OfertaService.get(oid)
        if not e or not o:
            return False
        e.ofertas.disconnect(o)
        return True

    @staticmethod
    def obtener_empresa(oid):
        o = OfertaService.get(oid)
        if not o:
            return None
        empresas = o.empresa.all()
        return empresas[0] if empresas else None

    @staticmethod
    def listar_por_empresa(eid):
        e = EmpresaService.get(eid)
        return list(e.ofertas.all()) if e else []


class RequisitoOfertaService:
    @staticmethod
    def vincular(oid, hid, nivel_minimo="basico", prioridad="obligatoria"):
        o = OfertaService.get(oid)
        h = HabilidadService.get(hid)
        if not o or not h:
            return None
        return _guardar_relacion(o.habilidades, h, {"nivel_minimo": nivel_minimo, "prioridad": prioridad})

    @staticmethod
    def desvincular(oid, hid):
        o = OfertaService.get(oid)
        h = HabilidadService.get(hid)
        if not o or not h:
            return False
        o.habilidades.disconnect(h)
        return True

    @staticmethod
    def listar_por_oferta(oid):
        o = OfertaService.get(oid)
        if not o:
            return []
        resultado = []
        for habilidad in o.habilidades.all():
            rel = o.habilidades.relationship(habilidad)
            resultado.append({
                "habilidad": habilidad,
                "nivel_minimo": rel.nivel_minimo,
                "prioridad": rel.prioridad,
            })
        return resultado


def _datos_postulacion(rel):
    return {
        "fecha": str(rel.fecha or ""),
        "fecha_estado": str(rel.fecha_estado or rel.fecha or ""),
        "estado": rel.estado,
        "estado_texto": ESTADOS_POSTULACION.get(rel.estado, rel.estado),
        "decidida": rel.estado in ESTADOS_FINALES,
        "carta_presentacion": rel.carta_presentacion or "",
    }


class PostulacionService:
    @staticmethod
    def postular(uid, oid, carta_presentacion="", estado="enviada"):
        u = UsuarioService.get(uid)
        o = OfertaService.get(oid)
        if not u or not o:
            return None
        return _guardar_relacion(u.postulaciones, o, {
            "fecha": date.today(),
            "estado": estado,
            "carta_presentacion": carta_presentacion.strip(),
        })

    @staticmethod
    @atomico
    def postular_si_abierta(uid, oid, carta_presentacion=""):
        """Devuelve 'enviada', 'cerrada', 'ya_postulado' o None si no existe."""
        bloquear("Oferta", "oid", oid)
        oferta = OfertaService.get(oid)
        if not oferta or not UsuarioService.get(uid):
            return None
        if oferta.estado != "abierta":
            return "cerrada"
        if PostulacionService.ha_postulado(uid, oid):
            return "ya_postulado"
        PostulacionService.postular(uid, oid, carta_presentacion=carta_presentacion)
        return "enviada"

    @staticmethod
    @atomico
    def retirar(uid, oid):
        """Quita la postulación si la empresa aún no decide. Devuelve True, o False si ya no se puede."""
        bloquear("Oferta", "oid", oid)
        filas = consulta(
            """
            MATCH (:Usuario {uid: $uid})-[r:POSTULA_A]->(:Oferta {oid: $oid})
            WHERE NOT r.estado IN $finales
            DELETE r
            RETURN count(*)
            """,
            uid=str(uid), oid=str(oid), finales=list(ESTADOS_FINALES),
        )
        return bool(filas and filas[0][0])

    @staticmethod
    def desvincular(uid, oid):
        u = UsuarioService.get(uid)
        o = OfertaService.get(oid)
        if not u or not o:
            return False
        u.postulaciones.disconnect(o)
        return True

    @staticmethod
    def ha_postulado(uid, oid):
        u = UsuarioService.get(uid)
        o = OfertaService.get(oid)
        return bool(u and o and u.postulaciones.is_connected(o))

    @staticmethod
    def listar_por_usuario(uid):
        u = UsuarioService.get(uid)
        if not u:
            return []
        resultado = []
        for oferta in u.postulaciones.all():
            rel = u.postulaciones.relationship(oferta)
            resultado.append({"oferta": oferta, **_datos_postulacion(rel)})
        return resultado

    @staticmethod
    def listar_por_oferta(oid):
        o = OfertaService.get(oid)
        if not o:
            return []
        resultado = []
        for usuario in o.candidatos.all():
            rel = o.candidatos.relationship(usuario)
            resultado.append({"usuario": usuario, **_datos_postulacion(rel)})
        return resultado

    @staticmethod
    def obtener_estado(uid, oid):
        filas = consulta(
            "MATCH (:Usuario {uid: $uid})-[r:POSTULA_A]->(:Oferta {oid: $oid}) RETURN r.estado",
            uid=str(uid), oid=str(oid),
        )
        return filas[0][0] if filas else None

    @staticmethod
    @atomico
    def cambiar_estado(uid, oid, estado):
        """Avanza una postulación que sigue en proceso. Una decisión ya tomada no se cambia."""
        bloquear("Oferta", "oid", oid)
        if estado not in ESTADOS_POSTULACION:
            return False
        filas = consulta(
            """
            MATCH (:Usuario {uid: $uid})-[r:POSTULA_A]->(:Oferta {oid: $oid})
            WHERE NOT r.estado IN $finales
            SET r.estado = $estado, r.fecha_estado = $hoy
            RETURN count(r)
            """,
            uid=str(uid), oid=str(oid), estado=estado, hoy=date.today().isoformat(), finales=list(ESTADOS_FINALES),
        )
        return filas[0][0] > 0

    @staticmethod
    def contar(oid):
        """(postulaciones, aceptadas) de una oferta. La cifra es pública; los nombres, no."""
        filas = consulta(
            """
            MATCH (o:Oferta {oid: $oid})
            RETURN COUNT { (:Usuario)-[:POSTULA_A]->(o) },
                   COUNT { (:Usuario)-[r:POSTULA_A]->(o) WHERE r.estado = 'aceptada' }
            """,
            oid=str(oid),
        )
        return tuple(filas[0]) if filas else (0, 0)

    @staticmethod
    @atomico
    def contratar(uid, oid):
        """
        Aceptar a alguien lo suma al equipo de la empresa, con el título del empleo como cargo.
        Devuelve None si ya no se puede (decidida, empleo cerrado, sin cupo o sin empresa).
        Si se llena el último cupo, el empleo se cierra y responde a quienes seguían en proceso.
        """
        bloquear("Oferta", "oid", oid)
        filas = consulta(
            """
            MATCH (u:Usuario {uid: $uid})-[r:POSTULA_A]->(o:Oferta {oid: $oid})<-[:PUBLICA]-(e:Empresa)
            WHERE o.estado = 'abierta' AND NOT r.estado IN $finales
              AND COUNT { (:Usuario)-[a:POSTULA_A]->(o) WHERE a.estado = 'aceptada' } < coalesce(o.cupos, 1)
            SET r.estado = 'aceptada', r.fecha_estado = $hoy
            MERGE (u)-[t:TRABAJA_EN]->(e)
            SET t.cargo = o.titulo, t.fecha_inicio = $hoy, t.fecha_fin = null, t.actual = true
            WITH u, o, e
            OPTIONAL MATCH (u)-[s:SOLICITA_EMPLEO]->(e)
            DELETE s
            WITH DISTINCT u, o, e
            OPTIONAL MATCH (u)-[i:INVITADO_A_TRABAJAR]->(e)
            DELETE i
            RETURN DISTINCT e, COUNT { (:Usuario)-[a:POSTULA_A]->(o) WHERE a.estado = 'aceptada' }, coalesce(o.cupos, 1)
            """,
            uid=str(uid), oid=str(oid), hoy=date.today().isoformat(), finales=list(ESTADOS_FINALES),
        )
        if not filas:
            return None
        empresa, aceptadas, cupos = filas[0]
        no_seleccionados = PostulacionService.cerrar_oferta(oid) if aceptadas >= cupos else []
        return {"empresa": Empresa.inflate(empresa), "no_seleccionados": no_seleccionados, "cubierta": aceptadas >= cupos}

    @staticmethod
    @atomico
    def cerrar_oferta(oid):
        """Cierra el empleo y le da respuesta a quienes seguían en proceso. Devuelve sus uid."""
        bloquear("Oferta", "oid", oid)
        filas = consulta(
            """
            MATCH (o:Oferta {oid: $oid})
            SET o.estado = 'cerrada'
            WITH o
            OPTIONAL MATCH (u:Usuario)-[r:POSTULA_A]->(o)
            WHERE NOT r.estado IN $finales
            SET r.estado = 'no_seleccionada', r.fecha_estado = $hoy
            RETURN u.uid
            """,
            oid=str(oid), hoy=date.today().isoformat(), finales=list(ESTADOS_FINALES),
        )
        return [fila[0] for fila in filas if fila[0]]

    @staticmethod
    def nuevas_para_administrador(uid):
        """Postulaciones sin revisar en las ofertas de las empresas que administra esta persona."""
        filas = consulta(
            """
            MATCH (:Usuario {uid: $uid})-[:ADMINISTRA]->(:Empresa)-[:PUBLICA]->(o:Oferta)
                  <-[r:POSTULA_A {estado: 'enviada'}]-(c:Usuario)
            RETURN o, c, r.fecha
            """,
            uid=str(uid),
        )
        return [
            {"oferta": Oferta.inflate(oferta), "usuario": Usuario.inflate(candidato), "fecha": str(fecha or "")}
            for oferta, candidato, fecha in filas
        ]


# ==============================================================================
# DUEÑOS DE LOS DATOS
# ==============================================================================

class PropiedadService:
    """Quién administra cada empresa y quién lidera cada proyecto."""

    @staticmethod
    def administrador_de(eid):
        empresa = EmpresaService.get(eid)
        administradores = empresa.administradores.all() if empresa else []
        return administradores[0] if administradores else None

    @staticmethod
    def lider_de(pid):
        proyecto = ProyectoService.get(pid)
        lideres = proyecto.lideres.all() if proyecto else []
        return lideres[0] if lideres else None

    @staticmethod
    def asignar_administrador(uid, eid):
        """Cada empresa tiene un solo administrador: asignar uno reemplaza al anterior."""
        usuario = UsuarioService.get(uid)
        empresa = EmpresaService.get(eid)
        if not usuario or not empresa:
            return False
        with _transaccion():
            for actual in empresa.administradores.all():
                actual.empresas_administradas.disconnect(empresa)
            usuario.empresas_administradas.connect(empresa)
        consulta("MATCH ()-[r:INVITADO_A_ADMINISTRAR]->(:Empresa {eid: $eid}) DELETE r", eid=str(eid))
        return True

    @staticmethod
    def asignar_lider(uid, pid):
        usuario = UsuarioService.get(uid)
        proyecto = ProyectoService.get(pid)
        if not usuario or not proyecto:
            return False
        with _transaccion():
            for actual in proyecto.lideres.all():
                actual.proyectos_liderados.disconnect(proyecto)
            usuario.proyectos_liderados.connect(proyecto)
        consulta("MATCH ()-[r:INVITADO_A {tipo: 'liderar'}]->(:Proyecto {pid: $pid}) DELETE r", pid=str(pid))
        if not usuario.proyectos.is_connected(proyecto):
            ParticipacionProyectoService.vincular(uid, pid, rol="Líder", fecha_inicio=date.today())
        return True

    @staticmethod
    def crear_empresa(uid, **datos):
        empresa = EmpresaService.create(**datos)
        PropiedadService.asignar_administrador(uid, empresa.eid)
        # Quien la crea también es parte de ella, como el líder de un proyecto
        EmpleoService.vincular(uid, empresa.eid, cargo="Fundador", fecha_inicio=date.today(), actual=True)
        return empresa

    @staticmethod
    def crear_proyecto(uid, **datos):
        proyecto = ProyectoService.create(**datos)
        PropiedadService.asignar_lider(uid, proyecto.pid)
        return proyecto

    @staticmethod
    def crear_oferta(eid, **datos):
        oferta = OfertaService.create(**datos)
        PublicacionOfertaService.vincular(eid, oferta.oid)
        return oferta

    @staticmethod
    def pendientes_de_transferir(uid):
        """Lo que este usuario administra y dejaría sin dueño a otras personas si eliminara su cuenta."""
        empresas = consulta("MATCH (:Usuario {uid: $uid})-[:ADMINISTRA]->(e:Empresa) RETURN e.nombre ORDER BY e.nombre", uid=str(uid))
        proyectos = consulta(
            """
            MATCH (:Usuario {uid: $uid})-[:LIDERA]->(p:Proyecto)
            WHERE EXISTS { MATCH (otro:Usuario)-[:PARTICIPA_EN]->(p) WHERE otro.uid <> $uid }
            RETURN p.nombre ORDER BY p.nombre
            """,
            uid=str(uid),
        )
        return [fila[0] for fila in empresas] + [fila[0] for fila in proyectos]

    @staticmethod
    def proyectos_individuales(uid):
        """Proyectos y publicaciones donde esta persona está sola: se eliminan con su cuenta."""
        filas = consulta(
            """
            MATCH (:Usuario {uid: $uid})-[:LIDERA]->(p:Proyecto)
            WHERE NOT EXISTS { MATCH (otro:Usuario)-[:PARTICIPA_EN]->(p) WHERE otro.uid <> $uid }
            RETURN p.pid, p.nombre ORDER BY p.nombre
            """,
            uid=str(uid),
        )
        return [{"pid": pid, "nombre": nombre} for pid, nombre in filas]

    @staticmethod
    def eliminar_cuenta(uid):
        for proyecto in PropiedadService.proyectos_individuales(uid):
            ProyectoService.delete(proyecto["pid"])
        consulta("MATCH (:Usuario {uid: $uid})-[:AUTOR_DE]->(p:Publicacion) DETACH DELETE p", uid=str(uid))
        consulta("MATCH (:Usuario {uid: $uid})-[:RECIBE]->(n:Notificacion) DETACH DELETE n", uid=str(uid))
        return UsuarioService.delete(uid)


# ==============================================================================
# SOLICITUDES E INVITACIONES PENDIENTES
# ==============================================================================

class InvitacionService:
    """
    Lo que espera la respuesta de otra persona. Vive en relaciones propias
    (SOLICITA_CONEXION, SOLICITA_UNIRSE, INVITADO_A, INVITADO_A_ADMINISTRAR) para que las rutas, las
    sugerencias y la analítica solo vean vínculos ya aceptados. Al aceptar se crea el
    vínculo real; al rechazar o cancelar simplemente se borra lo pendiente.
    """

    # ------------------------------------------------------------------ conexiones
    @staticmethod
    def estado_conexion(yo, otro):
        """Devuelve 'conectados', 'enviada', 'recibida' o None."""
        if ConexionService.estan_conectados(yo, otro):
            return "conectados"
        filas = consulta(
            """
            RETURN EXISTS { (:Usuario {uid: $yo})-[:SOLICITA_CONEXION]->(:Usuario {uid: $otro}) },
                   EXISTS { (:Usuario {uid: $otro})-[:SOLICITA_CONEXION]->(:Usuario {uid: $yo}) }
            """,
            yo=str(yo), otro=str(otro),
        )
        enviada, recibida = filas[0]
        return "enviada" if enviada else "recibida" if recibida else None

    @staticmethod
    @atomico
    def solicitar_conexion(origen, destino, mensaje=""):
        """Devuelve 'enviada', 'ya_enviada', 'conectados', 'aceptada' (la otra persona ya la había pedido) o None."""
        bloquear("Usuario", "uid", origen, destino)
        if origen == destino or not UsuarioService.get(origen) or not UsuarioService.get(destino):
            return None
        estado = InvitacionService.estado_conexion(origen, destino)
        if estado == "conectados":
            return "conectados"
        if estado == "enviada":
            return "ya_enviada"
        if estado == "recibida":
            InvitacionService.responder_conexion(destino, origen, aceptar=True)
            return "aceptada"
        consulta(
            """
            MATCH (a:Usuario {uid: $origen}), (b:Usuario {uid: $destino})
            CREATE (a)-[:SOLICITA_CONEXION {mensaje: $mensaje, fecha: $hoy}]->(b)
            """,
            origen=str(origen), destino=str(destino), mensaje=mensaje, hoy=date.today().isoformat(),
        )
        return "enviada"

    @staticmethod
    @atomico
    def responder_conexion(origen, destino, aceptar):
        bloquear("Usuario", "uid", origen, destino)
        filas = consulta(
            """
            MATCH (:Usuario {uid: $origen})-[r:SOLICITA_CONEXION]->(:Usuario {uid: $destino})
            WITH r, r.mensaje AS mensaje
            DELETE r
            RETURN mensaje
            """,
            origen=str(origen), destino=str(destino),
        )
        if not filas:
            return False
        if aceptar:
            ConexionService.conectar(origen, destino, mensaje=filas[0][0] or "")
        return True

    @staticmethod
    def _solicitudes(patron, uid):
        filas = consulta(
            f"MATCH {patron} RETURN otro, r.mensaje, r.fecha ORDER BY r.fecha DESC, otro.nombre",
            uid=str(uid),
        )
        return [
            {"usuario": Usuario.inflate(otro), "mensaje": mensaje or "", "fecha": str(fecha or "")}
            for otro, mensaje, fecha in filas
        ]

    @staticmethod
    def solicitudes_recibidas(uid):
        return InvitacionService._solicitudes("(otro:Usuario)-[r:SOLICITA_CONEXION]->(:Usuario {uid: $uid})", uid)

    @staticmethod
    def solicitudes_enviadas(uid):
        return InvitacionService._solicitudes("(:Usuario {uid: $uid})-[r:SOLICITA_CONEXION]->(otro:Usuario)", uid)

    # ------------------------------------------------------------------ proyectos
    @staticmethod
    @atomico
    def invitar_a_proyecto(uid, pid, rol="Colaborador", fecha_inicio=None):
        """
        Devuelve 'invitado', 'unido' (ya lo había pedido) o False si el usuario o el proyecto no existen.
        Lanza ValueError si la fecha no es válida.
        """
        bloquear("Proyecto", "pid", pid)
        fecha = a_fecha(fecha_inicio)
        if not UsuarioService.get(uid) or not ProyectoService.get(pid):
            return False
        if InvitacionService.estado_union(uid, pid) == "solicitada":
            InvitacionService.responder_union(uid, pid, aceptar=False)
            ParticipacionProyectoService.vincular(uid, pid, rol=rol, fecha_inicio=fecha)
            return "unido"
        consulta(
            """
            MATCH (u:Usuario {uid: $uid}), (p:Proyecto {pid: $pid})
            MERGE (u)-[r:INVITADO_A]->(p)
            ON CREATE SET r.tipo = 'colaborar', r.fecha = $hoy
            SET r.rol = $rol, r.fecha_inicio = $fecha
            """,
            uid=str(uid), pid=str(pid), rol=rol, fecha=fecha.isoformat() if fecha else None,
            hoy=date.today().isoformat(),
        )
        return "invitado"

    @staticmethod
    def estado_union(uid, pid):
        """Devuelve 'miembro', 'invitado', 'solicitada' o None."""
        filas = consulta(
            """
            RETURN EXISTS { (:Usuario {uid: $uid})-[:PARTICIPA_EN]->(:Proyecto {pid: $pid}) },
                   EXISTS { (:Usuario {uid: $uid})-[:INVITADO_A]->(:Proyecto {pid: $pid}) },
                   EXISTS { (:Usuario {uid: $uid})-[:SOLICITA_UNIRSE]->(:Proyecto {pid: $pid}) }
            """,
            uid=str(uid), pid=str(pid),
        )
        miembro, invitado, solicitada = filas[0]
        return "miembro" if miembro else "invitado" if invitado else "solicitada" if solicitada else None

    @staticmethod
    @atomico
    def solicitar_unirse(uid, pid):
        """Devuelve 'enviada', 'ya_enviada', 'miembro', 'aceptada' (ya lo habían invitado), 'cerrado' o None."""
        bloquear("Proyecto", "pid", pid)
        proyecto = ProyectoService.get(pid)
        if not proyecto or not UsuarioService.get(uid):
            return None
        if proyecto.estado == "completado":
            return "cerrado"
        estado = InvitacionService.estado_union(uid, pid)
        if estado == "miembro":
            return "miembro"
        if estado == "solicitada":
            return "ya_enviada"
        if estado == "invitado":
            InvitacionService.responder_proyecto(uid, pid, aceptar=True)
            return "aceptada"
        consulta(
            """
            MATCH (u:Usuario {uid: $uid}), (p:Proyecto {pid: $pid})
            CREATE (u)-[:SOLICITA_UNIRSE {fecha: $hoy}]->(p)
            """,
            uid=str(uid), pid=str(pid), hoy=date.today().isoformat(),
        )
        return "enviada"

    @staticmethod
    @atomico
    def responder_union(uid, pid, aceptar):
        bloquear("Proyecto", "pid", pid)
        filas = consulta(
            "MATCH (:Usuario {uid: $uid})-[r:SOLICITA_UNIRSE]->(:Proyecto {pid: $pid}) DELETE r RETURN 1",
            uid=str(uid), pid=str(pid),
        )
        if not filas:
            return False
        if aceptar:
            ParticipacionProyectoService.vincular(uid, pid, rol="Colaborador", fecha_inicio=date.today())
        return True

    @staticmethod
    def solicitudes_union_de_proyecto(pid):
        filas = consulta(
            "MATCH (u:Usuario)-[r:SOLICITA_UNIRSE]->(:Proyecto {pid: $pid}) RETURN u, r.fecha ORDER BY r.fecha DESC",
            pid=str(pid),
        )
        return [{"usuario": Usuario.inflate(u), "fecha": str(fecha or "")} for u, fecha in filas]

    @staticmethod
    def solicitudes_union_para_lider(uid):
        filas = consulta(
            """
            MATCH (:Usuario {uid: $uid})-[:LIDERA]->(p:Proyecto)<-[r:SOLICITA_UNIRSE]-(u:Usuario)
            RETURN u, p, r.fecha ORDER BY r.fecha DESC
            """,
            uid=str(uid),
        )
        return [{"usuario": Usuario.inflate(u), "proyecto": Proyecto.inflate(p), "fecha": str(fecha or "")} for u, p, fecha in filas]

    @staticmethod
    def solicitudes_union_enviadas(uid):
        filas = consulta(
            "MATCH (:Usuario {uid: $uid})-[r:SOLICITA_UNIRSE]->(p:Proyecto) RETURN p ORDER BY r.fecha DESC",
            uid=str(uid),
        )
        return [Proyecto.inflate(fila[0]) for fila in filas]

    @staticmethod
    def proponer_lider(uid, pid):
        if not UsuarioService.get(uid) or not ProyectoService.get(pid):
            return False
        consulta("MATCH ()-[r:INVITADO_A {tipo: 'liderar'}]->(:Proyecto {pid: $pid}) DELETE r", pid=str(pid))
        consulta(
            """
            MATCH (u:Usuario {uid: $uid}), (p:Proyecto {pid: $pid})
            MERGE (u)-[r:INVITADO_A]->(p)
            SET r.tipo = 'liderar', r.fecha = $hoy
            """,
            uid=str(uid), pid=str(pid), hoy=date.today().isoformat(),
        )
        return True

    @staticmethod
    @atomico
    def cerrar_pendientes_de_proyecto(pid):
        """Borra solicitudes e invitaciones a colaborar. La de liderar sigue: es entre miembros."""
        bloquear("Proyecto", "pid", pid)
        filas = consulta(
            """
            MATCH (u:Usuario)-[r:SOLICITA_UNIRSE|INVITADO_A]->(:Proyecto {pid: $pid})
            WHERE type(r) = 'SOLICITA_UNIRSE' OR coalesce(r.tipo, 'colaborar') <> 'liderar'
            WITH u, r
            DELETE r
            RETURN DISTINCT u.uid
            """,
            pid=str(pid),
        )
        return [fila[0] for fila in filas]

    @staticmethod
    @atomico
    def responder_proyecto(uid, pid, aceptar):
        bloquear("Proyecto", "pid", pid)
        filas = consulta(
            """
            MATCH (:Usuario {uid: $uid})-[r:INVITADO_A]->(:Proyecto {pid: $pid})
            WITH r, r.tipo AS tipo, r.rol AS rol, r.fecha_inicio AS fecha_inicio
            DELETE r
            RETURN tipo, rol, fecha_inicio
            """,
            uid=str(uid), pid=str(pid),
        )
        if not filas:
            return False
        tipo, rol, fecha_inicio = filas[0]
        if aceptar and tipo == "liderar":
            if not ParticipacionProyectoService.es_miembro(uid, pid):
                return False
            PropiedadService.asignar_lider(uid, pid)
        elif aceptar:
            ParticipacionProyectoService.vincular(uid, pid, rol=rol or "Colaborador", fecha_inicio=fecha_inicio)
        return True

    @staticmethod
    def tipo_invitacion_proyecto(uid, pid):
        filas = consulta(
            "MATCH (:Usuario {uid: $uid})-[r:INVITADO_A]->(:Proyecto {pid: $pid}) RETURN r.tipo",
            uid=str(uid), pid=str(pid),
        )
        return filas[0][0] if filas else None

    @staticmethod
    def pendientes_de_proyecto(pid):
        filas = consulta(
            "MATCH (u:Usuario)-[r:INVITADO_A]->(:Proyecto {pid: $pid}) RETURN u, r.tipo, r.rol ORDER BY u.nombre",
            pid=str(pid),
        )
        return [{"usuario": Usuario.inflate(u), "tipo": tipo, "rol": rol or ""} for u, tipo, rol in filas]

    # ------------------------------------------------------------------ empresas
    @staticmethod
    def proponer_administrador(uid, eid):
        if not UsuarioService.get(uid) or not EmpresaService.get(eid):
            return False
        consulta("MATCH ()-[r:INVITADO_A_ADMINISTRAR]->(:Empresa {eid: $eid}) DELETE r", eid=str(eid))
        consulta(
            """
            MATCH (u:Usuario {uid: $uid}), (e:Empresa {eid: $eid})
            CREATE (u)-[:INVITADO_A_ADMINISTRAR {fecha: $hoy}]->(e)
            """,
            uid=str(uid), eid=str(eid), hoy=date.today().isoformat(),
        )
        return True

    @staticmethod
    @atomico
    def responder_empresa(uid, eid, aceptar):
        bloquear("Empresa", "eid", eid)
        filas = consulta(
            "MATCH (:Usuario {uid: $uid})-[r:INVITADO_A_ADMINISTRAR]->(:Empresa {eid: $eid}) DELETE r RETURN 1",
            uid=str(uid), eid=str(eid),
        )
        if not filas:
            return False
        if aceptar:
            if not EmpleoService.es_empleado(uid, eid):
                return False
            PropiedadService.asignar_administrador(uid, eid)
        return True

    @staticmethod
    def cancelar_de_empresa(eid):
        filas = consulta("MATCH (u:Usuario)-[r:INVITADO_A_ADMINISTRAR]->(:Empresa {eid: $eid}) DELETE r RETURN u.uid", eid=str(eid))
        return filas[0][0] if filas else None

    @staticmethod
    def pendiente_de_empresa(eid):
        filas = consulta("MATCH (u:Usuario)-[:INVITADO_A_ADMINISTRAR]->(:Empresa {eid: $eid}) RETURN u", eid=str(eid))
        return Usuario.inflate(filas[0][0]) if filas else None

    # ------------------------------------------------------------------ bandeja personal
    @staticmethod
    def invitaciones_de(uid):
        proyectos = consulta(
            """
            MATCH (:Usuario {uid: $uid})-[r:INVITADO_A]->(p:Proyecto)
            RETURN p.pid, p.nombre, r.tipo, r.rol, r.fecha ORDER BY r.fecha DESC
            """,
            uid=str(uid),
        )
        empresas = consulta(
            """
            MATCH (:Usuario {uid: $uid})-[r:INVITADO_A_ADMINISTRAR]->(e:Empresa)
            RETURN e.eid, e.nombre, r.fecha ORDER BY r.fecha DESC
            """,
            uid=str(uid),
        )
        return [
            {"pid": pid, "nombre": nombre, "tipo": tipo, "rol": rol or "", "fecha": str(fecha or "")}
            for pid, nombre, tipo, rol, fecha in proyectos
        ] + [
            {"eid": eid, "nombre": nombre, "tipo": "administrar", "rol": "", "fecha": str(fecha or "")}
            for eid, nombre, fecha in empresas
        ]


# ==============================================================================
# NOTIFICACIONES
# ==============================================================================

class NotificacionService:
    """
    Avisos de lo que ya pasó. Un rechazo borra la solicitud, así que no queda nada en el
    grafo de qué avisar: por eso cada aviso se guarda como (:Usuario)-[:RECIBE]->(:Notificacion).
    Lo pendiente, en cambio, se deduce de las relaciones (ver core.presentacion.avisos_para).
    """

    @staticmethod
    def crear(uid, titulo, detalle="", url="", icono="bell"):
        consulta(
            """
            MATCH (u:Usuario {uid: $uid})
            CREATE (u)-[:RECIBE]->(:Notificacion {
                nid: $nid, titulo: $titulo, detalle: $detalle, url: $url, icono: $icono, fecha: $hoy, creada: $creada
            })
            """,
            uid=str(uid), nid=uuid4().hex, titulo=titulo, detalle=detalle, url=url, icono=icono,
            hoy=date.today().isoformat(), creada=time(),
        )

    @staticmethod
    def de_usuario(uid, limite=30):
        filas = consulta(
            """
            MATCH (:Usuario {uid: $uid})-[:RECIBE]->(n:Notificacion)
            RETURN n.nid, n.titulo, n.detalle, n.url, n.icono, n.fecha, n.creada
            ORDER BY n.creada DESC
            LIMIT $limite
            """,
            uid=str(uid), limite=int(limite),
        )
        return [
            {"nid": nid, "titulo": titulo, "detalle": detalle or "", "url": url or "", "icono": icono or "bell", "fecha": str(fecha or ""), "creada": creada or 0}
            for nid, titulo, detalle, url, icono, fecha, creada in filas
        ]
