
CREATE TABLE IF NOT EXISTS users (
    id_user BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    matricule VARCHAR(50) NOT NULL UNIQUE,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'INVENTORIST',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    last_login_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMPTZ,

    CONSTRAINT users_role_check CHECK (role IN ('INVENTORIST', 'BACKOFFICE'))
);


CREATE TABLE IF NOT EXISTS agency (
    code_agency VARCHAR(20) PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    agency_type VARCHAR(30) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT agency_type_check
        CHECK (
            agency_type IN (
                'AGENCY',
                'SERVICE',
                'DIRECTION',
                'DEPARTMENT'
            )
        ),

    CONSTRAINT agency_parent_fk FOREIGN KEY (parent_code_agency) REFERENCES agency(code_agency) ON DELETE RESTRICT
);



CREATE TABLE IF NOT EXISTS immobilization_family (
    id_family BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    title VARCHAR(150) NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);


CREATE TABLE IF NOT EXISTS immobilization_subfamily (
    id_subfamily BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_family BIGINT NOT NULL,
    title VARCHAR(150) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_subfamily_family FOREIGN KEY (id_family) REFERENCES immobilization_family(id_family) ON DELETE RESTRICT,
    CONSTRAINT uq_subfamily_family_title UNIQUE (id_family, title)
);


CREATE TABLE IF NOT EXISTS localization (
    id_localization BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    type_code VARCHAR(30),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);


CREATE TABLE IF NOT EXISTS suppliers (
    id_supplier BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    address TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);


CREATE TABLE IF NOT EXISTS campaign (
    campaign_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'DRAFT',
    created_by BIGINT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT campaign_date_check CHECK (end_date >= start_date),
    CONSTRAINT campaign_status_check
        CHECK (
            status IN (
                'DRAFT',
                'IN_PROGRESS',
                'EXTENDED',
                'CANCELLED',
                'COMPLETED'
            )
        ),
    CONSTRAINT campaign_created_by_fk FOREIGN KEY (created_by) REFERENCES users(id_user) ON DELETE SET NULL
);



-- CAMPAIGN <-> AGENCY
-- Relation N-N

CREATE TABLE IF NOT EXISTS campaign_agency (
    campaign_id BIGINT NOT NULL,
    code_agency VARCHAR(20) NOT NULL,

    PRIMARY KEY (campaign_id, code_agency),
    CONSTRAINT fk_campaign_agency_campaign FOREIGN KEY (campaign_id) REFERENCES campaign(campaign_id) ON DELETE CASCADE,
    CONSTRAINT fk_campaign_agency_agency FOREIGN KEY (code_agency) REFERENCES agency(code_agency) ON DELETE RESTRICT
);


-- CAMPAIGN <-> USER
-- Relation N-N

CREATE TABLE IF NOT EXISTS campaign_user (
    campaign_id BIGINT NOT NULL,
    id_user BIGINT NOT NULL,

    PRIMARY KEY (campaign_id, id_user),
    CONSTRAINT fk_campaign_user_campaign FOREIGN KEY (campaign_id) REFERENCES campaign(campaign_id) ON DELETE CASCADE,
    CONSTRAINT fk_campaign_user_user FOREIGN KEY (id_user) REFERENCES users(id_user) ON DELETE RESTRICT
);



-- CAMPAIGN ASSIGNMENT
-- Permet de dire : Jean travaille sur la campagne 2026 ET Jean travaille sur l'agence ABJ001 dans cette campagne.
CREATE TABLE IF NOT EXISTS campaign_assignment (
    campaign_id BIGINT NOT NULL,
    id_user BIGINT NOT NULL,
    code_agency VARCHAR(20) NOT NULL,

    PRIMARY KEY (campaign_id, id_user, code_agency ),
    CONSTRAINT fk_assignment_campaign_user FOREIGN KEY (campaign_id, id_user) REFERENCES campaign_user(campaign_id, id_user) ON DELETE CASCADE,
    CONSTRAINT fk_assignment_campaign_agency FOREIGN KEY (campaign_id, code_agency) REFERENCES campaign_agency(campaign_id, code_agency) ON DELETE CASCADE
);


CREATE TABLE IF NOT EXISTS immobilization (
    id_immobilization BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    immobilization_account VARCHAR(50),
    amortization_account VARCHAR(50),
    dotation_account VARCHAR(50),
    order_number VARCHAR(50),
    order_date DATE,
    delivery_note_number VARCHAR(50),
    delivery_note_date DATE,
    invoice_number VARCHAR(50),
    invoice_date DATE,
    acquittement_date DATE,
    acquittement_value NUMERIC(15,2),
    remaining_value NUMERIC(15,2), -- Valeur restante
    rate NUMERIC(5,2), -- Taux d'amortissement en pourcentage.
    immobilization_duration INTEGER, -- Durée d'immobilisation en mois    
    cumul_amort NUMERIC(15,2), -- Cumul amortissement

    id_subfamily BIGINT NOT NULL,
    id_localization BIGINT,
    id_supplier BIGINT,
    code_agency VARCHAR(20) NOT NULL,

    image_object_key TEXT,
    image_file_name VARCHAR(255),
    image_content_type VARCHAR(100),
    image_file_size BIGINT,
    image_etag VARCHAR(255),

    created_by BIGINT,
    updated_by BIGINT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMPTZ,

    CONSTRAINT fk_immobilization_subfamily FOREIGN KEY (id_subfamily) REFERENCES immobilization_subfamily(id_subfamily) ON DELETE RESTRICT,
    CONSTRAINT fk_immobilization_localization FOREIGN KEY (id_localization) REFERENCES localization(id_localization) ON DELETE SET NULL,
    CONSTRAINT fk_immobilization_supplier FOREIGN KEY (id_supplier) REFERENCES suppliers(id_supplier) ON DELETE SET NULL,
    CONSTRAINT fk_immobilization_agency FOREIGN KEY (code_agency) REFERENCES agency(code_agency) ON DELETE RESTRICT,
    CONSTRAINT fk_immobilization_created_by FOREIGN KEY (created_by) REFERENCES users(id_user) ON DELETE SET NULL,
    CONSTRAINT fk_immobilization_updated_by FOREIGN KEY (updated_by) REFERENCES users(id_user) ON DELETE SET NULL,
    CONSTRAINT check_rate CHECK ( rate IS NULL OR ( rate >= 0 AND rate <= 100 ) )

);


--QR CODE
-- Une immobilisation peut avoir plusieurs QR codes dans
-- son historique, mais un seul QR code ACTIVE.

CREATE TABLE IF NOT EXISTS qr_code (
    id_qr_code BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_immobilization BIGINT NOT NULL,
    public_token VARCHAR(100) NOT NULL UNIQUE, -- Token aléatoire et non séquentiel généré par l'application
    version INTEGER NOT NULL DEFAULT 1,
    status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    revoked_at TIMESTAMPTZ,
    created_by BIGINT,

    CONSTRAINT fk_qr_immobilization FOREIGN KEY (id_immobilization) REFERENCES immobilization(id_immobilization) ON DELETE RESTRICT,
    CONSTRAINT fk_qr_created_by FOREIGN KEY (created_by) REFERENCES users(id_user) ON DELETE SET NULL,
    CONSTRAINT qr_status_check CHECK ( status IN ( 'ACTIVE', 'REVOKED' ) )

);


-- Un seul QR actif par immobilisation.
CREATE UNIQUE INDEX IF NOT EXISTS uq_active_qr_immobilization
ON qr_code(id_immobilization)
WHERE status = 'ACTIVE';


-- Représente l'état d'une immobilisation dans une campagne.
-- Exemple : Campagne 2026 + Immobilisation 123 = FOUND
-- Cette table contient l'état courant.

CREATE TABLE IF NOT EXISTS inventory (
    id_inventory BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    campaign_id BIGINT NOT NULL,
    id_immobilization BIGINT NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'NOT_INVENTORIED',
    last_scan_at TIMESTAMPTZ,
    last_scanned_by BIGINT,
    comment TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_inventory_campaign FOREIGN KEY (campaign_id) REFERENCES campaign(campaign_id) ON DELETE RESTRICT,
    CONSTRAINT fk_inventory_immobilization FOREIGN KEY (id_immobilization) REFERENCES immobilization(id_immobilization) ON DELETE RESTRICT,
    CONSTRAINT fk_inventory_last_user FOREIGN KEY (last_scanned_by) REFERENCES users(id_user) ON DELETE SET NULL,
    CONSTRAINT inventory_status_check
        CHECK (
            status IN (
                'NOT_INVENTORIED',
                'FOUND',
                'NOT_FOUND',
                'MOVED',
                'DAMAGED',
                'UNKNOWN'
            )
        ),

    CONSTRAINT uq_campaign_immobilization UNIQUE ( campaign_id, id_immobilization )
);


-- ============================================================
-- Historique de tous les scans.
-- Une immobilisation peut donc être scannée plusieurs fois dans une même campagne.
-- ============================================================

CREATE TABLE IF NOT EXISTS inventory_scan (
    id_scan BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    id_inventory BIGINT NOT NULL,
    id_user BIGINT NOT NULL,
    scanned_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(30) NOT NULL,
    id_localization BIGINT,
    comment TEXT,
    latitude NUMERIC(10,7),
    longitude NUMERIC(10,7),
    device_id VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_scan_inventory FOREIGN KEY (id_inventory) REFERENCES inventory(id_inventory) ON DELETE RESTRICT,
    CONSTRAINT fk_scan_user FOREIGN KEY (id_user) REFERENCES users(id_user) ON DELETE RESTRICT,
    CONSTRAINT fk_scan_localization FOREIGN KEY (id_localization) REFERENCES localization(id_localization) ON DELETE SET NULL,
    CONSTRAINT scan_status_check
        CHECK (
            status IN (
                'FOUND',
                'NOT_FOUND',
                'MOVED',
                'DAMAGED',
                'UNKNOWN'
            )
        ),

);


