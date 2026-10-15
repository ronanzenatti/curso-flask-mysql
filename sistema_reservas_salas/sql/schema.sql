-- sql/schema.sql
CREATE DATABASE IF NOT EXISTS gestao_reservas_salas
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE gestao_reservas_salas;

-- 1. Tabela de Usuários
CREATE TABLE IF NOT EXISTS usuarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(120) NOT NULL,
    email VARCHAR(150) NOT NULL UNIQUE,
    senha_hash VARCHAR(255) NOT NULL,
    setor VARCHAR(80) NOT NULL DEFAULT 'Geral',
    cargo_etiqueta VARCHAR(60) NOT NULL DEFAULT 'Solicitante',
    ativo TINYINT(1) NOT NULL DEFAULT 1,
    criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- 2. Catálogo de Permissões do Sistema
CREATE TABLE IF NOT EXISTS permissoes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    codigo VARCHAR(60) NOT NULL UNIQUE,
    nome VARCHAR(100) NOT NULL,
    modulo VARCHAR(50) NOT NULL,
    descricao VARCHAR(255) NOT NULL,
    INDEX idx_permissoes_modulo (modulo, codigo)
) ENGINE=InnoDB;

-- 3. Tabela Associativa de Permissões Personalizadas por Usuário
CREATE TABLE IF NOT EXISTS usuario_permissoes (
    usuario_id INT NOT NULL,
    permissao_id INT NOT NULL,
    concedido_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (usuario_id, permissao_id),
    CONSTRAINT fk_up_usuario
        FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_up_permissao
        FOREIGN KEY (permissao_id) REFERENCES permissoes(id)
        ON DELETE CASCADE
) ENGINE=InnoDB;

-- 4. Tabela de Salas Disponíveis para Reserva
CREATE TABLE IF NOT EXISTS salas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    codigo VARCHAR(25) NOT NULL UNIQUE,
    nome VARCHAR(120) NOT NULL,
    bloco VARCHAR(60) NOT NULL,
    capacidade INT NOT NULL DEFAULT 10,
    recursos VARCHAR(255) NOT NULL DEFAULT '',
    ativa TINYINT(1) NOT NULL DEFAULT 1,
    criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ck_salas_capacidade CHECK (capacidade >= 1)
) ENGINE=InnoDB;

-- 5. Tabela de Reservas de Salas
CREATE TABLE IF NOT EXISTS reservas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    sala_id INT NOT NULL,
    usuario_id INT NOT NULL,
    aprovador_id INT NULL,
    titulo VARCHAR(150) NOT NULL,
    finalidade VARCHAR(255) NOT NULL,
    data_reserva DATE NOT NULL,
    hora_inicio TIME NOT NULL,
    hora_fim TIME NOT NULL,
    participantes_estimados INT NOT NULL DEFAULT 1,
    status ENUM('pendente', 'aprovada', 'rejeitada', 'cancelada') NOT NULL DEFAULT 'pendente',
    observacoes TEXT NULL,
    criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_reserva_sala
        FOREIGN KEY (sala_id) REFERENCES salas(id)
        ON DELETE RESTRICT,
    CONSTRAINT fk_reserva_usuario
        FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
        ON DELETE RESTRICT,
    CONSTRAINT fk_reserva_aprovador
        FOREIGN KEY (aprovador_id) REFERENCES usuarios(id)
        ON DELETE SET NULL,
    CONSTRAINT ck_reserva_horario CHECK (hora_fim > hora_inicio),
    CONSTRAINT ck_reserva_participantes CHECK (participantes_estimados >= 1),
    INDEX idx_reservas_conflito (sala_id, data_reserva, status, hora_inicio, hora_fim),
    INDEX idx_reservas_listagem (data_reserva, status, titulo)
) ENGINE=InnoDB;
