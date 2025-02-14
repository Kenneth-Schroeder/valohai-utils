from typing import Optional
import os
import logging
from enum import Enum

from valohai.internals import global_state, vfs
from valohai.internals.download_type import DownloadType
from valohai.internals.global_state_loader import load_global_state_if_necessary
from valohai.internals.input_info import InputInfo

logger = logging.getLogger()


class DuplicateHandling(Enum):
    OVERWRITE = "overwrite"  # Default behavior - last file wins
    APPEND_INDEX = "append_index"  # Append _1, _2, etc to duplicates
    APPEND_HASH = "append_hash"  # Append part of file hash to duplicates


def modify_filename(base_name: str, index: int = 0, file_hash: str = "") -> str:
    name, ext = os.path.splitext(base_name)
    if index > 0:
        return f"{name}_{index}{ext}"
    if file_hash:
        return f"{name}_{file_hash[:8]}{ext}"
    return base_name


def get_input_vfs(
    name: str,
    process_archives: bool = True,
    download_type: DownloadType = DownloadType.OPTIONAL,
    duplicate_handling: DuplicateHandling = DuplicateHandling.OVERWRITE,
) -> vfs.VFS:
    v = vfs.VFS()
    ii = get_input_info(name)

    logger.info(f"Debug: Processing input {name}")  # Debug logger.info
    if ii:
        ii.download_if_necessary(name, download_type)

        # Debug: logger.info all files before processing
        logger.info("Debug: All files before processing:")
        for file_info in ii.files:
            logger.info(f"  - Path: {file_info.path}, Name: {file_info.name}")

        # Keep track of filenames we've seen
        seen_names = {}

        for file_info in ii.files:
            assert file_info.path

            final_name = file_info.name
            if duplicate_handling != DuplicateHandling.OVERWRITE:
                if file_info.name in seen_names:
                    if duplicate_handling == DuplicateHandling.APPEND_INDEX:
                        index = seen_names[file_info.name] + 1
                        seen_names[file_info.name] = index
                        final_name = modify_filename(file_info.name, index=index)
                        logger.info(
                            f"Debug: Renaming duplicate {file_info.name} to {final_name}"
                        )  # Debug logger.info
                    elif duplicate_handling == DuplicateHandling.APPEND_HASH:
                        final_name = modify_filename(
                            file_info.name, file_hash=file_info.sha256
                        )
                        logger.info(
                            f"Debug: Renaming duplicate {file_info.name} to {final_name}"
                        )  # Debug logger.info
                else:
                    seen_names[file_info.name] = 0

            vfs.add_disk_file(
                v,
                name=final_name,
                path=file_info.path,
                process_archives=process_archives,
            )

        # Debug: logger.info final VFS contents
        logger.info("Debug: Final VFS contents:")
        for file in v.files:
            logger.info(f"  - {file.name}")

    return v


def get_input_info(name: str) -> Optional[InputInfo]:
    load_global_state_if_necessary()
    return global_state.inputs.get(name, None)
