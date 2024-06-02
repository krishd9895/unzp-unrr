import os
import requests
import zipfile
import rarfile
import shutil
import py7zr
from pyrogram import Client, filters

# Set up your bot's token, API ID, and API Hash as environment variables
telegram_token = os.environ['BOT_TOKEN']
api_id = int(os.environ['API_ID'])
api_hash = os.environ['API_HASH']

# Create the Pyrogram client
app = Client("unarchive_bot", bot_token=telegram_token, api_id=api_id, api_hash=api_hash)

# Define the /start command handler
@app.on_message(filters.command("start"))
def start(client, message):
    message.reply("Welcome! Send me a .zip, .rar, or .7z file to unarchive.")

# Define the /unarchive command handler
@app.on_message(filters.command(["unarchive", "ua"]) & filters.reply)
def unarchive(client, message):
    replied_message = message.reply_to_message

    if replied_message.document:
        file_name = replied_message.document.file_name
        file_id = replied_message.document.file_id
        file_type = "document"
    elif replied_message.text and (replied_message.text.startswith("http://") or replied_message.text.startswith("https://")):
        url = replied_message.text
        try:
            # Send a HEAD request to get the file metadata
            response = requests.head(url, allow_redirects=True)
            response.raise_for_status()
            content_type = response.headers.get('Content-Type')
            if content_type:
                if 'zip' in content_type:
                    file_extension = '.zip'
                elif 'rar' in content_type:
                    file_extension = '.rar'
                elif '7z' in content_type:
                    file_extension = '.7z'
                else:
                    message.reply("The URL does not point to a ZIP, RAR, or 7Z file.")
                    return
                file_name = os.path.basename(url)
            else:
                message.reply("Unable to determine the file type from the URL.")
                return
            file_type = "url"
        except requests.exceptions.RequestException as e:
            message.reply(f"Error checking the file type: {e}")
            return
    else:
        message.reply("Please reply to a ZIP, RAR, or 7Z file or URL to unarchive.")
        return

    if file_type == "document" and file_name.endswith(('.zip', '.rar', '.7z')):
        try:
            # Send acknowledgment message
            message.reply("File received. Extracting...")

            # Download the document (compressed file)
            file_path = client.download_media(file_id, file_name)

            # Determine the type of compressed file and extract accordingly
            if file_name.endswith('.zip'):
                destination_dir = os.path.join(os.getcwd(), 'extracted_files_zip')
                os.makedirs(destination_dir, exist_ok=True)
                extracted_files = unzip_file(file_path, destination_dir)
            elif file_name.endswith('.rar'):
                destination_dir = os.path.join(os.getcwd(), 'extracted_files_rar')
                os.makedirs(destination_dir, exist_ok=True)
                extracted_files = unrar_file(file_path, destination_dir)
            elif file_name.endswith('.7z'):
                destination_dir = os.path.join(os.getcwd(), 'extracted_files_7z')
                os.makedirs(destination_dir, exist_ok=True)
                extracted_files = un7z_file(file_path, destination_dir)

            # Send files sequentially with their original relative paths
            for file_info in extracted_files:
                send_file(client, message.chat.id, file_info['path'], file_info['relative_path'])

            # Send completion message
            client.send_message(chat_id=message.chat.id, text="Extraction complete.")

            # Clean up: delete the downloaded and extracted files
            os.remove(file_path)
            shutil.rmtree(destination_dir)

        except (ValueError, Exception) as e:
            message.reply(f"An error occurred: {e}")
            if os.path.exists(file_path):
                os.remove(file_path)  # Clean up: delete the downloaded file

    elif file_type == "url" and file_extension in ['.zip', '.rar', '.7z']:
        try:
            # Send acknowledgment message
            message.reply("File received. Extracting...")

            # Send a message about the download status
            message.reply(f"Downloading {file_name}...")

            # Download the file from the URL
            response = requests.get(url, stream=True)
            response.raise_for_status()

            # Save the downloaded file to the downloads folder
            downloads_dir = os.path.join(os.getcwd(), 'downloads')
            os.makedirs(downloads_dir, exist_ok=True)
            file_path = os.path.join(downloads_dir, file_name)
            with open(file_path, 'wb') as file:
                for chunk in response.iter_content(chunk_size=8192):
                    file.write(chunk)

            # Determine the type of compressed file and extract accordingly
            if file_extension == '.zip':
                destination_dir = os.path.join(os.getcwd(), 'extracted_files_zip')
                os.makedirs(destination_dir, exist_ok=True)
                extracted_files = unzip_file(file_path, destination_dir)
            elif file_extension == '.rar':
                destination_dir = os.path.join(os.getcwd(), 'extracted_files_rar')
                os.makedirs(destination_dir, exist_ok=True)
                extracted_files = unrar_file(file_path, destination_dir)
            elif file_extension == '.7z':
                destination_dir = os.path.join(os.getcwd(), 'extracted_files_7z')
                os.makedirs(destination_dir, exist_ok=True)
                extracted_files = un7z_file(file_path, destination_dir)

            # Send files sequentially with their original relative paths
            for file_info in extracted_files:
                send_file(client, message.chat.id, file_info['path'], file_info['relative_path'])

            # Send completion message
            client.send_message(chat_id=message.chat.id, text="Extraction complete.")

            # Clean up: delete the downloaded and extracted files
            os.remove(file_path)
            shutil.rmtree(destination_dir)

        except requests.exceptions.RequestException as e:
            message.reply(f"Error downloading the file: {e}")
        except (ValueError, Exception) as e:
            message.reply(f"An error occurred: {e}")
            if os.path.exists(file_path):
                os.remove(file_path)  # Clean up: delete the downloaded file

# Function to handle unzip operation
def unzip_file(file_path, destination_dir):
    try:
        extracted_files = []
        with zipfile.ZipFile(file_path, 'r') as zip_ref:
            for file in zip_ref.namelist():
                zip_ref.extract(file, destination_dir)
                extracted_files.append({
                    'path': os.path.join(destination_dir, file),
                    'relative_path': file
                })
        return extracted_files
    except zipfile.BadZipFile:
        os.remove(file_path)
        raise ValueError("The provided ZIP file is corrupted.")


# Function to handle unrar operation
def unrar_file(file_path, destination_dir):
    try:
        extracted_files = []
        with rarfile.RarFile(file_path, 'r') as rar_ref:
            for file in rar_ref.namelist():
                rar_ref.extract(file, destination_dir)
                extracted_files.append({
                    'path': os.path.join(destination_dir, file),
                    'relative_path': file
                })
        return extracted_files
    except rarfile.BadRarFile:
        os.remove(file_path)
        raise ValueError("The provided RAR file is corrupted.")

# Function to handle un7z operation
def un7z_file(file_path, destination_dir):
    try:
        extracted_files = []
        with py7zr.SevenZipFile(file_path, mode='r') as archive:
            for file in archive.getnames():
                archive.extract(destination_dir, file)
                extracted_files.append({
                    'path': os.path.join(destination_dir, file),
                    'relative_path': file
                })
        return extracted_files
    except py7zr.exceptions.Bad7zFile:
        os.remove(file_path)
        raise ValueError("The provided 7z file is corrupted.")

# Function to send file to the user
def send_file(client, chat_id, file_path, relative_path):
    directory_name = os.path.dirname(relative_path)
    file_name = os.path.basename(file_path)
    with open(file_path, 'rb') as file:
        client.send_document(chat_id, file, caption=directory_name, file_name=file_name)

# Define the /clean command handler
@app.on_message(filters.command("clean"))
def clean(client, message):
    directories = ['downloads', 'extracted_files_zip', 'extracted_files_rar', 'extracted_files_7z']
    for directory in directories:
        dir_path = os.path.join(os.getcwd(), directory)
        if os.path.exists(dir_path):
            shutil.rmtree(dir_path)
            os.makedirs(dir_path, exist_ok=True)  # Recreate the directory
    message.reply("Cleanup complete. All files have been deleted from the specified directories.")


# Run the Pyrogram client
app.run()
