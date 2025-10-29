from functools import lru_cache
from typing import Annotated

from fastapi import Depends, FastAPI

from config import Settings

description = """
This emulates the SoundTouch servers so you don't need connectivity
to use speakers.

## Marge

dunno yet

## Bmx

also dunno
"""

tags_metadata = [
    {
        "name": "marge",
        "description": "Oh Homie, stop bricking my speakers!",
    },
    {
        "name": "bmx",
        "description": "lord knows",
    },
]
app = FastAPI(
    title="SoundCork",
    description=description,
    summary="Emulates SoundTouch servers.",
    version="0.0.1",
    openapi_tags=tags_metadata,
)


@lru_cache
def get_settings():
    return Settings()


@app.get("/")
def read_root():
    return {"Bose": "Can't Brick Us"}


@app.post(
    "/marge/streaming/support/power_on",
    tags=["marge"],
)
def power_on(settings: Annotated[Settings, Depends(get_settings)]):
    return (
        f'<?xml version="1.0" encoding="UTF-8" ?><device-data><device id="{settings.device_id}">'
        f"<serialnumber>{settings.device_serial_number}</serialnumber>"
        f"<firmware-version>{settings.firmware_version}</firmware-version>"
        f'<product product_code={settings.product_code} type={settings.type}>'
        f'<serialnumber>{settings.product_serial_number}</serialnumber>'
        f'</product></device><diagnostic-data><device-landscape>'
        f'<gateway-ip-address>{settings.gateway_ip_address}</gateway-ip-address>'
        f'<macaddresses><macaddress>{"</macaddress><macaddress>".join(settings.macaddresses)}</macaddress></macaddresses>'
        f"<ip-address>{settings.ip_address}</ip-address>"
        f'<network-connection-type>{settings.type}</network-connection-type>'
        "</device-landscape><network-landscape>"
        '<network-data xmlns="http://www.Bose.com/Schemas/2012-12/NetworkMonitor/" />'
        "</network-landscape></diagnostic-data></device-data>"
    )
