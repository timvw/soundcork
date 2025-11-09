from typing import List

from pydantic import BaseModel


class BmxResponse(BaseModel):
    _links: dict
    askAgainAfter: int
    bmx_services: List


class IconSet(BaseModel):
    defaultAlbumArt: str
    largeSvg: str
    monochromePng: str
    monochromeSvg: str
    smallSvg: str


class Asset(BaseModel):
    color: str
    description: str
    icons: IconSet
    name: str
    shortDescription: str


class Id(BaseModel):
    name: str
    value: int


class Service(BaseModel):
    _links: dict
    askAdapter: bool
    assets: Asset
    baseUrl: str
    signupUrl: str
    streamTypes: List
    id: Id
    authenticationModel: dict


class Stream(BaseModel):
    _links: dict
    bufferingTimeout: int
    connectingTimeout: int
    hasPlaylist: bool
    isRealtime: bool
    streamUrl: str


class Audio(BaseModel):
    hasPlaylist: bool
    isRealtime: bool
    maxTimeout: int
    streamUrl: str
    streams: List


class BmxPlaybackResponse(BaseModel):
    _links: dict
    audio: Audio
    imageUrl: str
    isFavorite: bool
    name: str
    streamType: str