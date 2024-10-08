import pytest

import tests.dv.block.test_base as test_base
import video_tools.dv.block as block
from tests.dv.block.test_base import BlockBinaryTestCase, BlockValidateCase
from tests.dv.util import NTSC_FILE, PAL_FILE

TRAILER = "".join([" FF"] * 72)


@pytest.mark.parametrize(
    "tc",
    [
        # pedantic DIF blocks to exercise code branches
        BlockBinaryTestCase(
            name="variety of values",
            input=f"1F 07 00  BF 2A 7B 7C 7D {TRAILER}",
            parsed=block.Header(
                block_id=block.BlockID(
                    type=block.Type.HEADER,
                    sequence=0xF,
                    channel=0,
                    dif_sequence=0,
                    dif_block=0,
                ),
                video_frame_dif_sequence_count=12,
                track_pitch=block.TrackPitch.D7_STANDARD_FORMAT,
                pilot_frame=0,
                application_id_track=block.ApplicationIDTrack.RESERVED_2,
                application_id_1=block.ApplicationID1.RESERVED_3,
                application_id_2=block.ApplicationID2.RESERVED_4,
                application_id_3=block.ApplicationID3.RESERVED_5,
            ),
            file_info=PAL_FILE,
        ),
        BlockBinaryTestCase(
            name="missing stuff",
            input=f"1F 07 00  3F FF 7F 7F 7F {TRAILER}",
            parsed=block.Header(
                block_id=block.BlockID(
                    type=block.Type.HEADER,
                    sequence=0xF,
                    channel=0,
                    dif_sequence=0,
                    dif_block=0,
                ),
                video_frame_dif_sequence_count=10,
                track_pitch=None,
                pilot_frame=None,
                application_id_track=None,
                application_id_1=None,
                application_id_2=None,
                application_id_3=None,
            ),
            file_info=NTSC_FILE,
        ),
        # real DIF blocks that I have captured from a Sony DCR-TRV460
        BlockBinaryTestCase(
            name="basic test: standard play, NTSC, consumer format, first header, pilot 1",
            input=f"1F 07 00  3F 78 78 78 78 {TRAILER}",
            parsed=block.Header(
                block_id=block.BlockID(
                    type=block.Type.HEADER,
                    sequence=0xF,
                    channel=0,
                    dif_sequence=0,
                    dif_block=0,
                ),
                video_frame_dif_sequence_count=10,
                track_pitch=block.TrackPitch.STANDARD_PLAY,
                pilot_frame=1,
                application_id_track=block.ApplicationIDTrack.CONSUMER_DIGITAL_VCR,
                application_id_1=block.ApplicationID1.CONSUMER_DIGITAL_VCR,
                application_id_2=block.ApplicationID2.CONSUMER_DIGITAL_VCR,
                application_id_3=block.ApplicationID3.CONSUMER_DIGITAL_VCR,
            ),
            file_info=NTSC_FILE,
        ),
        BlockBinaryTestCase(
            name="basic test: standard play, NTSC, consumer format, first header, pilot 0",
            input=f"1F 07 00  3F 68 78 78 78 {TRAILER}",
            parsed=block.Header(
                block_id=block.BlockID(
                    type=block.Type.HEADER,
                    sequence=0xF,
                    channel=0,
                    dif_sequence=0,
                    dif_block=0,
                ),
                video_frame_dif_sequence_count=10,
                track_pitch=block.TrackPitch.STANDARD_PLAY,
                pilot_frame=0,
                application_id_track=block.ApplicationIDTrack.CONSUMER_DIGITAL_VCR,
                application_id_1=block.ApplicationID1.CONSUMER_DIGITAL_VCR,
                application_id_2=block.ApplicationID2.CONSUMER_DIGITAL_VCR,
                application_id_3=block.ApplicationID3.CONSUMER_DIGITAL_VCR,
            ),
            file_info=NTSC_FILE,
        ),
        BlockBinaryTestCase(
            name="basic test: long play, NTSC, consumer format, first header, pilot 0",
            input=f"1F 07 00  3F 48 78 78 78 {TRAILER}",
            parsed=block.Header(
                block_id=block.BlockID(
                    type=block.Type.HEADER,
                    sequence=0xF,
                    channel=0,
                    dif_sequence=0,
                    dif_block=0,
                ),
                video_frame_dif_sequence_count=10,
                track_pitch=block.TrackPitch.LONG_PLAY,
                pilot_frame=0,
                application_id_track=block.ApplicationIDTrack.CONSUMER_DIGITAL_VCR,
                application_id_1=block.ApplicationID1.CONSUMER_DIGITAL_VCR,
                application_id_2=block.ApplicationID2.CONSUMER_DIGITAL_VCR,
                application_id_3=block.ApplicationID3.CONSUMER_DIGITAL_VCR,
            ),
            file_info=NTSC_FILE,
        ),
        # DVCPRO50 color bars from https://archive.org/details/SMPTEColorBarsBadTracking
        BlockBinaryTestCase(
            name="DVCPRO50 color bars",
            input=f"1F 4F 00  3F F9 79 79 79 {TRAILER}",
            parsed=block.Header(
                block_id=block.BlockID(
                    type=block.Type.HEADER,
                    sequence=0xF,
                    channel=1,
                    dif_sequence=4,
                    dif_block=0,
                ),
                video_frame_dif_sequence_count=10,
                track_pitch=None,
                pilot_frame=None,
                application_id_track=block.ApplicationIDTrack.D7_STANDARD_FORMAT,
                application_id_1=block.ApplicationID1.D7_STANDARD_FORMAT,
                application_id_2=block.ApplicationID2.D7_STANDARD_FORMAT,
                application_id_3=block.ApplicationID3.D7_STANDARD_FORMAT,
            ),
            file_info=NTSC_FILE,
        ),
    ],
    ids=lambda tc: tc.name,
)
def test_header_block_binary(tc: BlockBinaryTestCase) -> None:
    test_base.run_block_binary_test_case(tc)


@pytest.mark.parametrize(
    "tc",
    [
        BlockValidateCase(
            name="invalid DIF sequence count",
            input=block.Header(
                block_id=block.BlockID(
                    type=block.Type.HEADER,
                    sequence=0xF,
                    channel=0,
                    dif_sequence=0,
                    dif_block=0,
                ),
                video_frame_dif_sequence_count=9,
                track_pitch=block.TrackPitch.STANDARD_PLAY,
                pilot_frame=1,
                application_id_track=block.ApplicationIDTrack.CONSUMER_DIGITAL_VCR,
                application_id_1=block.ApplicationID1.CONSUMER_DIGITAL_VCR,
                application_id_2=block.ApplicationID2.CONSUMER_DIGITAL_VCR,
                application_id_3=block.ApplicationID3.CONSUMER_DIGITAL_VCR,
            ),
            failure="DIF header block must specify sequence count of 10 or 12.",
            file_info=NTSC_FILE,
        ),
        BlockValidateCase(
            name="DIF sequence count does not match system",
            input=block.Header(
                block_id=block.BlockID(
                    type=block.Type.HEADER,
                    sequence=0xF,
                    channel=0,
                    dif_sequence=0,
                    dif_block=0,
                ),
                video_frame_dif_sequence_count=12,
                track_pitch=block.TrackPitch.STANDARD_PLAY,
                pilot_frame=1,
                application_id_track=block.ApplicationIDTrack.CONSUMER_DIGITAL_VCR,
                application_id_1=block.ApplicationID1.CONSUMER_DIGITAL_VCR,
                application_id_2=block.ApplicationID2.CONSUMER_DIGITAL_VCR,
                application_id_3=block.ApplicationID3.CONSUMER_DIGITAL_VCR,
            ),
            failure="DIF header block does not match with expected system SYS_525_60.",
            file_info=NTSC_FILE,
        ),
        BlockValidateCase(
            name="partial track information: no track pitch",
            input=block.Header(
                block_id=block.BlockID(
                    type=block.Type.HEADER,
                    sequence=0xF,
                    channel=0,
                    dif_sequence=0,
                    dif_block=0,
                ),
                video_frame_dif_sequence_count=10,
                track_pitch=None,
                pilot_frame=1,
                application_id_track=block.ApplicationIDTrack.CONSUMER_DIGITAL_VCR,
                application_id_1=block.ApplicationID1.CONSUMER_DIGITAL_VCR,
                application_id_2=block.ApplicationID2.CONSUMER_DIGITAL_VCR,
                application_id_3=block.ApplicationID3.CONSUMER_DIGITAL_VCR,
            ),
            failure="Track pitch and pilot frame must be both present or absent together.",
            file_info=NTSC_FILE,
        ),
        BlockValidateCase(
            name="partial track information: no pilot frame",
            input=block.Header(
                block_id=block.BlockID(
                    type=block.Type.HEADER,
                    sequence=0xF,
                    channel=0,
                    dif_sequence=0,
                    dif_block=0,
                ),
                video_frame_dif_sequence_count=10,
                track_pitch=block.TrackPitch.STANDARD_PLAY,
                pilot_frame=None,
                application_id_track=block.ApplicationIDTrack.CONSUMER_DIGITAL_VCR,
                application_id_1=block.ApplicationID1.CONSUMER_DIGITAL_VCR,
                application_id_2=block.ApplicationID2.CONSUMER_DIGITAL_VCR,
                application_id_3=block.ApplicationID3.CONSUMER_DIGITAL_VCR,
            ),
            failure="Track pitch and pilot frame must be both present or absent together.",
            file_info=NTSC_FILE,
        ),
        BlockValidateCase(
            name="negative pilot frame",
            input=block.Header(
                block_id=block.BlockID(
                    type=block.Type.HEADER,
                    sequence=0xF,
                    channel=0,
                    dif_sequence=0,
                    dif_block=0,
                ),
                video_frame_dif_sequence_count=10,
                track_pitch=block.TrackPitch.STANDARD_PLAY,
                pilot_frame=-1,
                application_id_track=block.ApplicationIDTrack.CONSUMER_DIGITAL_VCR,
                application_id_1=block.ApplicationID1.CONSUMER_DIGITAL_VCR,
                application_id_2=block.ApplicationID2.CONSUMER_DIGITAL_VCR,
                application_id_3=block.ApplicationID3.CONSUMER_DIGITAL_VCR,
            ),
            failure="DIF header block must specify a pilot frame of 0 or 1.",
            file_info=NTSC_FILE,
        ),
        BlockValidateCase(
            name="pilot frame high",
            input=block.Header(
                block_id=block.BlockID(
                    type=block.Type.HEADER,
                    sequence=0xF,
                    channel=0,
                    dif_sequence=0,
                    dif_block=0,
                ),
                video_frame_dif_sequence_count=10,
                track_pitch=block.TrackPitch.STANDARD_PLAY,
                pilot_frame=2,
                application_id_track=block.ApplicationIDTrack.CONSUMER_DIGITAL_VCR,
                application_id_1=block.ApplicationID1.CONSUMER_DIGITAL_VCR,
                application_id_2=block.ApplicationID2.CONSUMER_DIGITAL_VCR,
                application_id_3=block.ApplicationID3.CONSUMER_DIGITAL_VCR,
            ),
            failure="DIF header block must specify a pilot frame of 0 or 1.",
            file_info=NTSC_FILE,
        ),
    ],
    ids=lambda tc: tc.name,
)
def test_header_block_validate_write(tc: BlockValidateCase) -> None:
    test_base.run_block_validate_case(tc)


def test_header_block_validate_read() -> None:
    """Test validation failures when reading a header block from binary.

    This is just a quick test to make sure the validation happens; most rules are tested in
    test_header_block_validate_write.
    """
    failure = "DIF header block does not match with expected system SYS_525_60."
    with pytest.raises(block.BlockError, match=failure):
        block.Header.parse_binary(bytes.fromhex(f"1F 07 00  BF 78 78 78 78 {TRAILER}"), NTSC_FILE)

    # also check the failure branches in parse_binary
    failure = "Zero bit in DIF header block is unexpectedly not zero."
    with pytest.raises(block.BlockError, match=failure):
        block.Header.parse_binary(bytes.fromhex(f"1F 07 00  7F 78 78 78 78 {TRAILER}"), NTSC_FILE)

    failure = "Reserved bits in DIF header block are unexpectedly in use."
    with pytest.raises(block.BlockError, match=failure):
        block.Header.parse_binary(bytes.fromhex(f"1F 07 00  3F 70 78 78 78 {TRAILER}"), NTSC_FILE)

    failure = "Reserved bits in DIF header block are unexpectedly in use."
    with pytest.raises(block.BlockError, match=failure):
        block.Header.parse_binary(bytes.fromhex(f"1F 07 00  3F 78 70 78 78 {TRAILER}"), NTSC_FILE)

    failure = "Reserved bits in DIF header block are unexpectedly in use."
    with pytest.raises(block.BlockError, match=failure):
        block.Header.parse_binary(bytes.fromhex(f"1F 07 00  3F 78 78 70 78 {TRAILER}"), NTSC_FILE)

    failure = "Reserved bits in DIF header block are unexpectedly in use."
    with pytest.raises(block.BlockError, match=failure):
        block.Header.parse_binary(bytes.fromhex(f"1F 07 00  3F 78 78 78 70 {TRAILER}"), NTSC_FILE)

    failure = "Unexpected values in the track information area of the DIF header block."
    with pytest.raises(block.BlockError, match=failure):
        block.Header.parse_binary(bytes.fromhex(f"1F 07 00  3F A8 78 78 78 {TRAILER}"), NTSC_FILE)

    failure = "Transmitting flags for some DIF blocks are off in the DIF header block."
    with pytest.raises(block.BlockError, match=failure):
        block.Header.parse_binary(bytes.fromhex(f"1F 07 00  3F 78 F8 78 78 {TRAILER}"), NTSC_FILE)

    failure = "Transmitting flags for some DIF blocks are off in the DIF header block."
    with pytest.raises(block.BlockError, match=failure):
        block.Header.parse_binary(bytes.fromhex(f"1F 07 00  3F 78 78 F8 78 {TRAILER}"), NTSC_FILE)

    failure = "Transmitting flags for some DIF blocks are off in the DIF header block."
    with pytest.raises(block.BlockError, match=failure):
        block.Header.parse_binary(bytes.fromhex(f"1F 07 00  3F 78 78 78 F8 {TRAILER}"), NTSC_FILE)
