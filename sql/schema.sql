CREATE TABLE IF NOT EXISTS users (
    matricule VARCHAR(10) PRIMARY KEY,

    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    email VARCHAR(255) NOT NULL,

    password_hash TEXT NOT NULL,

    role VARCHAR(20) NOT NULL DEFAULT 'INVENTORIST',

    is_active BOOLEAN NOT NULL DEFAULT TRUE,

    last_login_at TIMESTAMPTZ,

    last_password_modification_date TIMESTAMPTZ DEFAULT NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMPTZ, -- soft delete

    CONSTRAINT users_role_check CHECK (role IN ('INVENTORIST', 'BACKOFFICE'))
);


CREATE TABLE IF NOT EXISTS agency (
    code_agency VARCHAR(5) PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    -- uc
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);



CREATE TABLE IF NOT EXISTS immobilization_family (
    id_family VARCHAR(5) PRIMARY KEY,
    title VARCHAR(150) NOT NULL UNIQUE,

    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);


CREATE TABLE IF NOT EXISTS immobilization_subfamily (
    id_subfamily VARCHAR(10) PRIMARY KEY,
    id_family VARCHAR(5) NOT NULL,

    title VARCHAR(150) NOT NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Account
    immo_account VARCHAR(9),
    dotation_account VARCHAR(9),
    depreciation_account VARCHAR(9),

    depreciation_year_rate DECIMAL,

    CONSTRAINT fk_subfamily_family FOREIGN KEY (id_family) REFERENCES immobilization_family(id_family) ON DELETE RESTRICT
);


CREATE TABLE IF NOT EXISTS localization (
    id_localization BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,  --car on ne maitrise pas la generation du location_code
    location_code VARCHAR(30) NOT NULL UNIQUE, -- varchar(10)?

    code_agency VARCHAR(5),

    -- location_type VARCHAR(20), -- Des valeurs a mettre

    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_agency_localization FOREIGN KEY (code_agency) REFERENCES agency(code_agency) ON DELETE SET NULL
);


CREATE TABLE IF NOT EXISTS suppliers (
    id_supplier BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    address TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);



CREATE TABLE IF NOT EXISTS immobilization (
    id_immobilization UUID PRIMARY KEY DEFAULT uuidv7(),

    id_immobilization_amplitude BIGINT UNIQUE DEFAULT NULL, -- de ce que j'ai compris l'id n'est pas interne au projet, il provient d'Amplitude. peut-etre doit etre non null (voir cas d'inventaire pour statuer)

    title VARCHAR(255),

    id_localization BIGINT,
    id_subfamily VARCHAR(10),
    id_supplier BIGINT DEFAULT NULL,

    serial_number VARCHAR(255),

    ubigreen_number VARCHAR(255),

    order_number VARCHAR(50),
    order_date DATE,

    delivery_note_number VARCHAR(50),
    delivery_note_date DATE,

    invoice_number VARCHAR(50),
    invoice_date DATE,

    acquittement_date DATE,
    acquittement_value NUMERIC(15,2),

    comment TEXT,

    status VARCHAR(30) NOT NULL DEFAULT 'GOOD',
    CONSTRAINT immo_status_check
        CHECK (
            status IN (
                'GOOD',
                'NOT_FOUND',
                'OUT_OF_SERVICE'
                'MOVED',
                'DAMAGED',
                'UNKNOWN'
            )
        ),
    CONSTRAINT immo_integrity_check CHECK (
        (title IS NOT NULL AND id_localization IS NOT NULL AND id_subfamily IS NOT NULL)
        OR status = 'UNKNOWN'
    ),

    created_by VARCHAR(10),
    updated_by VARCHAR(10) NOT NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMPTZ, --soft delete?

    CONSTRAINT fk_immobilization_localization FOREIGN KEY (id_localization) REFERENCES localization(id_localization) ON DELETE SET NULL,
    CONSTRAINT fk_immobilization_subfamily FOREIGN KEY (id_subfamily) REFERENCES immobilization_subfamily(id_subfamily) ON DELETE RESTRICT,
    CONSTRAINT fk_immobilization_supplier FOREIGN KEY (id_supplier) REFERENCES suppliers(id_supplier) ON DELETE SET NULL,

    CONSTRAINT fk_immobilization_created_by FOREIGN KEY (created_by) REFERENCES users(matricule) ON DELETE SET NULL,
    CONSTRAINT fk_immobilization_updated_by FOREIGN KEY (updated_by) REFERENCES users(matricule) ON DELETE SET NULL
);


-----------------------------
CREATE TABLE IF NOT EXISTS campaign (
    campaign_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    title VARCHAR(255),

    start_date DATE NOT NULL,
    end_date DATE NOT NULL,

    status VARCHAR(20) NOT NULL DEFAULT 'DRAFT',

    created_by VARCHAR(10),
    updated_by VARCHAR(10),

    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT campaign_date_check CHECK (end_date >= start_date),
    CONSTRAINT campaign_status_check
        CHECK (
            status IN (
                'DRAFT',
                'CANCELLED',
                'COMPLETED'
            )
        ),
    CONSTRAINT campaign_created_by_fk FOREIGN KEY (created_by) REFERENCES users(matricule) ON DELETE SET NULL,
    CONSTRAINT campaign_updated_by_fk FOREIGN KEY (updated_by) REFERENCES users(matricule) ON DELETE SET NULL

);



-- CAMPAIGN <-> AGENCY
-- Relation N-N

CREATE TABLE IF NOT EXISTS campaign_localization (
    campaign_id BIGINT NOT NULL,
    id_localization BIGINT NOT NULL,

    PRIMARY KEY (campaign_id, id_localization),
    CONSTRAINT fk_campaign_localization_campaign FOREIGN KEY (campaign_id) REFERENCES campaign(campaign_id) ON DELETE CASCADE,
    CONSTRAINT fk_campaign_localization_localization FOREIGN KEY (id_localization) REFERENCES localization(id_localization) ON DELETE CASCADE
);


-- CAMPAIGN <-> USER
-- Relation N-N

CREATE TABLE IF NOT EXISTS campaign_user (
    campaign_id BIGINT NOT NULL,
    matricule VARCHAR(10) NOT NULL,

    PRIMARY KEY (campaign_id, matricule),
    CONSTRAINT fk_campaign_user_campaign FOREIGN KEY (campaign_id) REFERENCES campaign(campaign_id) ON DELETE CASCADE,
    CONSTRAINT fk_campaign_user_user FOREIGN KEY (matricule) REFERENCES users(matricule) ON DELETE RESTRICT
);



-- CAMPAIGN ASSIGNMENT
-- Permet de dire : Jean travaille sur la campagne 2026 ET Jean travaille sur l'agence ABJ001 dans cette campagne.
CREATE TABLE IF NOT EXISTS campaign_assignment (
    campaign_id BIGINT NOT NULL,
    matricule VARCHAR(10) NOT NULL,
    id_localization BIGINT NOT NULL,

    PRIMARY KEY (campaign_id, matricule, id_localization),
    CONSTRAINT fk_assignment_campaign_user FOREIGN KEY (campaign_id, matricule) REFERENCES campaign_user(campaign_id, matricule) ON DELETE CASCADE,
    CONSTRAINT fk_assignment_campaign_localization FOREIGN KEY (campaign_id, id_localization) REFERENCES campaign_localization(campaign_id, id_localization) ON DELETE CASCADE
);



--QR CODE
-- le code qr peut-etre obtenu via id_immobilization.


-- Représente l'état d'une immobilisation dans une campagne.
-- Exemple : Campagne 2026 + Immobilisation 123 = FOUND
-- Cette table contient l'état courant.

CREATE TABLE IF NOT EXISTS inventory (
    id_inventory BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    campaign_id BIGINT NOT NULL,
    id_immobilization UUID NOT NULL,

    status VARCHAR(30) NOT NULL DEFAULT 'GOOD',

    last_scan_at TIMESTAMPTZ,
    last_scanned_by VARCHAR(10),

    latitude NUMERIC(10,7),
    longitude NUMERIC(10,7),
    device_id VARCHAR(255),

    comment TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_inventory_campaign FOREIGN KEY (campaign_id) REFERENCES campaign(campaign_id) ON DELETE RESTRICT,
    CONSTRAINT fk_inventory_immobilization FOREIGN KEY (id_immobilization) REFERENCES immobilization(id_immobilization) ON DELETE RESTRICT,
    CONSTRAINT fk_inventory_last_user FOREIGN KEY (last_scanned_by) REFERENCES users(matricule) ON DELETE SET NULL,
    CONSTRAINT inventory_status_check
        CHECK (
            status IN (
                'GOOD',
                'NOT_FOUND',
                'MOVED',
                'DAMAGED',
                'UNKNOWN'
            )
        )
);

CREATE OR REPLACE FUNCTION update_changetimestamp_column()
RETURNS TRIGGER AS $$
BEGIN
   NEW.updated_at = NOW();
   RETURN NEW;
END;
$$ language 'plpgsql';



DO $$
DECLARE
    tables_list TEXT[] := ARRAY['users', 'immobilization_subfamily', 'suppliers', 'immobilization', 'campaign', 'inventory'];
    table_name TEXT;
BEGIN
    FOREACH table_name IN ARRAY tables_list
    LOOP

        EXECUTE format('
        DROP TRIGGER IF EXISTS trg_%I_updated_date ON %I;',
        table_name, table_name);

        EXECUTE format('
            CREATE OR REPLACE TRIGGER trg_%I_updated_date
            BEFORE UPDATE ON %I
            FOR EACH ROW
            EXECUTE FUNCTION update_changetimestamp_column();',
            table_name, table_name);

        -- Optionnel : Affiche un message de confirmation dans la console
        RAISE NOTICE 'Trigger créé avec succès pour la table : %', table_name;
    END LOOP;
END $$;





