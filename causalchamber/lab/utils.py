# MIT License

# Copyright (c) 2025 Causal Chamber GmbH

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

# Authors:
#   - Juan L. Gamella [juan@causalchamber.ai]

"""This module contains helper functions, e.g., to download and
extract .zip files and check their MD5 checksums.

"""

import numpy as np
import zipfile
import requests
from pathlib import Path
import hashlib
from tqdm import tqdm

# --------------------------------------------------------------------
# Functions to download, extract and verify datasets


def download_and_extract(
    url,
    root,
    checksum=None,
    algorithm='md5',
    verbose=True,
):
    """
    Parameters
    ----------
    url : string
        The download URL.
    root : string
        The path to the directory on the local computer, where the file will be downloaded and extracted.
    checksum : string or NoneType, default=None
        The expected MD5 checksum of the downloaded file, which will
        be checked against its actual checksum. If `None`, the
        checksum is not checked.
    algorithm : str in ['md5', 'sha256'], optional
        The algorithm used to compute the checksum. Defaults to 'md5'
    verbose : bool, optional
        If True, traces are printed and a download progress bar is shown. If False no
        outputs are produced. Defauls to True.

    Returns
    -------
    None

    """
    # Check input
    if algorithm == 'md5':
        hasher = _compute_md5
    elif algorithm == 'sha256':
        hasher = _compute_sha256
    else:
        raise ValueError("algorithm must be 'md5' or 'sha256'")
    
    local_zipfile = "causal_chamber_" + hashlib.md5(url.encode()).hexdigest() + ".zip"
    zip_path = Path(root, local_zipfile)
    # Download
    _download(url, zip_path, verbose=verbose)
    # Verify    
    if checksum is not None:
        print("  Verifying checksum...", end="") if verbose else None
        computed = hasher(zip_path)
        if checksum != computed:
            raise Exception(
                f'Checksum does not match!\n  expected: "{checksum}"\n  computed: "{computed}"'
            )
        else:
            print(" done.") if verbose else None
    # Extract    
    print(f'  Extracting zip-file contents to "{root}"...', end="") if verbose else None
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(root)
    print(" done.") if verbose else None


def _download(url, output_path, verbose):
    """Function to actually download the file from the given URL into the given output_path."""
    print(f'Downloading dataset from "{url}" into "{output_path}"\n') if verbose else None
    response = requests.get(url, stream=True)
    total_size_in_bytes = int(response.headers.get("content-length", 0))
    block_size = 1024  # 1 Kibibyte
    if verbose:
        progress_bar = tqdm(total=total_size_in_bytes, unit="iB", unit_scale=True)
    with open(output_path, "wb") as file:
        for data in response.iter_content(block_size):
            progress_bar.update(len(data)) if verbose else None
            file.write(data)
    if verbose:
        progress_bar.close()
        if total_size_in_bytes != 0 and progress_bar.n != total_size_in_bytes:
            print("ERROR, something went wrong")


def _unzip(path, output_dir):
    """
    Unzips the file at the given path into the given output_dir.
    """
    print(f'  Extracting "{path}" to "{output_dir}"')
    with zipfile.ZipFile(path, "r") as zip_ref:
        zip_ref.extractall(output_dir)


def _compute_md5(path):
    """Compute the MD5 checksum of a file at the given path."""
    hasher = hashlib.md5()
    with open(path, "rb") as f:
        data = f.read()
        hasher.update(data)
    return hasher.hexdigest()

def _compute_sha256(path):
    """Compute the SHA-256 checksum of a file at the given path."""
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        data = f.read()
        hasher.update(data)
    return hasher.hexdigest()
