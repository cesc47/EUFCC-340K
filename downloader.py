import concurrent.futures
import urllib
import os
from tqdm import tqdm
import PIL
from PIL import Image
from collections import defaultdict


def download_image(url, img_name):
    try:
        urllib.request.urlretrieve(url, img_name)
        print(f'Image {img_name} downloaded')
    except Exception as e:
        print(f'Exception: {e}')
        print(f'Error downloading image {img_name}')


def download_images(df, root_dir, num_threads=12):
    """
    Download images from the urls in the dataframe using multiple threads.
    The images are saved in the folder root_dir/database/images.
    :param df: It is a dataframe that contains the urls of the images
    :param root_dir: It is the root directory where the images will be saved
    :param num_threads: Number of CPU threads to use for concurrent downloading (default: 4)
    """
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = []
        for _, row in tqdm(df.iterrows(), total=len(df)):
            filename = row['idInSource']
            database = row['database']
            url = row['#portraitMedia.original']
            img_name = os.path.join(root_dir, database, 'images', f'{filename}.jpg')
            if not os.path.exists(img_name):
                future = executor.submit(download_image, url, img_name)
                futures.append(future)

        # Wait for all tasks to complete
        for future in concurrent.futures.as_completed(futures):
            try:
                future.result()
            except Exception as e:
                print(f'Exception: {e}')
                print('Error occurred during image download.')


def validate_images(df, root_dir):
    """
    Check if the images are valid. If the size of the image is less than 2.5KB, the image is removed.
    :param df: It is a dataframe that contains the urls of the images.
    :param root_dir: It is the root directory where the images are saved.
    :return: It returns the dataframe without the images that are not valid.
    """
    print('Validating images...')
    invalid_indices = []
    for index, row in tqdm(df.iterrows(), total=df.shape[0]):
        filename = row['idInSource']
        database = row['database']
        img_name = os.path.join(root_dir, database, 'images', f'{filename}.jpg')
        try:
            Image.open(img_name).close()
        except (FileNotFoundError, PIL.UnidentifiedImageError) as e:
            print(f'Error opening image {img_name}: {e}')
            invalid_indices.append(index)

    df.drop(invalid_indices, inplace=True)

    return df


def detect_duplicates(df, root_dir, datasets):
    print('Detecting duplicates...')
    # Step 1: Generate hashes and annotations
    hashes = {}
    for idx, row in tqdm(enumerate(df.itertuples(), start=1), total=len(df)):
        try:
            if ['EUROPEANA'] == list(datasets):
                image_path = os.path.join(root_dir, 'EUROPEANA', 'images', f'{row.idInSource}.jpg')
            else:
                image_path = os.path.join(root_dir, row.database, 'images', f'{row.idInSource}.jpg')
            with Image.open(image_path) as image:
                if image.mode != 'RGB':
                    image = image.convert('RGB')

                annotation = f'{row[2]} // {row[3]} // {row[4]}'
                image_hash = hash(image.tobytes())
                hashes[row.idInSource] = image_hash, annotation

        except (OSError, FileNotFoundError):
            continue

    # Step 2: Build a hash index to detect duplicates
    hash_index = defaultdict(list)
    hash_index_annotations = defaultdict(list)
    duplicates = {}
    duplicates_annotations = {}

    for key, (image_hash, annotation) in hashes.items():
        hash_index[image_hash].append(key)
        hash_index_annotations[image_hash].append(annotation)

    for key_list, key_list_annotations in zip(hash_index.values(), hash_index_annotations.values()):
        # Found image duplicate
        if len(key_list) > 1:
            main_key = key_list[0]
            duplicates[main_key] = key_list[1:]
        # found image and annotation duplicate
        if len(key_list_annotations) > 1:
            # compare strings to see if they are the same or not
            main_key = key_list_annotations[0]
            same = True
            for key in key_list_annotations[1:]:
                if main_key != key:
                    same = False
            if same:
                duplicates_annotations[main_key] = key_list_annotations[1:]

    # remove the duplicates
    print('Removing duplicates...')
    for key, value in tqdm(duplicates.items()):
        # read key value from df
        row_key_index = df.index[df['idInSource'] == key]
        row_key = df.loc[row_key_index].copy()

        # read value values from df
        for v in value:
            row_value_index = df.index[df['idInSource'] == v]
            row_value = df.loc[row_value_index].copy()

            # put together the annotations
            for col in ['classifications.hierarchy', 'objectTypes.hierarchy', 'subjects.hierarchy',
                        'materials.hierarchy']:
                if isinstance(row_key[col].values[0], float) or isinstance(row_value[col].values[0], float):
                    # set the value that is not nan in row_key
                    if isinstance(row_key[col].values[0], float):
                        df.loc[row_key_index, col] = row_value[col].values[0]
                else:
                    # split both by $ and put together, without repeating
                    combined_values = ' $ '.join(
                        list(set(row_key[col].values[0].split(' $ ') + row_value[col].values[0].split(' $ '))))
                    df.loc[row_key_index, col] = combined_values

        # remove the rows of the duplicates
        df = df[~df['idInSource'].isin(value)]

    return df