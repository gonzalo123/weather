from sense_hat import SenseHat
from influxdb import InfluxDBClient
import datetime
import logging
import requests
import json
from subprocess import check_output
import os
import sys
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)

current_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(dotenv_path="{}/.env".format(current_dir))

sensor_mac_address = os.getenv("BEEWI_SENSOR")
openweathermap_api_key = os.getenv("OPENWEATHERMAP_API_KEY")
influxdb_host = os.getenv("INFLUXDB_HOST")
influxdb_port = os.getenv("INFLUXDB_PORT")
influxdb_database = os.getenv("INFLUXDB_DATABASE")

reader = '{}/reader.js'.format(current_dir)


def get_rain_level_from_weather(weather):
    rain = False
    rain_level = 0
    if len(weather) > 0:
        for w in weather:
            if w['icon'] == '09d':
                rain = True
                rain_level = 1
            elif w['icon'] == '10d':
                rain = True
                rain_level = 2
            elif w['icon'] == '11d':
                rain = True
                rain_level = 3
            elif w['icon'] == '13d':
                rain = True
                rain_level = 4

    return rain, rain_level


def openweathermap():
    data = {}
    r = requests.get(
        "http://api.openweathermap.org/data/2.5/weather?id=3110044&appid={}&units=metric".format(
            openweathermap_api_key))

    if r.status_code == 200:
        current_data = r.json()
        data['weather'] = current_data['main']
        rain, rain_level = get_rain_level_from_weather(current_data['weather'])
        data['weather']['rain'] = rain
        data['weather']['rain_level'] = rain_level

    r2 = requests.get(
        "http://api.openweathermap.org/data/2.5/uvi?lat=43.32&lon=-1.93&appid={}".format(openweathermap_api_key))
    if r2.status_code == 200:
        data['uvi'] = r2.json()

    r3 = requests.get(
        "http://api.openweathermap.org/data/2.5/forecast?id=3110044&appid={}&units=metric".format(
            openweathermap_api_key))

    if r3.status_code == 200:
        forecast = r3.json()['list']
        data['forecast'] = []
        for f in forecast:
            rain, rain_level = get_rain_level_from_weather(f['weather'])
            data['forecast'].append({
                "dt": f['dt'],
                "fields": {
                    "temp": float(f['main']['temp']),
                    "humidity": float(f['main']['humidity']),
                    "rain": rain,
                    "rain_level": int(rain_level),
                    "pressure": float(float(f['main']['pressure']))
                }
            })

        return data


def persists(measurement, fields, location, time):
    logging.info("{} {} [{}] {}".format(time, measurement, location, fields))
    influx_client.write_points([{
        "measurement": measurement,
        "tags": {"location": location},
        "time": time,
        "fields": fields
    }])


def in_sensors():
    try:
        sense = SenseHat()
        pressure = sense.get_pressure()
        reader_output = check_output([reader, sensor_mac_address]).strip()
        sensor_info = json.loads(reader_output)
        temperature = sensor_info['temperature']
        humidity = sensor_info['humidity']

        persists(measurement='home_pressure', fields={"value": float(pressure)}, location="in", time=current_time)
        persists(measurement='home_humidity', fields={"value": float(humidity)}, location="in", time=current_time)
        persists(measurement='home_temperature', fields={"value": float(temperature)}, location="in",
                 time=current_time)
    except Exception as err:
        logging.error(err)


def out_sensors():
    try:
        out_info = openweathermap()

        persists(measurement='home_pressure',
                 fields={"value": float(out_info['weather']['pressure'])},
                 location="out",
                 time=current_time)
        persists(measurement='home_humidity',
                 fields={"value": float(out_info['weather']['humidity'])},
                 location="out",
                 time=current_time)
        persists(measurement='home_temperature',
                 fields={"value": float(out_info['weather']['temp'])},
                 location="out",
                 time=current_time)
        persists(measurement='home_rain',
                 fields={"value": out_info['weather']['rain'], "level": out_info['weather']['rain_level']},
                 location="out",
                 time=current_time)
        persists(measurement='home_uvi',
                 fields={"value": float(out_info['uvi']['value'])},
                 location="out",
                 time=current_time)
        for f in out_info['forecast']:
            persists(measurement='home_weather_forecast',
                     fields=f['fields'],
                     location="out",
                     time=datetime.datetime.utcfromtimestamp(f['dt']).isoformat())

    except Exception as err:
        logging.error(err)


influx_client = InfluxDBClient(host=influxdb_host, port=influxdb_port, database=influxdb_database)
current_time = datetime.datetime.utcnow().isoformat()

in_sensors()
out_sensors()
