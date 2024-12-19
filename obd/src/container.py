import functools
import inspect
import obdio

from socketio import AsyncServer

from src.configuration_service import ConfigurationService
from src.obd_service import OBDService
from src.injector_service import InjectorService

class Container():

    def __init__(self):
        self.sio_server = AsyncServer(cors_allowed_origins='*', json=obdio, async_mode='asgi')
        self.config_service = ConfigurationService(self.sio_server)
        self.obd_service = OBDService(self.sio_server, self.config_service)
        self.injector_service = InjectorService(self.sio_server, self.config_service, self.obd_service)

        self.instance_map = {
            ConfigurationService: self.config_service,
            OBDService: self.obd_service,
            InjectorService: self.injector_service,
            AsyncServer: self.sio_server,
        }

    def get(self, cls):
        """
        Retrieve an instance of the given class from the container.

        Args:
            cls (Type): The class type of the service.

        Returns:
            Instance of the requested service.

        Raises:
            ValueError: If the service is not found in the container.
        """
        if cls in self.instance_map:
            return self.instance_map[cls]
        raise ValueError(f"Dependency for {cls} not found")
    

def inject(func):
    """
    A decorator to inject dependencies into functions based on type annotations.

    Args:
        func (Callable): The function to decorate.

    Returns:
        Callable: The wrapped function with dependencies injected.
    """
    if inspect.iscoroutinefunction(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            sig = inspect.signature(func)
            bound = sig.bind_partial(*args, **kwargs)
            bound.apply_defaults()
            
            for name, param in sig.parameters.items():
                if name not in bound.arguments:
                    if param.annotation != inspect.Parameter.empty:
                        dependency = container.get(param.annotation)
                        kwargs[name] = dependency
            return await func(*args, **kwargs)
        return async_wrapper
    else:
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            sig = inspect.signature(func)
            bound = sig.bind_partial(*args, **kwargs)
            bound.apply_defaults()
            
            for name, param in sig.parameters.items():
                if name not in bound.arguments:
                    if param.annotation != inspect.Parameter.empty:
                        dependency = container.get(param.annotation)
                        kwargs[name] = dependency
            return func(*args, **kwargs)
        return sync_wrapper
    

container = Container()
