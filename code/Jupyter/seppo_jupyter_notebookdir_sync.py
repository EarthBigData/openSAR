#!/usr/bin/env python
'''
SEPPO Tools for Jupyter Notebooks
Author: Josef Kellndorfer @jkellndorfer

- Sync all notebooks and in the nb_directory with   
  <nb_directory>_executed directory
- Clears all notebooks
- Syncs to github
'''

import os,sys
import seppo_jupyter_clear_notebook
import subprocess as sp
import shutil
from pathlib import Path
import datetime


def myargsgarse(a):
	import argparse

	class CustomFormatter(argparse.ArgumentDefaultsHelpFormatter, argparse.RawDescriptionHelpFormatter):
			pass
	thisprog=os.path.basename(a[0])
	epilog='\
	\nSyncs notebooks between a notebook directory and an exectued directory (will be created if it does not exists. Clears the notebooks in the not executed directory and prepares for syncing with github which can be turned on.'
	p = argparse.ArgumentParser(prog=thisprog,epilog=epilog, description='SEPPO Notebook sync and git upload',formatter_class=CustomFormatter)

	p.add_argument("-dryrun","--DryRun",required=False, help="dry run",action='store_true')
	p.add_argument("-gs","--GitSync",required=False, help="Syncing to github",action='store_true')
	p.add_argument("-lo","--list_only",required=False, help="Only list all files and quit.",action='store_true')
	p.add_argument("-nc","--noClearing",required=False, help="Do not clear the notebooks in the non executed folder. Just sync.",action='store_true')
	p.add_argument("-overwrite","--overwrite",required=False, help="Overwrite older notebook in executed path",action='store_true')
	p.add_argument("-f","--force",required=False, help="Forces clearing of notebook in non executed path even if -o is not set and notebook in executed path is older.",action='store_true')
	p.add_argument("-v","--verbose",required=False, help="Verbose output",action='store_true',default=False)
	p.add_argument("notebook_directory",help='Notebook Directory (preferablythe executed one)',action='store')
	args=p.parse_args(a[1:])

	return args

def processing(args):

	valid_endings=['.ipynb','.md']

	# if args.notebook_directory=='.': 
	# 	notebook_directory=os.getcwd()
	# else:
	# 	notebook_directory=args.notebook_directory

	# notebook_directory=notebook_directory.rstrip('/').rstrip('\\')

	notebook_directory=Path(args.notebook_directory).absolute().as_posix()
	if not os.path.exists(notebook_directory):
		print('Invalid path:\n',notebook_directory)
		sys.exit(1)

	if notebook_directory.endswith('_executed') or notebook_directory.find('_executed/')>-1:
		notebook_directory_executed=notebook_directory
		notebook_directory=notebook_directory.replace('_executed','')
	else:
		notebook_directory_executed=notebook_directory+'_executed'

	print('NOTEBOOKS FOLDER:          ',notebook_directory)
	print('NOTEBOOKS FOLDER EXECUTED: ',notebook_directory_executed)
	# Create the directories if they don't exist
	if not args.DryRun:
		os.makedirs(notebook_directory_executed,exist_ok=True)
		os.makedirs(notebook_directory,exist_ok=True)

	syncfiles=[]
	syncfiles_listing=[]
	nb_dir=Path(notebook_directory)
	for i in valid_endings:
		syncfiles_listing+=[x for x in nb_dir.rglob('*'+i) if x.as_posix().find('.ipynb_checkpoints')==-1]
		syncfiles+=[x.as_posix().replace(notebook_directory,'').lstrip('/') for x in nb_dir.rglob('*'+i) if x.as_posix().find('.ipynb_checkpoints')==-1]

	syncfiles_executed=[]
	syncfiles_executed_listing=[]
	nb_dir=Path(notebook_directory_executed)
	for i in valid_endings:
		syncfiles_executed_listing+=[x for x in nb_dir.rglob('*'+i) if x.as_posix().find('.ipynb_checkpoints')==-1]
		syncfiles_executed+=[x.as_posix().replace(notebook_directory_executed,'').lstrip('/') for x in nb_dir.rglob('*'+i) if x.as_posix().find('.ipynb_checkpoints')==-1]

	# Find the missing notebooks 
	missing_in_notebooks=set(syncfiles_executed) -set(syncfiles)
	missing_in_notebooks_executed=set(syncfiles) -set(syncfiles_executed)

	if args.list_only:
		print('**** NOTEBOOK FOLDERS:')
		for f in syncfiles_listing: print('{:12d} {} {}'.format(f.stat().st_size,datetime.datetime.fromtimestamp(f.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S'),f.as_posix().replace(notebook_directory,'').lstrip('/')))
		print('**** NOTEBOOK EXECUTED FOLDERS:')
		for f in syncfiles_executed_listing: print('{:12d} {} {}'.format(f.stat().st_size,datetime.datetime.fromtimestamp(f.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S'),f.as_posix().replace(notebook_directory_executed,'').lstrip('/')))
		print('**** MISSING IN NOTEBOOK FOLDERS:')
		for f in missing_in_notebooks: print(f)
		print('**** MISSING IN NOTEBOOK EXECUTED FOLDERS:')
		for f in missing_in_notebooks_executed: print(f)
		sys.exit(1)

	# copy missing files between the directories
	for i in missing_in_notebooks:
		src=os.path.join(notebook_directory_executed,i)
		dst=os.path.join(notebook_directory,i)
		if not args.DryRun:
			print('Copy from executed to not executed notebook directory:',i)
			os.makedirs(os.path.dirname(os.path.join(notebook_directory,i)),exist_ok=True)
			shutil.copy2(src,dst)
		else:
			# print('DRYRUN: cp {} {}'.format(src,dst))
			print('DRYRUN: Copy from executed to not executed notebook directory:',i)

	for i in missing_in_notebooks_executed:
		dst=os.path.join(notebook_directory_executed,i)
		src=os.path.join(notebook_directory,i)
		if not args.DryRun:
			print('Copy from not executed to executed notebook directory:',i)
			os.makedirs(os.path.dirname(os.path.join(notebook_directory_executed,i)),exist_ok=True)
			shutil.copy2(src,dst)
		else:
			print('DRYRUN: Copy from not executed to executed notebook directory:',i)

	# Now let's look at all the notebook files on the notebooks directory
	nb_files=[]
	nb_dir=Path(notebook_directory)
	for i in valid_endings:
		nb_files+=[x.as_posix() for x in nb_dir.rglob('*'+i) if x.as_posix().find('.ipynb_checkpoints')==-1 and x.as_posix().lower().endswith('.ipynb')]

	new_versions=[]
	if not args.noClearing:
		for i in nb_files:
			print('****** {}'.format(i))
			outputpath=os.path.dirname(i.replace(notebook_directory,notebook_directory_executed))
			myargs=['seppo_jupyter_clear_notebook.py',i,'-o',outputpath]
			if args.overwrite: myargs.append('--overwrite')
			if args.force: myargs.append('--force')
			if args.DryRun:
				myargs.append('--DryRun')
			if args.verbose:
				print(' '.join(myargs))
			new_version=seppo_jupyter_clear_notebook.main(myargs)
			if new_version:
					new_versions.append(new_version)


	if new_versions and args.GitSync:
		cwd=os.getcwd()
		os.chdir(notebook_directory)

		# First do a pull of the latest versions to see if there are conflicts
		cmd='git pull -q'
		print(cmd)
		sp.call(cmd.split())

		print('Adding all {} files for commit.'.format(valid_endings))
		for i in syncfiles:
			cmd='git add '+i
			sp.call(cmd.split())

		if len(sys.argv)==3:
			comment=sys.argv[2]
		else:
			comment="automatic commit"

		cmd='git commit -a -m "{}"'.format(comment)
		print(cmd)
		os.system(cmd)

		cmd=('git push')
		print(cmd)
		os.system(cmd)
	else:
		print('Number of new versions:',len(new_versions))

def main(a):
	args=myargsgarse(a)
	return processing(args)

if __name__ == '__main__':
	main(sys.argv)
