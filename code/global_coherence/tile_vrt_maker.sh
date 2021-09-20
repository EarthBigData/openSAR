#/bin/bash
# Execute this script from inside a downloaded tile directory
# Author: Josef Kellndorfer
# Date:   20-09-2021

TILE=$(basename $(pwd))
echo ${TILE}

SEASONS="winter spring summer fall"
PARS="COH AMP rho tau rmse"

for P in ${PARS}
do
	echo ${P}
	rm -rf optfile
	for S in ${SEASONS}
	do
		echo ${S}
		ls ${TILE}_${S}_*${P}*.tif >> optfile
	done
	gdalbuildvrt -separate -input_file_list optfile ${TILE}_${P}.vrt
	if [ $(which seppo_name_bands.py) ]
	then 
	   	seppo_name_bands.py ${TILE}_${P}.vrt optfile
	fi
done
rm -rf optfile
