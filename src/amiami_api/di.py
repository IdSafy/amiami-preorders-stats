from dependency_injector import containers, providers

from amiami_api.api import AmiAmiApi
from amiami_api.service import AmiamiService
from amiami_api.store import AmiAmiOrdersFileStore, AmiAmiOrdersStore
from amiami_api.telegram_bot import create_bot


class DIContainer(containers.DeclarativeContainer):
    wiring_config = containers.WiringConfiguration(modules=[".web", ".telegram_bot"])

    config = providers.Configuration()
    api = providers.Singleton(
        AmiAmiApi,
        username=config.username,
        password=config.password,
    )
    store = providers.Singleton[AmiAmiOrdersStore](
        AmiAmiOrdersFileStore,
        file_path=config.store_file_path,
    )

    telegram_bot = providers.Singleton(
        create_bot,
        token=config.telegram_bot_token,
    )

    service = providers.Singleton(
        AmiamiService,
        api=api,
        store=store,
    )
