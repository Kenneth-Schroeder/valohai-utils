from enum import Enum
import glob
import os
from typing import Any, Dict, Iterable, List, Optional, Union

from valohai_yaml.utils import listify

from valohai.internals.download import download_url, request_download_urls
from valohai.internals.download_type import DownloadType
from valohai.internals.utils import uri_to_filename
from valohai.paths import get_inputs_path


class DuplicateHandling(Enum):
    OVERWRITE = "overwrite"  # Default behavior - last file wins
    APPEND_INDEX = "append_index"  # Append _1, _2, etc to duplicates
    APPEND_HASH = "append_hash"  # Append part of file hash to duplicates


class FileInfo:
    def __init__(
        self,
        *,
        name: str,
        uri: Optional[str] = None,
        path: Optional[str] = None,
        size: Optional[int] = None,
        checksums: Optional[Dict[str, str]] = None,
        metadata: Optional[List[Dict[str, Any]]] = None,
        datum_id: Optional[str] = None,
    ) -> None:
        self.name = str(name)
        self.uri = str(uri) if uri else None
        self.download_url = self.uri
        self.checksums = dict(checksums) if checksums else {}
        self.path = str(path) if path else None
        self.size = int(size) if size else None
        self.metadata = list(metadata) if metadata else []
        self.datum_id = str(datum_id) if datum_id else None

    def is_downloaded(self) -> Optional[bool]:
        return bool(self.path and os.path.isfile(self.path))

    def download(self, path: str, force_download: bool = False) -> None:
        if not self.download_url:
            raise ValueError("Can not download file with no URI")
        self.path = download_url(
            self.download_url, os.path.join(path, self.name), force_download
        )
        # TODO: Store size & checksums if they become useful

    @classmethod
    def from_json_data(cls, json_data: Dict[str, Any]) -> "FileInfo":
        return cls(
            name=json_data["name"],
            uri=json_data.get("uri"),
            path=json_data.get("path"),
            size=json_data.get("size"),
            checksums=json_data.get("checksums"),
            metadata=json_data.get("metadata"),
            datum_id=json_data.get("datum_id"),
        )


class InputInfo:
    def __init__(self, files: Iterable[FileInfo], input_id: Optional[str] = None):
        self.files = list(files)
        self.input_id = input_id

    def is_downloaded(self) -> bool:
        if not self.files:
            return False
        return all(f.is_downloaded() for f in self.files)

    def download_if_necessary(
        self, name: str, download: DownloadType = DownloadType.OPTIONAL
    ) -> None:
        if (
            download == DownloadType.ALWAYS
            or not self.is_downloaded()
            and download == DownloadType.OPTIONAL
        ):
            path = get_inputs_path(name)
            os.makedirs(path, exist_ok=True)
            if self.input_id:
                filenames_to_urls = request_download_urls(self.input_id)
                for file in self.files:
                    if not file.is_downloaded():
                        file.download_url = filenames_to_urls[file.name]
            for f in self.files:
                f.download(path, force_download=(download == DownloadType.ALWAYS))

    @classmethod
    def from_json_data(cls, json_data: Dict[str, Any]) -> "InputInfo":
        return cls(
            input_id=json_data.get("input_id"),
            files=[FileInfo.from_json_data(d) for d in json_data.get("files", ())],
        )

    @classmethod
    def from_urls_and_paths(
        cls,
        urls_and_paths: Union[str, List[str]],
        duplicate_handling: DuplicateHandling = DuplicateHandling.OVERWRITE,
    ) -> "InputInfo":
        files = []
        seen_names = {}

        def modify_filename(base_name: str, index: int = 0) -> str:
            name, ext = os.path.splitext(base_name)
            if index > 0:
                return f"{name}_{index}{ext}"
            return base_name

        for value in listify(urls_and_paths):
            value = str(value)
            if "://" not in value:  # The string is a local path
                for path in glob.glob(value):
                    base_name = os.path.basename(path)
                    final_name = base_name

                    if duplicate_handling == DuplicateHandling.APPEND_INDEX:
                        if base_name in seen_names:
                            seen_names[base_name] += 1
                            final_name = modify_filename(
                                base_name, seen_names[base_name]
                            )
                        else:
                            seen_names[base_name] = 0

                    files.append(
                        FileInfo(
                            name=final_name,
                            uri=None,
                            path=path,
                            size=None,
                            checksums=None,
                        )
                    )
            else:  # The string is an URL
                base_name = uri_to_filename(value)
                final_name = base_name

                if duplicate_handling == DuplicateHandling.APPEND_INDEX:
                    if base_name in seen_names:
                        seen_names[base_name] += 1
                        final_name = modify_filename(base_name, seen_names[base_name])
                    else:
                        seen_names[base_name] = 0

                files.append(
                    FileInfo(
                        name=final_name,
                        uri=value,
                        path=None,
                        size=None,
                        checksums=None,
                    )
                )

        return cls(files=files)
