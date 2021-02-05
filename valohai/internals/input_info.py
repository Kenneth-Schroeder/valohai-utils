import json
import os
from typing import Optional

from valohai import paths
from valohai.internals.download import download_url
from valohai.internals.download_type import DownloadType
from valohai.internals.global_state import input_infos
from valohai.paths import get_inputs_path


class FileInfo:
    def __init__(self, *, name, uri, path, size, checksums):
        self.name = str(name)
        self.uri = str(uri)
        self.checksums = checksums
        self.path = str(path) if path else None
        self.size = int(size) if size else None

    def is_downloaded(self):
        return self.path and os.path.isfile(self.path)

    def download(self, path, force_download: bool = False):
        self.path = download_url(self.uri, os.path.join(path, self.name), force_download)
        # TODO: Store size & checksums if they become useful

    @staticmethod
    def uri_to_filename(uri: str) -> str:
        return uri[uri.rfind("/") + 1 :]


class InputInfo:
    def __init__(self, files):
        self.files = list(files)

    def is_downloaded(self):
        if not self.files:
            return False

        return all(f.is_downloaded() for f in self.files)

    def download(self, path, force_download: bool = False):
        for f in self.files:
            f.download(path, force_download)

    def store(self, name: str):
        input_infos[name] = self

    @staticmethod
    def load(name: str, download: Optional[DownloadType] = DownloadType.OPTIONAL):
        """Get InputInfo for a given input name.

        Looks for the InputInfo from the in-memory cache and if found, downloads the input according
        to the download strategy (Never, Optional, Always)

        If InputInfo not found from in-memory cache, look it up from inputs_config_path and store it.
        If it is found this way, the file is always downloaded already.

        :param name: Name of the input.
        :param download: Download strategy for the input. (Never, Optional, Always)
        :return: InputInfo instance for this input name
        """
        if name in input_infos:
            info = input_infos[name]
            if download == DownloadType.ALWAYS or not info.is_downloaded() and download == DownloadType.OPTIONAL:
                path = get_inputs_path(name)
                os.makedirs(path, exist_ok=True)
                info.download(get_inputs_path(name),
                              force_download=True if download == DownloadType.ALWAYS else False)
            return info

        inputs_config_path = paths.get_inputs_config_path()
        if os.path.isfile(inputs_config_path):
            with open(inputs_config_path) as json_file:
                data = json.load(json_file)
                input_info_data = data.get(name)
                if input_info_data:
                    input_info = InputInfo.from_json_data(input_info_data)
                    input_info.store(name)
                    return input_infos[name]

    @classmethod
    def from_json_data(cls, json_data: dict) -> "InputInfo":
        return cls(files=[FileInfo(**d) for d in json_data.get("files", ())])
