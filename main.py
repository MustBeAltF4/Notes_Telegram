import logging
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Updater, CommandHandler, ConversationHandler, MessageHandler, Filters
import psycopg2

db_settings = {
    'user': 'ваши_данные',
    'password': 'ваши_данные',
    'host': 'ваши_данные',
    'database': 'ваши_данные'
}

SELECT_ACTION, ENTER_NOTE_NAME, ENTER_NOTE_TEXT, VIEW_NOTES = range(4)


def start(update, context):
    user_id = update.effective_user.id
    context.user_data['user_id'] = user_id

    reply_keyboard = [['Добавить заметку', 'Просмотреть заметки']]
    markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    update.message.reply_text(
        'Привет! Я бот для заметок. Что бы вы хотели сделать?',
        reply_markup=markup
    )
    return SELECT_ACTION


def select_action(update, context):
    user_id = context.user_data.get('user_id')
    action = update.message.text
    if action == 'Добавить заметку':
        update.message.reply_text('Введите имя заметки:')
        return ENTER_NOTE_NAME
    elif action == 'Просмотреть заметки':
        show_notes(update, context, user_id)
        return VIEW_NOTES


def enter_note_name(update, context):
    context.user_data['note_name'] = update.message.text
    update.message.reply_text('Введите текст заметки:')
    return ENTER_NOTE_TEXT


def enter_note_text(update, context):
    user_id = context.user_data.get('user_id')
    note_name = context.user_data['note_name']
    note_text = update.message.text
    save_note_to_db(user_id, note_name, note_text)
    update.message.reply_text('Заметка сохранена.')
    return ConversationHandler.END


def save_note_to_db(user_id, note_name, note_text):
    try:
        conn = psycopg2.connect(**db_settings)
        cursor = conn.cursor()
        cursor.execute('INSERT INTO notes (user_id, name, text) VALUES (%s, %s, %s)', (user_id, note_name, note_text))
        conn.commit()
        cursor.close()
        conn.close()
    except (Exception, psycopg2.Error) as error:
        logging.error('Ошибка при сохранении заметки: %s', error)


def show_notes(update, context, user_id):
    try:
        conn = psycopg2.connect(**db_settings)
        cursor = conn.cursor()
        cursor.execute('SELECT name FROM notes WHERE user_id = %s', (user_id,))
        notes = cursor.fetchall()
        cursor.close()
        conn.close()

        if notes:
            note_list = [note[0] for note in notes]
            reply_keyboard = [note_list[i:i + 2] for i in range(0, len(note_list), 2)]
            markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
            update.message.reply_text(
                'Выберите заметку:',
                reply_markup=markup
            )
            return VIEW_NOTES
        else:
            update.message.reply_text('У вас нет заметок.')
            return ConversationHandler.END
    except (Exception, psycopg2.Error) as error:
        logging.error('Ошибка при получении списка заметок: %s', error)
        update.message.reply_text('Произошла ошибка. Попробуйте еще раз.')
        return ConversationHandler.END


def view_note_text(update, context):
    user_id = context.user_data.get('user_id')
    note_name = update.message.text
    try:
        conn = psycopg2.connect(**db_settings)
        cursor = conn.cursor()
        cursor.execute('SELECT text FROM notes WHERE user_id = %s AND name = %s', (user_id, note_name))
        note_text = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        update.message.reply_text(note_text)
    except (Exception, psycopg2.Error) as error:
        logging.error('Ошибка при получении текста заметки: %s', error)
        update.message.reply_text('Произошла ошибка. Попробуйте еще раз.')


def cancel(update, context):
    update.message.reply_text('Операция отменена.', reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


def error(update, context):
    logging.error('Произошла ошибка: %s', context.error)


def main():
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

    updater = Updater('ваши_данные', use_context=True)

    dp = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            SELECT_ACTION: [MessageHandler(Filters.text, select_action)],
            ENTER_NOTE_NAME: [MessageHandler(Filters.text, enter_note_name)],
            ENTER_NOTE_TEXT: [MessageHandler(Filters.text, enter_note_text)],
            VIEW_NOTES: [MessageHandler(Filters.text, view_note_text)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    dp.add_handler(conv_handler)

    dp.add_error_handler(error)

    updater.start_polling()

    updater.idle()


if __name__ == '__main__':
    main()
