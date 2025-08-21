import numpy as np
import numpy.typing as nptype
from dataclasses import dataclass

type PCMAudioArray = nptype.NDArray[np.int16]


@dataclass
class AudioChunk:
    data: list[PCMAudioArray]
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
