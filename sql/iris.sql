
CREATE TABLE users(
    login VARCHAR(10) NOT NULL PRIMARY KEY,

    last_name VARCHAR(255),
    first_name VARCHAR(255),

    password_hash TEXT NOT NULL,

    last_login_at TIMESTAMPTZ,

    last_password_modification_date TIMESTAMPTZ DEFAULT NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMPTZ

);

CREATE TABLE role(
    id_role BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    title VARCHAR(20) NOT NULL UNIQUE
);

CREATE TABLE user_role(
    login VARCHAR(10) NOT NULL,
    id_role BIGINT NOT NULL,

    CONSTRAINT fk_user_role_id_role FOREIGN KEY (id_role) REFERENCES role(id_role) ON DELETE CASCADE,
    CONSTRAINT fk_user_role_login FOREIGN KEY (login) REFERENCES users(login) ON DELETE CASCADE
);


CREATE TABLE clients(
    internal_client_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    is_bank_client BOOLEAN NOT NULL DEFAULT TRUE,

    bank_client_id INTEGER UNIQUE,

    client_name VARCHAR(255) NOT NULL,
    birthdate DATE,
    phone_number VARCHAR(255) UNIQUE,

    email VARCHAR(255) UNIQUE,

    birth_place  VARCHAR(255),

    CONSTRAINT clients_integrity_check CHECK (
        bank_client_id IS NOT NULL or is_bank_client=FALSE
    ),

    CONSTRAINT clients_integrity_minimal_client_info CHECK (
        phone_number IS NOT NULL or email IS NOT NULL
    ) 

);


CREATE TABLE products(
    product_code VARCHAR(10) PRIMARY KEY,
    title VARCHAR(255)
);


CREATE TABLE clients_product(
    bank_client_id INTEGER NOT NULL,
    product_code VARCHAR(10),
    CONSTRAINT fk_account_client FOREIGN KEY (bank_client_id) REFERENCES clients(bank_client_id) ON DELETE CASCADE,
    CONSTRAINT fk_client_product FOREIGN KEY (product_code) REFERENCES products(product_code) ON DELETE CASCADE

);


CREATE TABLE account_number(
    bank_client_id INTEGER NOT NULL,
    account_number VARCHAR(255),
    CONSTRAINT fk_account_client FOREIGN KEY (bank_client_id) REFERENCES clients(bank_client_id) ON DELETE CASCADE
);


CREATE TABLE codification_reason(
    reason_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    content TEXT,
    deleted_at TIMESTAMPTZ

);


CREATE TABLE codification_sub_reason(
    sub_reason_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    reason_id BIGINT,
    title TEXT,
    deleted_at TIMESTAMPTZ,
    CONSTRAINT fk_codification_reason FOREIGN KEY (reason_id) REFERENCES codification_reason(reason_id) ON DELETE CASCADE
);


CREATE TABLE campaign(
    campaign_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    title VARCHAR(255),

    campaign_type VARCHAR(20),
    CONSTRAINT campaign_type_check CHECK (
        campaign_type IN ('INTERNAL', 'EXTERNAL')
    ),

    campaign_object VARCHAR(20),
    CONSTRAINT campaign_object_check CHECK (
        campaign_type IN ('INFORMATION', 'TELESALE')
    ),

    objective TEXT,
    client_target TEXT,

    start_date date,
    end_date date

);


CREATE TABLE campaign_product(
    campaign_id BIGINT,
    product_code VARCHAR(10),

    CONSTRAINT fk_campaign_product_code FOREIGN KEY (product_code) REFERENCES products(product_code) ON DELETE CASCADE,
    CONSTRAINT fk_campaign_id_product FOREIGN KEY (campaign_id) REFERENCES campaign(campaign_id) ON DELETE CASCADE

);

CREATE TABLE campaign_users(
    campaign_id BIGINT,
    user_login VARCHAR(10),

    CONSTRAINT fk_campaign_users_login FOREIGN KEY (user_login) REFERENCES users(login) ON DELETE CASCADE,

    CONSTRAINT fk_campaign_id_users FOREIGN KEY (campaign_id) REFERENCES campaign(campaign_id) ON DELETE CASCADE

);


CREATE TABLE campaign_client_concerned(
    campaign_id BIGINT,
    internal_client_id BIGINT,
    user_login VARCHAR(10),

    CONSTRAINT fk_campaign_client FOREIGN KEY (internal_client_id) REFERENCES clients(internal_client_id) ON DELETE CASCADE,
    CONSTRAINT fk_campaign_id_client FOREIGN KEY (campaign_id) REFERENCES campaign(campaign_id) ON DELETE CASCADE,
    CONSTRAINT fk_campaign_client_concerned_users FOREIGN KEY (user_login) REFERENCES users(login) ON DELETE CASCADE

);



CREATE TABLE codification(
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,

    internal_client_id BIGINT,

    resume TEXT,

    canal VARCHAR(255),
    CONSTRAINT canal_check CHECK (
        canal IN (
            'OUTBOUND_EMAIL', 'INCOMMING_EMAIL',
             'OUTBOUND_CALL', 'INCOMMING_CALL'
        )
    ),

    campaign_id BIGINT DEFAULT NULL,

    sub_reason_id BIGINT,

    user_login VARCHAR(10),

    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,


    CONSTRAINT fk_codification_client FOREIGN KEY (internal_client_id) REFERENCES clients(internal_client_id) ON DELETE CASCADE,
    CONSTRAINT fk_codification_reason FOREIGN KEY (sub_reason_id) REFERENCES codification_sub_reason(sub_reason_id) ON DELETE CASCADE,
    CONSTRAINT fk_codification_users FOREIGN KEY (user_login) REFERENCES users(login) ON DELETE CASCADE,

    CONSTRAINT fk_campaign_id FOREIGN KEY (campaign_id) REFERENCES campaign(campaign_id) ON DELETE CASCADE

);


CREATE TABLE product_proposition(
    codification_id BIGINT,

    is_sales_rebound BOOLEAN NOT NULL DEFAULT FALSE,

    product_code VARCHAR(10),  -- need table product
    amount NUMERIC(15,2) DEFAULT NULL,

    status VARCHAR(20) NOT NULL DEFAULT 'PRE_SALES',
    CONSTRAINT status_check CHECK (
        status IN (
            'PRE_SALES', 'CANCEL',
             'DONE', 'NOT_INTERESTED'
        )
    ),

    CONSTRAINT fk_pp_codification FOREIGN KEY (codification_id) REFERENCES codification(id) ON DELETE CASCADE,
    CONSTRAINT fk_client_product FOREIGN KEY (product_code) REFERENCES products(product_code) ON DELETE CASCADE

);




