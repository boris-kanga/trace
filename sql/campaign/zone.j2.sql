WITH loc AS (
        SELECT
            c.id_localization,{% if full %}
            STRING_AGG(matricule, '|') AS attached_user
            {% else %}'' AS attached_user{% endif %}
        FROM
            {% if full %}
            campaign_localization c LEFT JOIN campaign_assignment a ON
                {% if matricule is not none %}
                (c.campaign_id, $2, c.id_localization) = (a.campaign_id, a.matricule, a.id_localization)
                {% else %}
                c.campaign_id = a.campaign_id
                {% endif %}
            {% elif matricule is not none %}
            campaign_assignment c
            {% else %}
            campaign_localization c
            {% endif %}
        WHERE
            c.campaign_id = $1
            {% if matricule is not none and not full %}AND matricule=$2{% endif %}
        GROUP BY c.id_localization
    ),
    inv AS (
        SELECT
            id_immobilization
        FROM inventory
        WHERE campaign_id = $1
        GROUP BY id_immobilization
    )
SELECT
    loc.id_localization,
    l.location_code,
    loc.attached_user,
    l.code_agency,
    a.title as agency_title,
    SUM(CASE WHEN imm.id_localization IS NOT NULL
        THEN 1 ELSE 0 END) AS immobilization_count,
    SUM(CASE WHEN inv.id_immobilization IS NOT NULL
                 THEN 1 ELSE 0 END) AS already_treat_count
FROM immobilization imm
    RIGHT JOIN loc
            ON loc.id_localization = imm.id_localization
    INNER JOIN localization l
            ON l.id_localization = loc.id_localization
    INNER JOIN agency a ON a.code_agency = l.code_agency
    LEFT JOIN inv
            ON inv.id_immobilization = imm.id_immobilization
WHERE
    imm.status IN ('GOOD', 'DAMAGED') OR imm.id_localization IS NULL
GROUP BY
    loc.id_localization,
    loc.attached_user,
    l.location_code,
    l.code_agency,
    a.title