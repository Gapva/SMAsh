import os
import requests
from zipfile import ZipFile
import rarfile
import py7zr
import shutil
from urllib.error import HTTPError

global_filename: str # unused for now
global_modpath: str
print() # extra linebreak

def create_data_folder():
	script_dir = os.path.dirname(os.path.realpath(__file__))
	data_folder = os.path.join(script_dir, 'data')
	if not os.path.exists(data_folder):
		os.makedirs(data_folder)
	return data_folder

def get_mod_path(data_folder):
	global global_modpath
	path_file = os.path.join(data_folder, 'path.txt')
	if os.path.exists(path_file):
		with open(path_file, 'r') as f:
			mod_path = f.read().strip()
			if os.path.exists(mod_path):
				return mod_path
			else:
				print(f"Path in {path_file} does not exist.")
	
	mod_path = input("Enter the path to your Ultimate 'mods' directory:\n> ").strip()
	while not os.path.exists(mod_path):
		print("Path does not exist. Please try again.")
		mod_path = input("Enter the path to your Ultimate 'mods' directory:\n> ").strip()
	
	with open(path_file, 'w') as f:
		f.write(mod_path)
	
	global_modpath = mod_path
	return mod_path

def extract_mod_and_file_id(download_link):
	if "https://gamebanana.com/dl/" in download_link:
		parts = download_link.split("/")[-1].split("#FileInfo_")
		if len(parts) == 2:
			return parts[0], parts[1]
	elif "https://gamebanana.com/mods/download/" in download_link:
		parts = download_link.split("/")[-1].split("#FileInfo_")
		if len(parts) == 2:
			return parts[0], parts[1]
	raise ValueError("Invalid download link format.")

def get_filename_from_api(mod_id, file_id):
	global global_filename
	api_url = f"https://gamebanana.com/apiv11/Mod/{mod_id}/DownloadPage"
	response = requests.get(api_url)
	response.raise_for_status()
	data = response.json()
	files = data['_aFiles']
	for file_info in files:
		if str(file_info["_idRow"]) == file_id:
			global_filename = file_info["_sFile"]
			return file_info["_sFile"]
	raise ValueError("Filename not found for the given file ID.")

def download_file(url, mod_path, filename):
	print(f"\nDownloading {filename}")
	response = requests.get(url, stream=True)
	response.raise_for_status()
	total_length = response.headers.get('content-length')

	if total_length is None:
		raise ValueError("Unable to determine file size for download.")

	total_length = int(total_length)
	downloaded_size = 0
	dest = os.path.join(mod_path, filename)

	with open(dest, 'wb') as f:
		for chunk in response.iter_content(chunk_size=8192):
			if chunk:  # filter out keep-alive new chunks
				f.write(chunk)
				downloaded_size += len(chunk)
				print(f"{downloaded_size} of {total_length} bytes", end='\r')

	if downloaded_size != total_length:
		os.remove(dest)
		raise ValueError("Download incomplete, file removed.")

	print(f"\nDownloaded to {dest}")
	return dest

def extract_archive(file_path, extract_to):
	print(f"\nExtracting {file_path.split(os.path.sep)[-1]} to {extract_to.split(os.path.sep)[-1]}")
	if file_path.endswith('.zip'):
		with ZipFile(file_path, 'r') as zip_ref:
			zip_ref.extractall(extract_to)
	elif file_path.endswith('.rar'):
		with rarfile.RarFile(file_path) as rar_ref:
			rar_ref.extractall(extract_to)
	elif file_path.endswith('.7z'):
		with py7zr.SevenZipFile(file_path, mode='r') as seven_z_ref:
			seven_z_ref.extractall(extract_to)
	else:
		print(f"Unsupported archive format: {file_path}")

def flatten_directory_structure(directory):
	print(f"Flattening directory structure of {directory.split(os.path.sep)[-1]}")
	for root, dirs, files in os.walk(directory):
		for name in files:
			shutil.move(os.path.join(root, name), directory)
		# for name in dirs:
		#	 shutil.rmtree(os.path.join(root, name))
		break

def delete_non_folders(directory):
	for item in os.listdir(directory):
		item_path = os.path.join(directory, item)
		if os.path.isfile(item_path):
			print(f"Cleaning extraneous root items")
			os.remove(item_path)
		elif os.path.isdir(item_path) and not os.path.islink(item_path):
			pass

def main():
	data_folder = create_data_folder()
	mod_path = get_mod_path(data_folder)
	
	download_link = input("\nPaste the download link for the GameBanana mod:\n> ").strip()
	
	try:
		mod_id, file_id = extract_mod_and_file_id(download_link)
	except ValueError as e:
		print(e)
		return
	
	try:
		filename = get_filename_from_api(mod_id, file_id)
	except ValueError as e:
		print(e)
		return
	
	download_url = f"https://gamebanana.com/dl/{file_id}"
	
	download_started = False
	while not download_started:
		try:
			dest = download_file(download_url, mod_path, filename)
		except ValueError as e:
			print(e)
			return
		except HTTPError as e:
			print("Encountered a gateway error, retrying")
			return
		else:
			download_started = True
	
	file_extension = os.path.splitext(dest)[-1].lower()
	if file_extension not in ['.zip', '.rar', '.7z']:
		print(f"Downloaded file does not have a valid archive extension: {dest}")
	else:
		extract_archive(dest, mod_path)
		os.remove(dest)
		delete_non_folders(mod_path)
		flatten_directory_structure(mod_path)
		input("\nMod downloaded and extracted successfully\nPress enter to exit SMAsh\n")

if __name__ == "__main__":
	main()
