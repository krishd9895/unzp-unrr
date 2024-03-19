import os
import telebot
import zipfile
import rarfile
import shutil

BOT_TOKEN = os.environ['TOKEN']
bot = telebot.TeleBot(BOT_TOKEN)


# Function to handle unzip operation
def unzip_file(file_path, destination_dir):
  try:
    with zipfile.ZipFile(file_path, 'r') as zip_ref:
      zip_ref.extractall(destination_dir)
  except zipfile.BadZipFile:
    os.remove(file_path)
    raise ValueError("The provided ZIP file is corrupted.")


# Function to handle unrar operation
def unrar_file(file_path, destination_dir):
  try:
    with rarfile.RarFile(file_path, 'r') as rar_ref:
      rar_ref.extractall(destination_dir)
  except rarfile.BadRarFile:
    os.remove(file_path)
    raise ValueError("The provided RAR file is corrupted.")


# Function to send file to the user
def send_file(bot, chat_id, file_path):
  with open(file_path, 'rb') as file:
    bot.send_document(chat_id, file)


# Function to send files in a directory to the user
def send_files_in_directory(bot, chat_id, directory_path):
  files = [
      f for f in os.listdir(directory_path)
      if os.path.isfile(os.path.join(directory_path, f))
  ]
  for file in files:
    send_file(bot, chat_id, os.path.join(directory_path, file))


# Define a handler for /start command
@bot.message_handler(commands=['start'])
def start(message):
  bot.reply_to(
      message,
      "Hello! Send me a .zip or .rar file and I'll extract its contents for you."
  )


# Define a handler for messages containing compressed files
@bot.message_handler(content_types=['document'])
def handle_document(message):
  try:
    # Clean up: delete old zip/rar files and extracted directories
    for item in os.listdir():
      if item.endswith('.zip') or item.endswith('.rar') or item.startswith(
          'extracted_files_'):
        if os.path.isfile(item):
          os.remove(item)
        elif os.path.isdir(item):
          shutil.rmtree(item)

    # Download the document (compressed file)
    file_info = bot.get_file(message.document.file_id)
    downloaded_file = bot.download_file(file_info.file_path)
    file_name = message.document.file_name

    # Save the downloaded file
    with open(file_name, 'wb') as new_file:
      new_file.write(downloaded_file)

    # Determine the type of compressed file and extract accordingly
    if file_name.endswith('.zip'):
      destination_dir = os.path.join(os.getcwd(), 'extracted_files_zip')
      os.makedirs(destination_dir, exist_ok=True)
      unzip_file(file_name, destination_dir)
    elif file_name.endswith('.rar'):
      destination_dir = os.path.join(os.getcwd(), 'extracted_files_rar')
      os.makedirs(destination_dir, exist_ok=True)
      unrar_file(file_name, destination_dir)
    else:
      os.remove(file_name)  # Clean up: delete the downloaded file
      bot.reply_to(
          message, "Unsupported file format. Please send a .zip or .rar file.")
      return

    # Iterate over subdirectories and send files sequentially
    for subdir, _, _ in os.walk(destination_dir):
      if subdir != destination_dir:
        bot.send_message(
            message.chat.id,
            f"Files in {os.path.relpath(subdir, destination_dir)}:")
        send_files_in_directory(bot, message.chat.id, subdir)

    # Clean up: delete the downloaded and extracted files
    os.remove(file_name)
    shutil.rmtree(destination_dir)

  except ValueError as e:
    bot.reply_to(message, f"Error: {e}")
  except Exception as e:
    bot.reply_to(message, f"An error occurred: {e}")
    os.remove(file_name)  # Clean up: delete the downloaded file


# Start the bot
bot.polling()
