import os.path

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
import yop_cloud_sdk


class Bot:
    def __init__(
            self,
            telegram_bot_token: str,
            yop_storage_url: str,
            yop_storage_token: str,
    ):
        self.yop_storage = yop_cloud_sdk.YOPStorage(host_url=yop_storage_url, token=yop_storage_token)
        self.bot_application = ApplicationBuilder().token(telegram_bot_token).build()
    
        start_handler = CommandHandler('start', self.start)
        download_handler = CommandHandler('download', self.download)
        upload_handler = MessageHandler(filters.Document.ALL, self.upload)
        
        self.bot_application.add_handler(start_handler)
        self.bot_application.add_handler(download_handler)
        self.bot_application.add_handler(upload_handler)

    def run_polling(self):
        self.bot_application.run_polling()

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        usage_text = \
            "/download <path> to download a file.\n" \
            "send file with <path> message to upload a file."
        await context.bot.send_message(chat_id=update.effective_chat.id, text=usage_text)

    async def download(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if context.args is None or len(context.args) != 1:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text='You need to specify exactly one file path.'
            )
            return
        
        path = context.args[0]
        file_name = os.path.basename(path)

        try:
            self.yop_storage.download(path, '.', file_name)
        except FileNotFoundError:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text='File was not found on server. Sorry bro.'
            )
            return

        await context.bot.send_document(chat_id=update.effective_chat.id, document=open(file_name, 'rb'))
        print(f'sent to @{update.effective_user.username}')

    async def upload(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        wrong_caption_text = 'You need to specify exactly one path for saving the file.'

        if update.message.caption is None:
            path = update.message.document.file_name
        else:
            caption_split = update.message.caption.split(' ')
            if len(caption_split) != 1:
                await context.bot.send_message(chat_id=update.effective_chat.id, text=wrong_caption_text)
                return

            path = caption_split[0]

        file_id = update.message.document.file_id
        new_file = await context.bot.get_file(file_id)
        await new_file.download_to_drive(update.message.document.file_name)
        print(f'recieved {update.message.document.file_name} from @{update.effective_user.username}. Uploading...')

        try:
            self.yop_storage.upload(update.message.document.file_name, '.', path)
        except RuntimeError:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text='Uploading failed. I don\'t know why. Try rebooting computer...'
            )
            return

        await context.bot.send_message(chat_id=update.effective_chat.id, text='Uploaded.')


def main():
    load_dotenv()
    Bot(
        telegram_bot_token=os.environ['TELEGRAM_BOT_TOKEN'],
        yop_storage_url=os.environ['YOP_STORAGE_URL'],
        yop_storage_token=os.environ['YOP_STORAGE_TOKEN'],
    ).run_polling()


if __name__ == '__main__':
    main()


