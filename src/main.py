"""
Application entry point — bootstraps QApplication and AppWindow.
"""
import sys

from PySide2.QtWidgets import QApplication
from PySide2.QtCore import Qt

from config.settings import settings
from utils.logger import logger
from ui.app_window import AppWindow


def main() -> int:
    settings.ensure_directories()
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION} (PySide2 frontend)")

    # Must be set before QApplication is created
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication.instance() or QApplication(sys.argv)
    app.setOrganizationName(settings.QSETTINGS_ORG)
    app.setApplicationName(settings.QSETTINGS_APP)
    app.setApplicationVersion(settings.APP_VERSION)

    window = AppWindow()
    window.show()

    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
