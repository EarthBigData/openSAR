# INSATLLATION INSTRUCTIONS FOR EBD OPEN SOURCE CODE AND TRAINING COURSES

Author: Josef Kellndorfer

email: [support@earthbigdata.com](mailto:support@earthbigdata.com)

## Software and Training Documents on Github

We maintain and distribute our open source software, training materials, and documents (often as Jupyter notebooks)  on the code sharing platform [github.com](http://github.com).

To establish collaboration between colleagues and the Earth Big Data Team you benefit from obtaining a free github account if you don't already have one. Once you have an account name,  email us at: 

[support@earthbigdata.com](mailto:support@earthbigdata.com)

Subject: EBD GITHUB ACCESS, githubusername: YOUR-GITHUB-USERNAME 

We will add you as a collaborator to the code distribution site, which will allow you to access and download specific course material or project specific software. You can participate in the discussion forums and  make your own code contributions to share with colleagues.  


## Python
Many aspects of geospatial data analysis can now be performed within the [**python**](https://www.python.org) programming language and its vast suite of open source contributed modules. Many python bindings exist today in major open source and commercial image processing and geographic information systems like [QGIS](https://qgis.org) and ArcGIS. Learning and using python for all spatial data analysis tasks prepares a trainee well for the future. 

Python is as a scripting/programming language very similar to *Matlab* or *IDL*. As such, users familiar with these languages should readlily be able to read and write python code. Python also has a tight integration with the statistical programming language [R](https://www.r-project.org) via a RPy interface, such that many statistical routines available in R can be called from within a python program. R DataFrames are mimicked in python with the powerful [**pandas**](https://pandas.pydata.org) package. Numerical computations and matrix operations for image analysis is tightly integrated with the [**numpy**](http://www.numpy.org) \(*num*erical *py*thon) package. Raster data stacks are typically loaded with the powerful python implementation of the *Geospatial Data Abstraction Library* [**gdal**](http://gdal.org). Data visualiation in python has advanced quite fast and parallels the capabilities of plotting of R via the main python plotting package [**matplotlib**](https://matplotlib.org) . The python [**bokeh**](https://bokeh.pydata.org/) package provides powerful interactive data visualization tools ready for web integration. Scientific data analysis and image processing with python also leans heavily on the scikit packages like image processing with [**scikit-image**](http://scikit-image.org/) or machine learning with [**scikit-learn**](http://scikit-learn.org/).

### Anaconda Python Installation with Miniconda
Obtain and install **miniconda** from the Anaconda python distribution. We prefer to work with the latest python 3 version (3.6), 64-bit distribution.

The downlaod and installation instructions are available at:

[https://conda.io/miniconda.html](https://conda.io/miniconda.html)

**NOTE FOR WINDOWS INSTALLATION:**

When you run the miniconda installer on windows, you must make choices on whether to add miniconda to the system path and registry. We recommend not doing that (unchecking the two boxes), so that you can keep your system clean, like on Mac and Linux. To work with conda python, you then fire up a **Anaconda command prompt** window, which adds miniconda to the path. From there you can type your conda commands.

If you don't do this, you can have python conflict problems.

## Earth Big Data LLC's *openSAR* 

To install Earth Big Data's *openSAR* distribution you can either clone it with the *git clone* command or retrieve the zip archive. Cloning the archive as the benefit that any updates to the package are easily downloaded later with the *git pull* command. Or you can contribute to improve the open source software with git pull requests. 

To clone the *openSAR* distribution:

    mkdir YOUR-GIT-REPOSOTORY-ROOT-PATH   # or create a folder using your system's file manager 
    cd YOUR-GIT-REPOSOTORY-ROOT-PATH      # e.g. /Users/me/github (Linux/Mac)
    git clone git@github.com:EarthBigData/openSAR.git
    
To retrieve a *zip* archive of the openSAR distribution and install it on your local computer:

    mkdir YOUR-GIT-REPOSOTORY-ROOT-PATH   # or create a folder using your system's file manager 

   GET THE ZIP ARHCIVE FROM [https://github.com/EarthBigData/openSAR/archive/master.zip](https://github.com/EarthBigData/openSAR/archive/master.zip). Unzip it in YOUR-GIT-REPOSOTORY-ROOT-PATH. Note that with this donwload method the branch name of the dstribution is part of the unzipped directory name, e.g. openSAR-master. You can rename that to openSAR if you want.
   

## Other code repositories

Just like the installation for EBD's *openSAR* package, you can install all other packages found on github to YOUR-GIT-REPOSOTORY-ROOT-PATH. For some packages you need to be added as a collaborator to be able to access them.

As an example, the 2018 SERVIR SAR Training course material can be obtained as a package as 

    > git clone git@github.com:jkellndorfer/servir_training.git
    
    OR 
    
    [https://github.com/jkellndorfer/servir_training/archive/master.zip](https://github.com/jkellndorfer/servir_training/archive/master.zip)

## Setup the conda environment *ebd*

To work with the code and notebooks, you need to establish virtual environments within Anaconda. THe advantage of virtual environments is the complete separation of different dependencies for projects. For example, for our training programs we establish a conda environment named **ebd**. This will show up in the Jupyeter Notebook (see below( as the **Kernel ebd**.

To create the *ebd* environment use the [conda_ebd.yml](ttps://github.com/EarthBigData/openSAR/tree/master/training/conda_ebd.yml) file available at our github repository at [https://github.com/EarthBigData/openSAR/tree/master/training](https://github.com/EarthBigData/openSAR/tree/master/training). On most browsers you can *Right Click*  this link to save the file to your local machine. Save or move the file into the same directory path from which you will execute the command below. 

After *miniconda* is installed, ensure that the environment variables are set correctly to execute "conda" and start a new terminal (Anaconda Command Prompt in WINDOWS). 
    
In a new terminal (Anaconda Terminal on Windows) type:

    > conda env create -f conda_ebd.yml 

## Jupyter Notebook 

To start the Jupyter notebook server working on your local webbrowser,  change to the root directory where you want to keep the notebooks.
Typically this would be *YOUR-GIT-REPOSOTORY-ROOT-PATH*

    > cd <PATH-TO-NOTEBOOK-DIRECTORY>

On a shell commandline prompt (Linux, Mac) or the Anaconda Command Prompt (Windows) enter: 

    > source activate root  # Linux/Mac
    > activate root         # Windows

Then start the notebook server with:

    > jupyter notebook

This last command starts a local jupyter server on 

[https://localhost.com](https://localhost:8888) 

The default webbrowser will be openeded and the jupyter notebook browser will be active. From the file menu a notebook can be selected and opened via double-click.

To stop the notebook server, use the CRTL+C keystrokes and answer "y". With this keystroke you will also find at any time the notebook server http address with it's token code which you can use to paste into any webbrowser to get access to the server in case the browswer has been closed. E.g.:

    > [I 22:45:11.589 NotebookApp] Saving file at /github/private/servir_training/notebooks/Kellndorfer_SERVIR_SAR_1.ipynb
    > ^C[I 23:07:29.927 NotebookApp] interrupted
    > Serving notebooks from local directory: /Users/josefk
    > 7 active kernels
    > The Jupyter Notebook is running at:
    > http://localhost:8888/?token=684a07ecd6e6118075463018a2ea2cec918c124c90c71e4f
    > Shutdown this notebook server (y/[n])? No answer for 5s: resuming operation...

As you see, if you don't answer "y" the server keeps running ...


## QGIS

During the course we will also make etensive use of the open source Quantum GIS software **QGIS Version 2.18**, preferably the **64 bit** version. If you install QGIS new, choose *Version 2.18*.

To install QGIS please see download and installation instructions at [qgis.org](https://qgis.org/en/site/forusers/download.html)

### Plugins

We will also make use of plugins for QGIS.
Install plugins with the menu in Qgis

    > Plugins > Manage and Install Plugins

- MultiQml

### Timeseries_SAR Plugin

A plugin for visualization of SAR Time series data is provided for the traning course. To install the plugin, copy the Windows or Linux version to the QGIS python plugin directory

Linux:
 
     > cd ~/.qgis2/python/plugins 
     > unzip Timeseries_SAR_linux.zip 
 
Windows:

    Locate the .qgis2 path and unzip the Plugin into the python/plugins subdirectory


## EXAMPLE DATA SETS FOR TRAINING AND PLAYING

See the [DATA_HOWTO.md](./DATA_HOWTO.md) for download instructions to obtain the training data sets.




        
