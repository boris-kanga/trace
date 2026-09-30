import click

import asyncio


from src.core.config import WORK_DIR, CONFIG
from src.core.logger import set_up_logging
from src.domain.entities.user import UserNotFound, Role

set_up_logging(WORK_DIR + "logs")


@click.group()
def cli():
    pass

@cli.command
@click.option("--port", default=CONFIG['BACKEND_PORT'])
def start_api_server(port: int):

    click.echo(f"Starting API server on port {port}...")

    from src.web.app import create_app
    from hypercorn.asyncio import serve
    from hypercorn.config import Config
    from asgiref.wsgi import WsgiToAsgi

    from init import InitData

    async def _():
        await InitData.default_db(init_db=True)
        service = await InitData.user_service()
        _root_user = CONFIG.get("USER_ROOT_USERNAME", "5307")
        try:
            await service.from_matricule(_root_user)
        except UserNotFound:

            await service.create_user(
                {
                    "matricule": _root_user,
                    "password": CONFIG.get("ROOT_USER_PASSWORD"),
                    "first_name": CONFIG.get("USER_ROOT_FIRST_NAME", "Boris"),
                    "last_name": CONFIG.get("USER_ROOT_LAST_NAME", "KANGA"),
                    "email": CONFIG.get("USER_ROOT_EMAIL", "boris.kanga@socgen.com"),
                    "role": Role.BACKOFFICE,
                }
            )
    if CONFIG.get("TESTING_LOCAL") == "true":
        pass
    else:
        asyncio.run(_())

        # TODO: voir la gestion des coûts via ubigreen

    app = create_app()
    config = Config()
    config.bind = [f"0.0.0.0:{port}"]
    asyncio.run(serve(WsgiToAsgi(app), config=config))


if __name__ == '__main__':
    cli()