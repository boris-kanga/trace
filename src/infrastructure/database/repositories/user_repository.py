
from src.domain.entities.user import User, UserException, UserNotFound
from src.domain.interfaces.user_repository_abc import UserRepositoryABC


class UserRepository(UserRepositoryABC):
    def __init__(self, db_object):
        UserRepositoryABC.__init__(self)
        self.db_object = db_object

    async def get(self, matricule: str) -> User:
        res = await self.db_object.execute(
            f"SELECT * FROM users "
            f"WHERE matricule = $1 AND deleted_at IS NULL "
            f"LIMIT 1", (matricule,)
        )
        if len(res) == 0:
            raise UserNotFound("%s not found" % (matricule,))
        res = res[0]
        return User.from_dict(**res)

    async def get_all(self) -> list[User]:
        res = await self.db_object.execute(
            """
            SELECT * FROM users WHERE deleted_at IS NULL
            """
        )
        return [User.from_dict(**row) for row in res]

    async def delete(self, matricule: str) -> bool:
        res = await self.db_object.execute(
            """
            UPDATE users
            SET deleted_at=NOW()
            WHERE matricule = $1
            """, (matricule,)
        )
        return res.size == 1

    async def create(self, user: User, password:str|None=None) -> bool:
        if not hasattr(user, "_password_hash") and password:
            user.password = password

        _user = user.to_dict()
        keys = (
            "matricule", "first_name", "last_name", "email", "password_hash", "role",
            "is_active", "last_login_at", "deleted_at"
        )
        res = await self.db_object.execute(
            f"""
            INSERT INTO users (
               {','.join(keys)}
            ) values ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            """, tuple(
                _user[key] for key in keys
            )
        )
        return res.size == 1


    async def update(self, user: User) -> bool:
        res = await self.db_object.execute(
            """
            UPDATE users 
            SET 
                first_name=$1,
                last_name=$2,
                email=$3,
                password_hash=$4,
                role=$5,
                is_active=$6,
                last_login_at=$7
            WHERE matricule = $8
            """, (
                user.first_name, user.last_name, user.email, user.password_hash,
                user.role.value, user.is_active, user.last_login_at, user.matricule)
        )
        return res.size == 1