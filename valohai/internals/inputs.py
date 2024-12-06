from typing import Optional

from valohai.internals import global_state, vfs
from valohai.internals.download_type import DownloadType
from valohai.internals.global_state_loader import load_global_state_if_necessary
from valohai.internals.input_info import InputInfo


def get_input_vfs(
    name: str,
    process_archives: bool = True,
    download_type: DownloadType = DownloadType.OPTIONAL,
) -> vfs.VFS:
    v = vfs.VFS()
    ii = get_input_info(name) # InputInfo -> path of each file in .files is checked in download_if_necessary

    if ii:
        for file_info in ii.files:
            import os
            from valohai.internals.download import resolve_datum
            from valohai.internals.utils import uri_to_filename
            from valohai.paths import get_inputs_path
            if file_info.uri.startswith("datum://"):
                #path = get_inputs_path(name)
                input_folder_path = get_inputs_path(name)
                datum_id_or_alias = uri_to_filename(file_info.uri)
                datum_obj = resolve_datum(datum_id_or_alias)
                filename = datum_obj["name"]
                file_path = os.path.join(input_folder_path, filename)
                file_info.path = file_path # needs to be generated (same as .zip later in download)
                file_info.name = filename # needs to be adjusted for archives processing in add_disk_file

            # print(file_info.path) 

        ii.download_if_necessary(name, download_type)
        for file_info in ii.files:
            assert file_info.path
            vfs.add_disk_file(
                v,
                name=file_info.name,
                path=file_info.path,
                process_archives=process_archives,
            )

    return v


def get_input_info(name: str) -> Optional[InputInfo]:
    load_global_state_if_necessary()
    return global_state.inputs.get(name, None)
