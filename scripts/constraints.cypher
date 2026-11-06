// ==============================================================================
// WheelsOn - Constraints e Indices para Neo4j (Cypher)
// ==============================================================================

// Restricciones de unicidad (Unique Constraints)
CREATE CONSTRAINT usuario_uid IF NOT EXISTS
  FOR (u:Usuario) REQUIRE u.uid IS UNIQUE;

CREATE CONSTRAINT usuario_email IF NOT EXISTS
  FOR (u:Usuario) REQUIRE u.email IS UNIQUE;

CREATE CONSTRAINT empresa_eid IF NOT EXISTS
  FOR (e:Empresa) REQUIRE e.eid IS UNIQUE;

CREATE CONSTRAINT empresa_nombre IF NOT EXISTS
  FOR (e:Empresa) REQUIRE e.nombre IS UNIQUE;

CREATE CONSTRAINT habilidad_hid IF NOT EXISTS
  FOR (h:Habilidad) REQUIRE h.hid IS UNIQUE;

CREATE CONSTRAINT habilidad_nombre IF NOT EXISTS
  FOR (h:Habilidad) REQUIRE h.nombre IS UNIQUE;

CREATE CONSTRAINT proyecto_pid IF NOT EXISTS
  FOR (p:Proyecto) REQUIRE p.pid IS UNIQUE;

CREATE CONSTRAINT oferta_oid IF NOT EXISTS
  FOR (o:Oferta) REQUIRE o.oid IS UNIQUE;

CREATE CONSTRAINT publicacion_pubid IF NOT EXISTS
  FOR (p:Publicacion) REQUIRE p.pubid IS UNIQUE;

CREATE CONSTRAINT avance_aid IF NOT EXISTS
  FOR (a:Avance) REQUIRE a.aid IS UNIQUE;

CREATE CONSTRAINT notificacion_nid IF NOT EXISTS
  FOR (n:Notificacion) REQUIRE n.nid IS UNIQUE;

// Indices de rendimiento para busquedas frecuentes
CREATE INDEX usuario_nombres IF NOT EXISTS
  FOR (u:Usuario) ON (u.nombre, u.apellido);

CREATE INDEX empresa_industria IF NOT EXISTS
  FOR (e:Empresa) ON (e.industria);

CREATE INDEX oferta_estado IF NOT EXISTS
  FOR (o:Oferta) ON (o.estado);

CREATE INDEX habilidad_categoria IF NOT EXISTS
  FOR (h:Habilidad) ON (h.categoria);

CREATE INDEX proyecto_estado IF NOT EXISTS
  FOR (p:Proyecto) ON (p.estado);
