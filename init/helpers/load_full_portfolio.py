import pandas
from src.core.config import WORK_DIR

from src.domain.entities.suppliers import Supplier
from src.domain.entities.localization import Localization, Agency
from src.domain.entities.immobilization import (
    Immobilization, ImmobilizationFamily,
    ImmobilizationSubFamily
)

from init import InitData


def _read_file(filename, equivalent_column):
    dataset = pandas.read_excel(filename)
    format_cols = {}
    for col in dataset.columns:
        for x, k in equivalent_column.values():
            if x.upper() in col.upper():
                format_cols[col] = k
                break

    dataset.rename(columns=format_cols, inplace=True)
    dataset = dataset[list(format_cols.values())]

    assert all(k in dataset.columns for k in equivalent_column.values())
    return dataset


async def add_family(family_file):
    _equivalent_column = {
        "FAMILLE": "id_family",
        "LIBELLE FAMILLE": "family_title",
        "SSFAM": "id_subfamily",
        "LIBELLE SOUS FAMILLE": "subfamily_title",
        "COMPTE IMMO": "immo_account",
        "COMPTE DOT": "dotation_account",
        "COMPTE AMORT": "depreciation_account",
        "TAUX AMORT": "depreciation_year_rate"
    }

    dataset = _read_file(family_file, _equivalent_column)

    dataset.dropna(subset=['id_subfamily'], inplace=True)

    family_data = (dataset[["id_family", "family_title"]]
        .rename(columns={"family_title": "title"})
        .drop_duplicates(subset=['id_family'])
    )

    family = []
    subfamily = []

    for _, row in family_data.iterrows():
        family.append(
            ImmobilizationFamily(
                row.id_family,
                row.title
            )
        )

    repo = await InitData.immobilization_repo()
    await repo.insert_family(family)
    for _, row in dataset.iterrows():
        subfamily.append(
            ImmobilizationSubFamily(
                row.id_subfamily,
                row.subfamily_title,
                ImmobilizationFamily(row.id_family, row.family_title),
                row.immo_account,
                row.dotation_account,
                row.depreciation_account,
                row.depreciation_year_rate
            )
        )
    await repo.insert_subfamily(subfamily)


async def load(filename: str | None=None):
    _equivalent_column = {
        "NUMIMMO": "id_immobilization_amplitude",
        "LIBIMMO": "title",
        "CODE AGENCE": "code_agency",
        "LIBELLE AGENCE": "agency_title",
        "LOCALISAT": "location_code",
        "FAMILLE": "id_family",
        "SSFAMILLE": "id_subfamily",
        "FOURNIS": "supplier_name",

        "NUMCDE": "order_number",
        "DATECDE": "order_date",

        "NUMBL": "delivery_note_number",
        "DATEBL": "delivery_note_date",

        "NUMFACT": "invoice_number",
        "DATEFACT": "invoice_date",

        "DATEACQ": "acquittement_date",
        "VALEURACQ": "acquittement_value"
    }

    if filename is None:
        filename = WORK_DIR + 'data' + 'full_portfolio.xlsx'

    dataset = _read_file(filename, _equivalent_column)

    repo = await InitData.immobilization_repo()
    async with repo as db_records:
        sub_family = db_records.get("sub_family") or {}
        localization_data: dict[str,Localization] = db_records.get("localization") or {}

        localization = {
            (l.agency, l.location_code): l for l in localization_data.values()
        }
        immobilizations = []
        for _, row in dataset.iterrows():
            im = Immobilization(
                row.id_immobilization_amplitude,
                row.title,
                (
                        localization.get((row.agency, row.location_code)) or
                        Localization(row.location_code, Agency(row.code_agency, row.agency_title))
                ),
                sub_family[row.id_subfamily],
                Supplier(row.supplier_name, None),

                row.order_number,
                row.order_date,

                row.delivery_note_number,
                row.delivery_note_date,

                row.invoice_number,
                row.invoice_date,

                row.acquittement_date,
                row.acquittement_value,
                created_by=None,
                updated_by=None
            )
            immobilizations.append(im)

        await repo.massive_save(immobilizations)
