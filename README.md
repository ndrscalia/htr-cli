Build the docker image (one-time, from the repo root):

```bash
docker build -t textfeatextractor .
```

The `-t textfeatextractor` tag is what later commands reference — pick any name you like, just keep it consistent.

To run the docker image that allows you to use `TextFeatExtractor`, mount the entire project directory into the container so the `htr-prep` package, `data/`, and `dataset/` are all visible inside:

```bash
docker run -it -v "$(pwd)":/workspace -w /workspace textfeatextractor bash
```

- `-v "$(pwd)":/workspace` bind-mounts the repo root at `/workspace`. Use an absolute path (e.g. `/Users/andreascalia/code/transkribus_api`) instead of `$(pwd)` if you're invoking the command from outside the project.
- `-w /workspace` sets the working directory so relative paths like `data/`, `dataset/`, and `polygons_coordinates.json` resolve the way the CLI expects.

The Dockerfile only installs the C++ deps (`pagexml`, `textfeat`); install the Python package once inside the container so the `htr-prep` CLI is available:

```bash
uv pip install --system -e . #--system skips the venv warning
```

The TFE-based preprocessing command is `htr-prep process-images-tfe` (see `src/htr_prep/image_processing_tfe.py`).

If you pulled the data yourself, you should have a `data/` directory that looks like this:
```
.
├── data
│   ├── images
│   └── xml_texts
```

The `split_dataset.py` script and the `data_extraction.py` replace NBSP with a regular space.
