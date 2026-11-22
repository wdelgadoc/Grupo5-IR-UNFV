#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VAOPE · Ejecución de las pruebas de reglas de negocio sobre el esquema sintético.

Universidad Nacional Federico Villarreal · Ingeniería de Requerimientos · Grupo 5
Línea base académica v2.4 (39 RF / 19 CU / 23 RN).

ADVERTENCIA: las pruebas se ejecutan sobre un esquema SQLite ACADÉMICO con datos
ficticios. Un resultado satisfactorio NO demuestra conformidad del sistema de
VAOPE ni de su base de datos, que no fueron facilitados.

Uso:  python3 VAOPE_ejecucion_pruebas_BD.py [--json salida.json]
"""
import sqlite3
import json
import sys
import os

ESQUEMA = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       'VAOPE_esquema_pruebas_SQLite.sql')
HOY = '2026-11-16'          # fecha de referencia de los datos de prueba
EJECUTADO = '2026-11-21'    # fecha de la ejecucion registrada en el JSON

RESULTADOS = []


def conectar():
    con = sqlite3.connect(':memory:')
    con.executescript(open(ESQUEMA, encoding='utf-8').read())
    con.execute('PRAGMA foreign_keys = ON')
    return con


def sembrar(con):
    """Datos ficticios mínimos: un organizador validado, un evento publicado,
    una función con dos zonas y tres compradores."""
    c = con.cursor()
    c.executemany(
        "INSERT INTO usuarios (id,correo,documento,nombres,fecha_nacimiento,rol) "
        "VALUES (?,?,?,?,?,?)",
        [(1, 'admin@ejemplo.test', '10000001', 'Administrador Uno', '1985-01-01',
          'administrador'),
         (2, 'org@ejemplo.test', '10000002', 'Organizador Uno', '1988-05-10',
          'organizador'),
         (3, 'comprador1@ejemplo.test', '10000003', 'Comprador Uno', '1995-03-20',
          'comprador'),
         (4, 'comprador2@ejemplo.test', '10000004', 'Comprador Dos', '1990-07-12',
          'comprador'),
         (5, 'acceso@ejemplo.test', '10000005', 'Operador Puerta', '1992-09-02',
          'acceso'),
         (6, 'agente@ejemplo.test', '10000006', 'Agente Soporte', '1991-11-30',
          'agente'),
         (7, 'org2@ejemplo.test', '10000007', 'Organizador Dos', '1987-02-02',
          'organizador')])
    c.execute("INSERT INTO organizadores (id,usuario_id,razon_social,estado,"
              "aprobado_por,fecha_decision) VALUES (1,2,'Productora Uno','validado',1,?)",
              (HOY,))
    c.execute("INSERT INTO organizadores (id,usuario_id,razon_social,estado) "
              "VALUES (2,7,'Productora Dos','pendiente')")
    c.execute("INSERT INTO eventos (id,organizador_id,nombre,categoria,ciudad,estado) "
              "VALUES (1,1,'Concierto de cumbia','conciertos','Lima','publicado')")
    c.execute("INSERT INTO funciones (id,evento_id,fecha_hora,capacidad,"
              "limite_por_comprador) VALUES (1,1,'2026-11-20 20:00',5000,4)")
    c.execute("INSERT INTO zonas (id,funcion_id,nombre,aforo,precio) "
              "VALUES (1,1,'Platea',100,120.00)")
    c.execute("INSERT INTO zonas (id,funcion_id,nombre,aforo,precio) "
              "VALUES (2,1,'General',200,45.00)")
    c.execute("INSERT INTO promociones (id,evento_id,codigo,tipo,valor,inicio,fin,"
              "stock_total,usos_por_comprador) "
              "VALUES (1,1,'PREVENTA20','porcentaje',20,'2026-10-01','2026-11-19',2,1)")
    con.commit()


def prueba(codigo, invariante, refs):
    """Decorador: registra el resultado de cada comprobación."""
    def envoltura(fn):
        con = conectar()
        try:
            sembrar(con)
            detalle = fn(con)
            RESULTADOS.append({'prueba': codigo, 'invariante': invariante,
                               'refs': refs, 'resultado': 'PASO',
                               'detalle': detalle or 'Comportamiento conforme.'})
        except AssertionError as e:
            RESULTADOS.append({'prueba': codigo, 'invariante': invariante,
                               'refs': refs, 'resultado': 'FALLO',
                               'detalle': str(e)})
        except Exception as e:
            RESULTADOS.append({'prueba': codigo, 'invariante': invariante,
                               'refs': refs, 'resultado': 'ERROR',
                               'detalle': f'{type(e).__name__}: {e}'})
        finally:
            con.close()
        return fn
    return envoltura


def debe_fallar(con, sql, params=(), motivo='', espera=None):
    """La sentencia debe ser rechazada por el motor. Cuando se indica «espera»,
    el mensaje del motor debe contener ese texto: una prueba que se satisface
    con un rechazo de otro control no acredita el control que enuncia."""
    try:
        con.execute(sql, params)
        con.commit()
    except sqlite3.IntegrityError as e:
        if espera is not None and espera not in str(e):
            raise AssertionError(
                f'El rechazo proviene de un control distinto del enunciado. '
                f'Se esperaba «{espera}» y el motor respondió «{e}».')
        return f'Rechazado por el motor: {e}'
    raise AssertionError(f'La operación fue aceptada y debía rechazarse. {motivo}')


def debe_pasar(con, sql, params=()):
    con.execute(sql, params)
    con.commit()
    return 'Operación aceptada como se esperaba.'


# =====================================================================
# BD-01 a BD-26
# =====================================================================
@prueba('BD-01', 'Unicidad del correo electrónico por cuenta', 'RF01 · RN-10')
def t01(con):
    return debe_fallar(con,
        "INSERT INTO usuarios (correo,documento,nombres,fecha_nacimiento,rol) "
        "VALUES ('comprador1@ejemplo.test','99999999','Duplicado','1990-01-01','comprador')")


@prueba('BD-02', 'Unicidad del documento de identidad por cuenta', 'RF01 · RN-10')
def t02(con):
    return debe_fallar(con,
        "INSERT INTO usuarios (correo,documento,nombres,fecha_nacimiento,rol) "
        "VALUES ('nuevo@ejemplo.test','10000003','Duplicado','1990-01-01','comprador')")


@prueba('BD-03', 'Restricción de mayoría de edad en el registro', 'RF01 · RN-02')
def t03(con):
    return debe_fallar(con,
        "INSERT INTO usuarios (correo,documento,nombres,fecha_nacimiento,rol) "
        "VALUES ('menor@ejemplo.test','20000001','Menor','2010-06-01','comprador')")


@prueba('BD-04', 'La suma de aforos de zonas no supera la capacidad de la función',
        'RF14, RF15 · RN-14')
def t04(con):
    con.execute("UPDATE funciones SET capacidad = 320 WHERE id = 1")
    con.commit()
    return debe_fallar(con,
        "INSERT INTO zonas (funcion_id,nombre,aforo,precio) VALUES (1,'VIP',100,180.00)",
        motivo='Aforo acumulado 300 + 100 sobre capacidad 320.')


@prueba('BD-05', 'Un organizador no validado no puede publicar eventos',
        'RF38 · RN-23 · CU-19')
def t05(con):
    return debe_fallar(con,
        "INSERT INTO eventos (organizador_id,nombre,categoria,ciudad,estado) "
        "VALUES (2,'Evento no autorizado','teatro','Lima','publicado')")


@prueba('BD-06', 'El precio de una zona debe ser mayor que cero', 'RF16')
def t06(con):
    return debe_fallar(con,
        "INSERT INTO zonas (funcion_id,nombre,aforo,precio) VALUES (1,'Gratis',10,0)")


@prueba('BD-07', 'Un código QR identifica a un único ticket', 'RF20 · RN-08')
def t07(con):
    con.execute("INSERT INTO reservas (id,zona_id,usuario_id,cantidad,creada,expira,estado) "
                "VALUES (1,1,3,1,'2026-11-16 10:00','2026-11-16 10:10','pagada')")
    con.execute("INSERT INTO transacciones (id,reserva_id,operacion_externa,importe,"
                "medio_pago,estado,fecha) VALUES (1,1,'OP-0001',120.00,'tarjeta',"
                "'aprobada','2026-11-16 10:05')")
    con.execute("INSERT INTO tickets (id,transaccion_id,zona_id,codigo_qr) "
                "VALUES (1,1,1,'QR-AAA')")
    con.commit()
    return debe_fallar(con,
        "INSERT INTO tickets (transaccion_id,zona_id,codigo_qr) VALUES (1,1,'QR-AAA')")


@prueba('BD-08', 'Un ticket solo pasa de emitido a utilizado una vez', 'RF22 · RN-08')
def t08(con):
    con.execute("INSERT INTO reservas (id,zona_id,usuario_id,cantidad,creada,expira,estado) "
                "VALUES (1,1,3,1,'2026-11-16 10:00','2026-11-16 10:10','pagada')")
    con.execute("INSERT INTO transacciones (id,reserva_id,operacion_externa,importe,"
                "medio_pago,estado,fecha) VALUES (1,1,'OP-0002',120.00,'tarjeta',"
                "'aprobada','2026-11-16 10:05')")
    con.execute("INSERT INTO tickets (id,transaccion_id,zona_id,codigo_qr) "
                "VALUES (1,1,1,'QR-BBB')")
    con.execute("UPDATE tickets SET estado='utilizado', fecha_ingreso='2026-11-20 19:05', "
                "operador_id=5, dispositivo='PUERTA-1' WHERE id=1")
    con.commit()
    r = debe_fallar(con, "UPDATE tickets SET estado='utilizado', "
                         "fecha_ingreso='2026-11-20 19:40' WHERE id=1")
    hora = con.execute("SELECT fecha_ingreso FROM tickets WHERE id=1").fetchone()[0]
    assert hora == '2026-11-20 19:05', 'Se perdió la hora del primer ingreso.'
    return r + ' Se conservó el primer ingreso 2026-11-20 19:05.'


@prueba('BD-09', 'No se emite ticket sin pago aprobado', 'RF19, RF20 · RN-06')
def t09(con):
    con.execute("INSERT INTO reservas (id,zona_id,usuario_id,cantidad,creada,expira,estado) "
                "VALUES (1,1,3,1,'2026-11-16 10:00','2026-11-16 10:10','vigente')")
    con.execute("INSERT INTO transacciones (id,reserva_id,operacion_externa,importe,"
                "medio_pago,estado,fecha) VALUES (1,1,'OP-0003',120.00,'tarjeta',"
                "'rechazada','2026-11-16 10:05')")
    con.commit()
    return debe_fallar(con,
        "INSERT INTO tickets (transaccion_id,zona_id,codigo_qr) VALUES (1,1,'QR-CCC')")


@prueba('BD-10', 'Idempotencia del identificador de operación de la pasarela',
        'RF25, RF26 · RN-20')
def t10(con):
    con.execute("INSERT INTO reservas (id,zona_id,usuario_id,cantidad,creada,expira,estado) "
                "VALUES (1,1,3,1,'2026-11-16 10:00','2026-11-16 10:10','pagada')")
    con.execute("INSERT INTO transacciones (id,reserva_id,operacion_externa,importe,"
                "medio_pago,estado,fecha) VALUES (1,1,'OP-REPETIDA',120.00,'yape',"
                "'aprobada','2026-11-16 10:05')")
    con.commit()
    return debe_fallar(con,
        "INSERT INTO transacciones (reserva_id,operacion_externa,importe,medio_pago,"
        "estado,fecha) VALUES (1,'OP-REPETIDA',120.00,'yape','aprobada',"
        "'2026-11-16 10:06')", motivo='Reintento del webhook de la pasarela.')


@prueba('BD-11', 'El cupo promocional no se sobreutiliza', 'RF32, RF33 · RN-17')
def t11(con):
    con.execute("INSERT INTO usos_promocion (promocion_id,usuario_id,estado) "
                "VALUES (1,3,'confirmado')")
    con.execute("INSERT INTO usos_promocion (promocion_id,usuario_id,estado) "
                "VALUES (1,4,'reservado')")
    con.commit()
    return debe_fallar(con,
        "INSERT INTO usos_promocion (promocion_id,usuario_id,estado) "
        "VALUES (1,1,'reservado')", motivo='Stock de la promoción = 2.')


@prueba('BD-12', 'El reintento de una devolución ya registrada se rechaza y la devolución del otro boleto del mismo cargo procede',
        'RF28 · RN-20')
def t12(con):
    con.execute("INSERT INTO reservas (id,zona_id,usuario_id,cantidad,creada,expira,estado) "
                "VALUES (1,1,3,2,'2026-11-16 10:00','2026-11-16 10:10','pagada')")
    con.execute("INSERT INTO transacciones (id,reserva_id,operacion_externa,importe,"
                "medio_pago,estado,fecha) VALUES (1,1,'OP-0004',240.00,'tarjeta',"
                "'aprobada','2026-11-16 10:05')")
    con.execute("INSERT INTO tickets (id,transaccion_id,zona_id,codigo_qr) "
                "VALUES (1,1,1,'QR-DDD')")
    con.execute("INSERT INTO tickets (id,transaccion_id,zona_id,codigo_qr) "
                "VALUES (2,1,1,'QR-DD2')")
    con.execute("INSERT INTO reembolsos (ticket_id,transaccion_id,causa,estado,clave_idem,importe,fecha) "
                "VALUES (1,1,'cancelacion','solicitado','IDEM-12A',120.00,?)", (HOY,))
    con.commit()
    r = debe_fallar(con,
        "INSERT INTO reembolsos (ticket_id,transaccion_id,causa,estado,clave_idem,importe,fecha) "
        "VALUES (1,1,'cancelacion','solicitado','IDEM-12A',120.00,?)", (HOY,),
        motivo='Reintento de una devolución ya registrada sobre el mismo boleto.',
        espera='excede el precio del boleto')
    est, imp, cuantas = con.execute(
        "SELECT estado, importe, COUNT(*) FROM reembolsos WHERE ticket_id=1").fetchone()
    assert cuantas == 1 and est == 'solicitado' and float(imp) == 120.00, \
        (f'El reintento debía dejar intacta la solicitud original; hay {cuantas} registros, '
         f'el primero «{est}» por S/ {imp}.')
    debe_pasar(con,
        "INSERT INTO reembolsos (ticket_id,transaccion_id,causa,estado,clave_idem,importe,fecha) "
        "VALUES (2,1,'cancelacion','solicitado','IDEM-12B',120.00,?)", (HOY,))
    n, suma = con.execute("SELECT COUNT(*), COALESCE(SUM(importe),0) FROM reembolsos "
                          "WHERE transaccion_id=1").fetchone()
    assert n == 2, f'Se esperaban 2 devoluciones sobre el cargo; hay {n}.'
    assert float(suma) == 240.00, f'El acumulado devuelto debía ser S/ 240.00; es S/ {suma}.'
    return (r + f' El control de saldo del boleto rechazó el reintento y la solicitud original '
            f'se conservó «{est}» por S/ {imp:.2f}. La devolución del segundo boleto sobre el '
            f'mismo cargo fue aceptada: {n} devoluciones por S/ {suma:.2f}, que es el importe '
            f'cobrado. El rechazo por clave de idempotencia se verifica en BD-24.')


@prueba('BD-13', 'Una causa de devolución no contemplada se rechaza', 'RF28 · RN-16')
def t13(con):
    con.execute("INSERT INTO reservas (id,zona_id,usuario_id,cantidad,creada,expira,estado) "
                "VALUES (1,1,3,1,'2026-11-16 10:00','2026-11-16 10:10','pagada')")
    con.execute("INSERT INTO transacciones (id,reserva_id,operacion_externa,importe,"
                "medio_pago,estado,fecha) VALUES (1,1,'OP-0005',120.00,'tarjeta',"
                "'aprobada','2026-11-16 10:05')")
    con.execute("INSERT INTO tickets (id,transaccion_id,zona_id,codigo_qr) "
                "VALUES (1,1,1,'QR-EEE')")
    con.commit()
    return debe_fallar(con,
        "INSERT INTO reembolsos (ticket_id,causa,estado,clave_idem,importe,fecha) "
        "VALUES (1,'cambio_de_opinion','solicitado','IDEM-3',120.00,?)", (HOY,),
        motivo='RN-16 admite solo cancelación, reprogramación o cobro duplicado.')


@prueba('BD-14', 'El conflicto de lectura sin conexión queda registrado y es detectable',
        'RF22 · RN-19')
def t14(con):
    con.execute("INSERT INTO reservas (id,zona_id,usuario_id,cantidad,creada,expira,estado) "
                "VALUES (1,1,3,1,'2026-11-16 10:00','2026-11-16 10:10','pagada')")
    con.execute("INSERT INTO transacciones (id,reserva_id,operacion_externa,importe,"
                "medio_pago,estado,fecha) VALUES (1,1,'OP-0006',120.00,'tarjeta',"
                "'aprobada','2026-11-16 10:05')")
    con.execute("INSERT INTO tickets (id,transaccion_id,zona_id,codigo_qr) "
                "VALUES (1,1,1,'QR-FFF')")
    con.execute("INSERT INTO lecturas_offline (ticket_id,dispositivo,hora_lectura,"
                "idem_intento) VALUES (1,'PUERTA-1','2026-11-20 19:05','INT-A')")
    con.execute("INSERT INTO lecturas_offline (ticket_id,dispositivo,hora_lectura,"
                "idem_intento) VALUES (1,'PUERTA-2','2026-11-20 19:06','INT-B')")
    con.commit()
    conflictos = con.execute(
        "SELECT ticket_id, COUNT(DISTINCT dispositivo) FROM lecturas_offline "
        "GROUP BY ticket_id HAVING COUNT(*) > 1").fetchall()
    assert conflictos, 'El conflicto entre dispositivos no resultó detectable.'
    con.execute("UPDATE lecturas_offline SET conflicto=1 WHERE ticket_id=1 "
                "AND hora_lectura > (SELECT MIN(hora_lectura) FROM lecturas_offline "
                "WHERE ticket_id=1)")
    con.commit()
    marcadas = con.execute("SELECT COUNT(*) FROM lecturas_offline "
                           "WHERE conflicto=1").fetchone()[0]
    assert marcadas == 1, f'Se esperaba 1 lectura en conflicto, se marcaron {marcadas}.'
    return ('Detectadas 2 lecturas del mismo ticket en dispositivos distintos; '
            'se marcó 1 como conflicto y se conservó la primera por hora. '
            'La detección es posterior a la sincronización, no la impide.')


@prueba('BD-15', 'Cada reclamo recibe un código único', 'RF35 · RN-18')
def t15(con):
    con.execute("INSERT INTO casos_soporte (numero,usuario_id,contacto,tipo,"
                "fecha_registro,fecha_limite) VALUES ('REC-00001',3,"
                "'comprador1@ejemplo.test','reclamo','2026-11-16','2026-12-09')")
    con.commit()
    return debe_fallar(con,
        "INSERT INTO casos_soporte (numero,usuario_id,contacto,tipo,fecha_registro,"
        "fecha_limite) VALUES ('REC-00001',4,'comprador2@ejemplo.test','reclamo',"
        "'2026-11-16','2026-12-09')")


@prueba('BD-16', 'El estado de un caso se limita al catálogo definido', 'RF34 a RF37')
def t16(con):
    return debe_fallar(con,
        "INSERT INTO casos_soporte (numero,usuario_id,contacto,tipo,estado,"
        "fecha_registro,fecha_limite) VALUES ('REC-00002',3,'c@ejemplo.test',"
        "'reclamo','archivado_sin_respuesta','2026-11-16','2026-12-09')")


@prueba('BD-17', 'La disponibilidad descuenta vendidos y reservas vigentes',
        'RF17, RF18 · RN-03')
def t17(con):
    con.execute("INSERT INTO reservas (id,zona_id,usuario_id,cantidad,creada,expira,estado) "
                "VALUES (1,1,3,2,'2026-11-16 10:00','2099-01-01 00:00','pagada')")
    con.execute("INSERT INTO reservas (id,zona_id,usuario_id,cantidad,creada,expira,estado) "
                "VALUES (2,1,4,3,'2026-11-16 10:00','2099-01-01 00:00','vigente')")
    con.commit()
    disp = con.execute("SELECT disponibles FROM v_disponibilidad "
                       "WHERE zona_id=1").fetchone()[0]
    assert disp == 95, f'Disponibilidad esperada 95 (100-2-3); obtenida {disp}.'
    return f'Aforo 100, vendidas 2, reservadas vigentes 3 → disponibles {disp}.'


@prueba('BD-18', 'Una reserva expirada deja de bloquear inventario', 'RF18 · RN-03')
def t18(con):
    con.execute("INSERT INTO reservas (id,zona_id,usuario_id,cantidad,creada,expira,estado) "
                "VALUES (1,1,3,4,'2026-11-16 10:00','2026-11-16 10:10','vigente')")
    con.commit()
    antes = con.execute("SELECT disponibles FROM v_disponibilidad "
                        "WHERE zona_id=1").fetchone()[0]
    con.execute("UPDATE reservas SET estado='expirada' WHERE id=1")
    con.commit()
    despues = con.execute("SELECT disponibles FROM v_disponibilidad "
                          "WHERE zona_id=1").fetchone()[0]
    assert despues == 100, f'Tras expirar se esperaba 100; se obtuvo {despues}.'
    return (f'Con la reserva vencida la disponibilidad era {antes} por fecha de '
            f'expiración pasada; tras marcarla expirada quedó en {despues}.')


@prueba('BD-19', 'Todo ticket se relaciona con una transacción y una reserva',
        'RF19, RF20 · RN-06')
def t19(con):
    return debe_fallar(con,
        "INSERT INTO tickets (transaccion_id,zona_id,codigo_qr) "
        "VALUES (999,1,'QR-HUERFANO')", motivo='Transacción inexistente.')


@prueba('BD-20', 'El valor de una promoción porcentual no excede el 100 %', 'RF30 · RN-17')
def t20(con):
    return debe_fallar(con,
        "INSERT INTO promociones (evento_id,codigo,tipo,valor,inicio,fin,stock_total,"
        "usos_por_comprador) VALUES (1,'EXCESO','porcentaje',120,'2026-10-01',"
        "'2026-11-19',10,1)")


@prueba('BD-21', 'El límite de entradas por comprador considera compras y reservas vigentes',
        'RF39 · RN-01')
def t21(con):
    con.execute("INSERT INTO reservas (zona_id,usuario_id,cantidad,creada,expira,estado) "
                "VALUES (1,3,3,'2026-11-16 10:00','2099-01-01 00:00','pagada')")
    con.commit()
    r = debe_fallar(con,
        "INSERT INTO reservas (zona_id,usuario_id,cantidad,creada,expira,estado) "
        "VALUES (2,3,2,'2026-11-16 10:05','2099-01-01 00:00','vigente')",
        motivo='Límite por comprador = 4; ya tenía 3 en la misma función.')
    return r + ' El cómputo cruzó zonas distintas de la misma función.'


@prueba('BD-22', 'Un pago aprobado sobre reserva expirada no emite ticket',
        'RF25 · RN-21')
def t22(con):
    con.execute("INSERT INTO reservas (id,zona_id,usuario_id,cantidad,creada,expira,estado) "
                "VALUES (1,1,3,1,'2026-11-16 10:00','2026-11-16 10:10','expirada')")
    con.execute("INSERT INTO transacciones (id,reserva_id,operacion_externa,importe,"
                "medio_pago,estado,fecha) VALUES (1,1,'OP-TARDIA',120.00,'tarjeta',"
                "'aprobada','2026-11-16 10:14')")
    con.commit()
    return debe_fallar(con,
        "INSERT INTO tickets (transaccion_id,zona_id,codigo_qr) VALUES (1,1,'QR-TARDE')",
        motivo='La reserva venció antes de la confirmación del cobro.')


@prueba('BD-23', 'Tras devolver el excedente, la reversión de la compra anula el boleto al confirmarse',
        'RF28 · RN-16, RN-22')
def t23(con):
    con.execute("INSERT INTO reservas (id,zona_id,usuario_id,cantidad,creada,expira,estado) "
                "VALUES (1,1,3,1,'2026-11-21 10:00','2026-11-21 10:10','pagada')")
    con.execute("INSERT INTO transacciones (id,reserva_id,operacion_externa,importe,"
                "medio_pago,estado,fecha) VALUES (1,1,'OP-0027',120.00,'tarjeta',"
                "'aprobada','2026-11-21 10:05')")
    con.execute("INSERT INTO transacciones (id,reserva_id,operacion_externa,importe,"
                "medio_pago,estado,fecha) VALUES (2,1,'OP-0028',120.00,'tarjeta',"
                "'aprobada','2026-11-21 10:06')")
    con.execute("INSERT INTO tickets (id,transaccion_id,zona_id,codigo_qr) "
                "VALUES (1,1,1,'QR-GGG')")
    con.execute("INSERT INTO reembolsos (id,ticket_id,transaccion_id,causa,estado,clave_idem,importe,fecha) "
                "VALUES (1,1,2,'cobro_duplicado','confirmado','IDEM-9A',120.00,?)", (HOY,))
    con.execute("INSERT INTO reembolsos (id,ticket_id,transaccion_id,causa,estado,clave_idem,importe,fecha) "
                "VALUES (2,1,1,'cancelacion','enviado','IDEM-9B',120.00,?)", (HOY,))
    con.commit()
    r = debe_fallar(con, "UPDATE tickets SET estado='anulado' WHERE id=1",
                    motivo='El único reembolso confirmado es el del cargo excedente, que no '
                           'revierte la compra; el del cargo original sigue «enviado».',
                    espera='no anula el boleto')
    con.execute("UPDATE reembolsos SET estado='confirmado' WHERE id=2")
    con.execute("UPDATE tickets SET estado='anulado' WHERE id=1")
    con.commit()
    est = con.execute("SELECT estado FROM tickets WHERE id=1").fetchone()[0]
    assert est == 'anulado', 'Confirmado el reembolso de la cancelación, la anulación debía proceder.'
    cobrado = con.execute("SELECT COALESCE(SUM(importe),0) FROM transacciones WHERE reserva_id=1").fetchone()[0]
    devuelto = con.execute("SELECT COALESCE(SUM(importe),0) FROM reembolsos WHERE estado='confirmado' "
                           "AND transaccion_id IN (SELECT id FROM transacciones WHERE reserva_id=1)").fetchone()[0]
    assert cobrado - devuelto == 0, 'El saldo neto de la compra debía quedar en cero.'
    return r + f' Confirmado el reembolso del cargo original, el boleto quedó «{est}» y el saldo neto de los dos cargos es S/ {cobrado - devuelto:.2f}.'


@prueba('BD-24', 'La clave de idempotencia del reembolso impide operaciones repetidas',
        'RF28 · RN-20')
def t24(con):
    con.execute("INSERT INTO reservas (id,zona_id,usuario_id,cantidad,creada,expira,estado) "
                "VALUES (1,1,3,2,'2026-11-16 10:00','2026-11-16 10:10','pagada')")
    con.execute("INSERT INTO transacciones (id,reserva_id,operacion_externa,importe,"
                "medio_pago,estado,fecha) VALUES (1,1,'OP-0008',240.00,'tarjeta',"
                "'aprobada','2026-11-16 10:05')")
    con.execute("INSERT INTO tickets (id,transaccion_id,zona_id,codigo_qr) "
                "VALUES (1,1,1,'QR-HHH')")
    con.execute("INSERT INTO tickets (id,transaccion_id,zona_id,codigo_qr) "
                "VALUES (2,1,1,'QR-III')")
    con.execute("INSERT INTO transacciones (id,reserva_id,operacion_externa,importe,"
                "medio_pago,estado,fecha) VALUES (2,1,'OP-0009',120.00,'tarjeta',"
                "'aprobada','2026-11-16 10:06')")
    con.execute("INSERT INTO reembolsos (ticket_id,transaccion_id,causa,estado,clave_idem,importe,fecha) "
                "VALUES (1,1,'reprogramacion','enviado','IDEM-REPETIDA',120.00,?)", (HOY,))
    con.commit()
    return debe_fallar(con,
        "INSERT INTO reembolsos (ticket_id,transaccion_id,causa,estado,clave_idem,importe,fecha) "
        "VALUES (2,2,'reprogramacion','enviado','IDEM-REPETIDA',120.00,?)", (HOY,),
        motivo='Reintento con la misma clave de idempotencia.',
        espera='reembolsos.clave_idem')


@prueba('BD-25', 'El Libro de Reclamaciones admite registro sin cuenta ni compra',
        'RF35 · CU-17')
def t25(con):
    r = debe_pasar(con,
        "INSERT INTO casos_soporte (numero,usuario_id,contacto,tipo,fecha_registro,"
        "fecha_limite) VALUES ('REC-00050',NULL,'visitante@ejemplo.test','reclamo',"
        "'2026-11-16','2026-12-09')")
    n = con.execute("SELECT COUNT(*) FROM casos_soporte WHERE usuario_id IS NULL "
                    "AND transaccion_id IS NULL").fetchone()[0]
    assert n == 1, 'El reclamo sin cuenta no quedó registrado.'
    return r + ' Reclamo registrado sin usuario ni transacción asociada.'


@prueba('BD-26', 'El historial de respuestas de un caso no se sobrescribe',
        'RF37 · RN-18')
def t26(con):
    con.execute("INSERT INTO casos_soporte (id,numero,usuario_id,contacto,tipo,"
                "fecha_registro,fecha_limite) VALUES (1,'REC-00060',3,"
                "'c@ejemplo.test','reclamo','2026-11-16','2026-12-09')")
    con.execute("INSERT INTO respuestas_caso (caso_id,agente_id,texto,fecha) "
                "VALUES (1,6,'Primera respuesta','2026-11-18')")
    con.execute("UPDATE casos_soporte SET estado='resuelto' WHERE id=1")
    con.execute("UPDATE casos_soporte SET estado='abierto' WHERE id=1")
    con.execute("INSERT INTO respuestas_caso (caso_id,agente_id,texto,fecha) "
                "VALUES (1,6,'Segunda respuesta tras reapertura','2026-11-20')")
    con.commit()
    n = con.execute("SELECT COUNT(*) FROM respuestas_caso WHERE caso_id=1").fetchone()[0]
    assert n == 2, f'Se esperaban 2 respuestas conservadas; hay {n}.'
    return f'Reapertura del caso con {n} respuestas conservadas en el historial.'


# =====================================================================

@prueba('BD-27', 'La devolución del cargo excedente identifica el cargo, conserva el boleto y deja el importe neto cobrado',
        'RF28 · RN-16, RN-20, RN-22')
def t27(con):
    con.execute("INSERT INTO reservas (id,zona_id,usuario_id,cantidad,creada,expira,estado) "
                "VALUES (1,1,3,1,'2026-11-21 10:00','2026-11-21 10:10','pagada')")
    con.execute("INSERT INTO transacciones (id,reserva_id,operacion_externa,importe,"
                "medio_pago,estado,fecha) VALUES (1,1,'OP-0027',120.00,'tarjeta',"
                "'aprobada','2026-11-21 10:05')")
    con.execute("INSERT INTO transacciones (id,reserva_id,operacion_externa,importe,"
                "medio_pago,estado,fecha) VALUES (2,1,'OP-0028',120.00,'tarjeta',"
                "'aprobada','2026-11-21 10:06')")
    con.execute("INSERT INTO tickets (id,transaccion_id,zona_id,codigo_qr) "
                "VALUES (1,1,1,'QR-DUP')")
    con.execute("INSERT INTO reembolsos (id,ticket_id,transaccion_id,causa,estado,clave_idem,importe,fecha) "
                "VALUES (1,1,2,'cobro_duplicado','confirmado','IDEM-27',120.00,?)", (HOY,))
    con.commit()
    r = debe_fallar(con, "UPDATE tickets SET estado='anulado' WHERE id=1",
                    motivo='La causa del reembolso es cobro duplicado: restituye el cargo excedente.',
                    espera='no anula el boleto')
    op = con.execute("SELECT t.operacion_externa FROM reembolsos rb "
                     "JOIN transacciones t ON t.id = rb.transaccion_id WHERE rb.id=1").fetchone()[0]
    assert op == 'OP-0028', f'El reembolso debía identificar el cargo excedente; identifica {op}.'
    est, qr = con.execute("SELECT estado, codigo_qr FROM tickets WHERE id=1").fetchone()
    assert est == 'emitido' and qr == 'QR-DUP', \
        f'El boleto debía conservar su vigencia y su código; está «{est}» con código {qr}.'
    cobrado = con.execute("SELECT COALESCE(SUM(importe),0) FROM transacciones "
                          "WHERE reserva_id=1").fetchone()[0]
    devuelto = con.execute("SELECT COALESCE(SUM(importe),0) FROM reembolsos "
                           "WHERE estado='confirmado'").fetchone()[0]
    neto = float(cobrado) - float(devuelto)
    assert neto == 120.00, f'El importe neto cobrado debía ser S/ 120.00; es S/ {neto:.2f}.'
    vendidas = con.execute("SELECT cantidad FROM reservas WHERE id=1 AND estado='pagada'").fetchone()[0]
    assert vendidas == 1, f'El cupo vendido debía conservarse en 1; es {vendidas}.'
    return (r + f' Se devolvió {op}; el boleto conserva el estado «{est}» con su código {qr}, '
            f'el importe neto cobrado es S/ {neto:.2f} y el cupo sigue vendido ({vendidas}).')


@prueba('BD-28', 'Un reembolso no puede asociarse al cargo de otra compra', 'RF28 · RN-20')
def t28(con):
    con.execute("INSERT INTO reservas (id,zona_id,usuario_id,cantidad,creada,expira,estado) "
                "VALUES (1,1,3,1,'2026-11-21 10:00','2026-11-21 10:10','pagada')")
    con.execute("INSERT INTO reservas (id,zona_id,usuario_id,cantidad,creada,expira,estado) "
                "VALUES (2,1,4,1,'2026-11-21 11:00','2026-11-21 11:10','pagada')")
    con.execute("INSERT INTO transacciones (id,reserva_id,operacion_externa,importe,"
                "medio_pago,estado,fecha) VALUES (1,1,'OP-0030',120.00,'tarjeta',"
                "'aprobada','2026-11-21 10:05')")
    con.execute("INSERT INTO transacciones (id,reserva_id,operacion_externa,importe,"
                "medio_pago,estado,fecha) VALUES (2,2,'OP-0031',120.00,'tarjeta',"
                "'aprobada','2026-11-21 11:05')")
    con.execute("INSERT INTO tickets (id,transaccion_id,zona_id,codigo_qr) "
                "VALUES (1,1,1,'QR-OTR')")
    con.commit()
    r = debe_fallar(con,
        "INSERT INTO reembolsos (ticket_id,transaccion_id,causa,estado,clave_idem,importe,fecha) "
        "VALUES (1,2,'cobro_duplicado','solicitado','IDEM-28',120.00,?)", (HOY,),
        motivo='El cargo OP-0031 pertenece a la compra de otro comprador.',
        espera='no pertenece a la compra del boleto')
    est = con.execute("SELECT estado FROM tickets WHERE id=1").fetchone()[0]
    saldo = con.execute("SELECT COALESCE(SUM(importe),0) FROM transacciones WHERE reserva_id=1").fetchone()[0]
    return r + f' El boleto conserva el estado «{est}» y el saldo de su compra permanece en S/ {saldo:.2f}.'


# ---------------------------------------------------------------------
# BD-29 a BD-32: devoluciones parciales, saldo reembolsable y terminalidad
# incorporadas por la solicitud de cambio SC-09 (linea base v2.4).
# ---------------------------------------------------------------------
@prueba('BD-29', 'Dos devoluciones parciales del mismo cargo anulan cada boleto por separado y dejan el saldo en cero',
        'RF28 · RN-20, RN-22')
def t29(con):
    con.execute("INSERT INTO reservas (id,zona_id,usuario_id,cantidad,creada,expira,estado) "
                "VALUES (1,1,3,2,'2026-11-21 09:00','2026-11-21 09:10','pagada')")
    con.execute("INSERT INTO transacciones (id,reserva_id,operacion_externa,importe,"
                "medio_pago,estado,fecha) VALUES (1,1,'OP-0040',240.00,'tarjeta',"
                "'aprobada','2026-11-21 09:05')")
    con.execute("INSERT INTO tickets (id,transaccion_id,zona_id,codigo_qr) "
                "VALUES (1,1,1,'QR-P01')")
    con.execute("INSERT INTO tickets (id,transaccion_id,zona_id,codigo_qr) "
                "VALUES (2,1,1,'QR-P02')")
    con.execute("INSERT INTO reembolsos (id,ticket_id,transaccion_id,causa,estado,clave_idem,importe,fecha) "
                "VALUES (1,1,1,'cancelacion','enviado','IDEM-29A',120.00,?)", (HOY,))
    con.execute("INSERT INTO reembolsos (id,ticket_id,transaccion_id,causa,estado,clave_idem,importe,fecha) "
                "VALUES (2,2,1,'cancelacion','enviado','IDEM-29B',120.00,?)", (HOY,))
    con.commit()
    con.execute("UPDATE reembolsos SET estado='confirmado' WHERE id=1")
    con.execute("UPDATE tickets SET estado='anulado' WHERE id=1")
    con.commit()
    e1 = con.execute("SELECT estado FROM tickets WHERE id=1").fetchone()[0]
    e2 = con.execute("SELECT estado FROM tickets WHERE id=2").fetchone()[0]
    assert e1 == 'anulado', f'El primer boleto debía quedar anulado; está «{e1}».'
    assert e2 == 'emitido', f'El segundo boleto debía seguir vigente; está «{e2}».'
    r = debe_fallar(con, "UPDATE tickets SET estado='anulado' WHERE id=2",
                    motivo='La devolución del segundo boleto aún no está confirmada.',
                    espera='sin reembolso confirmado')
    con.execute("UPDATE reembolsos SET estado='confirmado' WHERE id=2")
    con.execute("UPDATE tickets SET estado='anulado' WHERE id=2")
    con.commit()
    e2 = con.execute("SELECT estado FROM tickets WHERE id=2").fetchone()[0]
    assert e2 == 'anulado', f'Confirmada su devolución, el segundo boleto debía anularse; está «{e2}».'
    cobrado = con.execute("SELECT importe FROM transacciones WHERE id=1").fetchone()[0]
    devuelto = con.execute("SELECT COALESCE(SUM(importe),0) FROM reembolsos "
                           "WHERE transaccion_id=1 AND estado='confirmado'").fetchone()[0]
    saldo = float(cobrado) - float(devuelto)
    assert saldo == 0.00, f'El saldo final del cargo debía ser S/ 0.00; es S/ {saldo:.2f}.'
    return (r + f' Cada confirmación anuló únicamente su boleto; devueltos S/ {devuelto:.2f} '
            f'de los S/ {cobrado:.2f} cobrados, el saldo final del cargo es S/ {saldo:.2f}.')


@prueba('BD-30', 'Al actualizar un reembolso rigen el saldo reembolsable del cargo y el precio del boleto',
        'RF28 · RN-20')
def t30(con):
    con.execute("INSERT INTO reservas (id,zona_id,usuario_id,cantidad,creada,expira,estado) "
                "VALUES (1,1,3,2,'2026-11-21 09:00','2026-11-21 09:10','pagada')")
    con.execute("INSERT INTO transacciones (id,reserva_id,operacion_externa,importe,"
                "medio_pago,estado,fecha) VALUES (1,1,'OP-0041',240.00,'tarjeta',"
                "'aprobada','2026-11-21 09:05')")
    con.execute("INSERT INTO tickets (id,transaccion_id,zona_id,codigo_qr) "
                "VALUES (1,1,1,'QR-S01')")
    con.execute("INSERT INTO tickets (id,transaccion_id,zona_id,codigo_qr) "
                "VALUES (2,1,1,'QR-S02')")
    con.execute("INSERT INTO reembolsos (id,ticket_id,transaccion_id,causa,estado,clave_idem,importe,fecha) "
                "VALUES (1,1,1,'cancelacion','enviado','IDEM-30A',100.00,?)", (HOY,))
    con.commit()
    # El cargo de S/ 240 conserva saldo, pero el boleto devuelto cuesta S/ 120.
    r1 = debe_fallar(con, "UPDATE reembolsos SET importe=150.00 WHERE id=1",
                     motivo='S/ 150 supera en S/ 30 el precio del boleto, aunque el cargo tenga saldo.',
                     espera='excede el precio del boleto')
    imp, causa, est = con.execute("SELECT importe, causa, estado FROM reembolsos WHERE id=1").fetchone()
    assert float(imp) == 100.00, f'La devolución debía conservar S/ 100.00; quedó en S/ {imp}.'
    # Cambiar la causa a cobro duplicado deja fuera el limite del boleto, pero no el del cargo.
    r2 = debe_fallar(con,
        "UPDATE reembolsos SET causa='cobro_duplicado', importe=250.00 WHERE id=1",
        motivo='S/ 250 supera el importe cobrado en el cargo.',
        espera='excede el saldo reembolsable del cargo')
    imp2, causa2 = con.execute("SELECT importe, causa FROM reembolsos WHERE id=1").fetchone()
    assert float(imp2) == 100.00 and causa2 == 'cancelacion', \
        f'El registro debía permanecer intacto; quedó «{causa2}» por S/ {imp2}.'
    return (f'Dado un cargo de S/ 240.00 que cubre dos boletos de S/ 120.00 y una devolución en trámite de '
            f'S/ 100.00 sobre el primero, elevarla a S/ 150.00 se rechazó por el precio del boleto '
            f'(«{r1.split(": ",1)[-1]}») y elevarla a S/ 250.00 cambiando la causa se rechazó por el saldo del '
            f'cargo («{r2.split(": ",1)[-1]}»). La devolución conserva S/ {imp2:.2f} y su causa «{causa2}».')


@prueba('BD-31', 'No se anula un boleto con la devolución de otro cargo de la misma compra',
        'RF28 · RN-22')
def t31(con):
    con.execute("INSERT INTO reservas (id,zona_id,usuario_id,cantidad,creada,expira,estado) "
                "VALUES (1,1,3,1,'2026-11-21 08:00','2026-11-21 08:10','pagada')")
    con.execute("INSERT INTO transacciones (id,reserva_id,operacion_externa,importe,"
                "medio_pago,estado,fecha) VALUES (1,1,'OP-0042',120.00,'tarjeta',"
                "'aprobada','2026-11-21 08:05')")
    con.execute("INSERT INTO transacciones (id,reserva_id,operacion_externa,importe,"
                "medio_pago,estado,fecha) VALUES (2,1,'OP-0043',120.00,'tarjeta',"
                "'aprobada','2026-11-21 08:06')")
    con.execute("INSERT INTO tickets (id,transaccion_id,zona_id,codigo_qr) "
                "VALUES (1,1,1,'QR-CRG')")
    con.execute("INSERT INTO reembolsos (id,ticket_id,transaccion_id,causa,estado,clave_idem,importe,fecha) "
                "VALUES (1,1,2,'cancelacion','confirmado','IDEM-31A',120.00,?)", (HOY,))
    con.commit()
    r = debe_fallar(con, "UPDATE tickets SET estado='anulado' WHERE id=1",
                    motivo='El cargo devuelto es OP-0043, y el boleto se sustenta en OP-0042.',
                    espera='no es el que sustenta el boleto')
    est, qr = con.execute("SELECT estado, codigo_qr FROM tickets WHERE id=1").fetchone()
    assert est == 'emitido' and qr == 'QR-CRG', \
        f'El boleto debía conservar su vigencia y su código; está «{est}» con código {qr}.'
    con.execute("INSERT INTO reembolsos (id,ticket_id,transaccion_id,causa,estado,clave_idem,importe,fecha) "
                "VALUES (2,1,1,'cancelacion','confirmado','IDEM-31B',120.00,?)", (HOY,))
    con.execute("UPDATE tickets SET estado='anulado' WHERE id=1")
    con.commit()
    est = con.execute("SELECT estado FROM tickets WHERE id=1").fetchone()[0]
    assert est == 'anulado', \
        f'Devuelto el cargo que sustenta el boleto, la anulación debía proceder; está «{est}».'
    return (r + f' Confirmada la devolución de OP-0042, que es el cargo que sustenta el boleto, '
            f'la anulación procedió y el boleto quedó «{est}».')


@prueba('BD-32', 'La confirmación repetida de un reembolso es idempotente y el reembolso confirmado no admite reproceso',
        'RF28 · RN-20, RN-22')
def t32(con):
    con.execute("INSERT INTO reservas (id,zona_id,usuario_id,cantidad,creada,expira,estado) "
                "VALUES (1,1,3,1,'2026-11-21 07:00','2026-11-21 07:10','pagada')")
    con.execute("INSERT INTO transacciones (id,reserva_id,operacion_externa,importe,"
                "medio_pago,estado,fecha) VALUES (1,1,'OP-0044',120.00,'tarjeta',"
                "'aprobada','2026-11-21 07:05')")
    con.execute("INSERT INTO tickets (id,transaccion_id,zona_id,codigo_qr) "
                "VALUES (1,1,1,'QR-TRM')")
    con.execute("INSERT INTO reembolsos (id,ticket_id,transaccion_id,causa,estado,clave_idem,importe,fecha) "
                "VALUES (1,1,1,'cancelacion','confirmado','IDEM-32',120.00,?)", (HOY,))
    con.commit()
    # Reintento del aviso de confirmacion: se acepta y no mueve nada.
    debe_pasar(con, "UPDATE reembolsos SET estado='confirmado' WHERE id=1")
    n = con.execute("SELECT COUNT(*) FROM reembolsos WHERE transaccion_id=1 "
                    "AND estado='confirmado'").fetchone()[0]
    devuelto = con.execute("SELECT COALESCE(SUM(importe),0) FROM reembolsos "
                           "WHERE transaccion_id=1 AND estado='confirmado'").fetchone()[0]
    assert n == 1 and float(devuelto) == 120.00, \
        f'La confirmación repetida no debía duplicar el movimiento; hay {n} registros por S/ {devuelto}.'
    r1 = debe_fallar(con, "UPDATE reembolsos SET importe=60.00 WHERE id=1",
                     motivo='Reproceso del importe de un reembolso ya confirmado.',
                     espera='no admite reproceso')
    r2 = debe_fallar(con, "UPDATE reembolsos SET estado='enviado' WHERE id=1",
                     motivo='Retroceso de estado de un reembolso ya confirmado.',
                     espera='no admite reproceso')
    est, imp = con.execute("SELECT estado, importe FROM reembolsos WHERE id=1").fetchone()
    assert est == 'confirmado' and float(imp) == 120.00, \
        f'El registro debía permanecer intacto; está «{est}» por S/ {imp}.'
    return (f'La confirmación repetida fue aceptada sin duplicar el movimiento: {n} registro '
            f'confirmado por S/ {devuelto:.2f}. El reproceso se rechazó dos veces: '
            f'«{r1.split(": ",1)[-1]}» y «{r2.split(": ",1)[-1]}». El reembolso permanece '
            f'«{est}» por S/ {imp:.2f}.')

@prueba('BD-33', 'En la misma compra, la actualización admisible y la devolución del otro boleto agotan el cargo sin duplicar movimientos',
        'RF28 · RN-20, RN-22')
def t33(con):
    con.execute("INSERT INTO reservas (id,zona_id,usuario_id,cantidad,creada,expira,estado) "
                "VALUES (1,1,3,2,'2026-11-21 09:00','2026-11-21 09:10','pagada')")
    con.execute("INSERT INTO transacciones (id,reserva_id,operacion_externa,importe,"
                "medio_pago,estado,fecha) VALUES (1,1,'OP-0045',240.00,'tarjeta',"
                "'aprobada','2026-11-21 09:05')")
    con.execute("INSERT INTO tickets (id,transaccion_id,zona_id,codigo_qr) "
                "VALUES (1,1,1,'QR-T01')")
    con.execute("INSERT INTO tickets (id,transaccion_id,zona_id,codigo_qr) "
                "VALUES (2,1,1,'QR-T02')")
    con.execute("INSERT INTO reembolsos (id,ticket_id,transaccion_id,causa,estado,clave_idem,importe,fecha) "
                "VALUES (1,1,1,'cancelacion','enviado','IDEM-33A',100.00,?)", (HOY,))
    con.commit()
    debe_pasar(con, "UPDATE reembolsos SET importe=120.00 WHERE id=1")
    debe_pasar(con,
        "INSERT INTO reembolsos (id,ticket_id,transaccion_id,causa,estado,clave_idem,importe,fecha) "
        "VALUES (2,2,1,'cancelacion','enviado','IDEM-33B',120.00,?)", (HOY,))
    con.execute("UPDATE reembolsos SET estado='confirmado' WHERE id IN (1,2)")
    con.execute("UPDATE tickets SET estado='anulado' WHERE id=1")
    con.execute("UPDATE tickets SET estado='anulado' WHERE id=2")
    con.commit()
    cobrado = con.execute("SELECT importe FROM transacciones WHERE id=1").fetchone()[0]
    devuelto = con.execute("SELECT COALESCE(SUM(importe),0) FROM reembolsos "
                           "WHERE transaccion_id=1 AND estado='confirmado'").fetchone()[0]
    saldo = float(cobrado) - float(devuelto)
    assert float(devuelto) == 240.00 and saldo == 0.00, \
        f'El total confirmado debía ser S/ 240.00 y el saldo S/ 0.00; son S/ {devuelto} y S/ {saldo:.2f}.'
    antes = con.execute("SELECT COUNT(*), COALESCE(SUM(importe),0) FROM reembolsos "
                        "WHERE transaccion_id=1 AND estado='confirmado'").fetchone()
    estados_antes = con.execute("SELECT id, estado FROM tickets ORDER BY id").fetchall()
    debe_pasar(con, "UPDATE reembolsos SET estado='confirmado' WHERE id=1")
    despues = con.execute("SELECT COUNT(*), COALESCE(SUM(importe),0) FROM reembolsos "
                          "WHERE transaccion_id=1 AND estado='confirmado'").fetchone()
    estados_despues = con.execute("SELECT id, estado FROM tickets ORDER BY id").fetchall()
    assert antes == despues, f'La confirmación repetida alteró los movimientos: {antes} → {despues}.'
    assert estados_antes == estados_despues, \
        f'La confirmación repetida alteró el estado de los boletos: {estados_antes} → {estados_despues}.'
    r1 = debe_fallar(con,
        "INSERT INTO reembolsos (ticket_id,transaccion_id,causa,estado,clave_idem,importe,fecha) "
        "VALUES (1,1,'cobro_duplicado','solicitado','IDEM-33C',1.00,?)", (HOY,),
        motivo='El cargo ya fue devuelto en su totalidad.',
        espera='excede el saldo reembolsable del cargo')
    return (f'La actualización admisible de S/ 100.00 a S/ 120.00 y la devolución del segundo boleto fueron '
            f'aceptadas: {despues[0]} movimientos confirmados por S/ {despues[1]:.2f}, saldo del cargo '
            f'S/ {saldo:.2f} y ambos boletos anulados. La confirmación repetida no alteró los movimientos ni '
            f'los estados, y una devolución adicional se rechazó: «{r1.split(": ",1)[-1]}».')


def main():
    total = len(RESULTADOS)
    paso = sum(1 for r in RESULTADOS if r['resultado'] == 'PASO')
    fallo = sum(1 for r in RESULTADOS if r['resultado'] == 'FALLO')
    error = sum(1 for r in RESULTADOS if r['resultado'] == 'ERROR')
    print('=' * 78)
    print('VAOPE · Pruebas de reglas de negocio sobre esquema SQLite sintético')
    print('Línea base académica v2.4 · datos ficticios · no es la BD de VAOPE')
    print('=' * 78)
    for r in RESULTADOS:
        print(f"{r['prueba']}  {r['resultado']:6s}  {r['invariante']}")
        print(f"          {r['refs']}")
        print(f"          {r['detalle']}")
    print('-' * 78)
    print(f'TOTAL {total} · PASÓ {paso} · FALLÓ {fallo} · ERROR {error}')
    salida = {'motor': 'sqlite3 ' + sqlite3.sqlite_version,
              'python': sys.version.split()[0],
              'fecha_ejecucion': EJECUTADO,
              'alcance': 'Esquema sintético académico con datos ficticios. '
                         'No corresponde a la base de datos de VAOPE.',
              'total': total, 'paso': paso, 'fallo': fallo, 'error': error,
              'resultados': RESULTADOS}
    if '--json' in sys.argv:
        destino = sys.argv[sys.argv.index('--json') + 1]
        json.dump(salida, open(destino, 'w', encoding='utf-8'),
                  ensure_ascii=False, indent=1)
        print(f'Salida JSON escrita en {destino}')
    return 0 if (fallo == 0 and error == 0) else 1


if __name__ == '__main__':
    sys.exit(main())
