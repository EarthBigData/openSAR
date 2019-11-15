#!/usr/bin/env python
'''
SEPPO Tools for Jupyter Notebooks
Author: Josef Kellndorfer  @jkellndorfer

- Syncs notebook with a notebook in <$(dirname $PWD)_executed> or given <output path> (default, can be turned off with -n)
- Clears notebook cells 
- Optionally save notebook in <$(dirname $PWD)_executed> or given <output path>
- can test with -dryrun
'''

import os,sys
import shutil
import filecmp
import subprocess as sp
import datetime

def myargsgarse(a):
	import argparse

	class CustomFormatter(argparse.ArgumentDefaultsHelpFormatter, argparse.RawDescriptionHelpFormatter):
			pass
	thisprog=os.path.basename(a[0])
	p = argparse.ArgumentParser(prog=thisprog,description='SEPPO Jupyter Notebook Clearer',formatter_class=CustomFormatter)
	p.add_argument("-o","--outputpath",required=False, help="if -s, outputpath. Defaults to ../$(dirname notebook)_executed if None. If notebook is in an executed path, the non executed path will be determined by deleting '_executed' from the provided notebook path",action='store',default=None)
	p.add_argument("-overwrite","--overwrite",required=False, help="Overwrite older notebook in executed path",action='store_true')
	p.add_argument("-f","--force",required=False, help="Forces clearing of notebook in non executed path even if -o is not set and notebook in executed path is older.",action='store_true')
	p.add_argument("-dryrun","--DryRun",required=False, help="dry run",action='store_true')
	p.add_argument("notebook",help='Notebookname',action='store')
	args=p.parse_args(a[1:])

	return args

def processing(args):

	if not os.path.exists(args.notebook):
		print(args.notebook, ' not found.')
		sys.exit(1)

	notebook=os.path.abspath(args.notebook)

	# Get the outputpath and executed name
	# First let's check if the notebook is in an executed path:
	if notebook.find('_executed')>-1:
		nb_executed_name=notebook
		nb_name=nb_executed_name.replace('_executed','')
	else:
		if args.outputpath:
			outputpath=args.outputpath
		else:
			outputpath=os.path.dirname(notebook) 
			if outputpath=='': outputpath=os.getcwd()
			outputpath+='_executed'
		# Determine the path to the executed and non executed notebooks
		nb_executed_name=os.path.join(outputpath,os.path.basename(notebook))
		nb_name=notebook

	# Now check if both files exist, and if not make a copy 
	newversion=False
	if not os.path.exists(nb_name):
		if not args.DryRun:
			os.makedirs(os.path.dirname(nb_name),exist_ok=True)
			shutil.copy2(nb_executed_name,nb_name)
		else: 
			print('DRYRUN: cp {} {}'.format(nb_executed_name,nb_name))
		newversion=True
	elif not os.path.exists(nb_executed_name):
		if not args.DryRun:
			os.makedirs(os.path.dirname(nb_executed_name),exist_ok=True)
			shutil.copy2(nb_name,nb_executed_name)
		else: 
			print('DRYRUN: cp {} {}'.format(nb_name,nb_executed_name))
		newversion=True
	else:
		print('Both notebook and executed notebook already exist.')
		# Now we check the versions
		nb_time          = int(os.path.getmtime(notebook))
		nb_executed_time = int(os.path.getmtime(nb_executed_name))
		nb_set_time      = nb_executed_time
		# print(nb_time,nb_executed_time)
		# First, is the notebook in executed newer (standard case)
		if nb_executed_time > nb_time:
			if not args.DryRun:
				shutil.copy2(nb_executed_name,nb_name)
			else: 
				print('DRYRUN: UPDATING NON EXECUTED VERSION: cp {} {}'.format(nb_executed_name,nb_name,))
			newversion=True
		# Second, check if the version in not executed folder is newer
		elif nb_executed_time < nb_time:
			if args.overwrite:
				if not args.DryRun:
					shutil.copy2(nb_name,nb_executed_name)
				else: 
					print('DRYRUN: UPDATING EXECUTED VERSION:cp {} {}'.format(nb_name,nb_executed_name))
				nb_set_time=nb_time
				newversion=True
			else:
				if args.DryRun: print('DRYRUN:')
				print('WARNING: Notebook in executed folder is older, but will not be overwritten. To overwrite set -o')
				if args.force:
					newversion=True
				else:
					print('WARNING: Newer notebook will not be cleared when executed notebook is older and is not overwritten. Force clearing with -f')
		else:
			# Same time for notebooks, check if they are the same size, in which case we assume 
			# that a manual copy was done and we should clear the notebook in the non executed path if forced
			if filecmp.cmp(nb_name,nb_executed_name,shallow=False):
				if args.force:
					newversion=True
					print('Forcing identical notebook to be cleared in notebooks folder')
				else:
					print('Keeping idential notebook untouched.')

		# If we have a newversion determined we will clear it now
		if newversion:
			if args.DryRun: print('DRYRUN: ', end='')		
			try:
				cmd='jupyter nbconvert --ClearOutputPreprocessor.enabled=True --inplace {}'.format(nb_name)
				print(cmd)
				if not args.DryRun:
					sp.call(cmd.split())
					# set the notebook to the previous nb_time so it wouldn't sync later if nothing changes
					# print(nb_time,nb_executed_time,nb_set_time)
					os.utime(nb_name,times=(nb_set_time,nb_set_time))
				return nb_name
			except Exception as e:
				print(e)
				return None
		else:
			print('No updates required.')
			return None

	# # Get last modification times of the notebook and the executed notebook if it exists
	# nb_time=os.path.getmtime(args.notebook)
	# if os.path.exists(nb_executed_name):
	# 	nb_executed_time = os.path.getmtime(nb_executed_name)
	# else:
	# 	nb_executed_time = 0

	# if args.DryRun and not os.path.exists(nb_executed_name):
	# 	identical=True
	# else:
	# 	identical=filecmp.cmp(args.notebook,nb_executed_name,shallow=False)

	# # Do some syncing of the newest version if wanted
	# if not args.no_sync:
	# 	if nb_executed_time > nb_time and not identical:
	# 		print('Overwriting {} with newer version from {}'.format(args.notebook,nb_executed_name))
	# 		if not args.DryRun:
	# 			os.remove(args.notebook)
	# 			shutilfile(nb_executed_name,args.notebook)

	# # Save the notebook to the executed directory
	# if args.save:
	# 	if os.path.exists(nb_executed_name) and (nb_time > nb_executed_time) and not identical:
	# 		if not args.DryRun:
	# 			os.remove(nb_executed_name)
	# 	if nb_time > nb_executed_time:
	# 		print('Syncing newest version of {} with directory {}'.format(os.path.basename(args.notebook),os.path.basename(outputpath)))
	# 		if not args.DryRun:
	# 			shutil.copyfile(args.notebook,nb_executed_name)
	# 			os.utime(nb_executed_name,(nb_time,nb_time))

	# if not nb_time==nb_executed_time and not identical:
	# 	try:
	# 		cmd='jupyter nbconvert --ClearOutputPreprocessor.enabled=True --inplace {}'.format(args.notebook)
	# 		print(cmd)
	# 		if not args.DryRun:
	# 				sp.call(cmd.split())
	# 		# set the notebook to the previous nb_time so it wouldn't sync later if nothing changes
	# 		os.utime(args.notebook,(nb_time,nb_time))
	# 		return args.notebook
	# 	except Exception as e:
	# 		print(e)
	# 		return None
	# else:
	# 	print('{} up to date.'.format(args.notebook))
	# 	return None


def main(a):
	args=myargsgarse(a)
	return processing(args)


if __name__ == '__main__':
	main(sys.argv)