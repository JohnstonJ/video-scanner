from dataclasses import dataclass

import pytest

import video_tools.dv.block as block
import video_tools.dv.file.info as dv_file_info
from tests.dv.util import NTSC_FILE, PAL_FILE

# ======================== REUSABLE TEST CASES ========================


@dataclass(kw_only=True)
class BlockBinaryTestCase:
    name: str
    input: str
    parsed: block.Block
    output: str | None = None
    file_info: dv_file_info.Info


def run_block_binary_test_case(tc: BlockBinaryTestCase) -> None:
    """Test round trip of a block from binary, to parsed, and then back to binary."""
    parsed = block.parse_binary(bytes.fromhex(tc.input), tc.file_info)
    assert parsed == tc.parsed
    updated = parsed.to_binary(tc.file_info)
    assert updated == bytes.fromhex(tc.output if tc.output is not None else tc.input)


@dataclass(kw_only=True)
class BlockValidateCase:
    name: str
    input: block.Block
    failure: str
    file_info: dv_file_info.Info


def run_block_validate_case(tc: BlockValidateCase) -> None:
    """Test validation failures when writing a block to binary."""
    with pytest.raises(block.BlockError, match=tc.failure):
        tc.input.to_binary(tc.file_info)


# ======================== DIF BLOCK ID TESTS ========================


@dataclass
class BlockIDBinaryTestCase:
    name: str
    input: str
    parsed: block.BlockID
    file_info: dv_file_info.Info


@pytest.mark.parametrize(
    "tc",
    [
        BlockIDBinaryTestCase(
            name="basic test",
            input="7A 4F 06",
            parsed=block.BlockID(
                type=block.Type.AUDIO,
                sequence=0xA,
                channel=1,
                dif_sequence=4,
                dif_block=6,
            ),
            file_info=NTSC_FILE,
        ),
        BlockIDBinaryTestCase(
            name="more basic testing",
            input="93 77 7D",
            parsed=block.BlockID(
                type=block.Type.VIDEO,
                sequence=0x3,
                channel=0,
                dif_sequence=7,
                dif_block=125,
            ),
            file_info=NTSC_FILE,
        ),
        BlockIDBinaryTestCase(
            name="max NTSC DIF sequence number",
            input="1F 97 00",
            parsed=block.BlockID(
                type=block.Type.HEADER,
                sequence=0xF,
                channel=0,
                dif_sequence=9,
                dif_block=0,
            ),
            file_info=NTSC_FILE,
        ),
        BlockIDBinaryTestCase(
            name="max PAL DIF sequence number",
            input="1F B7 00",
            parsed=block.BlockID(
                type=block.Type.HEADER,
                sequence=0xF,
                channel=0,
                dif_sequence=11,
                dif_block=0,
            ),
            file_info=PAL_FILE,
        ),
        BlockIDBinaryTestCase(
            name="max VAUX DIF block number",
            input="50 07 02",
            parsed=block.BlockID(
                type=block.Type.VAUX,
                sequence=0x0,
                channel=0,
                dif_sequence=0,
                dif_block=2,
            ),
            file_info=NTSC_FILE,
        ),
    ],
    ids=lambda tc: tc.name,
)
def test_block_id_binary(tc: BlockIDBinaryTestCase) -> None:
    parsed = block.BlockID.parse_binary(bytes.fromhex(tc.input), tc.file_info)
    assert parsed == tc.parsed
    updated = parsed.to_binary(tc.file_info)
    assert updated == bytes.fromhex(tc.input)


@dataclass
class BlockIDValidateTestCase:
    name: str
    input: block.BlockID
    failure: str
    file_info: dv_file_info.Info


@pytest.mark.parametrize(
    "tc",
    [
        BlockIDValidateTestCase(
            name="invalid header sequence",
            input=block.BlockID(
                type=block.Type.HEADER,
                sequence=0x0,
                channel=0,
                dif_sequence=0,
                dif_block=0,
            ),
            failure=(
                "DIF block ID for header or subcode block has unexpected "
                "non-0xF sequence number of 0x0."
            ),
            file_info=NTSC_FILE,
        ),
        BlockIDValidateTestCase(
            name="invalid subcode sequence",
            input=block.BlockID(
                type=block.Type.SUBCODE,
                sequence=0x0,
                channel=0,
                dif_sequence=0,
                dif_block=0,
            ),
            failure=(
                "DIF block ID for header or subcode block has unexpected "
                "non-0xF sequence number of 0x0."
            ),
            file_info=NTSC_FILE,
        ),
        BlockIDValidateTestCase(
            name="invalid DIF sequence sequence",
            input=block.BlockID(
                type=block.Type.HEADER,
                sequence=0xF,
                channel=0,
                dif_sequence=10,
                dif_block=0,
            ),
            failure=(
                "DIF block ID has DIF sequence number of 10 that "
                "is too high for system SYS_525_60."
            ),
            file_info=NTSC_FILE,
        ),
        BlockIDValidateTestCase(
            name="invalid DIF sequence sequence",
            input=block.BlockID(
                type=block.Type.HEADER,
                sequence=0xF,
                channel=0,
                dif_sequence=12,
                dif_block=0,
            ),
            failure=(
                "DIF block ID has DIF sequence number of 12 that "
                "is too high for system SYS_625_50."
            ),
            file_info=PAL_FILE,
        ),
        BlockIDValidateTestCase(
            name="DIF block number too high",
            input=block.BlockID(
                type=block.Type.HEADER,
                sequence=0xF,
                channel=0,
                dif_sequence=0,
                dif_block=1,
            ),
            failure=(
                "DIF block ID has DIF block number of 1 that "
                "is too high for a block type of HEADER."
            ),
            file_info=PAL_FILE,
        ),
    ],
    ids=lambda tc: tc.name,
)
def test_block_id_validate_write(tc: BlockIDValidateTestCase) -> None:
    """Test validation failures when writing a block ID to binary."""
    with pytest.raises(block.BlockError, match=tc.failure):
        tc.input.to_binary(tc.file_info)


def test_block_id_validate_read() -> None:
    """Test validation failures when reading a block ID from binary.

    This is just a quick test to make sure the validation happens; most rules are tested in
    test_block_id_validate_write.
    """

    failure = "DIF block ID has DIF block number of 3 that is too high for a block type of VAUX."
    with pytest.raises(block.BlockError, match=failure):
        block.BlockID.parse_binary(bytes.fromhex("50 07 03"), NTSC_FILE)

    # also check the failure branches in parse_binary
    failure = "Reserved bits in DIF block identifier were unexpectedly cleared."
    with pytest.raises(block.BlockError, match=failure):
        block.BlockID.parse_binary(bytes.fromhex("00 00 00"), NTSC_FILE)
