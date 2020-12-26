# Get a file's SHA1 hash.

import argparse
import hashlib
import enum


# MARK: - Hash Types
class HashAlgorithm (enum.Enum):
    SHA1 = "1"
    SHA224 = "224"
    SHA256 = "256"
    SHA384 = "384"
    SHA512 = "512"

    def get_hasher(self):
        if (self is HashAlgorithm.SHA1):
            return hashlib.sha1()
        elif (self is HashAlgorithm.SHA224):
            return hashlib.sha224()
        elif (self is HashAlgorithm.SHA256):
            return hashlib.sha256()
        elif (self is HashAlgorithm.SHA384):
            return hashlib.sha384()
        elif (self is HashAlgorithm.SHA512):
            return hashlib.sha512()

    def get_description(self):
        return f"SHA{self.value}"


# MARK: - Hash Functions
def get_sha_hash_of_file(filename: str, hash_algorithm: HashAlgorithm) -> str:
    """
    In this function we simply read a whole file into memory, which is not optimal for big files.
    """
    hasher = hash_algorithm.get_hasher()

    with open(filename, "rb") as f:
        content = f.read()
        hasher.update(content)

    return hasher.hexdigest()


def get_sha_hash_of_big_file(filename: str, hash_algorithm: HashAlgorithm) -> str:
    hasher = hash_algorithm.get_hasher()

    block_size = 65536
    
    with open(filename, "rb") as f:
        partial_content = f.read(block_size)
        while len(partial_content) > 0:
            hasher.update(partial_content)
            partial_content = f.read(block_size)

    return hasher.hexdigest()


# MARK: - Main
if (__name__ == "__main__"):
    # MARK: Parse args
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", "-f", type=str, default=None, help="Filename of the file to hash.")
    parser.add_argument("--algorithm", "-a", type=str, default=HashAlgorithm.SHA256.value, help=f"Algorithm: {HashAlgorithm.SHA1.value}, {HashAlgorithm.SHA224.value}, {HashAlgorithm.SHA256.value}, {HashAlgorithm.SHA384.value}, {HashAlgorithm.SHA512.value}. (default: %(default)s)")
    args = parser.parse_args()
    
    filename = args.file
    algorithm = HashAlgorithm(args.algorithm)
    
    algorithm_description = algorithm.get_description()

    print(f"{algorithm_description} hash for {filename}")
    # TODO: Use the "big file" function only if the file is big.
    print(f"Whole file {algorithm_description} hash: {get_sha_hash_of_file(filename, algorithm)}")
    print(f"Fragmented file {algorithm_description} hash: {get_sha_hash_of_big_file(filename, algorithm)}")
