from typing import Optional

from valohai.internals import global_state, vfs
from valohai.internals.download_type import DownloadType
from valohai.internals.global_state_loader import load_global_state_if_necessary
from valohai.internals.input_info import InputInfo, DuplicateHandling


def get_input_vfs(
    name: str,
    process_archives: bool = True,
    download_type: DownloadType = DownloadType.OPTIONAL,
    duplicate_handling: DuplicateHandling = DuplicateHandling.OVERWRITE,
) -> vfs.VFS:
    """Get a VFS for an input.

    :param name: Name of the input
    :param process_archives: When facing an archive file, is it unpacked or returned as is
    :param download_type: Whether to force download or use cached files
    :param duplicate_handling: How to handle duplicate filenames
    :return: Virtual File System object containing the input files
    """
    v = vfs.VFS()
    # Pass duplicate_handling to get_input_info to handle duplicates at InputInfo level
    ii = get_input_info(name, duplicate_handling=duplicate_handling)
    if ii:
        ii.download_if_necessary(name, download_type)
        for file_info in ii.files:
            assert file_info.path
            vfs.add_disk_file(
                v,
                name=file_info.name,  # Names are already unique from InputInfo
                path=file_info.path,
                process_archives=process_archives,
            )
    return v


def get_input_info(
    name: str, duplicate_handling: DuplicateHandling = DuplicateHandling.OVERWRITE
) -> Optional[InputInfo]:
    """Get input info with duplicate handling.

    :param name: Name of the input
    :param duplicate_handling: How to handle duplicate filenames
    :return: InputInfo object if found, None otherwise
    """
    load_global_state_if_necessary()
    input_info = global_state.inputs.get(name, None)
    if input_info:
        # Convert the input info using the specified duplicate handling
        return InputInfo.from_urls_and_paths(
            [f.uri for f in input_info.files if f.uri],
            duplicate_handling=duplicate_handling,
        )
    return None
