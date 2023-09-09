from PySide6.QtCore import QSettings


class HasSettings:
    def __init__(self):
        super().__init__()
        self.settings = QSettings()
        self.settings.beginGroup(self.settings_group_name())
        try:
            self.settings_load()
        finally:
            self.settings.endGroup()

    def settings_group_name(self) -> str:
        raise NotImplementedError()

    def settings_load(self):
        pass

    def settings_save(self):
        pass

    def closeEvent(self, event):
        super().closeEvent(event)  # type: ignore

        self.settings.beginGroup(self.settings_group_name())
        try:
            self.settings_save()
        finally:
            self.settings.endGroup()
        event.accept()
