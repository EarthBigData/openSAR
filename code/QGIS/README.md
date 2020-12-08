v2 is for QGIS 2.x

v3 is for QGIS 3.x (developed with QT 5.13 and QGIS 3.8)


2020-12-07:

For QGIS 3.16 on MacOS Catalina and Big Sur you might have to upgrade Pillow:

$ cd /Applications/QGIS.app/Contents/MacOS/bin

$ ./pip3 install pillow -U
Collecting pillow
  Downloading Pillow-8.0.1-cp37-cp37m-macosx_10_10_x86_64.whl (2.2 MB)
     |████████████████████████████████| 2.2 MB 2.7 MB/s
Installing collected packages: pillow
  Attempting uninstall: pillow
    Found existing installation: Pillow 7.2.0
    Uninstalling Pillow-7.2.0:
      Successfully uninstalled Pillow-7.2.0
Successfully installed pillow-8.0.1