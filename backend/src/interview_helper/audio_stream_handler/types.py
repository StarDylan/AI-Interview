import numpy as np
from typing import Any
from dataclasses import dataclass

type PCMAudioArray = np.ndarray[tuple[Any], np.dtype[np.float32]]


@dataclass
class AudioChunk:
    data: PCMAudioArray
    framerate: int
    number_of_channels: int


@dataclass
class ICECandidate:
    foundation: str
    component: int
    protocol: str
    priority: int
    ip: str
    port: int
    ice_type: str
