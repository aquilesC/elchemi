from setuptools import setup, find_packages


setup(
    name='elchemi',
    version='1.0.0rc1',
    packages=find_packages(),
    entry_points={
        'console_scripts': ["elchemi=elchemi.start:start", ]
        },
    install_requires=[ #FIXME: Check parity with requirements.txt
        'numpy',
        'pyqtgraph',
        'dwf',
        'pyqt5', #FIXME: Explore usage of Qt6 (and perhaps move to PySide6)
        'h5py',
        'pylon',
        'click',
        'pyyaml',
        'scipy',
        'matplotlib',
        'pypylon',
        ]
    )