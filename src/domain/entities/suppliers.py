from contextlib import contextmanager
from dataclasses import dataclass, field


_suppliers_register = {None: None}
_need_to_register = True


EMPTY = "EMPTY-TRACE-SAFE"



def _name_in_register(name):
    if name == EMPTY:
        return False
    if name in (float("nan"), None, "None", "null", "", "nan") or not isinstance(name, str):
        return True, None
    name = name.lower().strip()
    if not name:
        return True, None
    return name in _suppliers_register, name


@contextmanager
def ignore_suppliers_register(empty=False):
    global _need_to_register
    if empty:
        _suppliers_register.clear()
        _suppliers_register[None] = None

    _need_to_register = False
    yield
    _need_to_register = True

@dataclass
class Supplier:
    id_supplier: int = field(init=False)
    name: str
    address: str | None = None

    def __new__(cls, name, *ags, **kwargs):
        if _need_to_register and name != EMPTY:
            if isinstance(name, int):
                for supplier in _suppliers_register.values():
                    if getattr(supplier, "id_supplier", None) == name:
                        return supplier
            _bool, name = _name_in_register(name)
            if _bool:
                return _suppliers_register[name]
        self = super().__new__(cls)
        if name != EMPTY:
            _suppliers_register[name] = self
        return self
