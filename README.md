# WheelsOn · Red profesional sobre Neo4j

Proyecto de Investigación y Desarrollo (I+D) de Bases de Datos. Aplicación web de una red
profesional: perfiles, conexiones entre personas, habilidades, empresas, proyectos, ofertas de
empleo con postulación por etapas, recomendaciones y un panel de analítica. Toda la red se guarda
en una base de datos de grafos (Neo4j).

**Tecnologías:** Python · Django · Neo4j · neomodel · Tailwind · Alpine.js.

| Carpeta | Qué contiene |
|---|---|
| `scripts/` | Scripts de Neo4j: restricciones e índices, datos de prueba y consultas (`queries.cypher`) |
| `wheelson/` | La aplicación Django |
| `wheelson/core/` | Modelos, consultas, vistas y pantallas |
| `wheelson/static/` | Estilos, imágenes y JavaScript |
| `documento/` | Documento de la entrega en LaTeX (`main.tex`) y su PDF (`main.pdf`) |

---

## Requisitos

| Programa | Versión | Nota |
|---|---|---|
| Python | 3.12 o superior | Django 6 no funciona con versiones anteriores. En Windows, marcar *Add Python to PATH* al instalarlo |
| Docker Desktop | cualquiera | Solo para correr Neo4j. Tiene que estar abierto antes de seguir |
| Git | cualquiera | Solo para clonar; también sirve descargar el proyecto en `.zip` |

Las librerías de Python (Django, neomodel, python-dotenv, whitenoise, etc.) se instalan solas con
`requirements.txt` en el paso 2. No hace falta instalar Neo4j a mano: Docker lo descarga.

---

## Correr el proyecto en local

### 1. Encender Neo4j

Con Docker Desktop abierto, en cualquier terminal:

```bash
docker run -d --name wheelson-neo4j -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/password neo4j:5
```

La primera vez tarda un poco porque descarga la imagen. Los otros días basta con:

```bash
docker start wheelson-neo4j
```

### 2. Descargar el proyecto e instalar las librerías

```bash
git clone <url-del-repositorio>
cd WheelsOn/wheelson
python -m venv .venv
```

Activa el entorno virtual (la terminal mostrará `(.venv)` al inicio):

- Windows: `.venv\Scripts\activate`
- Mac o Linux: `source .venv/bin/activate`

Instala las librerías:

```bash
pip install -r requirements.txt
```

En Mac o Linux, si `python` no existe, usa `python3`. En Windows también funciona `py`.

### 3. Configurar la conexión (`.env`)

Copia el archivo `.env.example` y nombra la copia `.env`:

- Windows: `copy .env.example .env`
- Mac o Linux: `cp .env.example .env`

Si creaste Neo4j con el comando del paso 1, no hay que cambiar nada: la conexión ya apunta a
`bolt://neo4j:password@localhost:7687`.

### 4. Crear la base y cargar los datos de prueba

```bash
python manage.py migrate
python manage.py cargar_datos
```

`migrate` solo crea el archivo SQLite donde Django guarda las sesiones de inicio de sesión; la red
no se guarda ahí. `cargar_datos` ejecuta en orden los scripts de `scripts/`: `constraints.cypher`,
`seed_data.cypher` y `datos_demo.cypher`. Al terminar debe decir *175 nodos y 788 relaciones*.

Si la base ya tiene datos y quieres dejarla como nueva:

```bash
python manage.py cargar_datos --limpiar
```

<details>
<summary>Alternativa: cargar los scripts a mano en Neo4j Browser</summary>

Abre <http://localhost:7474>, entra con usuario `neo4j` y contraseña `password`, y pega y ejecuta
en este orden el contenido de `scripts/constraints.cypher`, `scripts/seed_data.cypher` y
`scripts/datos_demo.cypher`. `scripts/queries.cypher` tiene las consultas del proyecto; se pueden
ejecutar una por una cambiando los parámetros (`$uid`, `$oid`, etc.) por valores reales.
</details>

### 5. Correr la aplicación

```bash
python manage.py runserver
```

Abre <http://127.0.0.1:8000>. En la pantalla de inicio de sesión hay botones de acceso rápido para
entrar como cualquier persona de prueba sin escribir la contraseña. También se puede entrar con
correo y contraseña:

| Correo | Contraseña | Qué tiene |
|---|---|---|
| `valentina.rios@wheelson.com` | `Rios#6842` | Administra Andina Logística y lidera un proyecto |
| `mateo@wheelson.com` | `Cisneros#6919` | Administra Nexus Corp y lidera Motor de Grafos WheelsOn |
| `wilson@wheelson.com` | `Estrada#4358` | Administrador de la plataforma |
| `paula.gomez@wheelson.com` | `Gomez#8323` | Usuaria sin empresa ni proyectos a cargo |

La lista completa (40 personas) está en `scripts/usuarios_demo.md`. Los datos son inventados.

Para detener el servidor: `Ctrl + C`. Para volver a abrirlo otro día: abrir Docker Desktop,
`docker start wheelson-neo4j`, activar el entorno (paso 2) y `python manage.py runserver`.

---
