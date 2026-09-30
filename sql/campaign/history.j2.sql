WITH loc AS (
        SELECT id_localization
        FROM campaign_assignment c
        WHERE
            c.campaign_id = $1
            {% if matricule is not none %}AND matricule=$2{% endif %}
        GROUP BY id_localization
    ),
    inv_dupl AS (
        SELECT
            id_immobilization,
            last_scanned_by,
            status,
            ROW_NUMBER() OVER (PARTITION BY id_immobilization ORDER BY updated_at DESC) AS rn
        FROM inventory
        WHERE campaign_id = $1
    ),
    inv AS (
        SELECT
            id_immobilization,
            last_scanned_by,
            status
        FROM inv_dupl
        WHERE rn = 1
    )
SELECT
    loc.id_localization,
    code_agency,
    imm.title,
    users.last_name || ' ' || users.first_name AS inventorist,
    inv.status,
    imm.id_immobilization
FROM immobilization imm
    INNER JOIN inv
            ON inv.id_immobilization = imm.id_immobilization
    {% if matricule is not none %}LEFT{% else %} INNER {% endif %} JOIN loc
            ON loc.id_localization = imm.id_localization
    INNER JOIN localization
            ON localization.id_localization = imm.id_localization
    INNER JOIN users
            ON users.matricule=inv.last_scanned_by
WHERE
    imm.status IN ('GOOD', 'DAMAGED')
    {% if matricule is not none %}
    AND (
        loc.id_localization IS NOT NULL
        OR inv.last_scanned_by=$2
    )
    {% endif %}