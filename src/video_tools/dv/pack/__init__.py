"""Contains model classes for DIF data packs contained in subcode, audio, and VAUX DIF blocks."""

from .aaux_source import (
    AAUXSource,
    AudioBlockPairing,
    AudioQuantization,
    EmphasisTimeConstant,
    LockedMode,
    StereoMode,
)
from .aaux_source_control import (
    AAUXRecordingMode,
    AAUXSourceControl,
    Direction,
    InsertChannel,
    ValidPlaybackSpeeds,
)
from .base import (
    CSVFieldMap,
    Pack,
    Type,
    ValidationError,
)
from .camera import (
    FocusMode,
    ValidFocusPositions,
)
from .camera_consumer import (
    AutoExposureMode,
    CameraConsumer1,
    CameraConsumer2,
    PanningDirection,
    ValidConsumerIrisFNumbers,
    ValidElectricZoomMagnifications,
    ValidFocalLengths,
    WhiteBalance,
    WhiteBalanceMode,
)
from .camera_shutter import CameraShutter
from .date import (
    AAUXRecordingDate,
    DaylightSavingTime,
    GenericDate,
    VAUXRecordingDate,
    Week,
)
from .misc import (
    AAUXBinaryGroup,
    GenericBinaryGroup,
    NoInfo,
    TitleBinaryGroup,
    Unknown,
    VAUXBinaryGroup,
)
from .parser import parse_binary
from .source_control import (
    CompressionCount,
    CopyProtection,
    InputSource,
    SourceSituation,
)
from .time import (
    AAUXRecordingTime,
    BlankFlag,
    ColorFrame,
    GenericTimecode,
    PolarityCorrection,
    TitleTimecode,
    VAUXRecordingTime,
)
from .vaux_source import (
    BlackAndWhiteFlag,
    ColorFramesID,
    SourceCode,
    SourceType,
    VAUXSource,
)
from .vaux_source_control import (
    FrameChange,
    FrameField,
    StillFieldPicture,
    VAUXRecordingMode,
    VAUXSourceControl,
)

__all__ = [
    "AAUXBinaryGroup",
    "AAUXRecordingDate",
    "AAUXRecordingMode",
    "AAUXRecordingTime",
    "AAUXSource",
    "AAUXSourceControl",
    "AudioBlockPairing",
    "AudioQuantization",
    "AutoExposureMode",
    "BlackAndWhiteFlag",
    "BlankFlag",
    "CameraConsumer1",
    "CameraConsumer2",
    "CameraShutter",
    "ColorFrame",
    "ColorFramesID",
    "CompressionCount",
    "CopyProtection",
    "CSVFieldMap",
    "DaylightSavingTime",
    "Direction",
    "EmphasisTimeConstant",
    "FocusMode",
    "FrameChange",
    "FrameField",
    "GenericBinaryGroup",
    "GenericDate",
    "GenericTimecode",
    "InputSource",
    "InsertChannel",
    "LockedMode",
    "NoInfo",
    "Pack",
    "PanningDirection",
    "parse_binary",
    "PolarityCorrection",
    "SourceCode",
    "SourceSituation",
    "SourceType",
    "StereoMode",
    "StillFieldPicture",
    "TitleBinaryGroup",
    "TitleTimecode",
    "Type",
    "Unknown",
    "ValidationError",
    "ValidConsumerIrisFNumbers",
    "ValidElectricZoomMagnifications",
    "ValidFocalLengths",
    "ValidFocusPositions",
    "ValidPlaybackSpeeds",
    "VAUXBinaryGroup",
    "VAUXRecordingDate",
    "VAUXRecordingMode",
    "VAUXRecordingTime",
    "VAUXSource",
    "VAUXSourceControl",
    "Week",
    "WhiteBalance",
    "WhiteBalanceMode",
]
