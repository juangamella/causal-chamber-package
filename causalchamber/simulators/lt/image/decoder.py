# MIT License

# Copyright (c) 2025 Juan L. Gamella

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

from causalchamber.simulators import Simulator
import requests
from pathlib import Path
import hashlib
import os
import numpy as np
import datetime
from tqdm import tqdm
import torch
import torch.nn as nn
import torchvision.transforms as transforms

# import wandb

# --------------------------------------------------------------------
# Public API

# Download URL for the pre-trained model
TORCH_MODEL_URL = "https://causalchamber.s3.eu-central-1.amazonaws.com/downloadables/sparkling-elevator-10.pkl"


class DecoderSimple(Simulator):
    inputs_names = [
        "red",
        "green",
        "blue",
        "pol_1",
        "pol_2",
    ]
    outputs_names = ["image"]

    def __init__(
        self,
        torch_model_url=TORCH_MODEL_URL,
        root="./",
        device="cpu",
        download=True,
    ):
        """
        Initializes the simulator by downloading and loading a pre-trained Torch model.

        The function checks whether the model has already been downloaded to the `root` directory.
        If the file is not found and `download` is set to True, it downloads the model from
        the given `torch_model_url`. Otherwise, it raises a `FileNotFoundError`. The model
        is then loaded onto the specified `device`, e.g., `cpu` or `cuda`.

        Parameters
        ----------
        torch_model_url : str, optional
            URL of the pre-trained Torch model (default: `TORCH_MODEL_URL`).
        root : str, optional
            Path to the directory where the model should be stored (default: "./").
        device : str, optional
            Device to load the model on ("cpu" or "cuda") (default: "cpu").
        download : bool, optional
            Whether to download the model if not found locally (default: True).

        Raises
        ------
        FileNotFoundError
            If the model is not found in the specified `root` directory and `download` is set to False.

        Notes
        -----
        - The model is stored with a unique filename derived from the hash of `torch_model_url`.
        - The `DecoderNetwork` class is used to load the Torch model (see below).
        - If the model is already available, it skips downloading and directly loads the model.
        """
        super(DecoderSimple, self).__init__()
        # Check if model has been already downloaded
        local_file = (
            "torch_model_" + hashlib.md5(torch_model_url.encode()).hexdigest() + ".pkl"
        )
        download_path = Path(root, local_file)
        if os.path.exists(download_path):
            print(f'Pre-trained model "{local_file}" found in "{root}".')
        else:
            if download:
                _download(torch_model_url, download_path)
            else:
                raise FileNotFoundError(
                    f'Could not find model in directory "{root}". Set download=True or choose another root directory (root).'
                )

        # Load the torch model
        # device = torch.device("cuda") if torch.cuda.is_available() else torch.device("cpu")
        self.torch_model = DecoderNetwork(device=torch.device(device))
        self.torch_model.load(download_path)
        print("Model loaded.")

    def _simulate(
        self,
        red,
        green,
        blue,
        pol_1,
        pol_2,
    ):
        """Produces synthetic images given values for the light-source color
        (`red,green,blue`) and polarizer positions (`pol_1, pol_2`).

        Parameters
        ----------
        red, green, blue : array_like
            1D arrays representing the brightness settings of the red, green, and blue LEDs
            respectively, each in the range [0, 255].
        pol_1, pol_2 : array_like
            1D arrays representing the positions of the tunnel's polarizers in degrees, in
            the range [-180, 180].

        Returns
        -------
        outputs : numpy.ndarray
            The array containing the images with shape (N,64,64,3)
            where N is the number of produced images (equal to the
            length of the input arrays red, green, ...). The values of
            the array are between 0 and 1.

        """
        # Normalize the inputs (so they're between -1 and 1)
        inputs = np.array([red, green, blue, pol_1, pol_2]).T
        # print(inputs.shape)
        inputs = (inputs - np.array([128, 128, 128, 0, 0])) / np.array(
            [128, 128, 128, 180, 180]
        )
        try:
            inputs = torch.tensor(inputs, dtype=torch.float32)
        except TypeError:
            inputs = torch.tensor(
                np.asarray(inputs, dtype=np.float32), dtype=torch.float32
            )
        outputs = self.torch_model(inputs).detach().cpu().numpy()
        # Unnormalize images
        outputs = (outputs + 1) / 2
        # Clip to valid image range [0,1]
        outputs = np.maximum(outputs, 0)
        outputs = np.minimum(outputs, 1)
        # Set color axis last (accounting for possible extra batch axis)
        axes = (0, 2, 3, 1) if outputs.ndim == 4 else (1, 2, 0)
        return np.transpose(outputs, axes=axes)


def _download(url, output_path):
    """Function to download the file from the given URL into the given output_path."""
    print(f'Downloading model from "{url}" into "{output_path}"\n')
    response = requests.get(url, stream=True)
    total_size_in_bytes = int(response.headers.get("content-length", 0))
    block_size = 1024  # 1 Kibibyte
    progress_bar = tqdm(total=total_size_in_bytes, unit="iB", unit_scale=True)
    with open(output_path, "wb") as file:
        for data in response.iter_content(block_size):
            progress_bar.update(len(data))
            file.write(data)
    progress_bar.close()
    if total_size_in_bytes != 0 and progress_bar.n != total_size_in_bytes:
        print("ERROR, something went wrong")


# --------------------------------------------------------------------
# Underlying PyTorch Model
#   for more details: see Appendix C of "Sanity Checking Causal
#   Representation Learning on a Simple Real-World System (2025) by
#   Juan L. Gamella*, Simom Bing* and Jakob Runge)


class TorchImageDataset(torch.utils.data.Dataset):
    """
    To load the image datasets used in training the DecoderNetwork below.
    """

    def __init__(self, images, labels, mean_labels=None, std_labels=None):
        # Normalize labels
        self.mean_labels = (
            labels.mean(axis=0, keepdims=True) if mean_labels is None else mean_labels
        )
        self.std_labels = (
            labels.std(axis=0, keepdims=True) if std_labels is None else std_labels
        )
        self.n = len(labels)
        self.labels = torch.tensor(
            (labels - self.mean_labels) / self.std_labels, dtype=torch.float32
        )

        # Process images: tensors with pixel values between [-1,1]
        transform = transforms.Compose(
            [
                transforms.ToTensor(),
                transforms.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5)),
            ]
        )
        self.images = [torch.unsqueeze(transform(im), 0) for im in images]
        # torch.unsqueeze(torch.flatten(transform(im)), 0) for im in images
        self.images = torch.cat(self.images)  # Concatenate images into a single tensor

    def __len__(self):
        return self.n

    def __getitem__(self, idx):
        if torch.is_tensor(idx):
            idx = idx.tolist()
        return self.labels[idx], self.images[idx]


class DecoderNetwork(nn.Module):
    """
    Torch model used to train/call the MLP used in the simulator.
    """

    def __init__(
        self,
        device="cuda",
    ):
        super().__init__()
        # Define layers
        self.image_size = 64
        hidden_dim = 4096
        self.net = nn.Sequential(
            # Input layer
            nn.Linear(5, hidden_dim),
            nn.ReLU(),
            # Hidden layer 1
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            # Hidden layer 2
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            # Output layer
            nn.Linear(hidden_dim, 3 * self.image_size * self.image_size),
        )
        # Set device
        self.device = device
        self.to(device)

    def forward(self, x):
        output = self.net(x.to(self.device))
        if x.dim() == 1:  # single tensor
            return output.view(3, self.image_size, self.image_size)
        else:  # account for batch size
            return output.view(output.shape[0], 3, self.image_size, self.image_size)

    def save(self, directory=None, path=None, tag=None):
        if directory is not None:
            timestamp = datetime.now().strftime("%Y_%m_%d-%H_%M_%S")
            path = (
                directory
                + f"model_{timestamp}"
                + ("" if tag is None else f"tag_{tag}")
                + ".pkl"
            )
        elif path is None:
            raise ValueError("Must provide either directory or path")
        torch.save(self.state_dict(), path)
        print(f'Saved model {self} to "{path}"')

    def load(self, path):
        # device = torch.device("cuda") if torch.cuda.is_available() else torch.device("cpu")
        self.load_state_dict(torch.load(path, map_location=torch.device("cpu")))

    def train(
        self,
        dataset_train,
        dataset_test,
        epochs=30,
        batch_size=2048,
        learning_rate=1e-3,
        weight_decay=1e-5,
        every=15,
    ):
        # Optional: log with weights & biases
        # wandb.init(
        #     # set the wandb project where this run will be logged
        #     project="chamber_models_decoder",
        #     # track hyperparameters and run metadata
        #     config={
        #         "tag": log_wandb,
        #         "learning_rate": learning_rate,
        #         "epochs": epochs,
        #         "batch_size": batch_size,
        #         "weight_decay": weight_decay,
        #         "device": self.device,
        #     },
        # )

        # Define loss and optimizer
        loss_function = torch.nn.MSELoss()
        optimizer = torch.optim.Adam
        opt_args = {"lr": learning_rate, "weight_decay": weight_decay}
        optimizer = optimizer(self.parameters(), **opt_args)

        # Dataloaders
        dataloader_args = {"shuffle": True, "num_workers": 0}
        train_dataloader = torch.utils.data.DataLoader(
            dataset_train, batch_size=batch_size, **dataloader_args
        )
        X_test, Y_test = next(
            iter(
                torch.utils.data.DataLoader(dataset_test, batch_size=len(dataset_test))
            )
        )

        # Training loop
        for epoch in tqdm(range(epochs)):
            # start = time.time()
            for i, (X, Y) in enumerate(train_dataloader):
                # Zero gradients
                optimizer.zero_grad()

                # Forward pass
                y_pred = self(X)
                loss = loss_function(y_pred, Y.to(self.device))

                # Zero gradients, backward pass, and update weights
                loss.backward()
                optimizer.step()

                # Compute test loss
                # test_loss = loss_function(self(X_test), Y_test.to(self.device)).item()
                # elapsed = time.time() - start
                # wandb.log({"train_loss": loss, "test_loss": test_loss})

        # Close wandb session
        # wandb.finish()
