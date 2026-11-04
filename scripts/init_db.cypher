// ==============================================================================
// WheelsOn - Inicializacion de Base de Datos Neo4j
// ==============================================================================

// 1. Limpieza opcional (descomentar si se desea reiniciar el grafo)
// MATCH (n) DETACH DELETE n;

// 2. Constraints de unicidad
CREATE CONSTRAINT usuario_uid IF NOT EXISTS FOR (u:Usuario) REQUIRE u.uid IS UNIQUE;
CREATE CONSTRAINT usuario_email IF NOT EXISTS FOR (u:Usuario) REQUIRE u.email IS UNIQUE;
CREATE CONSTRAINT empresa_eid IF NOT EXISTS FOR (e:Empresa) REQUIRE e.eid IS UNIQUE;
CREATE CONSTRAINT empresa_nombre IF NOT EXISTS FOR (e:Empresa) REQUIRE e.nombre IS UNIQUE;
CREATE CONSTRAINT habilidad_hid IF NOT EXISTS FOR (h:Habilidad) REQUIRE h.hid IS UNIQUE;
CREATE CONSTRAINT habilidad_nombre IF NOT EXISTS FOR (h:Habilidad) REQUIRE h.nombre IS UNIQUE;
CREATE CONSTRAINT proyecto_pid IF NOT EXISTS FOR (p:Proyecto) REQUIRE p.pid IS UNIQUE;
CREATE CONSTRAINT oferta_oid IF NOT EXISTS FOR (o:Oferta) REQUIRE o.oid IS UNIQUE;

// 3. Indices de optimizacion para consultas de grafos y filtros
CREATE INDEX usuario_nombres IF NOT EXISTS FOR (u:Usuario) ON (u.nombre, u.apellido);
CREATE INDEX empresa_industria IF NOT EXISTS FOR (e:Empresa) ON (e.industria);
CREATE INDEX oferta_estado IF NOT EXISTS FOR (o:Oferta) ON (o.estado);
CREATE INDEX habilidad_categoria IF NOT EXISTS FOR (h:Habilidad) ON (h.categoria);
CREATE INDEX proyecto_estado IF NOT EXISTS FOR (p:Proyecto) ON (p.estado);
