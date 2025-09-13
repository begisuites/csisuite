import importlib
from importlib.machinery import ModuleSpec
import importlib.util
from pathlib import Path
import sys
import time
from typing import Dict
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from services.api import Api
from plugins.plugin_base import Plugin
from PySide6 import QtCore

class PluginFileHandler(FileSystemEventHandler):
    def __init__(self, plugin_manager):
        self.plugin_manager = plugin_manager
        self.last_modified = {}
        
    def on_modified(self, event):
        if event.is_directory or not event.src_path.endswith('.py'):
            return
        
        # Check if the file was modified recently to avoid multiple reloads as debounce mechanism
        if event.src_path in self.last_modified:
            if QtCore.QDateTime.currentDateTime().toSecsSinceEpoch() - self.last_modified[event.src_path] < 1:
                return

        self.last_modified[event.src_path] = QtCore.QDateTime.currentDateTime().toSecsSinceEpoch()
        QtCore.QMetaObject.invokeMethod(
            self.plugin_manager, "reload_plugin_from_path",
            QtCore.Qt.QueuedConnection,
            QtCore.Q_ARG(str, event.src_path)
        )

class PluginManager(QtCore.QObject):
    _instance : 'PluginManager' = None

    def __init__(self, api : Api, plugins_folder: str = "plugins"):
        super().__init__()
        PluginManager._instance = self
        self.api = api
        self.plugins_folder = Path(plugins_folder)
        self.plugins: Dict[str, (ModuleSpec, Plugin)] = {}
        self.observer = Observer()
        self.file_handler = PluginFileHandler(self)
        self.render_tick = 0

    @staticmethod
    def get_instance() -> 'PluginManager':
        return PluginManager._instance
    
    def load_plugins(self, directory: Path = None):
        """Load all plugins from the plugins folder recursively"""
        directory = self.plugins_folder if directory is None else directory
        for plugin_file in directory.iterdir():
            if plugin_file.is_file() and plugin_file.suffix == '.py':
                self.load_plugin(plugin_file)
            if plugin_file.is_dir():
                self.load_plugins(plugin_file)
    
    def load_plugin(self, plugin_file: str):
        """Load a single plugin module"""
        try:
            plugin_name = Path(plugin_file).absolute().relative_to(Path.cwd()).as_posix()
            spec = importlib.util.spec_from_file_location(plugin_name, plugin_file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            plugins = [obj for obj in vars(module).values() if isinstance(obj, type) and issubclass(obj, Plugin) and obj is not Plugin]
            
            if not plugins:
                return
            elif len(plugins) > 1:
                raise ValueError(f"❌ Multiple plugins found in {plugin_file}: {', '.join([p.__name__ for p in plugins])}")

            plugin = plugins[0](self.api)
            self.plugins[plugin_name] = (module, plugin)
            plugin.plugin_file = plugin_file
            print(f"🔌 Loaded module {plugin_name}")

        except Exception as e:
            print(f"❌ Failed to load plugin {plugin_file}: {e}")
    
    @QtCore.Slot(str)
    def reload_plugin_from_path(self, file_path: str):
        """Reload a plugin from its file path"""
        plugin_name = Path(file_path).absolute().relative_to(Path.cwd()).as_posix()
        try:
            if plugin_name in self.plugins:
                _, plugin = self.plugins[plugin_name]
                if not self.supports_hot_reload(plugin):
                    print(f"⚠️  Plugin {plugin_name} does not support hot-reloading. Please restart the application to apply changes.")
                    return
                self.unload_plugin(plugin_name)
            if Path(file_path).exists():
                self.load_plugin(file_path)
            self.api.ui().build()
        except Exception as e:
            print(f"❌ Failed to reload plugin {plugin_name}: {e}")
    
    def supports_hot_reload(self, plugin) -> bool:
        return "deactivate" in plugin.__class__.__dict__

    def get_plugin(self, name: str):
        return self.plugins.get(name)[1]

    def get_all_plugins(self) -> list[tuple[str, Plugin]]:
        return [(name, plugin) for name, (_, plugin) in self.plugins.items()]

    def start_hot_reload(self):
        self.observer.schedule(self.file_handler, str(self.plugins_folder), recursive=True)
        self.observer.start()
        print(f"🔄 Started hot-reloading for plugins in /{Path(self.plugins_folder).relative_to(Path.cwd())}")

    def stop_hot_reload(self):
        self.observer.stop()
        self.observer.join()
        print("🛑 Stopped hot-reloading plugins")
    
    def unload_plugin(self, plugin_name: str):
        module, plugin = self.plugins.get(plugin_name, (None, None))
        if plugin:
            plugin.deactivate()
            del plugin
        if module in sys.modules:
            del sys.modules[module.__name__]
        importlib.invalidate_caches()
        print(f"🔌❌ Unloaded module: {plugin_name}")

    def build(self):
        for _, plugin in self.get_all_plugins():
            plugin.build()

    def render(self):
        self.render_tick += 1
        for _, plugin in self.get_all_plugins():
            start = time.perf_counter()
            if self.render_tick % plugin.render_schedule() == 0:
                plugin.render(self.render_tick)
            elapsed = time.perf_counter() - start
            plugin.add_performance_time(elapsed)