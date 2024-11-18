from dependency_injector import containers, providers

from amiami_api.api import AmiAmiApi
from amiami_api.store import AmiAmiOrdersFileStore, AmiAmiOrdersStore


class DIContainer(containers.DeclarativeContainer):
    wiring_config = containers.WiringConfiguration(modules=[".web"])

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
