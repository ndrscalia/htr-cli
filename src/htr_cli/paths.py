from pathlib import Path

# input
DATA_DIR = Path("data")
IMAGES_DIR = DATA_DIR / "images"
XML_DIR = DATA_DIR / "xml_texts"

# intermediate
LINES_CSV = Path("lines.csv")
POLYGONS_JSON = Path("polygons_coordinates.json")

# output
DATASET_DIR = Path("dataset")
CHECKPOINT = DATASET_DIR / "images_processing_ckpt.txt"
SYMS_TXT = DATASET_DIR / "syms.txt"
TRAIN_IMAGES = DATASET_DIR / "images" / "train"
VAL_IMAGES = DATASET_DIR / "images" / "val"
TEST_IMAGES = DATASET_DIR / "images" / "test"
TRAIN_IDS = DATASET_DIR / "train_ids.txt"
VAL_IDS = DATASET_DIR / "val_ids.txt"
TEST_IDS = DATASET_DIR / "test_ids.txt"
TRAIN_TOK_TEXT = DATASET_DIR / "train.txt"
VAL_TOK_TEXT = DATASET_DIR / "val.txt"
TEST_TOK_TEXT = DATASET_DIR / "test.txt"
TRAIN_TEXT = DATASET_DIR / "train_text.txt"
VAL_TEXT = DATASET_DIR / "val_text.txt"
TEST_TEXT = DATASET_DIR / "test_text.txt"
CORPUS_CHAR = DATASET_DIR / "corpus_characters.txt" # this is needed to train a LM with KenLM, not for PyLaia
TOK_TXT = DATASET_DIR / "tokens.txt" # this is needed to predict with a LM (KenLM), not for PyLaia
LEX_TXT = DATASET_DIR / "lexicon_characters.txt" # this is needed to predict with a LM (KenLM), not for PyLaia
DICTIONARY = DATASET_DIR / "dictionary.txt" # this is used for postprocessing with LM, not for PyLaia

# summary
DIRS = [DATA_DIR, IMAGES_DIR, XML_DIR, DATASET_DIR, TRAIN_IMAGES, VAL_IMAGES, TEST_IMAGES]
