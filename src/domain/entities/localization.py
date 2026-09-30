from dataclasses import dataclass, field


@dataclass(frozen=True)
class Agency:
    code_agency: str
    title: str

    def __eq__(self, other):
        if hasattr(other, "code_agency"):
            return self.code_agency == other.code_agency
        return self.code_agency == other


@dataclass
class Localization:
    id_localization: int = field(init=False)
    location_code: str

    agency: Agency

    def __hash__(self):
        return hash((self.agency.code_agency, self.location_code))

    def __eq__(self, other):
        if hasattr(other, "id_localization") and hasattr(self, "id_localization"):
            return self.id_localization == other.id_localization
        return self.agency.code_agency == other.agency.code_agency and self.location_code == other.location_code

    @classmethod
    def from_dict(cls, data):
        self = cls(
            data["location_code"],
            Agency(
                data["code_agency"] if "code_agency" in data else data["agency"]["code_agency"],
                data["title"] if "title" in data else data["agency"]["title"],
            )
        )
        if "id_localization" in data:
            self.id_localization = data["id_localization"]
        return self
