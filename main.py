import json, os, httplib2, traceback
from googleapiclient.discovery import build
from oauth2client.service_account import ServiceAccountCredentials
from pprint import pprint

def get_service_sacc():
    """Создание сервисного аккаунта Google"""
    creds_json = os.path.dirname(__file__) + "/creds/mysacc2.json"
    scopes = ['https://www.googleapis.com/auth/spreadsheets']
    creds_service = ServiceAccountCredentials.from_json_keyfile_name(
        creds_json, scopes).authorize(httplib2.Http())
    return build('sheets', 'v4', http=creds_service)

class Project(object):
    def __init__(self, name, link, sheet_name="Отзывы"):
        self.name = name
        self.sheet_name = sheet_name
        self.link = link
        self.sheet_id = self.link.split('/')[-2]
        self.status = True

        # Все данные из листа отзывов
        self.all_values = sheet.values().get(
            spreadsheetId=self.sheet_id, range=f"{self.sheet_name}!A1:ZZ100").execute()['values']

        # Определение необходимых нам столбцов с данными по ссылкам на отзывы и валидацией процесса их написания

        # тут мы определяем максимально заполненную строку среди таблицы, исходя из длин всех (учёт пустых ячеек)
        example_value = max([len(self.all_values[1:][elem]) for elem in range(len(self.all_values[1:]))])
        lst_cols_reviews_links, lst_cols_reviews_dates = [], []

        # проверка на то, одинаковы ли длины всех строк в таблице
        # это условие для реализации поиска индексов столбцов валидации с полностью ПУСТЫМИ ЯЧЕЙКАМИ
        if len(set([len(self.all_values[1:][elem]) for elem in range(len(self.all_values[1:]))])) != 1:
            example_index = [len(self.all_values[1:][elem]) for elem in range(len(self.all_values[1:]))].index(example_value)
            example_data = self.all_values[1:][example_index]

            # ЭТО КОД для установки столбцов данных в случае, когда в столбцах валидации есть ХОТЬ ОДНА строчка с непустыми ячейками
            for index_elem, data_elem in enumerate(example_data):
                if (data_elem.startswith('@') or data_elem.startswith('https://')) and len(lst_cols_reviews_links) == 0:
                    lst_cols_reviews_links.append(index_elem)
                if (data_elem.startswith('Да') or data_elem.startswith('Нет') or
                    data_elem.startswith('—') or data_elem == '') and len(lst_cols_reviews_dates) == 0:
                    lst_cols_reviews_links.append(index_elem - 1)
                    lst_cols_reviews_dates.append(index_elem)
                    lst_cols_reviews_dates.append(len(example_data))

        else:
            # ЭТО КОД для установки столбцов данных в случае, когда в столбцах валидации ВСЕ ЯЧЕЙКИ - ПУСТЫЕ
            example_data = self.all_values[0][2:]
            len_final_data = int(len(example_data) / 2)
            lst_cols_reviews_links.append(2)
            lst_cols_reviews_links.append(2 + len_final_data - 1)
            lst_cols_reviews_dates.append(2 + len_final_data)
            lst_cols_reviews_dates.append(2 + len(example_data))

        # Входные датасеты базы активистов, базы ссылок на отзывы, базы дат отзывов и базы отчётности выполнения отзывов
        self.base_users = [user[0:2] for user in self.all_values[1:]]
        self.base_reviews = [review[2:(lst_cols_reviews_links[1]+1)] for review in self.all_values[1:]]
        self.base_dates = self.all_values[0][lst_cols_reviews_dates[0]:lst_cols_reviews_dates[1]]
        self.is_done = [is_done[lst_cols_reviews_dates[0]:lst_cols_reviews_dates[1]] for is_done in self.all_values[1:]]

        # дополнительная проверка на то, что у нас столбцы с валидацией ПОЛНОСТЬЮ ПУСТЫЕ
        if sum([len(elem) for elem in self.is_done]) == 0:
           self.is_done = [[''] * (lst_cols_reviews_dates[1] - lst_cols_reviews_dates[0]) for _ in self.all_values[1:]]

    def check_feedbacks(self):
        list_fakapers = []
        """Проверяет, кто не написал отзывы"""
        n_rev_day = max([len(self.is_done[elem]) for elem in range(len(self.is_done))])
        try:
            for u in range(len(self.base_users)):
                # список отчётности заполнения отзывов
                if len(self.is_done[u]) < n_rev_day or len(self.is_done[u]) == 0:
                    self.is_done[u] += [''] * (n_rev_day - len(self.is_done[u]))
                if_list = [False if elem == 'Нет' or elem == '' else True for elem in self.is_done[u]]
                if False in if_list:
                    # Находим ссылки на отзывы, которые не были написаны
                    list_links_rev = [self.base_reviews[u][ind] for ind in range(len(if_list)) if if_list[ind] == False]
                    list_links_rev_now = ['https://instagram.com/' + link[1:] if link[0] == '@'
                                          else link for link in list_links_rev]

                    # Работаем с нахождением даты написания отзывов
                    list_dates = [self.base_dates[ind] for ind in range(len(if_list)) if if_list[ind] == False]

                    # Составляем структуру элемента листа факапщиков
                    user = {'name': self.base_users[u][0], 'id': self.base_users[u][1],
                            'reviews_links': list_links_rev_now, 'dates_reviews': list_dates}
                    list_fakapers.append(user)
        except:
            print(traceback.format_exc())

        if list_fakapers == []:
            #send_message(peer_id, 'Все молодцы, факапов нет!')
            return []
        else:
            #send_message(peer_id, final_text)
            return list_fakapers

    def format_feedbacks(self):
        fak_list, str_fak = self.check_feedbacks(), ''
        if len(fak_list) != 0:
            for ind, fak in enumerate(fak_list):
                str_fak += f'\nФакапер № {ind+1}, @id{fak["id"]} ({fak["name"]})\nНе написаны следующие отзывы:\n'
                list_reviews = [
                    f"{index + 1}) {fak['dates_reviews'][index]} отзыв по такой ссылке: {fak['reviews_links'][index]}"
                    for index in range(len(fak['reviews_links']))]
                str_fak += '\n'.join(list_reviews)
                str_fak += '\n'
            return str_fak
        else:
            return 'А факаперов нет, ну и прекрасно!'

    def remind_feedbacks(self, peer_id=0):
        """
        Напомнить в лс тем, кто не написал отзывы.
        На данный момент прописка в лс неактуальна, но может быть полезна в некоторых случаях.
        """
        fakaps = self.check_feedbacks()
        if fakaps == []:
            print('Список людей пуст. Чтобы обновить список, используй команду «!проверка».')
            #send_message(peer_id, 'Список людей пуст. Чтобы обновить список, используй команду «!проверка».')
        else:
            print("Пошла моча по трубам...")
            #send_message(peer_id, "Пошла моча по трубам...")
            for u in range(len(fakaps)):
                user_id, user_name = fakaps[u]['id'], fakaps[u]['name']
                list_reviews = [
                    f"{index + 1}) {fakaps[u]['dates_reviews'][index]} ты не написал(-а) отзыв по такой ссылке: {fakaps[u]['reviews_links'][index]}"
                    for index in range(len(fakaps[u]['reviews_links']))]

                final_text = f'Привет, {user_name}!\n\nПисать отзывы — обязанность каждого активиста ПК.\n'
                final_text += '\n'.join(list_reviews)
                final_text += f'\nСделай, пожалуйста, это маленькое ТЗ как можно скорее!\n\nСсылка: {self.link}'
                print(final_text)
                #send_message(user_id, final_text)
            print("Готово! Рассылка прошла успешно.")
            #send_message(peer_id, "Готово! Рассылка прошла успешно.")

    def update_value(self, param, value):
        if param.lower() == "статус":
            self.status = value
        elif param.lower() == "таймер":
            self.timer = value

    def __str__(self):
        final_str = "\nПроект " + self.name + "\n"
        final_str += "Ссылка на таблицу: " + self.link + "\n"
        final_str += "Статус проекта: " + ("работает" if self.status else "не работает") + "\n"
        final_str += "\nСписок факаперов слева направо:\n" + self.format_feedbacks()
        return final_str

# Авторизация
service = get_service_sacc()
sheet = service.spreadsheets()

# 1 этап — проверка базы на пустоту
name_projects, if_base_null = [], False

def add_to_database(name, link, sheet_name="Отзывы", status=True):
    done_data = {
        name: {
            "link": link,
            "sheet_name": sheet_name,
            "status": str(status)
        }
    }
    try:
        with open('data/db.json', 'r', encoding='utf-8') as file:
            all_data = json.load(file)

        with open('data/db.json', 'w', encoding='utf-8') as file:
            all_data[name] = done_data[name]
            json.dump(all_data, file, ensure_ascii=False, indent=4)
        return f"Проект {name} успешно добавлен в базу db.json!"

    except (FileNotFoundError, json.decoder.JSONDecodeError, TypeError) as e:
        with open('data/db.json', 'w', encoding='utf-8') as file:
            json.dump(done_data, file, ensure_ascii=False, indent=4)
        return f"Проект {name} успешно добавлен в базу db.json, урааа!"

def get_state_base():
    try:
        with open('data/db.json', 'r', encoding='utf-8') as file:
            data = json.load(file)
            name_projects = list(data.keys())
        return data, name_projects
    except (FileNotFoundError, json.decoder.JSONDecodeError, TypeError) as e:
        return [], []

def find_project_in_base(name, method='проверка'):
    data, name_projects = get_state_base()
    if name in name_projects:
        link, sheet_name = data[name]['link'], data[name]['sheet_name']
        project = Project(name=name, link=link, sheet_name=sheet_name)
        if method == 'рассылка':
            return project.remind_feedbacks()
        else:
            print(project)
    elif (data == []) and (name_projects == []):
        print("Случилась ошибка при чтении базы: возможно, она просто пустая...")
    else:
        print("Такого проекта не существует в базе, попробуйте снова!")

if __name__ == "__main__":
    # 2 этап — инициализация проекта для поиска факапщиков и реализация команд бота
    while True:
        command = input("Введи любую команду => ").split()
        try:
            if len(command) > 1:

                # 1 команда "!добавить {название проекта} {ссылка на табличку}"
                if command[0].lower() == "!добавить" and command[-1].startswith("https://"):
                    data, name_projects = get_state_base()
                    name, link = ' '.join(command[1:-1]), command[-1]
                    if name not in name_projects:
                        state_adding = add_to_database(name=name, link=link)
                        print(state_adding)
                    else:
                        if data[name]['link'] == link:
                            print(f"Проект {name} со ссылкой {link}\nУже существует в базе.")
                        else:
                            state_updating = add_to_database(name=name, link=link)
                            print(f"Проект {name} с новой ссылкой {link} обновлён в базе!")

                # 2 команда "!проверка {название проекта}"
                elif command[0] == "!проверка":
                    find_project_in_base(name=' '.join(command[1:]))

                # 3 команда "!рассылка {название проекта}"
                elif command[0] == "!рассылка":
                    try:
                        find_project_in_base(name=' '.join(command[1:]), method='рассылка')
                    except AttributeError:
                        continue

                else:
                    print("Такой команды нет в списке, попробуй написать что-то из этого:")
                    print("1 команда !добавить {название проекта} {ссылка на табличку}")
                    print("2 команда !проверка {название проекта}")
                    print("3 команда !рассылка {название проекта}")
            else:
                print("Такой команды нет в списке, попробуй написать что-то из этого:")
                print("1 команда !добавить {название проекта} {ссылка на табличку}")
                print("2 команда !проверка {название проекта}")
                print("3 команда !рассылка {название проекта}")

                # моя часть - это можно удалить в финальном коде
                if_exit = input("Желаешь закончить проверку? (да/нет) => ").lower()
                if if_exit == 'да':
                    break
        except:
            print("Возникла ошибка в процессе работы бота, код ошибки: ")
            print(traceback.format_exc())
