# Get a file's SHA1 hash.

import argparse
import hashlib


# MARK: - Hash Functions
def get_sha1_hash_of_file(filename: str) -> str:
    """
    In this function we simply read a whole file into memory, which is not optimal for big files.
    """
    hasher = hashlib.sha1()

    with open(filename, "rb") as f:
        content = f.read()
        hasher.update(content)

    return hasher.hexdigest()

def get_sha1_hash_of_big_file(filename: str) -> str:
    block_size = 65536
    hasher = hashlib.sha1()
    
    with open(filename, "rb") as f:
        partial_content = f.read(block_size)
        while len(partial_content) > 0:
            hasher.update(partial_content)
            partial_content = f.read(block_size)

    return hasher.hexdigest()


# MARK: - Main
if (__name__ == "__main__"):
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", type=str, default=None)

    args = parser.parse_args()

    filename = args.file

    print(f"SHA1 hash for {filename}")
    print("Whole file SHA1 hash:", get_sha1_hash_of_file(filename))
    print("Fragmented file SHA1 hash:", get_sha1_hash_of_big_file(filename))
