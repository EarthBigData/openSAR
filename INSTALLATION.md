# INSTALLATION INSTRUCTIONS FOR EBD OPEN SOURCE CODE AND TRAINING COURSES

Author: Josef Kellndorfer

email: [support@earthbigdata.com](mailto:support@earthbigdata.com)

## Software and Training Documents on Github

We maintain and distribute our open source software, training materials, and documents (often as Jupyter notebooks)  as **repositories** on the code sharing platform [github.com](http://github.com).

To establish collaboration between colleagues and the Earth Big Data Team you benefit from obtaining a free github account if you don't already have one. Once you have an account name,  email us at: 

[support@earthbigdata.com](mailto:support@earthbigdata.com)

Subject: EBD GITHUB ACCESS, githubusername: YOUR-GITHUB-USERNAME 

We will add you as a collaborator to the code distribution site, which will allow you to access and download specific course material or project specific software. You can participate in the discussion forums and  make your own code contributions to share with colleagues.  

**NOTE: YOU DO NOT NEED THE ACCOUNT TO PROCEED WITH INSTALLATION OF SOFTWARE LISTED HERE. AND WE TYPICALLY SHARE ALL MATERIAL DURING A COURSE AS WELL. BUT UPDATES WILL BE POSTED ON THE GITHUB ACCOUNT openSAR**

### Code management with *git*

If you don't have the code management software **git** installed on your system, we highly recommend to install it. Using **git** and **Github**, you can easily "clone" code repositories to your local computer. Cloning from Github has the benefit that any updates to a repository is easily updated later with the *git pull* command. Or you can contribute to improve the shared repository by pushing your modifications back to Github with *git push*. Download the **git** installer from

[https://git-scm.com/downloads](https://git-scm.com/downloads)

## Python
Many aspects of geospatial data analysis can now be performed within the [**python**](https://www.python.org) programming language and its vast suite of open source contributed modules. Many python bindings exist today in major open source and commercial image processing and geographic information systems like [QGIS](https://qgis.org) and ArcGIS. Learning and using python for all spatial data analysis tasks prepares a trainee well for the future. 

Python is as a scripting/programming language very similar to *Matlab* or *IDL*. As such, users familiar with these languages should readlily be able to read and write python code. Python also has a tight integration with the statistical programming language [R](https://www.r-project.org) via a RPy interface, such that many statistical routines available in R can be called from within a python program. R DataFrames are mimicked in python with the powerful [**pandas**](https://pandas.pydata.org) package. Numerical computations and matrix operations for image analysis is tightly integrated with the [**numpy**](http://www.numpy.org) \(*num*erical *py*thon) package. Raster data stacks are typically loaded with the powerful python implementation of the *Geospatial Data Abstraction Library* [**gdal**](http://gdal.org). NEW 2020: A very powerful new approach to big data processing is with [**xarray**](https://xarray.pydata.org) and [**dask**](https://dask.org). Data visualiation in python has advanced quite fast and parallels the capabilities of plotting of R via the main python plotting package [**matplotlib**](https://matplotlib.org) . The python [**bokeh**](https://bokeh.pydata.org/) and [**holoviews**](http://holoviews.org)packages provides powerful interactive data visualization tools ready for web integration. Scientific data analysis and image processing with python also leans heavily on the scikit packages like image processing with [**scikit-image**](http://scikit-image.org/) or machine learning with [**scikit-learn**](http://scikit-learn.org/).

For a basic introduction to python see [https://www.learnpython.org/](https://www.learnpython.org/)

### Anaconda Python Installation

Obtain and install the free **Miniconda python** distribution. We prefer to work with the latest python 3 version, 64-bit distribution.

The download and installation instructions are available at:

[https://conda.io/miniconda.html](https://conda.io/miniconda.html)

**NOTE FOR WINDOWS INSTALLATION:**
PLEASE AVOID ALL SPACES IN FILENAMES,PATHNAMES, AND USERNAMES! IT's EASIEST TO INSTALL Miniconda at the root level, e.g. *C:\Miniconda3*
When you run the Miniconda installer on Windows, you must make choices on whether to add Miniconda to the system path and registry. We recommend **NOT** doing that (unchecking the two boxes), so that you can keep your system clean, like on Mac and Linux. To work with conda python, you then fire up a **Anaconda Prompt** window, which adds anaconda to the path. From there you can type your conda commands. If you don't do this, you can have python conflict problems.

    Fix for no Anaconda prompt:
    If there is no Anaconda Prompt (or it got lost), create a "New Shortcut" from the desktop. 
    Use the following as the target (Replace with the correct shortcut to where Miniconda is installed):

            %windir%\System32\cmd.exe "/K" C:\miniconda3\Scripts\activate.bat C:\miniconda3

    Also set the correct starting directory, e.g. to the user's home c:\Users\MYUSERNAME 

After *miniconda* is installed, ensure that the environment variables are set correctly to execute "conda" and start a new terminal. In the terminal (e.g. *bash* on Linux/Mac, *Anaconda Prompt* on Windows) type the lines from one of the online or off line instructions:

#### ONLINE Installation from conda-forge 
This is the preferred way if you have a decent internet connection.

Typically you want to install packages from the conda-forge community channel:

    conda config --add channels conda-forge --force
    conda update --yes --all
    conda install --yes nb_conda_kernels
    

#### OFFLINE Alternative installation from a local file channel (e.g. without Internet)
Alternatively, you can also use a custom channel, e.g. from a file if provided:
Important is to execute the second line *conda config --remove channels defaults* to avoid conflicts and if the internet is slow. For later updates one can add the channel back later with *conda config --add channels defaults*

    conda config --add channels PATH-TO-CHANNEL-DIRECTORY --force
    conda config --remove channels defaults 
    conda update --yes --all
    conda install --yes nb_conda_kernels

Examples for PATH-TO-CHANNEL-DIRECTORY-NAME

    Windows: c:\TEMP\ebdchannel
    Linux:   /tmp/ebdchannel

## Earth Big Data LLC's *openSAR* 

To install Earth Big Data's *openSAR* distribution you can clone it with the *[git](https://git-scm.com/downloads) clone* command. 

To clone the *openSAR* distribution with git open a terminal (Linux/Mac) or the **GIT Prompt** (Windows):

*NOTE FOR WINDOWS: Replace "mkdir" with "md"*

    mkdir YOUR-GIT-REPOSOTORY-ROOT-PATH  
    cd YOUR-GIT-REPOSOTORY-ROOT-PATH     
    git clone https://github.com/EarthBigData/openSAR.git
    
Alternatively, if you don't use git or prefer not to clone, retrieve a *zip* archive of the openSAR distribution and install it on your local computer. Get the zip archive from: [https://github.com/EarthBigData/openSAR](https://github.com/EarthBigData/openSAR). Click the green **Clone or Download** button and choose **Download ZIP**. Unzip it in YOUR-GIT-REPOSOTORY-ROOT-PATH. Note that with this donwload method the branch name of the dstribution is part of the unzipped directory name, e.g. openSAR-master. You can rename that to openSAR if you want.
   
## Setup the conda environments

After *anaconda* is installed, ensure that the environment variables are set correctly to execute "conda" and start a new terminal. 

To work with the code and notebooks, you need to establish virtual environments within Anaconda. The advantage of virtual environments is the complete separation of different dependencies for projects. We provide environemnt files to create kernels in the conda environment to work with. You can obtain these files in the **openSAR/notebooks** folder or download directly from github:

- [jhub.yml](https://raw.githubusercontent.com/EarthBigData/openSAR/master/notebooks/jhub.yml)
- [ebd.yml](https://raw.githubusercontent.com/EarthBigData/openSAR/master/notebooks/ebd.yml)

On most browsers you can *Right Click* this link to save the file to your local machine. Make sure you are have the "raw" file and not an html version. Some browsers may add a ".txt" ending, so you may have to rename the file after download to "conda_ebd.yml". Save or move the file into the same directory path from which you will execute the command below. 

### jhub kernel
We run our notebooks in jupyter lab (or notebook if you prefer) started from a separate **jhub** kernel. To install this kernel use the **jhub.yml** conda environment file found in the openSAR/notebooks folder

In your Anaconda/Miniconda aware shell locate the environment files and type:

    conda env create -f jhub.yml

### ebd kernel
For our training programs we establish a conda environment named **ebd**. This will show up in the Jupyter Lab/Notebook (see below) as the **ebd kernel**. To create the **ebd kernel** type:

    conda env create -f ebd.yml


**Alternative installation with file-based channel:**

If you are using a local file channel as the source for the installation files, you can add the path to the file channel directory as the first channels entry in your environment file before your rund the *conda env create* command 
- Create for example a  *conda_ebd.yml* file in a text editor.
- Undder the *channels:* line add the path to the file channel directory preceded with a '-'

Your conda_ebd.yml file should then look some thing like this:

    name: ebd
    channels:
    - c:\TEMP\ebdchannel
    dependencies:
    - python>=3.6
    - nb_conda_kernels
    - bokeh
    - matplotlib
    - pandas
    - gdal
    - ffmpeg
    - scipy
    - scikit-image
    - scikit-learn


Once you have added the path to your local channel run the *conda env create* command from above.

Now you have a new virutal environment built called **ebd**.

## Jupyter Notebook 

To start the Jupyter Lab server working on your local webbrowser,  change to the root directory where you want to keep the notebooks (advanced users can change the default directory for notebooks in a configuration file).
Typically this would be *YOUR-GIT-REPOSOTORY-ROOT-PATH*

    cd <PATH-TO-NOTEBOOK-DIRECTORY>

On a shell commandline prompt (Linux, Mac) or the Anaconda Command Prompt (Windows) enter: 

    conda activate jhub  

Then start the Jupyter Lab server with:

    jupyter lab

This last command starts a local jupyter server on 

[https://localhost:8888](https://localhost:8888) 

The default webbrowser will be openeded and the jupyter lab  browser will be active. From the file menu a notebook can be selected and opened via double-click.

To stop the notebook server, use the CRTL+C keystrokes and answer "y". With this keystroke you will also find at any time the notebook server http address with it's token code which you can use to paste into any webbrowser to get access to the server in case the browswer has been closed. E.g.:

    > [I 22:45:11.589 NotebookApp] Saving file at /github/private/servir_training/notebooks/Kellndorfer_SERVIR_SAR_1.ipynb
    > ^C[I 23:07:29.927 NotebookApp] interrupted
    > Serving notebooks from local directory: /Users/josefk
    > 7 active kernels
    > The Jupyter Notebook is running at:
    > http://localhost:8888/?token=684a07ecd6e6118075463018a2ea2cec918c124c90c71e4f
    > Shutdown this notebook server (y/[n])? No answer for 5s: resuming operation...

As you see, if you don't answer "y" the server keeps running ...


## Other code repositories

Just like the installation for EBD's *openSAR* package, you can install all other packages found on github to YOUR-GIT-REPOSOTORY-ROOT-PATH. For some packages you need to be added as a collaborator to be able to access them.

As an example, the SERVIR SAR Training course material can be obtained as a package as 

    git clone https://github.com/jkellndorfer/servir_training.git
    
OR 
    
Download this zip archive: [https://github.com/jkellndorfer/servir_training/archive/master.zip](https://github.com/jkellndorfer/servir_training/archive/master.zip)




## QGIS

In our courses we will also make etensive use of the open source Quantum GIS software **QGIS Version 3.10+**, preferably the **64 bit** version. If you install QGIS new, choose *Version 3.12*.

To install QGIS please see download and installation instructions at [qgis.org](https://qgis.org/en/site/forusers/download.html)

### Plugins

We will also make use of plugins for QGIS.
Install plugins with the menu in Qgis

    > Plugins > Manage and Install Plugins

- MultiQml

### QGIS Timeseries_SAR Plugin

Earth Big Data's SAR Time series Plotter is an open source tool and  used for the traning courses. To install the plugin, download it and while running QGIS select in the *Plugins -> Manage and Install Plugins* the **Install from Zip** option.

The plugins can be found [here](
https://github.com/EarthBigData/openSAR/blob/master/code/QGIS/).

Select the  

    Linux/MacOS:
    v3/plugins/Timeseries_SAR_v3_Linux_MacOS.zip

    Windows:
    v3/plugins/Timeseries_SAR_v3_Windows.zip


## EXAMPLE DATA SETS FOR TRAINING AND PLAYING

See the [DATA_HOWTO.md](./DATA_HOWTO.md) for download instructions to obtain the training data sets.




        
