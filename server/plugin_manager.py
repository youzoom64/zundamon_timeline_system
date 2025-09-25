import importlib
import sys
from pathlib import Path
import logging
import asyncio

class PluginManager:
    def __init__(self, config):
        self.config = config
        self.plugins = {}
        self.hooks = {
            'on_system_start': [],
            'on_system_stop': [],
            'on_timeline_start': [],
            'on_timeline_end': [],
            'on_speech_start': [],
            'on_speech_end': [],
            'on_scene_change': [],
            'on_comment_received': [],
            'on_comment_response': [],
            'on_character_change': [],
            'on_error': []
        }
        self.logger = logging.getLogger(__name__)
        self.plugin_dir = Path(self.config["plugins"]["plugin_dir"])
        
    def load_plugins(self):
        """プラグイン読み込み"""
        if not self.plugin_dir.exists():
            self.logger.warning(f"プラグインディレクトリが見つかりません: {self.plugin_dir}")
            return
        
        # プラグインディレクトリをPythonパスに追加
        if str(self.plugin_dir) not in sys.path:
            sys.path.insert(0, str(self.plugin_dir))
        
        for plugin_name in self.config["plugins"]["enabled"]:
            try:
                self.load_plugin(plugin_name)
            except Exception as e:
                self.logger.error(f"プラグイン読み込み失敗: {plugin_name}, {e}")
    
    def load_plugin(self, plugin_name: str):
        """個別プラグイン読み込み"""
        try:
            # プラグインモジュール読み込み
            module = importlib.import_module(plugin_name)
            
            # プラグインクラス取得
            plugin_class_name = f"{plugin_name.capitalize()}Plugin"
            if hasattr(module, plugin_class_name):
                plugin_class = getattr(module, plugin_class_name)
            else:
                # デフォルトクラス名で検索
                plugin_class = getattr(module, "Plugin", None)
            
            if not plugin_class:
                raise ImportError(f"プラグインクラスが見つかりません: {plugin_class_name}")
            
            # プラグインインスタンス作成
            plugin_instance = plugin_class(self.config)
            self.plugins[plugin_name] = plugin_instance
            
            # フック登録
            self.register_plugin_hooks(plugin_name, plugin_instance)
            
            self.logger.info(f"プラグイン読み込み完了: {plugin_name}")
            
        except Exception as e:
            self.logger.error(f"プラグイン読み込みエラー: {plugin_name}, {e}")
            raise
    
    def register_plugin_hooks(self, plugin_name: str, plugin_instance):
        """プラグインフック登録"""
        for hook_name in self.hooks.keys():
            if hasattr(plugin_instance, hook_name):
                hook_method = getattr(plugin_instance, hook_name)
                self.hooks[hook_name].append((plugin_name, hook_method))
                self.logger.debug(f"フック登録: {plugin_name}.{hook_name}")
    
    def unload_plugin(self, plugin_name: str):
        """プラグイン削除"""
        if plugin_name in self.plugins:
            # フック削除
            for hook_list in self.hooks.values():
                hook_list[:] = [(name, method) for name, method in hook_list if name != plugin_name]
            
            # プラグイン削除
            del self.plugins[plugin_name]
            self.logger.info(f"プラグイン削除: {plugin_name}")
    
    async def execute_hook(self, hook_name: str, *args, **kwargs):
        """プラグインフック実行"""
        if hook_name not in self.hooks:
            self.logger.warning(f"未知のフック: {hook_name}")
            return
        
        for plugin_name, hook_method in self.hooks[hook_name]:
            try:
                if asyncio.iscoroutinefunction(hook_method):
                    await hook_method(*args, **kwargs)
                else:
                    hook_method(*args, **kwargs)
            except Exception as e:
                self.logger.error(f"プラグインフック実行エラー: {plugin_name}.{hook_name}, {e}")
    
    def get_plugin(self, plugin_name: str):
        """プラグインインスタンス取得"""
        return self.plugins.get(plugin_name)
    
    def list_plugins(self):
        """読み込み済みプラグイン一覧"""
        return list(self.plugins.keys())
    
    def get_plugin_info(self, plugin_name: str):
        """プラグイン情報取得"""
        plugin = self.plugins.get(plugin_name)
        if not plugin:
            return None
        
        info = {
            "name": plugin_name,
            "class": plugin.__class__.__name__,
            "hooks": []
        }
        
        # 実装されているフック一覧
        for hook_name in self.hooks.keys():
            if hasattr(plugin, hook_name):
                info["hooks"].append(hook_name)
        
        return info