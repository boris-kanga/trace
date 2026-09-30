import uuid
from typing import List

from src.core.logger import get_logger
from src.domain.entities.immobilization import ImmobilizationStatus, Immobilization
from src.domain.entities.localization import Localization
from src.domain.interfaces.campaign_repository_abc import CampaignRepositoryABC
from src.domain.entities.campaign import Campaign, CampaignStatus, Inventory
from src.domain.entities.user import User


logger = get_logger(__name__)

class CampaignRepository(CampaignRepositoryABC):
    def __init__(self, db):
        self.db = db

    async def get(
            self,
            year=None, _id=None, status=None,
            user: User | None = None

    ) -> List[Campaign]:
        added_sql = ""
        join_sql = ""
        added_params = []
        if year:
            added_params.append(year)
            added_sql += "\nAND EXTRACT(YEAR FROM c.created_at)=$"+str(len(added_params))

        if _id:
            added_params.append(_id)
            added_sql += "\nAND campaign_id=$"+str(len(added_params))

        if status:
            added_sql += "\nAND " + {
                "active":"status='DRAFT' AND start_date<=CURRENT_DATE AND end_date>=CURRENT_DATE",
                "completed": "status='COMPLETED'",
                "cancelled": "status='CANCELLED'"
            }[status]
        if isinstance(user, User):
            join_sql="\n INNER JOIN campaign_user cu ON cu.campaign_id=c.campaign_id"
            added_params.append(user.matricule)
            added_sql += "\nAND cu.matricule=$"+str(len(added_params))

        res = await self.db.execute(
           f"""
            SELECT 
                c.*,
                cte_by.matricule AS cte_matricule,
                cte_by.first_name AS cte_first_name,
                cte_by.last_name AS cte_last_name,
                cte_by.email AS cte_email,
                cte_by.password_hash AS cte_password_hash,
                cte_by.role AS cte_role, 
                cte_by.is_active AS cte_is_active,
                cte_by.last_login_at AS cte_last_login_at,
                cte_by.last_password_modification_date AS 
                    cte_last_password_modification_date,
                cte_by.deleted_at AS cte_deleted_at,
                
                upt_by.matricule AS upt_matricule,
                upt_by.first_name AS upt_first_name,
                upt_by.last_name AS upt_last_name,
                upt_by.email AS upt_email,
                upt_by.password_hash AS upt_password_hash,
                upt_by.role AS upt_role, 
                upt_by.is_active AS upt_is_active,
                upt_by.last_login_at AS upt_last_login_at,
                upt_by.last_password_modification_date AS 
                    upt_last_password_modification_date,
                upt_by.deleted_at AS upt_deleted_at
                
            FROM campaign c INNER JOIN users cte_by
                    ON c.created_by = cte_by.matricule
                INNER JOIN users upt_by 
                    ON c.updated_by = upt_by.matricule
                {join_sql}
            WHERE
               1=1
                {added_sql}
            """, added_params
        )

        cpgs = []
        user_keys = (
            "matricule",
            "first_name", "last_name", "email", "password_hash",
            "role", "is_active", "last_login_at", "deleted_at",
            "last_password_modification_date"
        )
        for row in res:
            cpg = Campaign(
                row["title"],
                row["start_date"],
                row["end_date"],
                created_by=User.from_dict({k: row["cte_"+k] for k in user_keys}),
                updated_by=User.from_dict({k: row["upt_"+k] for k in user_keys}),
                status=CampaignStatus(row["status"])
            )

            cpg.campaign_id = row["campaign_id"]
            cpgs.append(cpg)

        return cpgs


    async def delete_campaign(self, campaign: Campaign | int) -> bool:
        if isinstance(campaign, Campaign):
            campaign = campaign.campaign_id
        res = await self.db.execute("""DELETE FROM campaign WHERE campaign_id = $1""", (campaign,))
        return res.size == 1

    async def update_campaign(self, campaign: Campaign, localization_ids: list[int] | None) -> bool:

        if localization_ids is not None:
            await self.db.execute("""
            DELETE FROM campaign_assignment 
            WHERE 
                id_localization <> ALL($1)
                AND campaign_id =$2
            """, (localization_ids, campaign.campaign_id))

            await self.db.execute("""
              DELETE
              FROM campaign_user
              WHERE matricule NOT IN (SELECT matricule FROM campaign_assignment WHERE campaign_id = $1)
                AND campaign_id = $1
              """, (campaign.campaign_id,))

            await self.db.insert_records(
                "campaign_localization",
                [(campaign.campaign_id, l) for l in localization_ids],
                columns=("campaign_id", "id_localization"),
                on_conflict="(campaign_id, id_localization) DO NOTHING"
            )

        await self.db.execute("""
          UPDATE campaign
          SET title=$1, start_date=$2, end_date=$3, updated_by=$4, status=$5
          WHERE campaign_id = $6
          """, (
            campaign.title, campaign.start_date, campaign.end_date, campaign.updated_by.matricule, campaign.status,
            campaign.campaign_id
        ))
        return True

    async def create(self, campaign: Campaign, localization_ids: list[int]) -> Campaign:
        _id = await self.db.execute("""
        INSERT INTO campaign (
            title, start_date, end_date, created_by, updated_by, status
        ) VALUES ($1,$2,$3,$4,$5,$6) RETURNING campaign_id;
        """, (
            campaign.title, campaign.start_date, campaign.end_date,
            campaign.created_by.matricule, campaign.updated_by.matricule,
            campaign.status.value)
                              )
        campaign.campaign_id = _id

        await self.db.insert_records(
            "campaign_localization",
            [(_id, l) for l in localization_ids],
            columns=("campaign_id", "id_localization"),
            on_conflict="(campaign_id, id_localization) DO NOTHING"
        )
        return campaign

    async def add_inventorist(self, campaign: Campaign | int, matricule, localization_ids: list[int]):
        if isinstance(campaign, Campaign):
            campaign_id = campaign.campaign_id
        else:
            campaign_id = campaign

        await self.db.execute("""
        DELETE FROM campaign_assignment WHERE campaign_id = $1 AND matricule = $2
        """, (campaign_id, matricule))

        await self.db.execute("""
        INSERT INTO campaign_user (campaign_id, matricule) 
        VALUES ($1, $2) ON CONFLICT (campaign_id, matricule) DO NOTHING
        """, (campaign_id, matricule))

        await self.db.insert_records(
            "campaign_assignment",
            [(campaign_id, matricule, l) for l in localization_ids],
            columns=("campaign_id", "matricule", "id_localization"),
            on_conflict="(campaign_id, matricule, id_localization) DO NOTHING"
        )

    async def get_inventorist(self, campaign: Campaign | int):
        if isinstance(campaign, Campaign):
            campaign = campaign.campaign_id
        res = await self.db.execute("""
            SELECT 
                * 
            FROM campaign_assignment c INNER JOIN users u
                    ON c.matricule = u.matricule
                INNER JOIN localization l
                    ON c.id_localization = l.id_localization
                INNER JOIN agency a 
                    ON a.code_agency = l.code_agency   
            WHERE campaign_id=$1
        """, (campaign,))

        result = {}

        for row in res:
            if row["matricule"] not in result:
                result[row["matricule"]] = {
                    "user": User.from_dict(row),
                    "localization": []
                }
            result[row["matricule"]]["localization"].append(
                Localization.from_dict(row)
            )
        return list(result.values())

    async def delete_inventorist(self, campaign: Campaign | int, matricule):
        if isinstance(campaign, Campaign):
            campaign_id = campaign.campaign_id
        else:
            campaign_id = campaign

        return (await self.db.execute("""
          DELETE
          FROM campaign_user
          WHERE campaign_id = $1
            AND matricule = $2
          """, (campaign_id, matricule)
        )).size == 1

    async def stats(self, campaign: list[Campaign | int]):
        _ids = [
            (c if isinstance(c, int) else c.campaign_id) for c in campaign
        ]
        if not _ids:
            return {}

        res_zone = await self.db.execute("""
            WITH loc AS 
                (SELECT * FROM campaign_localization WHERE campaign_id = ANY($1::int[]))
            SELECT 
                loc.campaign_id,
                COUNT(DISTINCT id_immobilization) AS immobilization_count,
                COUNT(DISTINCT code_agency) AS zone_count
            FROM immobilization INNER JOIN loc ON loc.id_localization = immobilization.id_localization
                INNER JOIN localization ON loc.id_localization = localization.id_localization
            WHERE 
                immobilization.status IN ('GOOD', 'DAMAGED')
            GROUP BY loc.campaign_id
        """, (_ids,))

        res_zone = {r["campaign_id"]: r for r in res_zone}

        res_user = await self.db.execute("""
            SELECT
                campaign_id,
                COUNT(*) AS user_count
            FROM campaign_user WHERE campaign_id = ANY($1)
            GROUP BY campaign_id
            """, (_ids,))

        res_user = {r["campaign_id"]: r for r in res_user}

        return {
            _id: {**(res_zone.get(_id) or {}), **(res_user.get(_id) or {})}
            for _id in _ids
        }

    async def campaign_zone(self, campaign_id, matricule=None, full=False):
        res = await self.db.execute(
            self.db.sql_file_j2("campaign.zone", matricule=matricule, full=full),
            (campaign_id, *([matricule] if matricule is not None else []))
        )

        for r in res:
            r["attached_user"] = list(filter(
                None, (r["attached_user"] or "").split("|")
            ))

        return res

    async def put_inventory(self, inv: Inventory):
        _id_im = inv.immobilization
        if not isinstance(_id_im, (str, uuid.UUID)):
            _id_im = _id_im.id_immobilization
        res = await self.db.execute("""
        INSERT INTO inventory(
            campaign_id, id_immobilization, status, 
            last_scan_at, last_scanned_by, 
            latitude, longitude, device_id, comment
        ) VALUES ($1,$2,$3,NOW(),$4,$5,$6,$7,$8)
        """, (
            inv.campaign if isinstance(inv.campaign, int) else inv.campaign.campaign_id,
            _id_im,
            inv.status.value, inv.last_scanned_by.matricule,
            inv.latitude, inv.longitude, inv.device_id, inv.comment
        ))
        return res.size == 1

    async def user_can_mark_inventory(self, campaign_id, id_immobilization, matricule):
        res = await self.db.execute("""
            SELECT 1
            FROM  immobilization imm LEFT JOIN campaign_assignment ca
                ON ca.id_localization = imm.id_localization
            WHERE (
                    campaign_id = $1 AND matricule = $2
                ) 
                AND id_immobilization = $3
            LIMIT 1
            """, (
                campaign_id, matricule, id_immobilization
            )
        )
        return bool(res)

    async def get_inventory_history(self, campaign_id, matricule=None):
        res = await self.db.execute(
            self.db.sql_file_j2("campaign.history", matricule=matricule),
            (campaign_id, *([matricule] if matricule is not None else []))
        )
        return res

    async def get_inventory_history_on_immobilization(self, id_immobilization, limit=5):
        res = await self.db.execute("""
        SELECT 
            inv.*,
            users.*
        FROM inventory inv INNER JOIN users 
            ON users.matricule=inv.last_scanned_by
        WHERE id_immobilization = $1
        ORDER BY inv.created_at DESC
            LIMIT $2
        """, (id_immobilization, limit))

        result = []
        for inv in res:
            inv_ = Inventory(
                campaign=inv["campaign_id"],
                immobilization=inv["id_immobilization"],
                status=ImmobilizationStatus(inv["status"]),
                last_scanned_by=User.from_dict(inv),
                comment=inv["comment"],
                latitude=inv["latitude"],
                longitude=inv["longitude"],
                device_id=inv["device_id"],
            )

            result.append(inv_)
        return result

    async def campaign_immobilization(self, campaign_id, matricule = None, localization_ids: list[int] | None = None, **kwargs):
        if matricule is not None:
            res = await self.db.execute("""
            SELECT id_localization FROM campaign_assignment
                WHERE campaign_id = $1 AND matricule = $2
            """, (campaign_id, matricule))
            res = [
                r["id_localization"] for r in res
            ]
            if localization_ids:
                localization_ids = [l for l in localization_ids if l in res]
            else:
                localization_ids = res
        added_sql = ""
        params = [campaign_id]
        if kwargs.get('serial_number'):
            params.append(kwargs.get('serial_number'))
            added_sql += f"\nAND imm.serial_number = ${len(params)}"

        if kwargs.get('title'):
            params.append(f"'%{kwargs['title']}%'")
            added_sql += f"\nAND imm.title LIKE ${len(params)}"

        if kwargs.get('id_immobilization_amplitude'):
            params.append(kwargs['id_immobilization_amplitude'])
            added_sql += f"\nAND imm.id_immobilization_amplitude = ${len(params)}"

        if localization_ids is not None:
            params.append(localization_ids)
            added_sql += f"\nAND imm.id_localization=ANY(${len(params)}::int[])"

        res = await self.db.execute(f"""
                SELECT 
                    imm.*
                FROM campaign_localization loc
                    INNER JOIN immobilization imm
                    ON loc.id_localization = imm.id_localization
                WHERE campaign_id = $1 
                    AND imm.status IN ('GOOD', 'DAMAGED')
                    {added_sql}
                """, params)
        return res

    async def merge_inventory_immo_status(self, campaign_id: int):
        res = await self.db.execute(
            f"""
                UPDATE immobilization as imm
                SET imm.status=inv.status, imm.comment=inv.comment
                FROM (
                    SELECT 
                        status, id_immobilization, comment,
                        ROW_NUMBER() OVER (PARTITION BY id_immobilization ORDER BY updated_at DESC) as rn
                    FROM inventory WHERE campaign_id=$1
                    ) inv
                WHERE imm.id_immobilization = inv.id_immobilization and rn=1   
            """, (campaign_id, )
            )
        return res

    async def most_recent_immobilization_status(self, id_immobilization):
        res = await self.db.execute(
            """
            SELECT 
                inv.status,
                inv.comment,
                inv.last_scanned_by,
                inv.campaign_id,
                inv.updated_at
            FROM inventory inv INNER JOIN campaign c
                ON inv.campaign_id = c.campaign_id
            WHERE id_immobilization = $1
            ORDER BY inv.updated_at DESC
            LIMIT 1
            """,
            (id_immobilization,)
        )
        if not res:
            return None
        return res[0]

