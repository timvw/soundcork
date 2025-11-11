from datetime import datetime
from typing import List

from model import SourceProvider


def source_providers() -> List:

    providers = [
        "PANDORA",
        "INTERNET_RADIO",
        "OFF",
        "LOCAL",
        "AIRPLAY",
        "CURRATED_RADIO",
        "STORED_MUSIC",
        "SLAVE_SOURCE",
        "AUX",
        "RECOMMENDED_INTERNET_RADIO",
        "LOCAL_INTERNET_RADIO",
        "GLOBAL_INTERNET_RADIO",
        "HELLO",
        "DEEZER",
        "SPOTIFY",
        "IHEART",
        "SIRIUSXM",
        "GOOGLE_PLAY_MUSIC",
        "QQMUSIC",
        "AMAZON",
        "LOCAL_MUSIC",
        "WBMX",
        "SOUNDCLOUD",
        "TIDAL",
        "TUNEIN",
        "QPLAY",
        "JUKE",
        "BBC",
        "DARFM",
        "7DIGITAL",
        "SAAVN",
        "RDIO",
        "PHONE_MUSIC",
        "ALEXA",
        "RADIOPLAYER",
        "RADIO.COM",
        "RADIO_COM",
        "SIRIUSXM_EVEREST",
    ]
    datestr = "2012-09-19T12:43:00.000+00:00"
    return [
        SourceProvider(id=i[0], created_on=datestr, name=i[1], updated_on=datestr)
        for i in enumerate(providers, start=1)
    ]
