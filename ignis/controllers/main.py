import faulthandler
import logging
import sys

from ignis.controllers.main_window import MainWindow
from ignis.model.configs import Configs
from ignis.utils import theme_utils

for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)

logging.basicConfig(
    handlers=[
        logging.FileHandler("ignis.log", "w", "utf-8"),
        logging.StreamHandler(sys.stdout),
    ]
)

faulthandler.enable(all_threads=True)

logging.info("Ignis Beta 2")

try:
    from PySide6.QtWidgets import QApplication
    from ignis.controllers.inputs_form import InputsForm
except:
    logging.exception("Failed to import a core module.")
    exit(1)

try:
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setPalette(theme_utils.gen_dark_palette())
    app.setFont(theme_utils.gen_font())

    configs = Configs.load()
    window = MainWindow(configs)
    window.show()

    app.exec()
except:
    logging.exception("Encountered a fatal error during startup or closing.")
    exit(1)

logging.info("Application exited.")
