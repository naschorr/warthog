"""
Service factory for creating and managing service dependencies.

This centralizes service creation logic and reduces duplication across
the different Warthog applications.
"""

from typing import Optional, TYPE_CHECKING

from confiddle import Confiddle, ConfiddleConfigModel, JsonProviderConfig, ProviderConfigModel
from src.common.configuration import WarthogConfig
from src.common.services import VehicleService, LoggingService
from src.common.utilities import get_root_directory

if TYPE_CHECKING:
    from src.vehicle_data_grabber.services.vehicle_data_orchestrator import VehicleDataOrchestrator
    from src.vehicle_data_grabber.services.vehicle_data_processor import VehicleDataProcessor
    from src.replay_data_grabber.services.replay_parser_service import ReplayParserService
    from src.replay_data_grabber.services.replay_manager_service import ReplayManagerService
    from src.replay_data_grabber.services.wt_ext_cli_client_service import WtExtCliClientService


class ServiceFactory:
    """
    Factory for creating and managing service instances.
    """

    # Lifecycle

    def __init__(self, config: Optional[WarthogConfig] = None):
        # Use provided config or load default
        if config is None:
            confiddle = Confiddle(
                ConfiddleConfigModel(
                    app=ProviderConfigModel(
                        json_file_provider=JsonProviderConfig(directory_path=get_root_directory() / "src")
                    )
                )
            )
            self._config = confiddle.load_config(WarthogConfig)
        else:
            self._config = config

        # Common services
        self._logging_service: Optional[LoggingService] = None
        self._vehicle_service: Optional[VehicleService] = None

        # Vehicle data grabber services
        self._vehicle_data_orchestrator: Optional["VehicleDataOrchestrator"] = None
        self._vehicle_data_processor: Optional["VehicleDataProcessor"] = None

        # Replay data grabber services
        self._wt_ext_cli_service: Optional["WtExtCliClientService"] = None
        self._replay_parser_service: Optional["ReplayParserService"] = None
        self._replay_manager_service: Optional["ReplayManagerService"] = None

    # Methods

    # Common Services

    def create_logging_service(self):
        """
        Get or create a LoggingService instance.
        """
        if self._logging_service is None:
            self._logging_service = LoggingService(self._config.logging_config)

    def get_vehicle_service(self) -> VehicleService:
        """
        Get or create a VehicleService instance.
        """
        if self._vehicle_service is None:
            self._vehicle_service = VehicleService(self._config.vehicle_service_config)
        return self._vehicle_service

    # Vehicle Data Grabber Services

    def get_vehicle_data_orchestrator(self) -> "VehicleDataOrchestrator":
        """
        Get or create a VehicleDataOrchestrator instance.
        """
        if self._vehicle_data_orchestrator is None:
            # Import here to avoid circular imports
            from src.vehicle_data_grabber.services.vehicle_data_orchestrator import VehicleDataOrchestrator

            self._vehicle_data_orchestrator = VehicleDataOrchestrator(
                self._config.vehicle_data_grabber_config.vehicle_data_orchestrator_config,
                vehicle_data_processor=self.get_vehicle_data_processor(),
                replay_manager_service=self.get_replay_manager_service(),
            )
        return self._vehicle_data_orchestrator

    def get_vehicle_data_processor(self) -> "VehicleDataProcessor":
        """
        Get or create a VehicleDataProcessor instance.
        """
        if self._vehicle_data_processor is None:
            # Import here to avoid circular imports
            from src.vehicle_data_grabber.services.vehicle_data_processor import VehicleDataProcessor

            self._vehicle_data_processor = VehicleDataProcessor(
                self._config.vehicle_data_grabber_config.vehicle_data_processor_config
            )
        return self._vehicle_data_processor

    # Replay Data Grabber Services

    def get_wt_ext_cli_client_service(self) -> "WtExtCliClientService":
        """
        Get or create a WtExtCliClientService instance.
        """
        if self._wt_ext_cli_service is None:
            # Import here to avoid circular imports
            from src.replay_data_grabber.services.wt_ext_cli_client_service import WtExtCliClientService

            self._wt_ext_cli_service = WtExtCliClientService(
                self._config.replay_data_grabber_config.wt_ext_cli_service_config
            )
        return self._wt_ext_cli_service

    def get_replay_parser_service(self) -> "ReplayParserService":
        """
        Get or create a ReplayParserService instance.
        """
        if self._replay_parser_service is None:
            # Import here to avoid circular imports
            from src.replay_data_grabber.services.replay_parser_service import ReplayParserService

            self._replay_parser_service = ReplayParserService(
                vehicle_service=self.get_vehicle_service(),
                wt_ext_cli_client_service=self.get_wt_ext_cli_client_service(),
            )
        return self._replay_parser_service

    def get_replay_manager_service(self, **kwargs) -> "ReplayManagerService":
        """
        Get or create a ReplayManagerService instance.
        """
        if self._replay_manager_service is None:
            # Import here to avoid circular imports
            from src.replay_data_grabber.services.replay_manager_service import ReplayManagerService

            base_config = self._config.replay_data_grabber_config.replay_manager_service_config
            filtered = {k: v for k, v in kwargs.items() if v is not None}
            service_config = base_config.model_copy(update=filtered) if filtered else base_config

            self._replay_manager_service = ReplayManagerService(
                service_config,
                replay_parser_service=self.get_replay_parser_service(),
            )
        return self._replay_manager_service
