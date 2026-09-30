import uuid
from typing import Literal

from src.core.logger import get_logger
from src.domain.entities.immobilization import (Immobilization, ImmobilizationFamily,
                                                ImmobilizationSubFamily, ImmobilizationStatus)
from src.domain.entities.suppliers import Supplier, ignore_suppliers_register
from src.domain.entities.user import Role
from src.domain.interfaces.immobilization_repository_abc import ImmobilizationRepositoryABC

from src.domain.entities.localization import Agency, Localization
from src.domain.interfaces.db_object_abc import AffectedRows


logger = get_logger(__name__)


async def get_info_temp(db_object):
    agency = await db_object.execute("SELECT * FROM agency")
    agency = {
        a["code_agency"]: Agency(
            a["code_agency"],
            a["title"]
        )
        for a in agency
    }
    localization = await db_object.execute("SELECT * FROM localization")
    localization = {
        l["id_localization"]: Localization(
            l["location_code"],
            agency[l["code_agency"]]
        )
        for l in localization
    }
    for _id, l in localization.items():
        l.id_localization = _id

    immobilization_family = await db_object.execute("SELECT * FROM immobilization_family")
    immobilization_family = {
        imf["id_family"]: ImmobilizationFamily(
            imf["id_family"],
            imf["title"]
        )
        for imf in immobilization_family
    }
    sub_family = await db_object.execute("SELECT * FROM immobilization_subfamily")
    sub_family = {
        ims["id_subfamily"]: ImmobilizationSubFamily(
            ims["id_subfamily"],
            ims["title"],
            immobilization_family[ims["id_family"]],

            ims["immo_account"],
            ims["dotation_account"],
            ims["depreciation_account"],
            ims["depreciation_year_rate"]
        )
        for ims in sub_family
    }
    suppliers = await db_object.execute("SELECT * FROM suppliers")
    with ignore_suppliers_register():
        suppliers = {
            s["id_supplier"]: Supplier(
                s["name"],
                s["address"]
            )
            for s in suppliers
        }
        for _id, s in suppliers.items():
            s.id_supplier = _id

    return dict(
        agency=agency, immobilization_family=immobilization_family,
        sub_family=sub_family, suppliers=suppliers, localization=localization
    )


class ImmobilizationRepository(ImmobilizationRepositoryABC):
    def __init__(self, db_object):
        self.db_object = db_object
        self._tmp = {}

    async def __aenter__(self):
        self._tmp = await get_info_temp(self.db_object)
        return self._tmp

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    async def create_supplier(self, supplier: Supplier, **kwargs):
        _id = await self.db_object.execute(
            """INSERT INTO suppliers (name, address) values ($1, $2) RETURNING id_supplier""",
            (supplier.name, supplier.address), conn=kwargs.get("conn")
        )
        supplier.id_supplier = _id
        return _id

    async def create_agency(self, agency: Agency, **kwargs):
        return await self.db_object.execute(
            """
            INSERT INTO agency (code_agency, title)
            VALUES ($1, $2) ON CONFLICT (code_agency) DO UPDATE SET title=EXCLUDED.title
            """, (agency.code_agency, agency.title), conn=kwargs.get("conn")
        )

    async def create_localization(self, localization: Localization, **kwargs):
        return await self.db_object.execute(
            """
            INSERT INTO localization (location_code,code_agency) VALUES ($1, $2) RETURNING id_localization
            """, (localization.location_code, localization.agency.code_agency), conn=kwargs.get("conn")
        )

    async def insert_family(self, family: list[ImmobilizationFamily], **kwargs):
        return await self.db_object.insert_records(
            "immobilization_family",
            family,
            on_conflict="(id_family) DO UPDATE SET title=EXCLUDED.title",
            conn=kwargs.get("conn")
        )

    async def insert_subfamily(self, subfamily: list[ImmobilizationSubFamily], **kwargs):
        logger.info(subfamily)
        return await self.db_object.insert_records(
            "immobilization_subfamily",
            subfamily,
            on_conflict="(id_subfamily) DO UPDATE "
                        "SET title=EXCLUDED.title,"
                        "immo_account=EXCLUDED.immo_account,"
                        "dotation_account=EXCLUDED.dotation_account,"
                        "depreciation_account=EXCLUDED.depreciation_account,"
                        "depreciation_year_rate=EXCLUDED.depreciation_year_rate",
            conn=kwargs.get("conn")
        )

    async def update_id(self, immobilization: Immobilization, new_id: uuid.UUID):
        new_blank_immo = await self.get(id_immobilization=new_id, status="UNKNOWN")
        if not new_blank_immo:
            return False
        new_blank_immo = new_blank_immo[0].to_dict()

        last_dict = immobilization.to_dict()

        extra_args = ["title", "serial_number", "comment", "status", "created_by", "updated_by"]

        for key in set(last_dict).difference(extra_args + ["id_immobilization"]):
            if new_blank_immo[key]:
                if new_blank_immo[key] != last_dict[key]:
                    return False
            else:
                new_blank_immo[key] = last_dict[key]

        for key in extra_args:
            new_blank_immo[key] = last_dict[key]

        new_blank_immo = Immobilization.from_dict(new_blank_immo)
        try:
            async with self.db_object.get_conn() as conn:
                async with conn.transaction():
                    await self.db_object.execute(
                        """
                        UPDATE inventory 
                        SET id_immobilization=$1
                        WHERE id_immobilization=$2
                        """, (new_id, immobilization.id_immobilization),
                        conn=conn
                    )
                    res = await self.delete(immobilization, conn=conn)
                    assert res.size == 1
                    await self.save(new_blank_immo, conn=conn)
        except AssertionError:
            return False
        return True

    async def save(self, immobilization: Immobilization, conn=None):
        if immobilization.supplier:
            s = immobilization.supplier
            if not getattr(s, "id_supplier", None):
                await self.create_supplier(s)
        if immobilization.updated_by is None:
            return None
        if hasattr(immobilization, "id_immobilization"):
            _id = immobilization.id_immobilization
            im = immobilization.to_dict()
            _id = im.pop("id_immobilization")
            im.pop("created_by")
            if isinstance(immobilization.updated_by, str):
                updater = await self.db_object.execute(
                    """
                    SELECT role FROM users WHERE matricule=$1 LIMIT 1
                    """, (immobilization.updated_by,), conn=conn
                )
                if not updater:
                    return False
                role = Role(updater[0]["role"])
            else:
                if immobilization.updated_by is None:
                    return False
                role = immobilization.updated_by.role
            if role == Role.INVENTORIST:
                prev_im = await self.get(id_immobilization=immobilization.id_immobilization)
                if not prev_im:
                    return False
                prev_im = prev_im[0]
                if prev_im.status != ImmobilizationStatus.UNKNOWN:
                    return False
                for k in ("title", "id_localization", "id_subfamily"):
                    if getattr(prev_im, k, None):
                        im.pop(k, None)
                im.id_immobilization_amplitude = Noneinnocentkericson@gmail.com

            keys = list(im.keys())
            im = [im[k] for k in keys] + [_id]

            logger.info(f"{keys+["id_immobilization"]} --> {im}")
            res = await self.db_object.execute(
                f"""
                UPDATE immobilization 
                SET {",".join(f"{k}=${i+1}" for i, k in enumerate(keys))}
                WHERE id_immobilization=${len(keys) + 1}""", im, conn=conn
            )
            return res.size == 1
        else:
            im = immobilization.to_dict()
            keys = list(im.keys())
            im = [im[k] for k in keys]
            res = await self.db_object.execute(
                f"""
                INSERT INTO immobilization ({",".join(keys)}) 
                VALUES ({",".join("$%s" %(i+1) for i in range(len(im)))}) 
                RETURNING id_immobilization""", im, conn=conn
            )
            immobilization.id_immobilization = uuid.UUID(str(res))
        return uuid.UUID(str(res))

    async def massive_save(self, immobilizations: list[Immobilization]):
        if not immobilizations:
            return
        keys = (
            "id_immobilization_amplitude",
            "title", "id_localization", "id_subfamily", "id_supplier",
            "order_number", "order_date", "delivery_note_number",
            "delivery_note_date", "invoice_number", "invoice_date",
            "acquittement_date", "acquittement_value",
            "status", "created_by", "updated_by", "serial_number",
            "ubigreen_number", "comment"
        )
        async with self.db_object.get_conn() as conn:
            async with conn.transaction():
                data = []
                for im in immobilizations:
                    data.append(im.to_dict())
                    if im.supplier and data[-1]["id_supplier"] is None:
                        im.supplier.id_supplier = await self.create_supplier(im.supplier, conn=conn)
                    # id_localization
                    if data[-1]["id_localization"] is None and im.localization:
                        im.localization.id_localization = await self.create_localization(
                            im.localization, conn=conn
                        )
                    data[-1] = [im.to_dict()[k] for k in keys]

                await self.db_object.insert_records(
                    "immobilization", data, keys, conn=conn
                )

    async def _get(self,  _as: Literal["items","size"]="items", **kwargs) -> list[Immobilization] | int:
        add_where_clause = ""
        add_join_table = []
        add_select_clause = (
            "im.*, "
            "l.code_agency, "
            "a.title AS a_title, "
            "location_code, "
            "s.name AS s_name, s.id_supplier, s.address,"
            "sub.id_subfamily, sub.id_family, sub.title AS sub_title, f.title AS f_title"
        )

        params = []

        if kwargs.get("status", "ALL").upper() != "ALL":
            status = kwargs["status"].upper()
            status = {"ASSOCIED": "<>'UNKNOWN'", "NOT_ASSOCIATED": "='UNKNOWN'"}.get(status)
            if status:
                add_where_clause += f"\nAND im.status {status}"
            else:
                params.append(ImmobilizationStatus(kwargs["status"]).value)
                add_where_clause +=f"\nAND im.status=${len(params)}"
        if kwargs.get("q"):
            q = kwargs.get("q").lower().strip()
            if q:
                params.append(f'%{q}%')
                add_where_clause += (
                    f"\nAND ("
                        f"LOWER(im.title) LIKE ${len(params)} OR "
                        f"LOWER(f.title) LIKE ${len(params)} OR "
                        f"LOWER(sub.title) LIKE ${len(params)}"
                    f")"
                )

        if kwargs.get("code_agency")  or kwargs.get("location_code"):
            if kwargs.get("code_agency"):
                params.append(kwargs["code_agency"])
                add_where_clause += f"\nAND l.code_agency=${len(params)}"
            if kwargs.get("location_code"):
                params.append(kwargs["location_code"])
                add_where_clause += f"\nAND l.location_code=${len(params)}"
        if kwargs.get("id_immobilization"):
            params.append(kwargs["id_immobilization"])
            add_where_clause += f"\nAND im.id_immobilization=${len(params)}"
        if kwargs.get("min_date"):
            params.append(kwargs["min_date"])
            add_where_clause += f"\nAND im.created_at >= ${len(params)}"

        if kwargs.get("max_date"):
            params.append(kwargs["max_date"])
            add_where_clause += f"\nAND im.created_at <= ${len(params)}"

        limit = kwargs.get("limit", None)
        cursor = kwargs.get("cursor", None)
        if cursor is not None:
            params.append(cursor)
            add_where_clause += f"\nAND im.id_immobilization>${len(params)}"
        if limit is not None:
            params.append(limit)

        add_join_clause = "\n".join(
            f"INNER JOIN {t} {al} ON im.{f}={al}.{f}"
             for t, al, f in add_join_table
        )
        if _as == "size":
            add_select_clause = "count(*) as nb"

        res = await self.db_object.execute(
            f"""
            SELECT {add_select_clause} FROM immobilization im
                LEFT JOIN localization l ON im.id_localization = l.id_localization
                LEFT JOIN agency a ON a.code_agency = l.code_agency
                
                LEFT JOIN immobilization_subfamily sub ON sub.id_subfamily = im.id_subfamily
                LEFT JOIN immobilization_family f ON f.id_family = sub.id_family 
                LEFT JOIN suppliers s ON im.id_supplier=s.id_supplier
                
                {add_join_clause}
            WHERE 1=1
                {add_where_clause}
                
            {"LIMIT $"+str(len(params)) if limit else ""}
            """, params
        )

        if _as == "size":
            return res[0]["nb"]

        ims = []
        for im in res:
            im = Immobilization.from_dict(im)
            ims.append(im)
        return ims

    async def delete(self, obj: Agency|Localization|Immobilization|Supplier, conn=None):
        if isinstance(obj, Agency):
            return await self.db_object.execute(
                "DELETE FROM agency WHERE code_agency=$1", [obj.code_agency], conn=conn
            )
        if isinstance(obj, Localization):
            return await self.db_object.execute(
                """
                DELETE FROM localization WHERE location_code=$1 AND code_agency=$2
                """,
                (obj.location_code, obj.agency.code_agency),conn=conn
            )
        if isinstance(obj, Immobilization):
            return await self.db_object.execute(
                """
                DELETE FROM immobilization WHERE id_immobilization=$1
                """, (obj.id_immobilization,), conn=conn
            )
        return AffectedRows(0)

    async def get_agency(self):
        res = await self.db_object.execute("""SELECT * FROM agency""")
        return [Agency(a["code_agency"], a["title"]) for a in res]

    async def get_localization(self):
        res = await self.db_object.execute(
            """
            SELECT * FROM localization 
            INNER JOIN agency ON localization.code_agency=agency.code_agency
            """)

        localizations = []
        for l in res:
            loc =  Localization(
                l["location_code"],
                Agency(
                    l["code_agency"],
                    l["title"]
                )
            )
            loc.id_localization = l["id_localization"]
            localizations.append(loc)
        return localizations

    async def get_family(self):
        res = await self.db_object.execute(
            """
            SELECT 
                id_family,
                title
            FROM immobilization_family family
            """)
        return [
                ImmobilizationFamily(
                    sub["id_family"],
                    sub["title"],
                )
            for sub in res]

    async def get_subfamily(self):
        res = await self.db_object.execute(
            """
            SELECT
                sub.id_subfamily,
                sub.title,
                sub.immo_account,
                sub.dotation_account,
                sub.depreciation_account,
                sub.depreciation_year_rate,
                sub.id_family,
                f.title as family_title
            FROM immobilization_subfamily sub
            INNER JOIN immobilization_family f ON 
                sub.id_family = f.id_family
            """)


        return [
            ImmobilizationSubFamily(
                sub["id_subfamily"],
                sub["title"],
                ImmobilizationFamily(
                    sub["id_family"],
                    sub["family_title"],
                ),
                sub["immo_account"],
                sub["dotation_account"],
                sub["depreciation_account"],
                sub["depreciation_year_rate"]
            )
            for sub in res]

    async def get_supplier(self):
        res = await self.db_object.execute(
            """
            SELECT 
                id_supplier, name, address
            FROM suppliers
            """
        )
        rows = []
        with ignore_suppliers_register(empty=True):
            for r in res:
                s = Supplier(
                    r["name"],
                    r["address"],
                )
                s.id_supplier = r["id_supplier"]
                rows.append(s)

        return rows
