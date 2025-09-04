"""
Service factory for creating and managing service dependencies.

This centralizes service creation logic and reduces duplication across
the different Warthog applications.
"""

from typing import Optional, TYPE_CHECKING

from src.common.configuration import WarthogConfig, get_config
from src.common.services import VehicleService, GitService, LoggingService

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
            self._config = get_config()
        else:
            self._config = config

        # Common services
        self._logging_service: Optional[LoggingService] = None
        self._vehicle_service: Optional[VehicleService] = None
        self._git_service: Optional[GitService] = None

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

    def get_vehicle_service(self, **kwargs) -> VehicleService:
        """
        Get or create a VehicleService instance.
        """
        if self._vehicle_service is None:
            self._vehicle_service = VehicleService(self._config.vehicle_service_config, **kwargs)
        return self._vehicle_service

    def get_git_service(self) -> GitService:
        """
        Get or create a GitService instance.
        """
        if self._git_service is None:
            self._git_service = GitService()
        return self._git_service

    # Vehicle Data Grabber Services

    def get_vehicle_data_orchestrator(self, **kwargs) -> "VehicleDataOrchestrator":
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
                git_service=self.get_git_service(),
                **kwargs,
            )
        return self._vehicle_data_orchestrator

    def get_vehicle_data_processor(self, **kwargs) -> "VehicleDataProcessor":
        """
        Get or create a VehicleDataProcessor instance.
        """
        if self._vehicle_data_processor is None:
            # Import here to avoid circular imports
            from src.vehicle_data_grabber.services.vehicle_data_processor import VehicleDataProcessor

            self._vehicle_data_processor = VehicleDataProcessor(
                self._config.vehicle_data_grabber_config.vehicle_data_processor_config, **kwargs
            )
        return self._vehicle_data_processor

    # Replay Data Grabber Services

    def get_wt_ext_cli_client_service(self, **kwargs) -> "WtExtCliClientService":
        """
        Get or create a WtExtCliClientService instance.
        """
        if self._wt_ext_cli_service is None:
            # Import here to avoid circular imports
            from src.replay_data_grabber.services.wt_ext_cli_client_service import WtExtCliClientService

            self._wt_ext_cli_service = WtExtCliClientService(
                self._config.replay_data_grabber_config.wt_ext_cli_service_config, **kwargs
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

            self._replay_manager_service = ReplayManagerService(
                self._config.replay_data_grabber_config.replay_manager_service_config,
                replay_parser_service=self.get_replay_parser_service(),
                **kwargs,
            )
        return self._replay_manager_service
