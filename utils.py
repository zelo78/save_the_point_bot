import requests
import config


def get_address_from_coords(*, longitude, latitude):
    '''Input: coordinates. Output: address'''
    location = f'{longitude},{latitude}'
    
    PARAMS = {
        'apikey': config.yandex_api,
        'format': 'json',
        'lang': 'ru_RU',
        'kind': 'house',
        'geocode': location,
    }

    #отправляем запрос по адресу геокодера.
    try:
        r = requests.get(url="https://geocode-maps.yandex.ru/1.x/", params=PARAMS)
        print(r)
        #получаем данные
        json_data = r.json()
        print(json_data)
        #вытаскиваем из всего пришедшего json именно строку с полным адресом.
        address_str = json_data["response"]["GeoObjectCollection"]["featureMember"][0]["GeoObject"]["metaDataProperty"]["GeocoderMetaData"]["AddressDetails"]["Country"]["AddressLine"]
        #возвращаем полученный адрес
        return address_str
    except Exception as e:
        #если не смогли, то возвращаем None
        return None