#!/usr/bin/env python
# -*- coding: utf-8 -*-

import httplib2
import pprint
import urllib2
import io

from apiclient.discovery import build
from apiclient.http import MediaFileUpload, MediaInMemoryUpload, MediaIoBaseDownload
from oauth2client.client import OAuth2WebServerFlow
from oauth2client.client import OAuth2Credentials
from apiclient import errors
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
from oauth2client.client import AccessTokenRefreshError

try:
	from pymongo import MongoClient
except ImportError:
	pass

# API: https://developers.google.com/drive/v2/reference/

# Path to client_secrets.json which should contain a JSON document such as:
#   {
#     "web": {
#       "client_id": "[[YOUR_CLIENT_ID]]",
#       "client_secret": "[[YOUR_CLIENT_SECRET]]",
#       "redirect_uris": [],
#       "auth_uri": "https://accounts.google.com/o/oauth2/auth",
#       "token_uri": "https://accounts.google.com/o/oauth2/token"
#     }
#   }
#CLIENTSECRETS_LOCATION = 'secrets.json'
CLIENTSECRETS_LOCATION = '/app/gdrive_secrets.json'
SCOPES = [
		'https://www.googleapis.com/auth/drive',
		'https://www.googleapis.com/auth/userinfo.email',
		'https://www.googleapis.com/auth/userinfo.profile',
		# Add other requested scopes.
]

class GetCredentialsException(Exception):
	"""Error raised when an error occurred while retrieving credentials.

	Attributes:
		authorization_url: Authorization URL to redirect the user to in order to
				               request offline access.
	"""

	def __init__(self, authorization_url):
		"""Construct a GetCredentialsException."""
		self.authorization_url = authorization_url

class RefreshCredentialsException(Exception):
	"""Error raised when a refresh access token refresh has failed."""

class CodeExchangeException(GetCredentialsException):
	"""Error raised when a code exchange has failed."""

class NoUserIdException(Exception):
	"""Error raised when no user ID could be retrieved."""


class IGDCredentials(object):
	"""docstring for IGDCredentials"""
	def __init__(self):
		super(IGDCredentials, self).__init__()

	def load(self):
		"""loads JSON credentials"""
		raise NotImplementedError('Interface method not defined at class %s'%self.__class__.__name__)

	def save(self, credentials):
		"""store JSON credentials"""
		raise NotImplementedError('Interface method not defined at class %s'%self.__class__.__name__)
		
class GDFileCredentials(object):
	"""docstring for IGDCredentials"""
	def __init__(self, filename='gdrive_credentials.json'):
		super(GDFileCredentials, self).__init__()
		self._filename = filename

	def load(self):
		"""loads JSON credentials"""
		try:
			return open(self._filename).read()
		except IOError, e:
			return None

	def save(self, credentials):
		"""store JSON credentials"""
		f = open(self._filename, 'w')
		f.write(credentials)
		f.close()


class GDMongoCredentials(IGDCredentials):
	"""docstring for GDMongoCredentials"""
	def __init__(self, db):
		super(GDMongoCredentials, self).__init__()
		self._db = db

	def _getCredentials(self):
		return self._db.settings.find_one({ 'gdrive_credentials': { "$exists": True } })

	def load(self):
		"""loads JSON credentials"""
		auth =  self._getCredentials()
		if auth:
			return auth.get('gdrive_credentials')
		return None

	def save(self, credentials):
		"""store JSON credentials"""
		auth =  self._getCredentials()
		if auth:
			auth['gdrive_credentials'] = credentials
			self._db.settings.save(auth)
		else:
			auth = { 'gdrive_credentials': credentials }
			self._db.settings.insert(auth)

		

class GoogleDrive(object):
	"""docstring for GoogleDrive"""
	def __init__(self, db=None, gdrive_redirect_uri=None, credentials_manager=None):
		super(GoogleDrive, self).__init__()
		self._db = db
		self._credentials = None
		self._drive_service = None
		self.gdrive_redirect_uri = gdrive_redirect_uri
		if credentials_manager is None:
			self._credentials_manager = IGDCredentials()
		else:
			self._credentials_manager = credentials_manager

	def getDB(self):
		if self._db is None:
			db_name = self._mongo_connection.split('/')[-1]
			self._db = MongoClient(self._mongo_connection)[db_name]
		return self._db

	def exchange_code(self, authorization_code):
		"""Exchange an authorization code for OAuth 2.0 credentials.

		Args:
			authorization_code: Authorization code to exchange for OAuth 2.0
			credentials.
		Returns:
			oauth2client.client.OAuth2Credentials instance.
		Raises:
			CodeExchangeException: an error occurred.
		"""
		if authorization_code is None or self.gdrive_redirect_uri is None:
			raise CodeExchangeException(None)
		
		flow = flow_from_clientsecrets(CLIENTSECRETS_LOCATION, ' '.join(SCOPES))
		flow.redirect_uri = self.gdrive_redirect_uri
		
		#flow = OAuth2WebServerFlow(CLIENT_ID, CLIENT_SECRET, SCOPES, self.gdrive_redirect_uri)
		try:
			credentials = flow.step2_exchange(authorization_code)
			return credentials
		except FlowExchangeError, error:
			raise CodeExchangeException(None)

	def get_authorization_url(self):
		"""Retrieve the authorization URL.

		Args:
			email_address: User's e-mail address.
			state: State for the authorization URL.
		Returns:
			Authorization URL to redirect the user to.
		"""
		
		flow = flow_from_clientsecrets(CLIENTSECRETS_LOCATION, ' '.join(SCOPES))
		flow.redirect_uri = self.gdrive_redirect_uri
		flow.params['access_type'] = 'offline'
		flow.params['approval_prompt'] = 'force'
		#flow.params['user_id'] = email_address
		#flow.params['state'] = state
		return flow.step1_get_authorize_url()

	def getCredentials(self, authorization_code=None):
		if self._credentials is None:
			#db_settings = self.getDB().settings
			#auth = db_settings.find_one({ 'gdrive_credentials': { "$exists": True } })
			auth = self._credentials_manager.load()
			if auth is not None:
				self._credentials = OAuth2Credentials.new_from_json(auth)
			else:
				auth = {}
			if self._credentials is not None and self._credentials.access_token_expired:
				try:
					self._credentials.refresh(httplib2.Http())
				except AccessTokenRefreshError, e:
					raise RefreshCredentialsException()
				#auth['gdrive_credentials'] = self._credentials.to_json()
				#db_settings.save(auth)
				self._credentials_manager.save(self._credentials.to_json())
			if self._credentials is None:
				try:
					self._credentials = self.exchange_code(authorization_code)
				except CodeExchangeException, error:
					error.authorization_url = self.get_authorization_url()
					raise error

				#auth['gdrive_credentials'] = self._credentials.to_json()
				#db_settings.save(auth)
				self._credentials_manager.save(self._credentials.to_json())
			#elif self._credentials.refresh_token is not None:
			#	auth['credentials'] = self._credentials.to_json()
			#	db_settings.save(auth)
		'''
		if self._credentials.access_token_expired:
			db_settings = self.getDB().settings
			auth = db_settings.find_one({ 'gdrive_credentials': { "$exists": True } })
			if auth is None:
				auth = {}
			self._credentials.refresh(httplib2.Http())
			auth['gdrive_credentials'] = self._credentials.to_json()
			db_settings.save(auth)
		'''
		return self._credentials

	def getUserInfo(self):
		"""Send a request to the UserInfo API to retrieve the user's information.

		Args:
			credentials: oauth2client.client.OAuth2Credentials instance to authorize the
				         request.
		Returns:
			User information as a dict.
		"""
		user_info_service = build(
				serviceName='oauth2', version='v2',
				http=self.getCredentials().authorize(httplib2.Http()))
		user_info = None
		try:
			user_info = user_info_service.userinfo().get().execute()
		except errors.HttpError, e:
			pass
		except AccessTokenRefreshError, e:
			raise RefreshCredentialsException()
		if user_info and user_info.get('id'):
			return user_info
		else:
			raise NoUserIdException()

	def getDriveService(self):
		if self._drive_service is None:
			http = httplib2.Http()
			http = self.getCredentials().authorize(http)
			self._drive_service = build('drive', 'v2', http=http)
		return self._drive_service

	def uploadFromMemory(self, buff, title=None, mimetype=None, parent_id=None):
		#media_body = MediaFileUpload(file_path_or_url, mimetype='text/plain', resumable=True)
		#media_body = MediaIoBaseUpload(open(file_path_or_url), mimetype='image/plain', resumable=True)
		#im = cStringIO.StringIO(page.read())
		#media_body = MediaIoBaseUpload(im, mimetype=page.headers['Content-Type'], resumable=True)
		if buff is None and mimetype == 'application/vnd.google-apps.folder':
			media_body = None
		else:
			media_body = MediaInMemoryUpload(buff, mimetype=mimetype, resumable=True)
		body = {
			'title': title,
			'mimeType': mimetype
		}
		# Set the parent folder.
		if parent_id:
			body['parents'] = [{'id': parent_id}]

		rv = None
		try:
			rv = self.getDriveService().files().insert(body=body, media_body=media_body).execute()
		except errors.HttpError, error:
			pass
		if rv and buff:
			self.addSharePermision(rv.get('id'))
		return rv

		'''
	def uploadFromStream(self, stream, title=None, mimetype=None, parent_id=None):
		if stream is None and mimetype == 'application/vnd.google-apps.folder':
			media_body = None
		else:
			media_body = MediaIoBaseUpload(stream, mimetype=mimetype, resumable=True)
		body = {
			'title': title,
			'mimeType': mimetype
		}
		# Set the parent folder.
		if parent_id:
			body['parents'] = [{'id': parent_id}]

		rv = None
		try:
			rv = self.getDriveService().files().insert(body=body, media_body=media_body).execute()
		except errors.HttpError, error:
			pass
		if rv and stream:
			self.addSharePermision(rv.get('id'))
		return rv
		'''

	def upload(self, url):
		(content, content_type, title) = self.URLcontent(url)
		return self.uploadFromMemory(content, mimetype=content_type, title=title)

	def fileUpdate(self, file_id, content, mimetype=None, new_revision=True):
		try:
			file_info = self.getDriveService().files().get(fileId=file_id).execute()
			if not mimetype:
				mimetype = file_info.get('mimeType')

			media_body = MediaInMemoryUpload(content, mimetype=mimetype, resumable=True)

			updated_file = self.getDriveService().files().update(fileId=file_id, newRevision=new_revision, media_body=media_body).execute()
			return updated_file
		except errors.HttpError, error:
			return None

	def URLcontent(self, url):
		req = urllib2.Request(url)
		page = urllib2.urlopen(req)
		title = url.split('/')[-1]
		title = title.split('?')[0]
		title = urllib2.unquote(title.encode('utf-8')).decode('utf-8')
		return (page.read(), page.headers['Content-Type'], title)


	def download(self, file_id):
		try:
			file_info = self.getDriveService().files().get(fileId=file_id).execute()
		except errors.HttpError, error:
			#print 'An error occurred: %s' % error
			return None
		download_url = file_info.get('downloadUrl')
		print download_url
		exit()
		if download_url:
			resp, content = self.getDriveService()._http.request(download_url)
			if resp.status == 200:
				return content
			else:
				#print 'An error occurred: %s' % resp
				return None
		else:
			# The file doesn't have any content stored on Drive.
			return None

	def addSharePermision(self, file_id):
		new_permission = {
			#'value': value,
			#'id': 'anyoneWithLink',
			'type': 'anyone',
			'withLink': True,
			'role': 'reader'
		}
		try:
			return self.getDriveService().permissions().insert(
					fileId=file_id, body=new_permission).execute()
		except errors.HttpError, error:
			#print 'An error occurred: %s' % error
			pass
		return None

	def getPermissions(self, file_id):
		try:
			return self.getDriveService().permissions().list(fileId=file_id).execute()
		except errors.HttpError, error:
			#print 'An error occurred: %s' % error
			pass
		return None

	def driveAbout(self):
		try:
			return self.getDriveService().about().get().execute()
		except errors.HttpError as error:
			#print 'An error occurred: %s' % error
			pass
		except AccessTokenRefreshError, err:
			raise RefreshCredentialsException()
		return None

	def allFiles_page(self, search_string=None, page_token=None, ids_only=True):
		try:
			param = {}
			if page_token:
				param['pageToken'] = page_token
			if search_string:
				param['q'] = search_string
			if maxResults:
				param['maxResults'] = maxResults
			children = self.getDriveService().files().list(**param).execute()

			if ids_only:
				rv = map(lambda el: el.get('id'), children['items'])
			else:
				rv = []
				for child in children.get('items', []):
					rv.append(self.fileInfo(child['id']))

			return (rv, children.get('nextPageToken'))
		except errors.HttpError, error:
			pass
		return ([], None)

	def retrieveAllFiles(self, search_string=None, ids_only=True):
		page_token = None
		rv = []
		while True:
			(tmp, page_token) = self.allFiles_page(search_string=search_string, page_token=page_token, ids_only=ids_only)
			rv.extend(tmp)
			if not page_token:
				break
		return rv

	def folderItems_page(self, folder_id='root', search_string=None, page_token=None, maxResults=None, ids_only=False):
		try:
			param = {}
			if page_token:
				param['pageToken'] = page_token
			if search_string:
				param['q'] = search_string
			if maxResults:
				param['maxResults'] = maxResults
			children = self.getDriveService().children().list(folderId=folder_id, **param).execute()

			if ids_only:
				rv = map(lambda el: el.get('id'), children['items'])
			else:
				rv = []
				for child in children.get('items', []):
					rv.append(self.fileInfo(child['id']))

			return (rv, children.get('nextPageToken'))
		except errors.HttpError, error:
			pass
		return ([], None)

	def folderItems(self, folder_id='root', search_string=None, ids_only=False):
		page_token = None
		rv = []
		while True:
			(tmp, page_token) = self.folderItems_page(folder_id=folder_id, search_string=search_string, page_token=page_token, ids_only=ids_only)
			rv.extend(tmp)
			if not page_token:
				break
		return rv

	def fileInfo(self, file_id):
		rv = None
		try:
			rv = self.getDriveService().files().get(fileId=file_id).execute()
		except errors.HttpError, error:
			pass
		return rv

	def download_file_content(self, drive_file):
		"""
			Download a file's content.
		"""
		download_url = drive_file.get('downloadUrl')
		if download_url:
			resp, content = self.getDriveService()._http.request(download_url)
			if resp.status == 200:
				return content
			else:
				return None
		else:
			# The file doesn't have any content stored on Drive.
			return None

	def download_file_to_file(self, drive_file, file_name, progress_show=True, progress_prefix=''):
		if "google-apps" in drive_file.get('mimeType'):
			# skip google files
			return
		request = self.getDriveService().files().get_media(fileId=drive_file.get('id'))
		fh = io.FileIO(file_name, 'wb')
		downloader = MediaIoBaseDownload(fh, request)
		done = False
		while done is False:
			status, done = downloader.next_chunk()
			if progress_show:
				print "\r%s %.2f%%."%(progress_prefix, (status.progress() * 100)),
		if progress_show:
			print

	def retrieve_page_changes(self, start_change_id=None, maxResults=None):
		try:
			param = {}
			if start_change_id:
				param['startChangeId'] = start_change_id
			if maxResults:
				param['maxResults'] = maxResults
			changes = self.getDriveService().changes().list(**param).execute()
			largestChangeId = changes.get('largestChangeId')

			items = changes['items']
			largestChangeId = start_change_id if len(items) == 0 else items[-1].get('id')

			return (items, largestChangeId)
		except errors.HttpError, error:
			pass
		return ([], None)

	def retrieve_all_changes(self, start_change_id=None, maxResults=None):
		result = []
		page_token = None
		largestChangeId = None
		while True:
			try:
				param = {}
				if start_change_id:
					param['startChangeId'] = start_change_id
				if page_token:
					param['pageToken'] = page_token
				if maxResults:
					param['maxResults'] = maxResults
				changes = self.getDriveService().changes().list(**param).execute()
				largestChangeId = changes.get('largestChangeId')

				result.extend(changes['items'])
				page_token = changes.get('nextPageToken')
				if not page_token:
					break
			except errors.HttpError, error:
				print 'An error occurred: %s' % error
				break
		return (result, largestChangeId)

	def fileMove(self, file_id, dest_folder):
		try:
			new_parent = {'id': dest_folder}
			info = self.getDriveService().parents().insert(fileId=file_id, body=new_parent).execute()
			parents = self.getDriveService().parents().list(fileId=file_id).execute()
			for parent in parents['items']:
				if parent.get('id') != dest_folder:
					self.getDriveService().parents().delete(fileId=file_id, parentId=parent.get('id')).execute()
			return info
	 	except errors.HttpError, error:
	 		return None



def repair_permissions(gdrive, db, limit=10):
	for problem_f in db.problem.find({'repair_error': {'$exists': False}}).limit(limit):
		permissions = gdrive.getPermissions(problem_f.get('gdid'))
		shared = False
		if permissions:
			for p in permissions.get('items'):
				if p.get('kind') == 'drive#permission' and p.get('type') == 'anyone' and p.get('withLink') and p.get('role') == 'reader':
					response = urllib2.urlopen('http://gdrive-cdn.herokuapp.com/get/%s/1270422367602.jpg'%problem_f.get('gdid'))
					print response.info().getheader('Content-Type').lower(),
					if 'html' not in response.info().getheader('Content-Type').lower():
						print problem_f.get('gdid'), 'OK'
						db.problem.remove(problem_f)
					else:
						problem_f['repair_error'] = True
						db.problem.save(problem_f)
						print problem_f.get('gdid'), 'FAIL'
					shared = True
					break
		if not shared:
			gdrive.addSharePermision(problem_f.get('gdid'))
			db.problem.remove(problem_f)
			print problem_f.get('gdid'), 'REPAIRED'


def move_to_folders(gdrive, db):
	#     "md5": "67b8a8acb6e08d6187217441d85127b2",
	import time, json

	#(files, next_token) = gdrive.folderItems_page(search_string='mimeType != \'application/vnd.google-apps.folder\' and trashed = false and (mimeType = \'image/jpeg\' or mimeType = \'image/jpg\' or mimeType = \'image/png\' or mimeType = \'image/gif\')', maxResults=2)
	(files, next_token) = gdrive.folderItems_page(search_string='mimeType != \'application/vnd.google-apps.folder\' and trashed = false and (mimeType = \'image/jpeg\' or mimeType = \'image/jpg\' or mimeType = \'image/png\' or mimeType = \'image/gif\')')
	folders = {}
	counter = 0
	for f in files:
		if f and f.has_key('createdDate'):
			tm = int(time.mktime(time.strptime(f.get('createdDate')[:19], '%Y-%m-%dT%H:%M:%S')))
			dt_str = time.strftime("%Y_%m_%d", time.gmtime(tm))

			if not folders.has_key(dt_str):
				# search folder
				tmp = gdrive.folderItems(search_string='mimeType = \'application/vnd.google-apps.folder\' and title contains \'%s\' and trashed = false'%dt_str)
				if len(tmp) > 0:
					folders[dt_str] = tmp[0].get('id')
				else:
					# create
					tmp = gdrive.uploadFromMemory(buff=None, title=dt_str, mimetype='application/vnd.google-apps.folder')
					if tmp:
						folders[dt_str] = tmp.get('id')
					else:
						print 'Can\'t create folder %s'%dt_str
						exit()
			#file_info = gdrive.filePatch(f.get('id'), addParents=folders[dt_str], removeParents=f.get('parents')[0].get('id'))
			file_info = gdrive.fileMove(f.get('id'), folders[dt_str])
			print f.get('id'), '\"%s\" moved to \"%s\"'%(f.get('title'), dt_str)
		counter += 1
	return counter



if __name__=='__main__':
	import json

	from cdn import db
	'''
		For create new credentials file you should go to 'cdn.py' and uncomment line:
			#gdrive = GoogleDrive(credentials_manager=GDFileCredentials('gdrive_credentials_tmp.json'))
		next run web server:
			venv/bin/python cdn.py
		on your browser go to:
			http://localhost:5000/auth
		and connect your google drive account
		rename 'gdrive_credentials_tmp.json' to 'credentials.json' and copy to '.gdrive' folder
	'''
	gdrive = GoogleDrive(credentials_manager=GDMongoCredentials(db))
	#gdrive = GoogleDrive(credentials_manager=GDFileCredentials('gdrive_credentials_masakaki02.json'))
	#gdrive = GoogleDrive(credentials_manager=GDFileCredentials('gdrive_credentials_masakaki05.json'))
	#gdrive = GoogleDrive(credentials_manager=GDFileCredentials('gdrive_credentials_masakaki00.json'))

	#repair_permissions(gdrive, db, limit=10)
	#while True:
	#	c = move_to_folders(gdrive, db)
	#	if not c:
	#		break
	#exit()

	#pprint.pprint(gdrive.upload('drive.py'))
	#pprint.pprint(gdrive.upload('http://www.barcodekanojo.com/profile_images/kanojo/2576048/1382482591/%D0%94%D0%B6%D0%B8%D0%BD.png?w=88&h=88&face=true'))
	#pprint.pprint(gdrive.getPermissions('0B-nxIpt4DE2TZlZUUmRVM29SWEk'))
	#pprint.pprint(gdrive.getPermissions('0B-nxIpt4DE2TeFVLTFNEWDZuN1E')) # 1x1

	'''
	about = gdrive.driveAbout()
	pprint.pprint(about)
	percent = float(about.get('quotaBytesUsed'))/float(about.get('quotaBytesTotal'))*100
	print 'Usage: %.2f%%'%percent
	'''
	
	'''
	#files = gdrive.folderItems('0B3V-BSgVkX4Zd1lDUk9ZRnlhRWc')
	files = gdrive.folderItems(search_string='mimeType != \'application/vnd.google-apps.folder\' and trashed = false', ids_only=True)
	print json.dumps(files)
	print len(files)
	'''
	
	#gdrive.download('0B-nxIpt4DE2TZlZUUmRVM29SWEk')
	

	'''
	#(changes, largestChangeId) = gdrive.retrieve_all_changes('2811')
	(changes, largestChangeId) = gdrive.retrieve_page_changes('2811')
	print json.dumps(changes)
	print len(changes), 'largestChangeId:', largestChangeId
	'''

	#print json.dumps(gdrive.fileInfo("1fGLew1w4uaSjdwO4agUPbJnn2PHa7nDFoGUNBQ49dv4"))
	#print json.dumps(gdrive.fileInfo('0B-nxIpt4DE2TWV9BVUVnM3lhcXc'))

	#from gdrive_backup import getPath
	#print getPath(gdrive, gdrive.fileInfo("0B-nxIpt4DE2TRmx2S0xtODJJRE0"))

	print gdrive.getUserInfo()
