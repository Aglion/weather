from flask import Flask, render_template, request
import requests
import os
from dotenv import load_dotenv

app = Flask(__name__)

# Загружаем настройки из файла .env (там хранится API-ключ)
load_dotenv()

# Берём ключ для AccuWeather из переменных окружения
API_KEY = os.getenv("weather_token")

def get_location_key(city):
    # Функция пытается найти уникальный ключ для города, чтобы потом по нему получить погоду
    url = f"http://dataservice.accuweather.com/locations/v1/cities/search"
    params = {
        'apikey': API_KEY,
        'q': city,
        'language': 'ru-ru'
    }

    try:
        # Отправляем запрос к AccuWeather, чтобы найти город
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        # Если получили данные, берём ключ города из первого результата
        # Если нет данных, вернём None
        if data:
            return data[0]['Key']
        else:
            return None
    except requests.RequestException:
        # Если была ошибка при запросе (например, нет интернета)
        # вернём None, чтобы потом показать ошибку
        return None


def get_current_weather(location_key):
    # Функция берёт текущую погоду по ключу города
    url = f"http://dataservice.accuweather.com/currentconditions/v1/{location_key}"
    params = {
        'apikey': API_KEY,
        'language': 'ru-ru',
        'details': 'true'
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        # Если данные есть, вернём первый элемент со сводкой погоды
        # Если нет, вернём None
        if data:
            return data[0]
        else:
            return None
    except requests.RequestException:
        # В случае проблем с запросом вернём None
        return None


def get_precipitation_probability(location_key):
    # Функция берёт вероятность осадков на ближайший час
    # Используем hourly forecast на 1 час вперёд
    url = f"http://dataservice.accuweather.com/forecasts/v1/hourly/1hour/{location_key}"
    params = {
        'apikey': API_KEY,
        'language': 'ru-ru',
        'details': 'true'
    }

    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()

        # Прогноз на ближайший час хранит процент вероятности осадков здесь:
        # data[0]['PrecipitationProbability']
        # Если такой информации нет, вернём None
        if data and len(data) > 0:
            return data[0]['PrecipitationProbability']
        else:
            return None
    except requests.RequestException:
        return None




def get_weather(city):
    # Функция, которая собирает всю нужную информацию о погоде для указанного города
    # Если не сможем получить данные, вернём сообщение об ошибке
    location_key = get_location_key(city)
    if not location_key:
        return None, "Не удалось найти город. Проверьте правильность написания."

    current_weather = get_current_weather(location_key)
    if not current_weather:
        return None, "Не удалось получить текущую погоду. Попробуйте позже."

    precipitation_probability = get_precipitation_probability(location_key)
    if precipitation_probability is None:
        # Если не нашли информацию о вероятности осадков, поставим 0%
        precipitation_probability = 0

    # Собираем все данные в один словарь, чтобы потом удобно их показать
    weather = {
        "city": city,
        "temperature": current_weather['Temperature']['Metric']['Value'],
        "humidity": current_weather['RelativeHumidity'],
        "wind_speed": current_weather['Wind']['Speed']['Metric']['Value'],
        "has_precipitation": current_weather['HasPrecipitation'],
        "precipitation_probability": precipitation_probability,
        "weather_text": current_weather['WeatherText']
    }
    return weather, None


def check_bad_weather(weather):
    # Функция проверяет, плохая ли погода
    conditions = []
    temp = weather['temperature']
    wind = weather['wind_speed']
    precip_prob = weather['precipitation_probability']

    if temp < 0 or temp > 35:
        conditions.append(f"температура: {temp}°C")

    if wind > 50:
        conditions.append(f"скорость ветра: {wind} км/ч")

    if precip_prob > 70:
        conditions.append(f"вероятность осадков: {precip_prob}%")

    # Если ничего плохого нет, вернём None, иначе вернём список плохих условий
    return conditions if conditions else None


@app.route('/')
def index():
    # Главная страница, где пользователь вводит начальный и конечный города
    return render_template('index.html')


@app.route('/check_weather', methods=['POST'])
def check_weather_route():
    # Когда пользователь нажимает кнопку "Проверить погоду",
    # мы берём данные из формы и пытаемся найти погоду
    start_city = request.form.get('start_city', '').strip()
    end_city = request.form.get('end_city', '').strip()

    # Проверяем, ввели ли пользователь оба города
    if not start_city or not end_city:
        return render_template('error.html', error_message="Вы не ввели название города.")

    # Берём погоду для обоих городов
    start_weather, start_error = get_weather(start_city)
    end_weather, end_error = get_weather(end_city)

    # Если возникли ошибки, покажем их пользователю
    if start_error:
        return render_template('error.html', error_message=f"Для города {start_city}: {start_error}")
    if end_error:
        return render_template('error.html', error_message=f"Для города {end_city}: {end_error}")

    # Проверяем, нет ли плохой погоды
    start_conditions = check_bad_weather(start_weather)
    end_conditions = check_bad_weather(end_weather)

    # Показываем результат пользователю
    return render_template('result.html',
                           start_weather=start_weather,
                           end_weather=end_weather,
                           start_conditions=start_conditions,
                           end_conditions=end_conditions)


if __name__ == '__main__':
    # Запускаем сайт в режиме отладки. Если что-то пойдёт не так, мы увидим ошибку в консоли.
    app.run(debug=True)
