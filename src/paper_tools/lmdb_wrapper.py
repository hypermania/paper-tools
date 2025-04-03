import lmdb
import msgpack
from typing import Generator, Any, Union

class LmdbWrapperBase:
    """LMDB database wrapper for Pythonic iteration and access."""
    
    def __init__(self, 
                 path: str,
                 map_size: int = 10737418240,  # Default 10GB
                 readonly: bool = True,
                 key_encoding: str = 'utf-8'):
        """
        Initialize LMDB interface.
        
        :param path: Path to LMDB database directory
        :param map_size: Maximum database size in bytes
        :param readonly: Open in read-only mode
        :param key_encoding: Encoding for converting string keys to/from bytes
        """
        self.env = lmdb.open(
            path,
            map_size=map_size,
            readonly=readonly,
            lock=not readonly,  # Disable lock in read-only mode
            metasync=False
        )
        self.key_encoding = key_encoding

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.env.close()

    def __len__(self):
        return self.env.stat()['entries']
        
    def encode_key(self, key: Union[str, bytes]) -> bytes:
        """Convert key to bytes for LMDB storage."""
        if isinstance(key, str):
            return key.encode(self.key_encoding)
        return key

    def decode_key(self, key: bytes) -> Union[str, bytes]:
        """Convert bytes key to original format."""
        if self.key_encoding:
            return key.decode(self.key_encoding)
        return key

    def pack_value(self, value: bytes) -> bytes:
        """Convert value to bytes for LMDB storage."""
        return value

    def unpack_value(self, value: bytes) -> bytes:
        """Convert bytes value to original format."""
        return value

    def __getitem__(self, key: Union[str, bytes]) -> Any:
        """Get a record by key."""
        with self.env.begin() as txn:
            packed = txn.get(self.encode_key(key))
            if packed is None:
                raise KeyError(f"Key {key!r} not found")
            #return msgpack.unpackb(packed)
            return self.unpack_value(packed)

    def __setitem__(self, key: Union[str, bytes], value: Any):
        """Set a record by key."""
        with self.env.begin(write=True) as txn:
            txn.put(
                self.encode_key(key),
                #msgpack.packb(value),
                self.pack_value(value),
                overwrite=True
            )

    def __iter__(self) -> Generator[Union[str, bytes], None, None]:
        """Iterate over all keys in the database."""
        with self.env.begin() as txn:
            cursor = txn.cursor()
            for key in cursor.iternext(keys=True, values=False):
                yield self.decode_key(key)

    def __contains__(self, item) -> bool:
        """Iterate over all keys in the database."""
        with self.env.begin() as txn:
            result = txn.get(self.encode_key(item)) != None
            return result

    def keys(self) -> Generator[Union[str, bytes], None, None]:
        """Alias for key iteration."""
        return self.__iter__()

    def values(self) -> Generator[Any, None, None]:
        """Iterate over all values in the database."""
        with self.env.begin() as txn:
            cursor = txn.cursor()
            for _, value in cursor:
                #yield msgpack.unpackb(value)
                yield self.unpack_value(value)

    def items(self) -> Generator[tuple, None, None]:
        """Iterate over all (key, value) pairs in the database."""
        with self.env.begin() as txn:
            cursor = txn.cursor()
            for key, value in cursor:
                yield (
                    self.decode_key(key),
                    #msgpack.unpackb(value)
                    self.unpack_value(value)
                )

    def setitem_batched(self, items: dict):
        """Set a collection of records from a {key: value} dict."""
        with self.env.begin(write=True) as txn:
            for key, value in items.items():
                txn.put(
                    self.encode_key(key),
                    self.pack_value(value),
                    overwrite=True
                )


"""
    def batch_writer(self, buffer_size: int = 1000):
        return LmdbBatchWriter(self, buffer_size)
"""

"""
class LmdbBatchWriter:
    
    def __init__(self, db: LmdbWrapper, buffer_size: int = 1000):
        self.db = db
        self.buffer_size = buffer_size
        self._buffer = []

    def __enter__(self):
        self.txn = self.db.env.begin(write=True)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._flush()
        self.txn.commit()

    def add(self, key: Union[str, bytes], value: Any):
        self._buffer.append((
            self.db.encode_key(key),
            msgpack.packb(value)
        ))
        if len(self._buffer) >= self.buffer_size:
            self._flush()

    def _flush(self):
        if self._buffer:
            for key, value in self._buffer:
                self.txn.put(key, value, overwrite=True)
            self._buffer.clear()
"""
