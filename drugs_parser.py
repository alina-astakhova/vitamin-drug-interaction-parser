import random
import requests
from bs4 import BeautifulSoup
import re
import csv
from time import sleep
from deep_translator import GoogleTranslator
from config import HEADERS, REQUEST_DELAY, TRANSLATE_TO_RUSSIAN


class DrugsComParser:
    def __init__(self, vitamin_name, vitamin_form=None):
        """
        Инициализация парсера для конкретного витамина

        Args:
            vitamin_name (str): Название витамина (например, 'niacinamide')
            vitamin_form (str): Форма витамина (опционально)
        """
        self.vitamin_name = vitamin_name.lower()
        self.vitamin_form = vitamin_form or vitamin_name
        self.vitamin_display_name = vitamin_name.capitalize()

        self.base_url = "https://www.drugs.com/drug-interactions"
        self.start_url = f"{self.base_url}/{self.vitamin_name}-index.html"

        # Инициализация переводчика
        self.translator = GoogleTranslator(source='en', target='ru') if TRANSLATE_TO_RUSSIAN else None

        # Сессия для повторного использования соединений
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    def clean_text(self, text):
        """Очистка текста от лишних пробелов и переносов строк"""
        if not text:
            return ""
        return re.sub(' +', ' ', text.replace('\n', ' ')).strip().capitalize()

    def translate_text(self, text):
        """Перевод текста на русский язык"""
        if not text or not self.translator:
            return text
        try:
            return self.translator.translate(text)
        except Exception as e:
            print(f"Ошибка перевода: {e}")
            return text

    def download_start_page(self):
        """Загрузка стартовой страницы со списком лекарств"""
        print(f"Загрузка стартовой страницы для {self.vitamin_display_name}...")

        try:
            response = self.session.get(self.start_url)
            response.raise_for_status()

            filename = f"{self.vitamin_name}_start.html"
            with open(filename, 'w', encoding='utf-8') as file:
                file.write(response.text)
            print(f"Стартовая страница сохранена как: {filename}")
            return filename

        except requests.RequestException as e:
            print(f"Ошибка при загрузке стартовой страницы: {e}")
            return None

    def parse_start_page(self, html_file):
        """Парсинг стартовой страницы и извлечение ссылок на лекарства"""
        print("Парсинг стартовой страницы...")

        with open(html_file, 'r', encoding='utf-8') as file:
            source = file.read()

        soup = BeautifulSoup(source, 'lxml')

        # Поиск элементов с лекарствами разных уровней взаимодействия
        elements = []
        for class_name in ["int_1", "int_2", "int_3"]:
            found_elements = soup.find_all('li', class_=class_name)[1:]
            if class_name in ["int_2", "int_3"]:
                found_elements = found_elements[:-2]  # Исключаем последние 2 элемента
            elements.extend(found_elements)

        print(f"Найдено лекарств: {len(elements)}")
        return elements

    def parse_drug_interaction(self, drug_element):
        """Парсинг информации о взаимодействии для конкретного лекарства"""
        drug_name = drug_element.text.strip()
        interaction_intensity = f"-{drug_element.get('class', [''])[0][4:]}"  # Извлекаем уровень из класса

        link_element = drug_element.find('a')
        if not link_element:
            return None

        relative_link = link_element.get('href', '')
        link_user = f"https://www.drugs.com{relative_link}"
        link_professional = f"{link_user}?professional=1"

        print(f"Обработка: {drug_name} (уровень: {interaction_intensity})")

        # Получение описаний взаимодействия
        description_user = self.get_interaction_description(link_user)
        description_professional = self.get_interaction_description(link_professional)

        # Перевод описаний
        description_user_ru = self.translate_text(description_user) if description_user else ""
        description_professional_ru = self.translate_text(description_professional) if description_professional else ""

        return {
            'link_user': link_user,
            'drug_name': drug_name,
            'interaction_intensity': interaction_intensity,
            'description_user': description_user or "",
            'description_user_ru': description_user_ru,
            'description_professional': description_professional or "",
            'description_professional_ru': description_professional_ru
        }

    def get_interaction_description(self, url):
        """Получение описания взаимодействия с указанного URL"""
        try:
            response = self.session.get(url)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'lxml')
            interaction_wrapper = soup.find('div', 'interactions-reference-wrapper')

            if interaction_wrapper:
                paragraphs = interaction_wrapper.find_all('p')
                if paragraphs:
                    return self.clean_text(paragraphs[0].text)

            return "Описание не найдено"

        except requests.RequestException as e:
            print(f"Ошибка при загрузке {url}: {e}")
            return "Ошибка загрузки"

    def run(self):
        """Основной метод запуска парсера"""
        print(f"Запуск парсера для: {self.vitamin_display_name}")

        # Шаг 1: Загрузка стартовой страницы
        html_file = self.download_start_page()
        if not html_file:
            return

        # Шаг 2: Парсинг стартовой страницы
        drug_elements = self.parse_start_page(html_file)

        if not drug_elements:
            print("Не найдено лекарств для обработки")
            return

        # Шаг 3: Создание CSV файла
        csv_filename = f"{self.vitamin_name}_interactions.csv"
        with open(csv_filename, 'w', encoding='utf-8-sig', newline='') as file:
            writer = csv.writer(file, delimiter=';')
            # Заголовки CSV
            writer.writerow([
                'Ссылка', 'Витамин', 'Форма', 'Название лекарства',
                'Уровень взаимодействия', 'Описание (пользователь)',
                'Описание (пользователь, рус)', 'Описание (профессионал)',
                'Описание (профессионал, рус)'
            ])

        # Шаг 4: Обработка каждого лекарства
        total_drugs = len(drug_elements)
        print(f"Начата обработка {total_drugs} лекарств...")

        for index, drug_element in enumerate(drug_elements, 1):
            drug_data = self.parse_drug_interaction(drug_element)

            if drug_data:
                # Запись в CSV
                with open(csv_filename, 'a', encoding='utf-8-sig', newline='') as file:
                    writer = csv.writer(file, delimiter=';')
                    writer.writerow([
                        drug_data['link_user'],
                        self.vitamin_display_name,
                        self.vitamin_form,
                        drug_data['drug_name'],
                        drug_data['interaction_intensity'],
                        drug_data['description_user'],
                        drug_data['description_user_ru'],
                        drug_data['description_professional'],
                        drug_data['description_professional_ru']
                    ])

            # Прогресс и задержка
            remaining = total_drugs - index
            print(f"Обработано: {index}/{total_drugs}. Осталось: {remaining}")

            if remaining > 0:
                delay = random.uniform(REQUEST_DELAY[0], REQUEST_DELAY[1])
                sleep(delay)

        print(f"Парсинг завершен! Результаты сохранены в: {csv_filename}")


def main():
    """Пример использования парсера"""
    # Создаем парсер для ниацинамида
    parser = DrugsComParser(
        vitamin_name="niacinamide",
        vitamin_form="niacinamide"
    )

    # Запускаем парсинг
    parser.run()


if __name__ == "__main__":
    main()