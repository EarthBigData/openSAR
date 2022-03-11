NOTE: PLEASE CHANGE ALL `import gdal` imports to
```
from osgeo import gdal
```
in all python programs and notebooks

# openSAR
[EARTH BIG DATA's](https://earthbigdata.com) open source repository for Synthetic Aperture Radar Image Processing. 

* Installation Instructions
  * Follow these [INSTALLATION](INSTALLATION.md) instructions to set up EBD's *openSAR*
  * To test the installation use the [InstallationTest.ipynb](notebooks/InstallationTest.ipynb) notebook and [testdata.zip](data/testdata.zip) data
  
* notebooks
  * Collection of Jupyter [notebooks](notebooks) around all things SAR

* yaml
  * Collection of environment files to be used with `conda` (see  [INSTALLATION](INSTALLATION.md))

* Data documentations
  * EBD SAR Time Series [Data Guide](documentation/EBD_DataGuide.md)

* Open source code
  * EBD SAR Time Series Plotting Tool as a [QGIS Plugin](code/QGIS)
  * Tools to [manage Jupyter notebooks](code/Jupyter)
  * ebdpy.py library files of useful tools (used e.g. in Jupyter Hub)

* Training
  * [Material and Instructions](TRAINING_MATERIAL.md) for [EBD](https://earthbigdata.com)/[SERVIR](https://www.servirglobal.net/) Training Courses
