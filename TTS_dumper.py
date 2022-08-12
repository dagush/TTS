# =============================================
# TTS downloader
# Based on https://github.com/theFroh/ttsunhoster
# =============================================
#!/usr/bin/env python3
import os
from json import load
import pprint
from enum import Enum

import requests
import urllib.parse

import concurrent.futures
import urllib.request

MAX_WORKERS = 15

class DataType(Enum):
    image = 1
    model = 2
    pdf = 3

# what do we want to fetch?
MESH_DATA = {
    "MeshURL": DataType.model,
    "NormalURL": DataType.image,
    "DiffuseURL": DataType.image,
    "ColliderURL": DataType.model
    }

IMAGE_DATA = {
    "ImageURL": DataType.image,
    "FaceURL":  DataType.image,
    "BackURL":  DataType.image,
    "ImageSecondaryURL": DataType.image
}

PDF_DATA = {
    "PDFUrl": DataType.pdf
}


# =====================================================
# slugify
# Taken from https://stackoverflow.com/questions/295135/turn-a-string-into-a-valid-filename
# =====================================================
import unicodedata
import re

def slugify(value, allow_unicode=False):
    """
    Taken from https://github.com/django/django/blob/master/django/utils/text.py
    Convert to ASCII if 'allow_unicode' is False. Convert spaces or repeated
    dashes to single dashes. Remove characters that aren't alphanumerics,
    underscores, or hyphens. Convert to lowercase. Also strip leading and
    trailing whitespace, dashes, and underscores.
    """
    value = str(value)
    if allow_unicode:
        value = unicodedata.normalize('NFKC', value)
    else:
        value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
    value = re.sub(r'[^\w\s-]', '', value.lower())
    return re.sub(r'[-\s]+', '-', value).strip('-_')


# =====================================================
# load_tts_url
# =====================================================
def load_tts_url(tts_url):
    path = None
    if tts_url[1] == DataType.image:
        path = os.path.join(image_dir, tts_url[2])
    elif tts_url[1] == DataType.model:
        path = os.path.join(model_dir, tts_url[2])
    elif tts_url[1] == DataType.pdf:
        path = os.path.join(pdf_dir, tts_url[2])
    if path is not None:
        if os.path.isfile(path) and not args.replace:
            print(f"\tload_tts_url: {path} already exists, skipping.")
            return 'skipping'

    r = requests.get(tts_url[0], headers={"User-Agent": "XY"})

    if r.status_code == requests.codes.ok:
        return r.content
    else:
        print("Error", tts_url[0], r.status_code)
        return None


def url_to_tts(url, dtype):
    url_path = urllib.parse.urlparse(url).path
    url_ext = os.path.splitext(url_path)[1]
    if url_ext == '' or url_ext == '.php':
        if dtype == DataType.image:
            url_ext = '.png'
        elif dtype == DataType.model:
            url_ext = '.obj'
        elif dtype == DataType.pdf:
            url_ext = '.pdf'

    return "".join([c for c in url if c.isalpha() or c.isdigit()]).rstrip() + url_ext


counter = 0
def json_extract(obj, keys):
    """Recursively fetch values from nested JSON."""
    arr = []

    def extract(obj, arr, keys):
        global counter
        """Recursively search for values of key in JSON tree."""
        if isinstance(obj, dict):
            for k, url in obj.items():
                if isinstance(url, (dict, list)):
                    extract(url, arr, keys)
                elif k in keys and url != '':
                    if url[:4] != "http":
                        url = "http://" + url # partly handles these
                    arr.append((url,keys[k], url_to_tts(url,keys[k])))
        elif isinstance(obj, list):
            for item in obj:
                extract(item, arr, keys)
        return arr

    values = extract(obj, arr, keys)
    return values


def parse_tts_custom_object(workshop_json):
    with open(workshop_json, "r", encoding="utf-8") as fp:
        save = load(fp)
        objects = save["ObjectStates"]

    image_urls = json_extract(objects, IMAGE_DATA)
    model_urls = json_extract(objects, MESH_DATA)
    pdf_urls = json_extract(objects, PDF_DATA)
    SaveName = slugify(save['SaveName'])

    return image_urls, model_urls, pdf_urls, SaveName



if __name__ == '__main__':
    download = False
    import argparse
    import sys

    parser = argparse.ArgumentParser(description="Unhosts Tabletop Simulator workshop custom content.")
    parser.add_argument("json_input", help="path to either a WorkshopFileInfos file, or one or more Workshop mod .json files", nargs="+")
    parser.add_argument("--output", "-o", help="where to store the Models and Images subdirectories")
    parser.add_argument("--replace", "-r", help="replace files already in the output directory")
    args = parser.parse_args()

    all_urls = []
    for json in args.json_input:
        print(json)
        image_urls, model_urls, pdf_urls, saveName = parse_tts_custom_object(json)

        all_urls = image_urls.copy()
        all_urls.extend(model_urls)
        all_urls.extend(pdf_urls)

    if args.output:
        output_dir = args.output
    else:
        output_dir = os.path.join(os.path.dirname(os.path.abspath(args.json_input[0])), 'TTS_' + saveName)

    print("Output directory:", output_dir)

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    image_dir = os.path.join(output_dir, "Images")
    if not os.path.exists(image_dir):
        os.makedirs(image_dir)
    model_dir = os.path.join(output_dir, "Models")
    if not os.path.exists(model_dir):
        os.makedirs(model_dir)
    pdf_dir = os.path.join(output_dir, "PDF")
    if not os.path.exists(pdf_dir):
        os.makedirs(pdf_dir)

    print("\nURL's to nab:")

    # get a list of all urls
    # all_urls = all_model_urls
    # all_urls.extend(all_image_urls)

    pprint.pprint(all_urls)

    print("\nGrabbing {} files".format(len(all_urls)))
    errorFiles = []
    n = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_url = {executor.submit(load_tts_url, url): url for url in all_urls}
        for future in concurrent.futures.as_completed(future_to_url):
            url = future_to_url[future]
            data = future.result()

            print("(%d/%d) %s" % (n, len(all_urls), url[0]))

            if data is not None and data != 'skipping':
                path = None
                if url[1] == DataType.image:
                    path = os.path.join(image_dir, url[2])
                elif url[1] == DataType.model:
                    path = os.path.join(model_dir, url[2])
                elif url[1] == DataType.pdf:
                    path = os.path.join(pdf_dir, url[2])
                if path is not None:
                    if not os.path.isfile(path) or args.replace:  # This verification is still needed because of the concurrency...
                        with open(path, "wb") as fp:
                            fp.write(data)
                    else:
                        print("\tWritting: Already exists, skipping.")
                sys.stdout.flush()
            else:
                if data is None:
                    errorFiles.append(url)

            n += 1

    print("Done!")
    print("\n\nERRORS:", len(errorFiles))
    print(*errorFiles, sep="\n")
