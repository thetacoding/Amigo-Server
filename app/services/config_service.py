import yaml
from pathlib import Path

class ConfigService:
    @staticmethod
    def _load_yaml(filename: str = "presets.yaml"):
        file_path = Path("data") / filename
        if not file_path.exists():
            return {}
        with open(file_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    
    @classmethod
    def get_all(cls):
        data = cls._load_yaml("presets.yaml")
        return data

    @classmethod
    def get_app_config(cls):
        data = cls._load_yaml("presets.yaml")
        return data.get("app_config", {})

    @classmethod
    def get_web_search_config(cls) -> dict:
        """联网检索路由：供应商顺序、是否允许回落等，见 app_config.web_search。"""
        app = cls.get_app_config() or {}
        return dict(app.get("web_search") or {})

    @classmethod
    def get_assets(cls, asset_type: str = None):
        data = cls._load_yaml("presets.yaml")
        assets = data.get("assets", {})
        if asset_type:
            return assets.get(asset_type, [])
        return assets
    
    @classmethod
    def get_chatSessions(cls):
        data = cls._load_yaml("presets.yaml")
        assets = data.get("chatSessions", {})
        return assets

    @classmethod
    def get_prompt_templates(cls):
        data = cls._load_yaml("prompt_templates.yaml")
        return data.get("prompt_templates", [])

    @classmethod
    def get_prompt_template(cls, template_id: str = "default_cloud_prompt"):
        templates = cls.get_prompt_templates()
        for template in templates:
            if template.get("id") == template_id:
                return template
        return {}