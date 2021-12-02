# How to setup a AWS intance as Panel Server

## Launch a ec2 instance

	in the security group enable 
	ssh
	http (port 80)
	https (port 443)

## Install Miniconda

	wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
	chmod 755 Miniconda3-latest-Linux-x86_64.sh
	./Miniconda3-latest-Linux-x86_64.sh
	# Set the conda-forge as primary channel to download packages
	conda config --add channels conda-forge
	# Get mamba as a faster solver
	conda install mamba -y

After installation, log out and back in to restart the shell

## Create a conda environment for our panel app

Create with a editor a file `environment.yml` as follows:

	name: ebdvis
	channels:
	- conda-forge
	dependencies:
	- aiohttp
	- fsspec
	- geoviews
	- imagecodecs
	- ipython
	- holoviews
	- hvplot
	- intake
	- numcodecs
	- xarray
	- zarr

Execute the following command to create the ebdvis kernel
	
	mamba env create -f environment.yml

## Launch the tornado server

Our Notebook got expported as executable code into the file `global_coherence_backscatter_sentinel1.py`. Then we can lauch a *tornado* webserver with the following command:

	sudo /home/ubuntu/miniconda3/envs/ebdvis/bin/panel serve /home/ubuntu/global_coherence_backscatter_sentinel1.py --port 80 --allow-websocket-origin=100.21.17.122