import argparse
from typing import BinaryIO

from colorama import Fore, Style, just_fix_windows_console

import video_tools.dv.block as block
import video_tools.dv.dif as dif
import video_tools.dv.file.info as dv_file_info
import video_tools.io_util as io_util


class DVDIFDumpArgs(argparse.Namespace):
    input_dv_file: list[str]
    frame_number: int | None
    block_type: str | None


def parse_args() -> DVDIFDumpArgs:
    parser = argparse.ArgumentParser(
        prog="dv_dif_dump",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description="Dump raw DIF blocks from a DV file.",
    )
    parser.add_argument(
        "input_dv_file",
        type=str,
        nargs=1,
        help="Input raw DV binary file.  It must not be in any kind of container.",
    )
    parser.add_argument(
        "--frame-number",
        type=int,
        help="Zero-based frame number to dump DIF blocks for.  All frames are dumped by default, "
        "which is especially useful if you want to dump two files and compare the output with an "
        "external text comparison tool.",
    )
    parser.add_argument(
        "--block-type",
        choices=[type.name for type in block.Type],
        type=str,
        help="Restrict output to only DIF blocks of a certain type.",
    )

    return parser.parse_args(namespace=DVDIFDumpArgs())


def read_frame_bytes(file: BinaryIO, file_info: dv_file_info.Info, frame_number: int) -> bytes:
    if frame_number < 0 or frame_number >= file_info.video_frame_count:
        raise ValueError("Frame number is out of range for this file.")

    file.seek(frame_number * file_info.video_frame_size)
    frame_bytes = io_util.read_file_bytes(file, file_info.video_frame_size)
    if len(frame_bytes) != file_info.video_frame_size:
        raise ValueError("Could not read an entire frame.")
    return frame_bytes


def dump_dif_blocks(
    frame_bytes: bytes,
    file_info: dv_file_info.Info,
    frame_number: int,
    block_type: block.Type | None,
) -> None:
    b_start = 0  # current block starting position
    type_color = {
        # Colors from DVRescue
        block.Type.HEADER: Fore.MAGENTA,
        block.Type.SUBCODE: Fore.CYAN,
        block.Type.VAUX: Fore.YELLOW,
        block.Type.AUDIO: Fore.GREEN,
        block.Type.VIDEO: Fore.BLUE,
    }
    for channel in range(file_info.video_frame_channel_count):
        for sequence in range(file_info.video_frame_dif_sequence_count):
            print(
                f"{Fore.RED}============================== "
                f"FRAME {frame_number} CHANNEL {channel} SEQUENCE {sequence} "
                f"=============================={Style.RESET_ALL}"
            )
            for blk in range(len(dif.DIF_SEQUENCE_TRANSMISSION_ORDER)):
                block_id = block.BlockID.parse_binary(frame_bytes[b_start : b_start + 3], file_info)
                if block_type is None or block_type == block_id.type:
                    if block_id.channel != channel or block_id.dif_sequence != sequence:
                        # This probably means we have encountered a more advanced, higher-bandwidth
                        # video format that we haven't yet added support for.  (Or the file itself
                        # is badly corrupted - beyond the corruption of tape read/dropout errors.)
                        print(
                            f"{Fore.RED}WARNING:  DIF block {blk} does not have the "
                            f"expected channel or DIF sequence numbers.{Style.RESET_ALL}"
                        )
                    print(
                        f"{blk:3} {frame_bytes[b_start:b_start+3].hex().upper()} "
                        f"{type_color[block_id.type]}"
                        f"{frame_bytes[b_start+3:b_start+block.BLOCK_SIZE].hex().upper()}"
                        f"{Style.RESET_ALL}"
                    )
                b_start += block.BLOCK_SIZE


def main() -> None:
    just_fix_windows_console()
    args = parse_args()
    input_dv_filename = args.input_dv_file[0]
    assert input_dv_filename is not None

    print(f"Reading frame data from {input_dv_filename}...")
    with open(input_dv_filename, mode="rb") as file:
        info = dv_file_info.read_dv_file_info(file)

        frames_to_dump = (
            list(range(info.video_frame_count))
            if args.frame_number is None
            else [args.frame_number]
        )
        for frame_number in frames_to_dump:
            frame_bytes = read_frame_bytes(file, info, frame_number)

            dump_dif_blocks(
                frame_bytes,
                info,
                frame_number,
                block.Type[args.block_type] if args.block_type is not None else None,
            )


if __name__ == "__main__":
    main()
