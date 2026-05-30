# TextFeatExtractor vs htr-prep parameter cheatsheet

| TFE parameter | Type | Our equivalent | Notes |
|---|---|---|---|
| `featype` | int | — | Output type, not relevant |
| `format` | int | — | Output format, not relevant |
| `verbose` | bool | — | Logging only |
| `procimgs` | bool | — | Internal flag |
| `stretch` | bool | `contrast_stretch` toggle in `process_images()` | |
| `enh` | bool | `enhance_sauvola` toggle in `process_images()` | |
| `enh_type` | int | — | Hardcoded to ENH_SAUVOLA (R=128) |
| `enh_win` | int | `win_size` param in `enhance_sauvola()` | |
| `enh_slp` | float | `slope` param in `enhance_sauvola()` | |
| `enh_prm` | float | `k` param in `enhance_sauvola()` | |
| `enh_prm_randmin` | float | — | Augmentation, not implemented |
| `enh_prm_randmax` | float | — | Augmentation, not implemented |
| `enh3_prm0` | float | — | 3-channel variant, not implemented |
| `enh3_prm2` | float | — | 3-channel variant, not implemented |
| `deslope` | bool | `deslope` toggle in `process_images()` | |
| `deslant` | bool | `deslant` toggle in `process_images()` | |
| `deslant_min` | float | `slant_min` param in `estimate_slant()` / `deslant()` | |
| `deslant_max` | float | `slant_max` param in `estimate_slant()` / `deslant()` | |
| `deslant_step` | float | `slant_step` param in `estimate_slant()` | |
| `deslant_hsteps` | int | `hsteps` param in `estimate_slant()` | |
| `slant_rand` | float | — | Augmentation, not implemented |
| `scale_rand` | float | — | Augmentation, not implemented |
| `normxheight` | int | — | Not implemented |
| `normheight` | int | `norm_height` param in `process_images()` | |
| `momentnorm` | bool | `moment_normalize` toggle in `process_images()` | |
| `minheight` | int | — | Not implemented |
| `maxwidth` | int | — | Not implemented (no cap) |
| `compute_fpgram` | bool | — | Feature extraction, not preprocessing |
| `compute_fcontour` | bool | — | Feature extraction, not preprocessing |
| `fcontour_dilate` | float | — | Feature extraction, not preprocessing |
| `padding` | int | hardcoded `10` in `process_images()` | Not a function param |
| `ypadding` | int | — | Not implemented |
