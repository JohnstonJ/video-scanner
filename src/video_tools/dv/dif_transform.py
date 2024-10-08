"""Contains functions for running user-provided commands to repair DV frame data."""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import asdict, dataclass, is_dataclass, replace
from typing import BinaryIO, Iterable, cast

import yaml

import video_tools.dv.data_util as du
import video_tools.dv.dif as dif
import video_tools.dv.pack as pack
from video_tools.typing import DataclassInstance

MOST_COMMON = "MOST_COMMON"

# Default thresholds
DEFAULT_MAX_CHANGED_PROPORTION = 0.05
DEFAULT_MAX_CONSECUTIVE_MODIFICATIONS = 3


@dataclass(frozen=True, kw_only=True)
class Thresholds:
    """Thresholds used to avoid accidentally making too many changes."""

    max_changed_proportion: float
    max_consecutive_modifications: int | None


@dataclass(kw_only=True)
class FrameChangeTracker:
    """Track changed frame statistics in order to watch Thresholds."""

    changed_frames: int = 0
    total_frames: int = 0
    last_consecutive_changed_frames: int = 0


@dataclass(frozen=True, kw_only=True)
class Command(ABC):
    """Base class for transforming frame data."""

    type: str
    start_frame: int
    end_frame: int | None
    thresholds: Thresholds

    def frame_range(self, all_frame_data: list[dif.FrameData]) -> Iterable[int]:
        """Return iterable of frame numbers that this command is supposed to operate on."""
        return range(
            self.start_frame,
            self.end_frame + 1 if self.end_frame is not None else len(all_frame_data),
        )

    def track_changed_frame(
        self,
        old_frame_data: dif.FrameData,
        new_frame_data: dif.FrameData,
        frame_number: int,
        tracker: FrameChangeTracker,
    ) -> None:
        """Track a changed frame in the FrameChangeTracker."""
        changed = old_frame_data != new_frame_data
        if changed:
            tracker.changed_frames += 1
            tracker.last_consecutive_changed_frames += 1
        else:
            tracker.last_consecutive_changed_frames = 0
        tracker.total_frames += 1

        if (
            self.thresholds.max_consecutive_modifications is not None
            and tracker.last_consecutive_changed_frames
            >= self.thresholds.max_consecutive_modifications
        ):
            raise ValueError(f"ERROR:  Changed too many frames in a row at frame {frame_number}.")

    def track_final_proportion(self, tracker: FrameChangeTracker) -> None:
        """Check the final proportion of changed frames against threshold."""
        proportion = float(tracker.changed_frames) / float(tracker.total_frames)
        print(
            f"Changed {proportion * 100:.2f}%, or {tracker.changed_frames}"
            f" of {tracker.total_frames} frames."
        )
        if proportion > self.thresholds.max_changed_proportion:
            raise ValueError("ERROR:  Changed too high a percentage of frames.")

    @abstractmethod
    def run(self, all_frame_data: list[dif.FrameData]) -> list[dif.FrameData]:
        """Run the command to modify all frames."""
        pass

    def command_expansion(self, all_frame_data: list[dif.FrameData]) -> list[Command]:
        """Split the command into multiple, more granular commands."""
        return [self]


def number_subpattern(field_name: str) -> str:
    return (
        r"((?P<"
        + field_name
        + r"_num>\d+)|(?P<"
        + field_name
        + r"_any>\*)|(\[(?P<"
        + field_name
        + r"_range_start>\d+)\s*,\s*(?P<"
        + field_name
        + r"_range_end>\d+)\]))"
    )


# Matches wildcards for command expansion
subcode_column_full_pattern = re.compile(
    r"^sc_pack_types_"
    + number_subpattern("channel")
    + "_"
    + number_subpattern("dif_sequence")
    + "_"
    + number_subpattern("pack")
    + r"$"
)
# Matches an exact subcode column specification
subcode_column_exact_pattern = re.compile(
    r"^sc_pack_types_(?P<channel>\d+)_(?P<dif_sequence>\d+)_(?P<pack>\d+)$"
)

ConstantValueType = int | DataclassInstance | str | None


@dataclass(frozen=True, kw_only=True)
class WriteConstantCommand(Command):
    """Writes the same constant value to all specified frames for the given column.

    If the specified value is MOST_COMMON, then the most common value in the given
    frame range will be chosen.

    For subcodes, the column must be specified as potential wildcards in the format
    sc_pack_types_<channel>_<dif sequence>_<pack number>.  That is the same as the
    format from the CSV file but with a pack number suffix so as to allow for
    modifying the packs individually.  Each numeric field can be an actual number,
    an inclusive range in the format "[start, end]", or a complete wildcard "*".
    All matching subcode packs will be modified using the same configured value
    and frame range.
    """

    column: str
    value: ConstantValueType

    def __str__(self) -> str:
        value_str = (
            "most common value"
            if self.value == MOST_COMMON
            else f"value {self.value_str(self.value)}"
        )
        return (
            f"write_constant to {self.column} in frames "
            f"[{self.start_frame}, {self.end_frame}] with {value_str}"
        )

    @staticmethod
    def parse_value_str(column: str, value_str: str | None) -> ConstantValueType:
        """Parse the configured value into the native data type used by FrameData."""
        if value_str == MOST_COMMON:
            return value_str
        value_str = value_str if value_str is not None else ""
        match column:
            case (
                "h_track_application_id"
                | "h_audio_application_id"
                | "h_video_application_id"
                | "h_subcode_application_id"
                | "sc_track_application_id"
                | "sc_subcode_application_id"
            ):
                assert value_str != ""
                return int(value_str, 0)
            case _ if subcode_column_full_pattern.match(column):
                # We used full pattern match because this is called before command expansion
                assert value_str != ""
                return int(value_str, 0)
            case _ if du.field_has_prefix(
                "sc_title_timecode", column, excluded_prefixes=["sc_title_timecode_bg"]
            ):
                return pack.TitleTimecode.parse_text_value(
                    du.remove_field_prefix("sc_title_timecode", column), value_str
                )
            case _ if du.field_has_prefix("sc_title_timecode_bg", column):
                return pack.TitleBinaryGroup.parse_text_value(
                    du.remove_field_prefix("sc_title_timecode_bg", column), value_str
                )
            case _ if du.field_has_prefix("sc_vaux_rec_date", column):
                return pack.VAUXRecordingDate.parse_text_value(
                    du.remove_field_prefix("sc_vaux_rec_date", column), value_str
                )
            case _ if du.field_has_prefix("sc_vaux_rec_time", column):
                return pack.VAUXRecordingTime.parse_text_value(
                    du.remove_field_prefix("sc_vaux_rec_time", column), value_str
                )
            case _:
                raise ValueError(f"Unsupported column {column} for write_constant command.")

    def value_str(self, value: ConstantValueType) -> str | None:
        """Convert the native data type used by FrameData into a configuration string."""
        match self.column:
            case (
                "h_track_application_id"
                | "h_audio_application_id"
                | "h_video_application_id"
                | "h_subcode_application_id"
                | "sc_track_application_id"
                | "sc_subcode_application_id"
            ):
                assert isinstance(value, int)
                return du.hex_int(value, 1)
            case _ if subcode_column_exact_pattern.match(self.column):
                assert isinstance(value, int)
                return du.hex_int(value, 2)
            case _ if du.field_has_prefix(
                "sc_title_timecode", self.column, excluded_prefixes=["sc_timecode_bg"]
            ):
                # assert is_dataclass isinstance(value, DataclassInstance)
                assert is_dataclass(value)
                return pack.TitleTimecode.to_text_value(
                    du.remove_field_prefix("sc_title_timecode", self.column),
                    cast(DataclassInstance, value),
                )
            case _ if du.field_has_prefix("sc_title_timecode_bg", self.column):
                assert is_dataclass(value)
                return pack.TitleBinaryGroup.to_text_value(
                    du.remove_field_prefix("sc_title_timecode_bg", self.column),
                    cast(DataclassInstance, value),
                )
            case _ if du.field_has_prefix("sc_vaux_rec_date", self.column):
                assert is_dataclass(value)
                return pack.VAUXRecordingDate.to_text_value(
                    du.remove_field_prefix("sc_vaux_rec_date", self.column),
                    cast(DataclassInstance, value),
                )
            case _ if du.field_has_prefix("sc_vaux_rec_time", self.column):
                assert is_dataclass(value)
                return pack.VAUXRecordingTime.to_text_value(
                    du.remove_field_prefix("sc_vaux_rec_time", self.column),
                    cast(DataclassInstance, value),
                )
            case _:
                raise ValueError(f"Unsupported column {self.column} for write_constant command.")

    def get_value_from_frame_data(self, frame_data: dif.FrameData) -> ConstantValueType:
        """Retrieve the value from FrameData using the configured column."""
        match self.column:
            case "h_track_application_id":
                return frame_data.header_track_application_id
            case "h_audio_application_id":
                return frame_data.header_audio_application_id
            case "h_video_application_id":
                return frame_data.header_video_application_id
            case "h_subcode_application_id":
                return frame_data.header_subcode_application_id
            case "sc_track_application_id":
                return frame_data.subcode_track_application_id
            case "sc_subcode_application_id":
                return frame_data.subcode_subcode_application_id
            case _ if (match := subcode_column_exact_pattern.match(self.column)):
                return frame_data.subcode_pack_types[int(match.group("channel"))][
                    int(match.group("dif_sequence"))
                ][int(match.group("pack"))]
            case _ if du.field_has_prefix(
                "sc_title_timecode", self.column, excluded_prefixes=["sc_timecode_bg"]
            ):
                return frame_data.subcode_title_timecode.value_subset_for_text_field(
                    du.remove_field_prefix("sc_title_timecode", self.column)
                )
            case _ if du.field_has_prefix("sc_title_timecode_bg", self.column):
                return frame_data.subcode_title_binary_group.value_subset_for_text_field(
                    du.remove_field_prefix("sc_title_timecode_bg", self.column)
                )
            case _ if du.field_has_prefix("sc_vaux_rec_date", self.column):
                return frame_data.subcode_vaux_recording_date.value_subset_for_text_field(
                    du.remove_field_prefix("sc_vaux_rec_date", self.column)
                )
            case _ if du.field_has_prefix("sc_vaux_rec_time", self.column):
                return frame_data.subcode_vaux_recording_time.value_subset_for_text_field(
                    du.remove_field_prefix("sc_vaux_rec_time", self.column)
                )
            case _:
                raise ValueError(f"Unsupported column {self.column} for write_constant command.")

    def set_frame_data_to_parsed_value(
        self, frame_data: dif.FrameData, value: ConstantValueType
    ) -> dif.FrameData:
        """Change the value in FrameData to the given value.

        The value needs to have already been parsed."""
        match self.column:
            case "h_track_application_id":
                assert isinstance(value, int)
                return replace(frame_data, header_track_application_id=value)
            case "h_audio_application_id":
                assert isinstance(value, int)
                return replace(frame_data, header_audio_application_id=value)
            case "h_video_application_id":
                assert isinstance(value, int)
                return replace(frame_data, header_video_application_id=value)
            case "h_subcode_application_id":
                assert isinstance(value, int)
                return replace(frame_data, header_subcode_application_id=value)
            case "sc_track_application_id":
                assert isinstance(value, int)
                return replace(frame_data, subcode_track_application_id=value)
            case "sc_subcode_application_id":
                assert isinstance(value, int)
                return replace(frame_data, subcode_subcode_application_id=value)
            case _ if (match := subcode_column_exact_pattern.match(self.column)):
                # Making a deep copy of frame_data.subcode_pack_types would be
                # the simple and naive way of doing this, but it's very slow.
                # Instead, we'll only copy the lists that we're actually changing.
                assert isinstance(value, int) or value is None
                channel = int(match.group("channel"))
                dif_sequence = int(match.group("dif_sequence"))
                pack = int(match.group("pack"))
                new_channels = frame_data.subcode_pack_types[:]  # shallow copy
                new_dif_sequences = new_channels[channel][:]
                new_packs = new_dif_sequences[dif_sequence][:]
                new_packs[pack] = value
                new_dif_sequences[dif_sequence] = new_packs
                new_channels[channel] = new_dif_sequences
                return replace(frame_data, subcode_pack_types=new_channels)
            case _ if du.field_has_prefix(
                "sc_title_timecode", self.column, excluded_prefixes=["sc_timecode_bg"]
            ):
                assert is_dataclass(value)
                return replace(
                    frame_data,
                    subcode_title_timecode=replace(
                        frame_data.subcode_title_timecode, **asdict(cast(DataclassInstance, value))
                    ),
                )
            case _ if du.field_has_prefix("sc_title_timecode_bg", self.column):
                assert is_dataclass(value)
                return replace(
                    frame_data,
                    subcode_title_binary_group=replace(
                        frame_data.subcode_title_binary_group,
                        **asdict(cast(DataclassInstance, value)),
                    ),
                )
            case _ if du.field_has_prefix("sc_vaux_rec_date", self.column):
                assert is_dataclass(value)
                return replace(
                    frame_data,
                    subcode_vaux_recording_date=replace(
                        frame_data.subcode_vaux_recording_date,
                        **asdict(cast(DataclassInstance, value)),
                    ),
                )
            case _ if du.field_has_prefix("sc_vaux_rec_time", self.column):
                assert is_dataclass(value)
                return replace(
                    frame_data,
                    subcode_vaux_recording_time=replace(
                        frame_data.subcode_vaux_recording_time,
                        **asdict(cast(DataclassInstance, value)),
                    ),
                )
            case _:
                raise ValueError(f"Unsupported column {self.column} for write_constant command.")

    def run(self, all_frame_data: list[dif.FrameData]) -> list[dif.FrameData]:
        # Look for most frequently occurring values and show them to the user.
        histogram: dict[ConstantValueType, int] = defaultdict(int)
        for frame in self.frame_range(all_frame_data):
            frame_data = all_frame_data[frame]
            histogram[self.get_value_from_frame_data(frame_data)] += 1
        sorted_keys = sorted(histogram, key=lambda k: histogram[k], reverse=True)
        print("Most common values for this field:")
        for key in sorted_keys:
            print(f" - {key!r}: {histogram[key]} frames")

        # Pick the value to write
        chosen_value = sorted_keys[0] if self.value == MOST_COMMON else self.value
        print(f"Using value {self.value_str(chosen_value)}.")

        # Update frames with new value
        tracker = FrameChangeTracker()
        for frame in self.frame_range(all_frame_data):
            frame_data = all_frame_data[frame]
            new_frame_data = self.set_frame_data_to_parsed_value(frame_data, chosen_value)
            all_frame_data[frame] = new_frame_data
            self.track_changed_frame(frame_data, new_frame_data, frame, tracker)
        self.track_final_proportion(tracker)

        return all_frame_data

    def command_expansion(self, all_frame_data: list[dif.FrameData]) -> list[Command]:
        """If the column is subcode, then expand into multiple commands."""
        match = subcode_column_full_pattern.match(self.column)
        if match:
            expanded: list[Command] = []
            channel_count = len(all_frame_data[0].subcode_pack_types)
            dif_sequence_count = len(all_frame_data[0].subcode_pack_types[0])
            pack_count = len(all_frame_data[0].subcode_pack_types[0][0])
            # Loop through all matching subcode indexes
            for channel in range(0, channel_count):
                if match.group("channel_num") is not None and channel != int(
                    match.group("channel_num")
                ):
                    continue
                if match.group("channel_range_start") is not None and (
                    channel < int(match.group("channel_range_start"))
                    or channel > int(match.group("channel_range_end"))
                ):
                    continue
                for dif_sequence in range(0, dif_sequence_count):
                    if match.group("dif_sequence_num") is not None and dif_sequence != int(
                        match.group("dif_sequence_num")
                    ):
                        continue
                    if match.group("dif_sequence_range_start") is not None and (
                        dif_sequence < int(match.group("dif_sequence_range_start"))
                        or dif_sequence > int(match.group("dif_sequence_range_end"))
                    ):
                        continue
                    for pack in range(0, pack_count):
                        if match.group("pack_num") is not None and pack != int(
                            match.group("pack_num")
                        ):
                            continue
                        if match.group("pack_range_start") is not None and (
                            pack < int(match.group("pack_range_start"))
                            or pack > int(match.group("pack_range_end"))
                        ):
                            continue
                        # At this point, we have a matching subcode
                        expanded.append(
                            replace(
                                self,
                                column=f"sc_pack_types_{channel}_{dif_sequence}_{pack}",
                            )
                        )
            return expanded

        return [self]


@dataclass(frozen=True, kw_only=True)
class RenumberArbitraryBits(Command):
    """Renumbers the arbitrary bits according to the given pattern.

    The initial value will be taken from the first frame if not specified.  The lower
    and upper bounds are inclusive, and define the valid range of arbitrary bit values
    to use.  The step defines how much to increment the arbitrary bits for every frame.
    """

    initial_value: int | None
    lower_bound: int
    upper_bound: int
    step: int

    def __str__(self) -> str:
        return (
            f"renumber_arbitrary_bits in frames [{self.start_frame}, {self.end_frame}] "
            f"with initial_value={self.initial_value}, lower_bound={self.lower_bound}, "
            f"upper_bound={self.upper_bound}, step={self.step}"
        )

    def run(self, all_frame_data: list[dif.FrameData]) -> list[dif.FrameData]:
        # Determine starting value
        next_value = (
            self.initial_value
            if self.initial_value is not None
            else all_frame_data[self.start_frame].arbitrary_bits
        )
        print(f"Using starting value {du.hex_int(next_value, 1)}...")
        # Quick sanity checks
        assert next_value >= self.lower_bound and next_value <= self.upper_bound
        assert self.step <= self.upper_bound - self.lower_bound + 1
        # Update frames with new value
        tracker = FrameChangeTracker()
        for frame in self.frame_range(all_frame_data):
            # Update arbitrary bits in frame
            frame_data = all_frame_data[frame]
            new_frame_data = replace(frame_data, arbitrary_bits=next_value)
            all_frame_data[frame] = new_frame_data
            self.track_changed_frame(frame_data, new_frame_data, frame, tracker)

            # Calculate next value
            next_value += self.step
            if next_value > self.upper_bound:
                next_value -= self.upper_bound - self.lower_bound + 1

        self.track_final_proportion(tracker)

        return all_frame_data


@dataclass(frozen=True, kw_only=True)
class RenumberTitleTimecodes(Command):
    """Renumbers the title timecodes.

    The initial value will be taken from the first frame if not specified.
    """

    initial_value: pack.TitleTimecode | None

    def __str__(self) -> str:
        return (
            f"renumber_title_timecodes in frames "
            f"[{self.start_frame}, {self.end_frame}] "
            f"with initial_value={self.initial_value}"
        )

    def run(self, all_frame_data: list[dif.FrameData]) -> list[dif.FrameData]:
        # Determine starting value
        next_value = (
            self.initial_value
            if self.initial_value is not None
            else all_frame_data[self.start_frame].subcode_title_timecode
        )
        assert next_value is not None
        next_value_str = next_value.to_text_value(
            None, next_value.value_subset_for_text_field(None)
        )
        print(f"Using starting value {next_value_str}...")
        # Update frames with new value
        tracker = FrameChangeTracker()
        for frame in self.frame_range(all_frame_data):
            # Update timecode in frame, but ONLY the actual time fields
            frame_data = all_frame_data[frame]

            new_tc = replace(
                frame_data.subcode_title_timecode,
                hour=next_value.hour,
                minute=next_value.minute,
                second=next_value.second,
                frame=next_value.frame,
                drop_frame=next_value.drop_frame,
            )
            new_frame_data = replace(frame_data, subcode_title_timecode=new_tc)

            all_frame_data[frame] = new_frame_data
            self.track_changed_frame(frame_data, new_frame_data, frame, tracker)

            # Calculate next value
            next_value = cast(pack.TitleTimecode, next_value.increment_frame(frame_data.system))

        self.track_final_proportion(tracker)

        return all_frame_data


@dataclass(frozen=True, kw_only=True)
class Transformations:
    commands: list[Command]

    def run(self, frame_data: list[dif.FrameData]) -> list[dif.FrameData]:
        for command in self.commands:
            for expanded_command in command.command_expansion(frame_data):
                print("===================================================")
                print(f"Running command {expanded_command}...")
                frame_data = expanded_command.run(frame_data)
        print("===================================================")
        return frame_data


def load_transformations(transformations_file: BinaryIO) -> Transformations:
    transformations_yaml = yaml.safe_load(transformations_file)

    # Read thresholds
    max_changed_proportion = transformations_yaml.get("thresholds", {}).get(
        "max_changed_proportion", DEFAULT_MAX_CHANGED_PROPORTION
    )
    max_consecutive_modifications = transformations_yaml.get("thresholds", {}).get(
        "max_consecutive_modifications", DEFAULT_MAX_CONSECUTIVE_MODIFICATIONS
    )
    global_thresholds = Thresholds(
        max_changed_proportion=float(max_changed_proportion),
        max_consecutive_modifications=(
            int(max_consecutive_modifications)
            if max_consecutive_modifications is not None
            else None
        ),
    )

    # Read commands
    commands: list[Command] = []
    for command_dict in transformations_yaml.get("commands", []) or []:
        # Look for per-command threshold overrides
        max_changed_proportion = command_dict.get("thresholds", {}).get(
            "max_changed_proportion", global_thresholds.max_changed_proportion
        )
        max_consecutive_modifications = command_dict.get("thresholds", {}).get(
            "max_consecutive_modifications",
            global_thresholds.max_consecutive_modifications,
        )
        local_thresholds = Thresholds(
            max_changed_proportion=float(max_changed_proportion),
            max_consecutive_modifications=(
                int(max_consecutive_modifications)
                if max_consecutive_modifications is not None
                else None
            ),
        )

        # Parse the command itself
        if command_dict["type"] == "write_constant":
            commands.append(
                WriteConstantCommand(
                    type=command_dict["type"],
                    column=command_dict["column"],
                    value=WriteConstantCommand.parse_value_str(
                        command_dict["column"], command_dict.get("value", MOST_COMMON)
                    ),
                    start_frame=command_dict.get("start_frame", 0),
                    end_frame=command_dict.get("end_frame", None),
                    thresholds=local_thresholds,
                )
            )
        elif command_dict["type"] == "renumber_arbitrary_bits":
            commands.append(
                RenumberArbitraryBits(
                    type=command_dict["type"],
                    initial_value=(
                        int(command_dict.get("initial_value", None), 0)
                        if command_dict.get("initial_value", None) is not None
                        else None
                    ),
                    lower_bound=int(command_dict.get("lower_bound", "0x0"), 0),
                    upper_bound=int(command_dict.get["upper_bound", "0xB"], 0),
                    step=int(command_dict.get("step", "0x1"), 0),
                    start_frame=command_dict.get("start_frame", 0),
                    end_frame=command_dict.get("end_frame", None),
                    thresholds=local_thresholds,
                )
            )
        elif command_dict["type"] == "renumber_title_timecodes":
            commands.append(
                RenumberTitleTimecodes(
                    type=command_dict["type"],
                    initial_value=(
                        cast(
                            pack.TitleTimecode,
                            pack.TitleTimecode.parse_text_values(
                                {None: command_dict.get("initial_value", "")}
                            ),
                        )
                        if command_dict.get("initial_value", None) is not None
                        else None
                    ),
                    start_frame=command_dict.get("start_frame", 0),
                    end_frame=command_dict.get("end_frame", None),
                    thresholds=local_thresholds,
                )
            )
        else:
            raise ValueError(f"Unrecognized command {command_dict['type']}.")

    return Transformations(
        commands=commands,
    )
