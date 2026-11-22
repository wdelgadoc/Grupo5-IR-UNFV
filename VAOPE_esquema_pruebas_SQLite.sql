-- =====================================================================
-- VAOPE · Esquema relacional sintético para la validación de reglas
-- Universidad Nacional Federico Villarreal · Ingeniería de Requerimientos
-- Grupo 5 · Línea base académica v2.4 (39 RF / 19 CU / 23 RN / 22 CP)
--
-- ADVERTENCIA: esquema ACADÉMICO con datos ficticios. No corresponde a la
-- base de datos de VAOPE ni pretende reproducir su modelo de producción.
-- Su único objeto es hacer verificables, de forma reproducible, las reglas
-- de negocio que pueden expresarse como invariantes de persistencia.
-- =====================================================================

PRAGMA foreign_keys = ON;

-- ------------------------------------------------- usuarios y organizadores
CREATE TABLE usuarios (
  id              INTEGER PRIMARY KEY,
  correo          TEXT NOT NULL UNIQUE,                     -- RN-10
  documento       TEXT NOT NULL UNIQUE,                     -- RN-10
  nombres         TEXT NOT NULL,
  fecha_nacimiento TEXT NOT NULL,
  rol             TEXT NOT NULL CHECK (rol IN
                    ('comprador','organizador','administrador','acceso','agente')),
  estado          TEXT NOT NULL DEFAULT 'activa'
                    CHECK (estado IN ('pendiente','activa','bloqueada')),
  -- RN-02: solo mayores de edad. Edad calculada contra la fecha de corte.
  CHECK (CAST((julianday('2026-11-16') - julianday(fecha_nacimiento))/365.25 AS INT) >= 18)
);

CREATE TABLE organizadores (
  id            INTEGER PRIMARY KEY,
  usuario_id    INTEGER NOT NULL UNIQUE REFERENCES usuarios(id),
  razon_social  TEXT NOT NULL,
  -- RN-23: solo un organizador validado puede publicar
  estado        TEXT NOT NULL DEFAULT 'pendiente'
                  CHECK (estado IN ('pendiente','observado','validado','rechazado')),
  aprobado_por  INTEGER REFERENCES usuarios(id),
  fecha_decision TEXT,
  motivo        TEXT
);

-- ------------------------------------------------- eventos, funciones, zonas
CREATE TABLE eventos (
  id             INTEGER PRIMARY KEY,
  organizador_id INTEGER NOT NULL REFERENCES organizadores(id),
  nombre         TEXT NOT NULL,
  categoria      TEXT NOT NULL,
  ciudad         TEXT NOT NULL,
  estado         TEXT NOT NULL DEFAULT 'borrador'
                   CHECK (estado IN ('borrador','publicado','desactivado','cancelado'))
);

CREATE TABLE funciones (
  id          INTEGER PRIMARY KEY,
  evento_id   INTEGER NOT NULL REFERENCES eventos(id),
  fecha_hora  TEXT NOT NULL,
  capacidad   INTEGER NOT NULL CHECK (capacidad >= 0),       -- RF14
  -- RF39 / RN-01: límite entero positivo de entradas por comprador
  limite_por_comprador INTEGER NOT NULL CHECK (limite_por_comprador >= 1),
  UNIQUE (evento_id, fecha_hora)
);

CREATE TABLE zonas (
  id          INTEGER PRIMARY KEY,
  funcion_id  INTEGER NOT NULL REFERENCES funciones(id),
  nombre      TEXT NOT NULL,
  aforo       INTEGER NOT NULL CHECK (aforo > 0),
  precio      NUMERIC NOT NULL CHECK (precio > 0),           -- RF16
  UNIQUE (funcion_id, nombre)
);

-- RN-14: la suma de aforos de las zonas no excede la capacidad de la función
CREATE TRIGGER trg_aforo_insert BEFORE INSERT ON zonas
BEGIN
  SELECT CASE WHEN (
    NEW.aforo + COALESCE((SELECT SUM(aforo) FROM zonas WHERE funcion_id = NEW.funcion_id), 0)
    > (SELECT capacidad FROM funciones WHERE id = NEW.funcion_id)
  ) THEN RAISE(ABORT, 'RN-14: la suma de aforos supera la capacidad de la funcion')
  END;
END;

CREATE TRIGGER trg_aforo_update BEFORE UPDATE OF aforo ON zonas
BEGIN
  SELECT CASE WHEN (
    NEW.aforo + COALESCE((SELECT SUM(aforo) FROM zonas
                          WHERE funcion_id = NEW.funcion_id AND id <> NEW.id), 0)
    > (SELECT capacidad FROM funciones WHERE id = NEW.funcion_id)
  ) THEN RAISE(ABORT, 'RN-14: la suma de aforos supera la capacidad de la funcion')
  END;
END;

-- RN-23: un evento solo se publica si su organizador esta validado
CREATE TRIGGER trg_publicar_evento BEFORE UPDATE OF estado ON eventos
WHEN NEW.estado = 'publicado'
BEGIN
  SELECT CASE WHEN (
    (SELECT estado FROM organizadores WHERE id = NEW.organizador_id) <> 'validado'
  ) THEN RAISE(ABORT, 'RN-23: el organizador no esta validado')
  END;
END;

CREATE TRIGGER trg_publicar_evento_ins BEFORE INSERT ON eventos
WHEN NEW.estado = 'publicado'
BEGIN
  SELECT CASE WHEN (
    (SELECT estado FROM organizadores WHERE id = NEW.organizador_id) <> 'validado'
  ) THEN RAISE(ABORT, 'RN-23: el organizador no esta validado')
  END;
END;

-- ------------------------------------------------- promociones
CREATE TABLE promociones (
  id            INTEGER PRIMARY KEY,
  evento_id     INTEGER NOT NULL REFERENCES eventos(id),
  codigo        TEXT NOT NULL,
  tipo          TEXT NOT NULL CHECK (tipo IN ('porcentaje','monto')),
  valor         NUMERIC NOT NULL CHECK (valor > 0),
  inicio        TEXT NOT NULL,
  fin           TEXT NOT NULL,
  stock_total   INTEGER NOT NULL CHECK (stock_total >= 0),   -- RF32
  usos_por_comprador INTEGER NOT NULL CHECK (usos_por_comprador >= 1),
  UNIQUE (evento_id, codigo),                                -- RF29
  CHECK (fin >= inicio),                                     -- RF31
  CHECK (tipo <> 'porcentaje' OR valor <= 100)               -- RN-17
);

CREATE TABLE usos_promocion (
  id            INTEGER PRIMARY KEY,
  promocion_id  INTEGER NOT NULL REFERENCES promociones(id),
  usuario_id    INTEGER NOT NULL REFERENCES usuarios(id),
  reserva_id    INTEGER,
  estado        TEXT NOT NULL DEFAULT 'reservado'
                  CHECK (estado IN ('reservado','confirmado','liberado'))
);

-- RN-17 / RF32: el cupo promocional no se sobreutiliza
CREATE TRIGGER trg_stock_promocion BEFORE INSERT ON usos_promocion
BEGIN
  SELECT CASE WHEN (
    (SELECT COUNT(*) FROM usos_promocion
      WHERE promocion_id = NEW.promocion_id AND estado IN ('reservado','confirmado'))
    >= (SELECT stock_total FROM promociones WHERE id = NEW.promocion_id)
  ) THEN RAISE(ABORT, 'RN-17: cupo promocional agotado')
  END;
END;

-- ------------------------------------------------- reservas
CREATE TABLE reservas (
  id          INTEGER PRIMARY KEY,
  zona_id     INTEGER NOT NULL REFERENCES zonas(id),
  usuario_id  INTEGER NOT NULL REFERENCES usuarios(id),
  cantidad    INTEGER NOT NULL CHECK (cantidad > 0),
  creada      TEXT NOT NULL,
  expira      TEXT NOT NULL,                                 -- RN-03
  estado      TEXT NOT NULL DEFAULT 'vigente'
                CHECK (estado IN ('vigente','pagada','expirada','liberada'))
);

-- RN-01 / RF39: limite de entradas por comprador y por funcion,
-- contando compras previas y reservas vigentes del mismo comprador
CREATE TRIGGER trg_limite_comprador BEFORE INSERT ON reservas
BEGIN
  SELECT CASE WHEN (
    NEW.cantidad + COALESCE((
      SELECT SUM(r.cantidad) FROM reservas r
        JOIN zonas z  ON z.id = r.zona_id
        JOIN zonas z2 ON z2.id = NEW.zona_id
      WHERE r.usuario_id = NEW.usuario_id
        AND z.funcion_id = z2.funcion_id
        AND r.estado IN ('vigente','pagada')), 0)
    > (SELECT f.limite_por_comprador FROM funciones f
         JOIN zonas z ON z.funcion_id = f.id WHERE z.id = NEW.zona_id)
  ) THEN RAISE(ABORT, 'RN-01: se supera el limite de entradas por comprador')
  END;
END;

-- RN-03 / RF17: una reserva no puede exceder la disponibilidad de la zona
CREATE TRIGGER trg_disponibilidad BEFORE INSERT ON reservas
BEGIN
  SELECT CASE WHEN (
    NEW.cantidad > (
      SELECT z.aforo
        - COALESCE((SELECT SUM(r.cantidad) FROM reservas r
                     WHERE r.zona_id = z.id AND r.estado = 'pagada'), 0)
        - COALESCE((SELECT SUM(r.cantidad) FROM reservas r
                     WHERE r.zona_id = z.id AND r.estado = 'vigente'
                       AND r.expira > NEW.creada), 0)
      FROM zonas z WHERE z.id = NEW.zona_id)
  ) THEN RAISE(ABORT, 'RN-03: disponibilidad insuficiente en la zona')
  END;
END;

-- ------------------------------------------------- transacciones y tickets
CREATE TABLE transacciones (
  id                 INTEGER PRIMARY KEY,
  reserva_id         INTEGER NOT NULL REFERENCES reservas(id),
  operacion_externa  TEXT NOT NULL UNIQUE,                   -- RN-20 idempotencia
  importe            NUMERIC NOT NULL CHECK (importe > 0),
  moneda             TEXT NOT NULL DEFAULT 'PEN',
  medio_pago         TEXT NOT NULL,
  estado             TEXT NOT NULL
                       CHECK (estado IN ('aprobada','rechazada','en_verificacion')),
  fecha              TEXT NOT NULL
);

CREATE TABLE tickets (
  id             INTEGER PRIMARY KEY,
  transaccion_id INTEGER NOT NULL REFERENCES transacciones(id),
  zona_id        INTEGER NOT NULL REFERENCES zonas(id),
  codigo_qr      TEXT NOT NULL UNIQUE,                       -- RN-08
  estado         TEXT NOT NULL DEFAULT 'emitido'
                   CHECK (estado IN ('emitido','utilizado','anulado','caducado')),
  fecha_ingreso  TEXT,
  operador_id    INTEGER REFERENCES usuarios(id),
  dispositivo    TEXT
);

-- RN-06: no se emite ningun ticket sin autorizacion aprobada de la pasarela
CREATE TRIGGER trg_ticket_sin_pago BEFORE INSERT ON tickets
BEGIN
  SELECT CASE WHEN (
    (SELECT estado FROM transacciones WHERE id = NEW.transaccion_id) <> 'aprobada'
  ) THEN RAISE(ABORT, 'RN-06: no se emite ticket sin pago aprobado')
  END;
END;

-- RN-08: un ticket solo pasa de emitido a utilizado una vez
CREATE TRIGGER trg_uso_unico BEFORE UPDATE OF estado ON tickets
WHEN NEW.estado = 'utilizado'
BEGIN
  SELECT CASE WHEN (OLD.estado <> 'emitido')
  THEN RAISE(ABORT, 'RN-08: el ticket no esta en estado emitido')
  END;
END;

-- RN-21: una transaccion aprobada sobre una reserva expirada no emite ticket
CREATE TRIGGER trg_pago_tardio BEFORE INSERT ON tickets
BEGIN
  SELECT CASE WHEN (
    (SELECT r.estado FROM reservas r
       JOIN transacciones t ON t.reserva_id = r.id
      WHERE t.id = NEW.transaccion_id) = 'expirada'
  ) THEN RAISE(ABORT, 'RN-21: reserva expirada, la transaccion va a conciliacion')
  END;
END;

-- ------------------------------------------------- devoluciones
-- Una compra puede pagarse en un solo cargo que cubre varios boletos (dos
-- butacas de S/ 120 en un cargo de S/ 240) y puede recibir un cargo excedente
-- por cobro duplicado. Por eso un cargo admite varias devoluciones legitimas y
-- el control no es la unicidad del cargo, sino el saldo reembolsable
-- acumulado por cargo y por boleto.
CREATE TABLE reembolsos (
  id             INTEGER PRIMARY KEY,
  ticket_id      INTEGER NOT NULL REFERENCES tickets(id),         -- RN-09
  transaccion_id INTEGER NOT NULL REFERENCES transacciones(id),   -- cargo que se restituye
  causa          TEXT NOT NULL
                  CHECK (causa IN ('cancelacion','reprogramacion','cobro_duplicado')), -- RN-16
  estado         TEXT NOT NULL DEFAULT 'solicitado'
                  CHECK (estado IN ('solicitado','aprobado','enviado',
                                    'confirmado','fallido')),     -- RN-22
  clave_idem     TEXT NOT NULL UNIQUE,                            -- RN-20 idempotencia
  importe        NUMERIC NOT NULL CHECK (importe > 0),
  fecha          TEXT NOT NULL
);

-- RN-20: el cargo devuelto debe pertenecer a la misma compra que el boleto
CREATE TRIGGER trg_reembolso_cargo_propio BEFORE INSERT ON reembolsos
BEGIN
  SELECT CASE WHEN (
    (SELECT t.reserva_id FROM transacciones t WHERE t.id = NEW.transaccion_id)
    IS NOT
    (SELECT tr.reserva_id FROM tickets tk
       JOIN transacciones tr ON tr.id = tk.transaccion_id
      WHERE tk.id = NEW.ticket_id)
  ) THEN RAISE(ABORT, 'RN-20: el cargo devuelto no pertenece a la compra del boleto')
  END;
END;

-- RN-20: la suma de las devoluciones vigentes de un cargo no excede lo cobrado
-- en ese cargo. Las devoluciones fallidas no movieron dinero y liberan saldo.
CREATE TRIGGER trg_reembolso_saldo_cargo BEFORE INSERT ON reembolsos
BEGIN
  SELECT CASE WHEN (
    NEW.importe + (SELECT COALESCE(SUM(importe),0) FROM reembolsos
                    WHERE transaccion_id = NEW.transaccion_id
                      AND estado <> 'fallido')
    > (SELECT importe FROM transacciones WHERE id = NEW.transaccion_id)
  ) THEN RAISE(ABORT, 'RN-20: la devolucion excede el saldo reembolsable del cargo')
  END;
END;

-- RN-20: la devolucion que revierte la compra de un boleto no excede el precio
-- de ese boleto. El cargo excedente por cobro duplicado no integra ese precio,
-- de modo que su restitucion se controla solo contra el saldo del cargo.
CREATE TRIGGER trg_reembolso_saldo_boleto BEFORE INSERT ON reembolsos
WHEN NEW.causa IN ('cancelacion','reprogramacion')
 AND NEW.transaccion_id = (SELECT transaccion_id FROM tickets WHERE id = NEW.ticket_id)
BEGIN
  SELECT CASE WHEN (
    NEW.importe + (SELECT COALESCE(SUM(importe),0) FROM reembolsos
                    WHERE ticket_id = NEW.ticket_id
                      AND transaccion_id = NEW.transaccion_id
                      AND causa IN ('cancelacion','reprogramacion')
                      AND estado <> 'fallido')
    > (SELECT z.precio FROM tickets tk
         JOIN zonas z ON z.id = tk.zona_id
        WHERE tk.id = NEW.ticket_id)
  ) THEN RAISE(ABORT, 'RN-20: la devolucion de la compra excede el precio del boleto')
  END;
END;

-- RN-20: el mismo control de saldo rige al actualizar el reembolso, de modo que
-- el cambio de importe, de cargo, de boleto, de causa o de estado no incorpore un
-- movimiento que el cargo ya no soporta. Se excluye del acumulado el propio
-- registro que se actualiza.
CREATE TRIGGER trg_reembolso_saldo_update
BEFORE UPDATE OF importe, transaccion_id, ticket_id, causa, estado ON reembolsos
WHEN NEW.estado <> 'fallido'
BEGIN
  SELECT CASE WHEN (
    NEW.importe + (SELECT COALESCE(SUM(importe),0) FROM reembolsos
                    WHERE transaccion_id = NEW.transaccion_id
                      AND estado <> 'fallido'
                      AND id <> OLD.id)
    > (SELECT importe FROM transacciones WHERE id = NEW.transaccion_id)
  ) THEN RAISE(ABORT, 'RN-20: la devolucion excede el saldo reembolsable del cargo')
  END;
END;

-- RN-20: al actualizar rige tambien el limite acumulado por boleto que se aplica
-- al registrar una reversion. Un cargo de S/ 240 que cubre dos boletos de S/ 120
-- conserva saldo despues de devolver S/ 100 por el primero, pero elevar esa
-- devolucion a S/ 150 excederia el precio de ese boleto. El cargo excedente por
-- cobro duplicado conserva su tratamiento propio y queda fuera de este limite.
CREATE TRIGGER trg_reembolso_saldo_boleto_update
BEFORE UPDATE OF importe, transaccion_id, ticket_id, causa, estado ON reembolsos
WHEN NEW.estado <> 'fallido'
 AND NEW.causa IN ('cancelacion','reprogramacion')
 AND NEW.transaccion_id = (SELECT transaccion_id FROM tickets WHERE id = NEW.ticket_id)
BEGIN
  SELECT CASE WHEN (
    NEW.importe + (SELECT COALESCE(SUM(importe),0) FROM reembolsos
                    WHERE ticket_id = NEW.ticket_id
                      AND transaccion_id = NEW.transaccion_id
                      AND causa IN ('cancelacion','reprogramacion')
                      AND estado <> 'fallido'
                      AND id <> OLD.id)
    > (SELECT z.precio FROM tickets tk
         JOIN zonas z ON z.id = tk.zona_id
        WHERE tk.id = NEW.ticket_id)
  ) THEN RAISE(ABORT, 'RN-20: la devolucion de la compra excede el precio del boleto')
  END;
END;

-- RN-20: cambiar el cargo o el boleto de un reembolso no puede romper el vinculo
-- con la compra, control que ya rige al registrarlo.
CREATE TRIGGER trg_reembolso_cargo_propio_update
BEFORE UPDATE OF transaccion_id, ticket_id ON reembolsos
BEGIN
  SELECT CASE WHEN (
    (SELECT t.reserva_id FROM transacciones t WHERE t.id = NEW.transaccion_id)
    IS NOT
    (SELECT tr.reserva_id FROM tickets tk
       JOIN transacciones tr ON tr.id = tk.transaccion_id
      WHERE tk.id = NEW.ticket_id)
  ) THEN RAISE(ABORT, 'RN-20: el cargo devuelto no pertenece a la compra del boleto')
  END;
END;

-- RN-20: un reembolso confirmado es terminal. La reconfirmacion y el reproceso
-- se rechazan, de manera que un reintento nunca duplique el movimiento.
CREATE TRIGGER trg_reembolso_terminal BEFORE UPDATE ON reembolsos
WHEN OLD.estado = 'confirmado'
BEGIN
  SELECT CASE WHEN (
    NEW.estado <> OLD.estado OR NEW.importe <> OLD.importe
    OR NEW.transaccion_id <> OLD.transaccion_id OR NEW.causa <> OLD.causa
  ) THEN RAISE(ABORT, 'RN-20: el reembolso confirmado no admite reproceso')
  END;
END;

-- RN-22: el ticket se anula solo cuando existe un reembolso confirmado, su
-- causa revierte la compra (cancelacion o reprogramacion) y el cargo devuelto
-- es el que sustenta ese boleto. La devolucion por cobro duplicado restituye el
-- cargo excedente y conserva el boleto, su QR y el cupo vendido; la devolucion
-- de otro cargo de la misma reserva tampoco habilita la anulacion.
CREATE TRIGGER trg_anular_ticket BEFORE UPDATE OF estado ON tickets
WHEN NEW.estado = 'anulado'
BEGIN
  SELECT CASE WHEN NOT EXISTS (
    SELECT 1 FROM reembolsos
     WHERE ticket_id = NEW.id AND estado = 'confirmado'
  ) THEN RAISE(ABORT, 'RN-22: no se anula el boleto sin reembolso confirmado')
  END;
  SELECT CASE WHEN NOT EXISTS (
    SELECT 1 FROM reembolsos
     WHERE ticket_id = NEW.id AND estado = 'confirmado'
       AND causa IN ('cancelacion','reprogramacion')
  ) THEN RAISE(ABORT, 'RN-22: el cobro duplicado restituye el cargo excedente, no anula el boleto')
  END;
  SELECT CASE WHEN NOT EXISTS (
    SELECT 1 FROM reembolsos
     WHERE ticket_id = NEW.id AND estado = 'confirmado'
       AND causa IN ('cancelacion','reprogramacion')
       AND transaccion_id = OLD.transaccion_id
  ) THEN RAISE(ABORT, 'RN-22: el cargo devuelto no es el que sustenta el boleto')
  END;
END;

-- ------------------------------------------------- validacion sin conexion
CREATE TABLE lecturas_offline (
  id            INTEGER PRIMARY KEY,
  ticket_id     INTEGER NOT NULL REFERENCES tickets(id),
  dispositivo   TEXT NOT NULL,
  hora_lectura  TEXT NOT NULL,
  idem_intento  TEXT NOT NULL UNIQUE,                        -- RN-19
  conciliada    INTEGER NOT NULL DEFAULT 0,
  conflicto     INTEGER NOT NULL DEFAULT 0
);

-- ------------------------------------------------- soporte
CREATE TABLE casos_soporte (
  id             INTEGER PRIMARY KEY,
  numero         TEXT NOT NULL UNIQUE,                       -- RF34, RF35
  usuario_id     INTEGER REFERENCES usuarios(id),            -- NULL: reclamo sin cuenta
  contacto       TEXT NOT NULL,
  transaccion_id INTEGER REFERENCES transacciones(id),
  tipo           TEXT NOT NULL CHECK (tipo IN ('consulta','reclamo','queja')),
  estado         TEXT NOT NULL DEFAULT 'abierto'
                   CHECK (estado IN ('abierto','en_atencion','en_espera',
                                     'resuelto','cerrado')),
  fecha_registro TEXT NOT NULL,
  fecha_limite   TEXT NOT NULL                               -- RN-18
);

CREATE TABLE respuestas_caso (
  id         INTEGER PRIMARY KEY,
  caso_id    INTEGER NOT NULL REFERENCES casos_soporte(id),
  agente_id  INTEGER NOT NULL REFERENCES usuarios(id),
  texto      TEXT NOT NULL,
  fecha      TEXT NOT NULL
);

-- ------------------------------------------------- vista de disponibilidad
CREATE VIEW v_disponibilidad AS
SELECT z.id AS zona_id, z.funcion_id, z.nombre, z.aforo,
       z.aforo
       - COALESCE((SELECT SUM(r.cantidad) FROM reservas r
                    WHERE r.zona_id = z.id AND r.estado = 'pagada'), 0)
       - COALESCE((SELECT SUM(r.cantidad) FROM reservas r
                    WHERE r.zona_id = z.id AND r.estado = 'vigente'
                      AND r.expira > datetime('now')), 0) AS disponibles
FROM zonas z;
