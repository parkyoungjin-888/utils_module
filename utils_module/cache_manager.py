import importlib
import os
from botocore.exceptions import ClientError
from typing import Optional, Tuple


class CacheManager:
    def __init__(self, s3_client, bucket: str, file_cache_dir: str = "./tmp/cache"):
        self.s3_client = s3_client
        self.bucket = bucket
        self.file_cache_dir = file_cache_dir
        os.makedirs(self.file_cache_dir, exist_ok=True)
        self._cache = {}

    def _get_remote_version(self, file_name: str) -> str:
        response = self.s3_client.head_object(Bucket=self.bucket, Key=file_name)
        version = response.get('VersionId') if response else None
        return version

    def _get_cached_version(self, file_name: str) -> Optional[str]:
        version_file = os.path.join(self.file_cache_dir, f"{file_name}.version")
        if not os.path.exists(version_file):
            return None
        with open(version_file, 'r') as f:
            return f.read().strip()

    def _save_cached_version(self, file_name: str, version: str):
        version_file = os.path.join(self.file_cache_dir, f"{file_name}.version")
        with open(version_file, 'w') as f:
            f.write(version)

    def _download_from_s3(self, file_name: str, version: Optional[str] = None) -> Tuple[str, str]:
        local_path = os.path.join(self.file_cache_dir, file_name.lstrip('/'))
        remote_version = self._get_remote_version(file_name)
        cached_version = self._get_cached_version(file_name)
        if version is None and cached_version == remote_version:
            return local_path, cached_version

        extra_args = {}
        if version is not None:
            extra_args['VersionId'] = version
        elif remote_version is not None:
            extra_args['VersionId'] = remote_version

        try:
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            self.s3_client.download_file(self.bucket, file_name, local_path, ExtraArgs=extra_args)
            self._save_cached_version(file_name, version or remote_version)
            return local_path, version or remote_version
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                raise FileNotFoundError(f"{file_name} is not found in S3")
            raise

    def _load_obj(self, file_name: str, obj_name: str, version: Optional[str] = None):
        local_path = os.path.join(self.file_cache_dir, file_name)
        self._download_from_s3(file_name, version)

        try:
            cache_dir = os.path.dirname(local_path)
            import sys
            if cache_dir not in sys.path:
                sys.path.append(cache_dir)
            module_name = os.path.splitext(os.path.basename(file_name))[0]
            module = importlib.import_module(module_name)
            _obj = getattr(module, obj_name)
            obj_key = f'{file_name}/{obj_name}'
            self._cache[obj_key] = _obj
        except Exception as e:
            raise ImportError(f"Failed to load {obj_name} from {file_name}: {str(e)}")

    def get_obj(self, file_name: str, obj_name: str, version: Optional[str] = None):
        obj_key = f'{file_name}/{obj_name}'
        if obj_key not in self._cache:
            self._load_obj(file_name, obj_name, version)
        return self._cache[obj_key]

    def download_file(self, file_name: str, version: Optional[str] = None):
        self._download_from_s3(file_name, version)
