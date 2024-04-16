import sys

import click
from PyQt5.QtWidgets import QApplication

from elchemi.experiments.live_acquisition import LiveAcquisition
from elchemi.view.main_window import ScatteringMainWindow
from elchemi.experiments.analysis import AnalyzeModel


@click.command()
@click.option('--config', default='config.yml', help='Path to the configuration file.')
def start(config):
    analysis = AnalyzeModel()
    acquisition = LiveAcquisition(config)
    acquisition.load_config()
    app = QApplication([])
    win = ScatteringMainWindow(analysis, acquisition)
    win.show()

    sys.exit(app.exec())
