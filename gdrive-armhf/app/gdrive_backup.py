#!/usr/bin/env python
# -*- coding: utf-8 -*-


from drive import GoogleDrive, GDFileCredentials, CodeExchangeException, NoUserIdException, IGDCredentials
import os
import json
import shutil

filter_files = ['.DS_Store']
gids = None

def build_filename(drive_file):
	if drive_file.get('mimeType') == 'application/vnd.google-apps.folder':
		return '%s_%s'%(drive_file.get('title'), drive_file.get('id'))

	fn = drive_file.get('title').split('.')
	if len(fn) > 1:
		fn = '%s_%s.%s'%('.'.join(fn[:-1])[:70], drive_file.get('id'), fn[-1])
	else:
		fn = '%s_%s'%(drive_file.get('title'), drive_file.get('id'))
	return fn

def getPath(gdrive, drive_file):
	rv = build_filename(drive_file)
	while True:
		is_root = False
		first_parent = None
		for p in drive_file.get('parents'):
			if first_parent is None:
				first_parent = p
			if p.get('isRoot'):
				is_root = True
				break
		if is_root or first_parent is None:
			break
		drive_file = gdrive.fileInfo(first_parent.get('id'))
		rv = '%s/%s'%(build_filename(drive_file), rv)
	return rv.encode('utf-8')


def getDirectory(gdrive, source_dir='root', dest_dir='.'):
	global gids
	print 'Checking directory %s (%s)'%(source_dir, dest_dir)
	files = gdrive.folderItems(folder_id=source_dir, search_string='mimeType != \'application/vnd.google-apps.folder\' and trashed = false')
	for f in files:
		filename = '%s/%s'%(dest_dir, build_filename(f))
		if os.path.exists(filename):
			print 'File \"%s\" alredy exists'%filename
		else:
			content = gdrive.download_file_content(f)
			if content:
				fo = open(filename, 'wb')
				fo.write(content)
				fo.close()
				gids[f.get('id')] = filename
			else:
				print '%s: file is empty'%filename
	dirs = gdrive.folderItems(folder_id=source_dir, search_string='mimeType = \'application/vnd.google-apps.folder\' and trashed = false')
	for d in dirs:
		next_dir = '%s/%s'%(dest_dir, build_filename(d))
		if os.path.exists(next_dir):
			print 'Folder \"%s\" alredy exists'%next_dir
		else:
			os.makedirs(next_dir)
			getDirectory(gdrive, source_dir=d.get('id'), dest_dir=next_dir)
			gids[d.get('id')] = next_dir

def inMydisk(drive_file):
	#   shared with me but not added (by len(parents) field), also can look to 'sharedWithMeDate' and 'sharingUser'
	#int(os.environ.get('BACKUP_SHARED', 0))
	return len(drive_file.get('parents')) > 0 or int(os.environ.get('BACKUP_SHARED', 0))

def canDownload(drive_file):
	# skip google apps files and
	#
	return ("google-apps" not in drive_file.get('mimeType')) and inMydisk(drive_file)

def applyChanges(gdrive, changes, start_change_id=None):
	global gids
	#(changes, lastChangeId) = gdrive.retrieve_all_changes(start_change_id=changeId)
	lastChangeId = None
	for c in changes:
		if c.get('id') != start_change_id:
			#print json.dumps(c)
			drive_file = c.get('file')
			if c.get('deleted'):
				if not drive_file:
					path = gids.get(c.get('fileId'))
					if path:
						if os.path.isfile(path):
							os.remove(path)
							print 'File \"%s\" deleted'%path
						elif os.path.isdir(path):
							shutil.rmtree(path)
							print 'Folder \"%s\" deleted'%path
						gids.pop(c.get('fileId'), None)
					continue
				if drive_file.get('mimeType') == 'application/vnd.google-apps.folder':
					dir_path = getPath(gdrive, drive_file)
					print '+Folder \"%s\" deleted'%dir_path
					shutil.rmtree(dir_path)
					gids.pop(drive_file.get('id'), None)
				elif canDownload(drive_file): # skip google apps files
					file_path = getPath(gdrive, drive_file)
					print '+File \"%s\" deleted'%file_path
					os.remove(file_path)
					gids.pop(drive_file.get('id'), None)
			else:
				if drive_file.get('mimeType') == 'application/vnd.google-apps.folder' and not inMydisk(drive_file):
					dir_path = getPath(gdrive, drive_file)
					if os.path.exists(dir_path):
						print 'Folder \"%s\" changed'%dir_path
					else:
						print 'Folder \"%s\" created'%dir_path
						os.makedirs(dir_path)
						gids[drive_file.get('id')] = dir_path
				elif canDownload(drive_file): # skip google apps files
					file_path = getPath(gdrive, drive_file)
					old_path = None
					if not os.path.exists(file_path):
						old_path = gids.get(drive_file.get('id'))
						if old_path:
							print 'File \"%s\" moving from \"%s\"'%(file_path, old_path)
							os.remove(file_path)
						else:
							print 'File \"%s\" creating'%file_path
					else:
						print 'File \"%s\" updating'%file_path
						os.remove(file_path)
					try:
						if '/' in file_path:
							dir_path = '/'.join(file_path.split('/')[:-1])
							if not os.path.exists(dir_path):
								os.makedirs(dir_path)
						gdrive.download_file_to_file(drive_file=drive_file, file_name=file_path, progress_show=False, progress_prefix=drive_file.get('title').encode('utf-8'))
						gids[drive_file.get('id')] = file_path
						'''
						content = gdrive.download_file_content(drive_file)
						if content:
							if '/' in file_path:
								dir_path = '/'.join(file_path.split('/')[:-1])
								if not os.path.exists(dir_path):
									os.makedirs(dir_path)
							fo = open(file_path, 'wb')
							fo.write(content)
							fo.close()
							gids[drive_file.get('id')] = file_path
						'''
					except Exception as e:
						print e
						return lastChangeId or start_change_id or -1
			lastChangeId = c.get('id')
	#return lastChangeId

if __name__=='__main__':
	#script_path = os.path.dirname(os.path.realpath(__file__))
	#os.chdir(script_path)
	#print script_path

	files = os.listdir('.')
	files = filter(lambda x: x not in filter_files, files)

	if len(files) == 0:
		os.makedirs('.gdrive')
		print 'Folder inited need login to gdrive.'
		exit()
	elif '.gdrive' not in files:
		print 'Folder not connected to google drive'
		exit(1)
	elif not os.path.isdir('.gdrive'):
		print '\".gdrive\" is file'
		exit(2)
	elif not os.path.isfile('.gdrive/credentials.json'):
		print 'Need login to gdrive.'
		exit(3)
	elif not os.path.isfile('.gdrive/changeId') and len(files) > 1:
		print 'Folder not empty and client can\'t found lastRevisionId'
		exit(4)

	gids = json.load(open('.gdrive/gids.json')) if os.path.isfile('.gdrive/gids.json') else {}
	changeId = open('.gdrive/changeId').read() if os.path.isfile('.gdrive/changeId') else None
	print 'Change id:', changeId # 2859

	gdrive = GoogleDrive(credentials_manager=GDFileCredentials('.gdrive/credentials.json'))

	use_changes = True
	if changeId or use_changes:
		while True:
			(changes, lastChangeId) = gdrive.retrieve_page_changes(start_change_id=changeId)
			errId = applyChanges(gdrive, changes, start_change_id=changeId)
			if errId: 
				lastChangeId = errId

			if errId != -1:
				fo = open('.gdrive/changeId', 'wb')
				fo.write(lastChangeId)
				fo.close()

				fo = open('.gdrive/gids.json', 'wb')
				fo.write(json.dumps(gids))
				fo.close()

			if errId:
				print 'Error with changeId: %s, exit'%errId
				exit(1)

			if lastChangeId is None or len(changes) < 2:
				break
			changeId = lastChangeId
	else:
		#getDirectory(gdrive=gdrive)
		pass


	'''
	if changeId:
		changeId = driveChanges(gdrive, changeId=changeId)
		print 'Last change id:', changeId
		exit()
	else:
		(changes, changeId) = gdrive.retrieve_all_changes(maxResults=10)
		getDirectory(gdrive=gdrive)
		#changeId = driveChanges(gdrive, changeId=changeId)

	fo = open('.gdrive/changeId', 'wb')
	fo.write(changeId)
	fo.close()

	fo = open('.gdrive/gids.json', 'wb')
	fo.write(json.dumps(gids))
	fo.close()
	'''

