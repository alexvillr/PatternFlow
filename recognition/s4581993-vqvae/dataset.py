import os
import sys
import zipfile

import requests
import numpy as np
import tensorflow as tf

dataset_location = "https://cloudstor.aarnet.edu.au/plus/s/tByzSZzvvVh0hZA/download"
dataset_directory = "dataset/"
dataset_zip_name = "keras_png_slices_data.zip"
dataset_folder_name = "keras_png_slices_data/"
dataset_train_folder = "keras_png_slices_train"
dataset_test_folder = "keras_png_slices_test"
dataset_val_folder = "keras_png_slices_validate"

image_size = (64, 64)

# Download the dataset, if it hasn't already been downloaded
def download_dataset():
    # Create the dataset directory
    if not os.path.isdir(dataset_directory):
        os.mkdir(dataset_directory)

    # Download dataset zip
    print(f"Downloading dataset into ./{dataset_directory}{dataset_zip_name}")
    if not os.path.exists(dataset_directory + dataset_zip_name):
        response = requests.get(dataset_location, stream=True)
        total_length = response.headers.get("content-length")

        with open(dataset_directory + dataset_zip_name, "wb") as f:
            # Show download progress bar (doesn't work on non-Unix systems)
            # Adapted from https://stackoverflow.com/a/15645088
            if total_length is None or not os.name == "posix":
                f.write(response.content)
            else:
                dl = 0
                total_length = int(total_length)
                for data in response.iter_content(chunk_size=4096):
                    dl += len(data)
                    f.write(data)
                    done = int(50 * dl / total_length)
                    sys.stdout.write("\r[8%sD%s]" % ('=' * done, ' ' * (50-done)))
                    sys.stdout.write(" %d%%" % int(dl / total_length * 100))
                    sys.stdout.flush()
            print()

        print("Dataset downloaded.\n")
    else:
        print("Dataset already downloaded.\n")

# Unzip the dataset
def unzip_dataset():
    print(f"Extracting dataset into ./{dataset_directory}{dataset_folder_name}")
    if not os.path.isdir(dataset_directory + dataset_folder_name):
        with zipfile.ZipFile(dataset_directory + dataset_zip_name) as z:
            z.extractall(path=dataset_directory)
        print("Dataset extracted.\n")
    else:
        print("Dataset already extracted.\n")

# Load the dataset
def load_dataset() -> (tf.data.Dataset, tf.data.Dataset, tf.data.Dataset):
    print("Loading training data...")
    train_ds = tf.keras.preprocessing.image_dataset_from_directory(
        dataset_directory + dataset_folder_name + dataset_train_folder,
        labels=None,
        image_size=image_size,
    )
    print("Loading testing data...")
    test_ds = tf.keras.preprocessing.image_dataset_from_directory(
        dataset_directory + dataset_folder_name + dataset_test_folder,
        labels=None,
        image_size=image_size,
    )
    print("Loading validation data...")
    val_ds = tf.keras.preprocessing.image_dataset_from_directory(
        dataset_directory + dataset_folder_name + dataset_val_folder,
        labels=None,
        image_size=image_size,
    )
    return (train_ds, test_ds, val_ds)

# Scale the given image to a range of [-0.5, 0.5] and change it to 1 colour channel
def _scale_image(image: tf.Tensor) -> tf.Tensor:
    image = image / 255 - 0.5
    image = tf.image.rgb_to_grayscale(image)
    return image

# Preprocess the data
def preprocess_data(dataset: tf.data.Dataset) -> np.array:
    return np.asarray(list(dataset.unbatch().map(_scale_image)))

# Load and preprocess the dataset
def get_dataset() -> (np.array, np.array, np.array):
    download_dataset()
    unzip_dataset()

    train_ds, test_ds, val_ds = load_dataset()

    train_ds = preprocess_data(train_ds)
    test_ds = preprocess_data(test_ds)
    val_ds = preprocess_data(val_ds)

    return (train_ds, test_ds, val_ds)

if __name__ == "__main__":
    get_dataset()
