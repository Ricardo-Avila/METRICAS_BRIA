-- =========================
-- TABLA USUARIO
-- =========================
CREATE TABLE usuario (
    extension      INTEGER PRIMARY KEY,
    nombre         VARCHAR(50) NOT NULL,
    departamento   VARCHAR(30),
    nota           VARCHAR(50)
);

-- =========================
-- TABLA DID
-- =========================
CREATE TABLE did (
    did     VARCHAR(20) PRIMARY KEY,
    pais    VARCHAR(20) NOT NULL
);

-- =========================
-- TABLA LLAMADA
-- =========================
CREATE TABLE llamada (
    uuid            VARCHAR(36) PRIMARY KEY,
    calldate        TIMESTAMP NOT NULL,
    duration        INTEGER NOT NULL,
    ringing         INTEGER NOT NULL,
    attended        BOOLEAN NOT NULL,
    direction       VARCHAR(8) NOT NULL,
    callerid        VARCHAR(30),
    destination     VARCHAR(30),
    srcuser         INTEGER,
    srcextension    INTEGER,
    dstuser         INTEGER,
    dstextension    INTEGER,
    path            VARCHAR(150),
    linkedid        VARCHAR(21) NOT NULL,
    astcallid       VARCHAR(12) NOT NULL,

    CONSTRAINT fk_src_extension
        FOREIGN KEY (srcextension)
        REFERENCES usuario(extension),

    CONSTRAINT fk_dst_extension
        FOREIGN KEY (dstextension)
        REFERENCES usuario(extension)
);

-- =========================
-- TABLA RUTA_PATH
-- =========================
CREATE TABLE ruta_path (
    id_ruta     INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_llamada  VARCHAR(36) NOT NULL,
    posicion    INTEGER NOT NULL,
    extension   INTEGER NOT NULL,\n\n    CONSTRAINT uq_ruta_llamada_pos\n        UNIQUE (id_llamada, posicion),\n

    CONSTRAINT fk_ruta_llamada
        FOREIGN KEY (id_llamada)
        REFERENCES llamada(uuid)
        ON DELETE CASCADE,

    CONSTRAINT fk_ruta_extension
        FOREIGN KEY (extension)
        REFERENCES usuario(extension)
);

INSERT INTO usuario (extension, nombre, departamento, nota) VALUES
(10, 'Pruebas', 'SoporteIT', 'Pruebas/Clearcom'),
(100, '100', 'SoporteIT', 'Pruebas/Clearcom'),
(101, 'Karina Ruiz', 'Operaciones', NULL),
(102, '102_Para_Asignar', 'SoporteIT', NULL),
(104, 'Rogerio Camargo', 'Direccion', NULL),
(105, 'Diobert Vasquez', 'Operaciones', NULL),
(106, 'Alberto Robles', 'Administracion', NULL),
(107, 'Isabel Blancarte', 'Operaciones', NULL),
(108, 'Yolanda Lopez', 'Desarrollo', NULL),
(109, 'Gerardo Mendez', 'Desarrollo', NULL),
(110, 'Gabriel Rosales', 'Direccion', NULL),
(111, 'Adriana De La Cruz', 'Desarrollo', NULL),
(112, 'Claudia Hernandez', 'Administracion', NULL),
(113, 'Diana Razgado', 'Operaciones', NULL),
(114, 'Melisa Dimas', 'Desarrollo', NULL),
(115, 'Gabriel Hernandez', 'Comercial', NULL),
(116, 'Victor H Penaloza', 'Operaciones', NULL),
(117, 'Daniel Ocegueda', 'Comercial', NULL),
(118, 'Mayra Martinez', 'Administracion', NULL),
(119, 'Dalia Jimenez', 'Desarrollo', NULL),
(120, 'Lluvia Guzman', 'Administracion', NULL),
(121, 'Mireya Hernandez', 'Administracion', NULL),
(122, 'Pamela Mejia', 'Cuentas', NULL),
(123, 'Ricardo Avila', 'SoporteIT', NULL),
(124, 'Monica Cervantes', 'Cuentas', NULL),
(125, 'Javier Guadalupe', 'Operaciones', NULL),
(126, 'Teresa Gaona', 'Comercial', NULL),
(129, 'Adrian Trejo', 'Operaciones', NULL),
(132, 'Andrea Hernandez', 'Operaciones', NULL),
(133, 'Giovanni Reyes', 'Operaciones', NULL),
(134, 'Edwin Calderon', 'Operaciones', NULL),
(135, 'Daniela Duran', 'Administracion', NULL),
(136, 'Alexis Sanchez', 'Operaciones', NULL),
(137, 'Eugenia Ortiz', 'Administracion', NULL),
(138, 'Yoseline Frausto', 'Operaciones', NULL),
(139, 'Israel Montiel', 'Operaciones', NULL),
(140, 'Luis Leal', 'Comercial', NULL),
(141, 'Luis Duran', 'Cuentas', NULL),
(145, 'Fernanda Romero', 'Operaciones', NULL),
(146, 'Nashby Martinez', 'Operaciones', NULL),
(147, 'Minerva Acosta', 'Comercial', NULL),
(148, 'Omar Soto', 'Comercial', NULL),
(152, 'Elizabeth Enriquez', 'Comercial', NULL),
(153, 'Jorge Mendez', 'Comercial', NULL),
(154, 'Mary Tere Saucedo', 'Comercial', NULL),
(155, 'Dulce Ramirez', 'Comercial', NULL),
(156, 'Mariel Hernandez', 'Operaciones', NULL),
(158, 'Alicia Jantes', 'Operaciones', NULL),
(160, 'Fernando Mogollon', 'Cuentas', NULL),
(161, 'Diane Huerta', 'Operacioones', NULL),
(162, 'Daniela Amador', 'Operaciones', NULL),
(163, 'Rodrigo Beristain', 'SoporteIT', NULL),
(164, 'Guadalupe Andrade', 'Operaciones', NULL),
(165, 'Maria Ramirez', 'Operaciones', NULL),
(166, 'Yamile Rodriguez', 'Comercial', NULL),
(167, 'Erika Gaspar', 'Operaciones', NULL),
(168, 'Melina Rios', 'Operaciones', NULL),
(169, 'Ana Lilia Cruz', 'Operaciones', NULL),
(170, 'Fatima Ramos', 'Operaciones', NULL),
(171, 'Angel Mendoza', 'Operaciones', NULL),
(172, '172_Para_Asignar', 'Operaciones', NULL),
(173, 'Dora Marquez', 'Operaciones', NULL),
(176, 'Valeria Villa', 'Comercial', NULL),
(180, 'Armando González', 'Operaciones', NULL),
(181, 'Diego Martínez', 'Operaciones', NULL),
(182, 'Eric Jaimes', 'Operaciones', NULL),
(183, 'Patricia Saldivar', 'Operaciones', NULL),
(184, 'Jose Hernando Martinez', 'Seguridad e ISO', NULL),

(1000, 'Ingles', 'Cola', 'Opcion 1'),
(1001, 'Soporte Proveedores', 'Cola', 'Opcion 2_2'),
(1002, 'Soporte Proveedores', 'Cola', 'Opcion 2_3'),
(1003, 'Soporte Proveedores', 'Cola', 'Opcion 2_1'),
(1005, 'Renovaciones', 'Cola', 'Opcion 3_2'),
(1006, 'Ventas', 'Cola', 'Opcion 4'),
(1007, 'Colombia', 'Cola', NULL),
(1008, 'Colombia DV', 'Cola', NULL),
(1009, 'Administracion', 'Cola', 'Opcion 5'),
(1011, 'Nuevos Registros', 'Cola', 'Opcion 3_1'),
(4000000, 'Soporte Saint Gobain', 'Cola', NULL);

INSERT INTO did (did, pais) VALUES
('50646004630', 'COSTA RICA'),
('576015801601', 'COLOMBIA'),
('50422170807', 'HONDURAS'),
('50222786319', 'GUATEMALA'),
('5078322461', 'PANAMA'),
('593964283801', 'ECUADOR'),
('50575132177', 'NICARAGUA'),
('50321130272', 'EL SALVADOR'),
('525544404475', 'MEXICO');

CREATE INDEX idx_llamada_calldate ON llamada(calldate);
CREATE INDEX idx_llamada_src_ext ON llamada(srcextension);
CREATE INDEX idx_llamada_dst_ext ON llamada(dstextension);
CREATE INDEX idx_ruta_llamada ON ruta_path(id_llamada);
