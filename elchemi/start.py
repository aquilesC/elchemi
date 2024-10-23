import sys
sys.path.append('/Users/fg/LPL/Code/Project/Software/Elchemi_1/elchemi')

import click
from PyQt5.QtWidgets import QApplication

from elchemi.experiments.live_acquisition import LiveAcquisition
from elchemi.view.main_window import DisplayWindow
from elchemi.experiments.harmonic_analysis import AnalyzeModel


@click.command()
@click.option('--config', default='config.yml', help='Path to the configuration file.')
def start(config):
    analysis = AnalyzeModel()
    acquisition = LiveAcquisition(config)
    acquisition.load_config()
    app = QApplication([])
    win = DisplayWindow(analysis, acquisition)
    win.show()

    sys.exit(app.exec())

start()