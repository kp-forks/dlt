import typing as t

from dlt.common.destination import Destination, DestinationCapabilitiesContext
from dlt.common.schema.typing import TTableIndexType
from dlt.destinations.impl.synapse import capabilities

from dlt.destinations.impl.synapse.configuration import (
    SynapseCredentials,
    SynapseClientConfiguration,
)

if t.TYPE_CHECKING:
    from dlt.destinations.impl.synapse.synapse import SynapseClient


class synapse(Destination[SynapseClientConfiguration, "SynapseClient"]):
    spec = SynapseClientConfiguration

    def capabilities(self) -> DestinationCapabilitiesContext:
        return capabilities()

    @property
    def client_class(self) -> t.Type["SynapseClient"]:
        from dlt.destinations.impl.synapse.synapse import SynapseClient

        return SynapseClient

    def __init__(
        self,
        credentials: t.Union[SynapseCredentials, t.Dict[str, t.Any], str] = None,
        default_table_index_type: t.Optional[TTableIndexType] = "heap",
        create_indexes: bool = False,
        auto_disable_concurrency: t.Optional[bool] = True,
        destination_name: t.Optional[str] = None,
        environment: t.Optional[str] = None,
        **kwargs: t.Any,
    ) -> None:
        """Configure the Synapse destination to use in a pipeline.

        All arguments provided here supersede other configuration sources such as environment variables and dlt config files.

        Args:
            credentials: Credentials to connect to the Synapse dedicated pool. Can be an instance of `SynapseCredentials` or
                a connection string in the format `synapse://user:password@host:port/database`
            default_table_index_type: Maps directly to the default_table_index_type attribute of the SynapseClientConfiguration object.
            create_indexes: Maps directly to the create_indexes attribute of the SynapseClientConfiguration object.
            auto_disable_concurrency: Maps directly to the auto_disable_concurrency attribute of the SynapseClientConfiguration object.
            **kwargs: Additional arguments passed to the destination config
        """
        super().__init__(
            credentials=credentials,
            default_table_index_type=default_table_index_type,
            create_indexes=create_indexes,
            auto_disable_concurrency=auto_disable_concurrency,
            destination_name=destination_name,
            environment=environment,
            **kwargs,
        )
