class AppConfig:
    """
    Class for Application configuration related functionalities
    Features - which features are enabled on an app
    """

    JWT = "jwt"
    URLS = "urls"
    APP_NAMES = ["analytics", "diagnostics", "websockets", "bridge_analytics"]
    APP_FEATURES = {
        "analytics": ["jwt", "urls"],
        "bridge_analytics": ["urls"],
        "diagnostics": ["jwt", "urls"],
        "websockets": ["jwt", "urls"],
    }

    def __init__(self):
        pass

    def is_jwt_enabled(self, app_name):
        """if jwt feature is enabled for an app"""
        return self.JWT in self.APP_FEATURES[app_name]

    def is_urls_enabled(self, app_name):
        """check if urls feature is enabled for an app"""
        return self.URLS in self.APP_FEATURES[app_name]

    def jwt_enabled_apps(self):
        """filter apps jwt enabled"""
        jwt_enabled_apps = []
        for app in self.APP_NAMES:
            if self.is_jwt_enabled(app):
                jwt_enabled_apps.append(app)
        return jwt_enabled_apps

    def urls_enabled_apps(self):
        """filter apps jwt enabled"""
        urls_enabled_apps = []
        for app in self.APP_NAMES:
            if self.is_urls_enabled(app):
                urls_enabled_apps.append(app)
        return urls_enabled_apps

    def all_apps(self):
        """return all apps"""
        return self.APP_NAMES


application_config = AppConfig()
