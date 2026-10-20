# Fish Classification in DFO Moored Echosounder Data

**Team:** Olivia Whitelaw, Amanda Tu, Ali Stein-Gagnon, Carson Underhay

## 1. Project Overview

Acoustic surveys are widely used to monitor fish stocks and zooplankton (Rousseau et al., 2022). Primitive research into acoustic fish detection dates back to 1929, when sound waves were used to detect goldfish in a pond (Johannesson & Mitson, 1983). Modern echosounders transmit sound waves and record returning echoes to study the distribution and abundance of aquatic organisms. For example, Rousseau et al. (2018) used fixed, autonomous Acoustic Zooplankton Fish Profilers (AZFPs) to monitor juvenile salmon migration in the Discovery Islands and Johnstone Strait, British Columbia.

Acoustic data analysis remains time-consuming and requires expert knowledge to classify biological targets from noise and other acoustic signals (Slonimer, 2022). This limits the efficiency of processing large datasets. Our project aims to develop models to classify fish targets in labelled AZFP data provided by Fisheries and Oceans Canada (DFO). This involves preprocessing and standardizing the data, developing models informed by existing research, and evaluating their performance. A further challenge, which we address as a stretch goal is determining whether models can generalize across different monitoring locations, hardware, and instrument calibrations.

## 2. Problem Statement

**Primary Goal:**
Build and compare a random forest and a CNN that classify fish species in labelled echogram regions from one DFO moored echosounder site. Starting with herring vs salmon and extending to additional species (ex. Hake, juvenile salmon) where enough labelled regions exist.

**Stretch goals:**
- Test how well both trained models generalize to a second, unseen site without retraining
- Develop a visualization dashboard to demonstrate the classification results

## 4. Dataset Description

We're working with echosounder data from Fisheries and Oceans Canada (DFO), shared with their permission. The full dataset is 4 TB and covers DFO's moored surveys from 2022 to 2025 at several sites on the BC coast, including Barkley Canyon, Brooks Peninsula, Bamfield, and the Malaspina Strait. It includes both the raw echosounder data and the files from DFO's Echoview processing.

We're only using data from DFO's Acoustic Zooplankton Fish Profiler (AZFP) echosounders.
It's moored near the seafloor, looking up, for a year (DFO's deployments run 365 days), pinging at two frequencies ~ 67 kHz and ~ 120-125 kHz. Everything is saved to a memory card as .01A files.
Each deployment comes with the raw `.01A` data files, an `.XML` and a `.DPL` file with the instrument settings and calibration. The labeled regions (`.evr`) and surface/ bottom lines (`.evl`) from Echoview give us our training labels.

## 5. Proposed Methodology

- **Label verification:** count DFO labelled regions per species
- **Acoustic processing:** convert raw AZFP data to Sv; remove bad pings, the surface boundary and background noise; separate day and night
- **Region extraction:** match DFO's labelled regions to cleaned data; compute the dB different
- **Classification models:** random forest on per-region features vs a CNN on region images, using the same train/ test split
- **Evaluation:** per class precision, recall and F1; RF vs CNN comparison

## 6. Tools and Technologies

- **Python and Echopype:** Echopype is an open-source Python library for interoperable and scalable echosounder data processing (Lee et al., 2024). It supports conversion of raw AZFP echosounder data files (.01A) into standardized NetCDF datasets which can then be analyzed and processed (Echopype Developers, 2024). It allows for integration with Python machine learning libraries which makes it suitable for this project.
- **Echofilter:** open-source deep-learning tool that detects the surface in upward looking echosounder data 
- **Xarray, Dask and Zarr:** Echopype is built on xarray; Zarr stores data in compressed chunks and Dask processes those chunks in parallel (Lee et al., 2024)
- **NumPy, Scipy and scikit-image:** used for array processing, filtering and morphological operations
- **Pvlib or astral:** calculate solar elevation from ping timestamps and mooring coordinates
- **Pytorch and torchvision:** used to build and train CNN
- **Pytorch-grad-cam:** Grad-CAM heatmaps for the CNN
- **GPU access**

## 7. Evaluation Metrics

- Balanced Accuracy
- Precision
- Recall
- F1-score
- Confusion Matrix
- ROC-AUC
- Learning curve

## 8. Timeline

| Weeks | Tasks |
|---|---|
| 1-2 | Preparation of dataset |
| 3-4 | Model training and tuning |
| 5 | Evaluation |
| 6 | Wrap up, final report and presentation |

## 9. Related Work

- **Rousseau et al. (2022):** DFO study using a seafloor-mounted, upward-looking, multi-frequency AZFP in Okisollo Channel (Discovery Islands), the same setup as our data. A random forest on per-school acoustic, shape and depth features separated juvenile salmon from herring with 98% accuracy, using daytime data only, background noise removal and a multi-frequency fish mask. Our RF baseline, feature set and fish mask follow this paper. 
- **Marques et al. (2021):** Uses Mask R-CNN to outline herring and juvenile salmon schools in 67 kHz echograms from DFO's seafloor AZFP in Okisollo Channel, with 153 herring and 252 salmon examples. Training from scratch performed poorly, so the model started from pretrained weights (transfer learning), which supports our use of a pretrained ResNet-18. 
- **Slonimer (2022); Slonimer et al. (2023):** Trains a U-Net to label every echogram pixel as herring, salmon, bubbles, surface or background, using AZFP data at 67, 125, 200 and 455 kHz stacked as input channels plus depth and solar elevation channels. Reached F1 scores of 93.0% (herring), 87.3% (salmon) and 86.5% (bubbles), and the added depth and solar elevation channels improved accuracy. Source for our fixed dB scaling, context channels and surface detection approach. 
- **Pala et al. (2024):** Their model first learns from unlabelled echogram patches, then is fine-tuned on the few labelled ones. Open-source code exists. Relevant because most of our year-long recordings are unlabelled. 


## 10. Individual Objectives

### Olivia Whitelaw

**Preprocessing**

**Objective 1: Data inventory, conversion, and label audit**
- PI1 (basic): Verify the annotations. DFO reports that the deployments have been annotated in Echoview. Export `.evr` regions, then count classed regions per species, site and deployment week
- PI2 (basic): Convert one deployment's .01A files to SV with echopype using its `.XML`/ `.DPL` calibration. Save as NetCDF/Zarr
- PI3 (basic): Parse `.evr` files with echoregions (OSOceanAcoustics, n.d.). Produce a table of every region (site, deployment, start/ end time, depth range, class, region type)
- PI4 (expected): Check that region time and depths line up with the Sv data. Check time zones (Echoview vs AZFP clock) and the depth reference and confirm visually on echograms
- PI5 (expected/ advanced): scale conversion to all sites and years with Dask/ Zarr chunking. Document calibration and instrument differences between deployments like frequency, ping rate, and bin size (Lee et al., 2024)

**Objective 2: Boundary removal**
- PI1 (basic): Flag and remove bad pings, gaps and "bad data" regions
- PI2 (basic): Mask the surface and near-field using `.evl` lines where they exist
- PI3 (expected): Implement automatic surface detection for periods with no `.evl` lines. First test the Echofilter model (Lowe et al., 2022) and then try a detector based on high-frequency Sv gradient (Slonimer, 2022).
- PI4 (expected): Validate it against the existing Echoview .evl lines
- PI5 (expected/ advanced): Seafloor or obstruction masking if needed (echopype detect_seafloor)

**ML: CNN**

**Objective 3: Build the Image dataset**
- PI1 (basic): Extract the cleaned Sv inside each DFO labelled region as a fixed size image
- PI2 (basic): Stack both frequencies (Sv 67 kHz, Sv 125 kHz) and their difference as input channels, scaled identically (fix dB range) across all images
- PI3 (expected): Sample "no fish" background images from empty water
- PI4 (expected): Add data augmentation (crop shifts, time flips, small level offsets) because there are not many labelled regions
- PI5 (advanced): context channels (depth below surface, solar elevation). Species sit at different depths and behave differently with light, adding solar elevation has been seen to help with accuracy (Slonimer et al., 2023).

### Amanda Tu

**Preprocessing**

**Objective 1: Noise removal**
- PI1 (basic): Apply background noise removal to the Sv data
- PI2 (basic): Produce before/ after echograms
- PI3 (expected): Add transient and impulse noise filtering
- PI4 (expected): Measure how many labelled regions remain after each cleaning step

**Objective 2: Train the CNN**
- PI1 (basic): Fine-tune a pretrained CNN (ResNet-18) on the shared split
- PI2 (basic): Apply regularization and early stopping to prevent overfitting
- PI3 (expected): Use a hierarchical output: the model decides in stages (fish or not, then herring or salmon, then adult or juvenile salmon, if enough labels), so "Unclassified" regions still train the first decision
- PI4 (expected): Report per-class precision, recall, F1 and confusion matrices on the same test set as the RF
- PI5 (advanced): Use hierarchical output to stop at broader label when the model is unsure, and measure how accuracy changes when it's allowed to answer less specifically

### Ali Stein-Gagnon

**Preprocessing**

**Objective 1: Day/ night separation and fish masking**
- PI1 (basic): Calculate solar elevation from each ping's timestamp and mooring coordinates
- PI2 (basic): Separate day and night data
- PI3 (expected): Compute the dB difference between the two frequencies
- PI4 (expected): Apply multi-frequency mask to separate fish from background (Rousseau et al., 2022)
- PI5 (advanced): Use the fish mask to remove background pixels inside each labelled region before the images are made

**ML: Random Forest**

**Objective 2: Feature Extraction**
- PI1 (basic): Per-region features: mean Sv at 67 and 125 kHz, Sv (67-125 kHz), mean depth, height, length, area
- PI2 (basic): Add context features: time of day, day of year, solar elevation, depth below surface
- PI3 (expected): Add shape and texture features: Sv variability, skewness, kurtosis
- PI4 (expected): Correlation/VIF screening to remove redundant features (following Rousseau et al., 2022)
- PI5 (advanced): Compare with Echoview's "analysis by region" school descriptor export if DFO has one

**Objective 3: Explore CNN variants**
- PI1 (basic): Backbone vs full fine-tuning
- PI2 (basic): Compare using 67 kHz only vs both frequencies plus their difference
- PI3 (expected): Plot CNN accuracy against the number of training regions for comparison with the RF
- PI4 (advanced): Use Grad-CAM heatmaps to check that the CNN focuses on the school rather than the surface or background

### Carson Underhay

**Preprocessing**

**Objective 1: Shared train/ validation/ test splits**
- PI1 (basic): Split the data by deployment week so no week appears in more than one set
- PI2 (basic): Save one split file used by both the RF and the CNN
- PI3 (expected): Report the number of regions per species in each split
- PI4 (expected): Flag species with too few regions for the CNN
- PI5 (advanced): Set up grouped cross-validation by week for more reliable scores on small classes

**ML: Random Forest**

**Objective 2: RF training and tuning**
- PI1 (basic): Baseline RF on the shared split
- PI2 (basic): Class weighting or balanced sampling for imbalanced classes
- PI3 (expected): Hyperparameter tuning with grouped cross-validation (never random folds)
- PI4 (expected): Per-class precision, recall, F1 and confusion matrices
- PI5 (advanced): Reproduce Rousseau's random-split setup next to the week-held-out split to measure how much a random split inflates scores

**Objective 3: Interpretation**
- PI1 (basic): Rank feature importance
- PI2 (basic): Check whether depth or date dominate predictions, which would suggest that the model relies on position and season rather than acoustic cues
- PI3 (expected): Identify which species are most often confused
- PI4 (expected): Show example echograms of correctly and incorrectly classified regions
- PI5 (advanced): Plot RF accuracy against the number of training regions for comparison with the CNN

## 11. References

**Echopype Developers. (2024).** *Converting raw files*. Echopype documentation. https://echopype.readthedocs.io/en/stable/convert.html#supported-raw-file-types

> Technical documentation listing the raw file types Echopype supports, including AZFP (.01A) files, which require the deployment's .XML file for conversion via the `sonar_model="AZFP"` setting.

**He, K., Zhang, X., Ren, S., & Sun, J. (2016).** Deep residual learning for image recognition. In *Proceedings of the IEEE Conference on Computer Vision and Pattern Recognition (CVPR)* (pp. 770–778). https://doi.org/10.1109/CVPR.2016.90

> Introduces ResNet, a CNN architecture. ResNet-18, the smallest version, is the pretrained backbone we fine-tune for species classification.

**Johannesson, K. A., & Mitson, R. B. (1983).** *Fisheries acoustics: A practical manual for aquatic biomass estimation* (FAO Fisheries Technical Paper No. 240). Food and Agriculture Organization of the United Nations.

> Foundational FAO manual on using echosounders to estimate fish biomass, including the early history of acoustic fish detection cited in our overview.

**Lee, W.-J., Setiawan, L., Tuguinay, C., Mayorga, E., & Staneva, V. (2024).** Interoperable and scalable echosounder data processing with Echopype. *ICES Journal of Marine Science*, 81(10), 1941–1951. https://doi.org/10.1093/icesjms/fsae133

> Paper from the Echopype developers describing the open-source Python package that converts raw echosounder data (including AZFP) into a standard netCDF/Zarr format and computes Sv. Built on xarray with Dask, so it scales from a laptop to the cloud for large datasets like ours.

**Lowe, S. C., McGarry, L. P., Douglas, J., Newport, J., Oore, S., Whidden, C., & Hasselman, D. J. (2022).** Echofilter: A deep learning segmentation model improves the automation, standardization, and timeliness for post-processing echosounder data in tidal energy streams. *Frontiers in Marine Science*, 9. https://doi.org/10.3389/fmars.2022.867857

> Echofilter is an open-source deep-learning tool that draws boundary lines you'd otherwise draw by hand in Echoview for upward-looking moorings. It was trained on Simrad EK80 data, not AZFP, so signal and noise will differ and it might work less well without retraining.

**Marques, T. P., Cote, M., Rezvanifar, A., Branzan Albu, A., Ersahin, K., Mudge, T., & Gauthier, S. (2021).** Instance segmentation-based identification of pelagic species in acoustic backscatter data. In *Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition Workshops (CVPRW)*. https://openaccess.thecvf.com/content/CVPR2021W/PBVS/papers/Marques_Instance_Segmentation-Based_Identification_of_Pelagic_Species_in_Acoustic_Backscatter_Data_CVPRW_2021_paper.pdf

**OSOceanAcoustics. (n.d.).** *Echoregions* [Computer software]. GitHub. https://github.com/OSOceanAcoustics/echoregions

> Open-source Python library that reads Echoview region (`.evr`) and line (`.evl`) files and converts them into masks aligned with Echopype Sv data. Links DFO's Echoview labels to our processed data.

**Pala, A., Oleynik, A., Malde, K., & Handegard, N. O. (2024).** Self-supervised feature learning for acoustic data analysis. *Ecological Informatics*, 84, 102878. https://doi.org/10.1016/j.ecoinf.2024.102878

**Rezvanifar, A., Marques, T. P., Cote, M., Branzan Albu, A., Slonimer, A., Tolhurst, T., Ersahin, K., Mudge, T., & Gauthier, S. (2019).** A deep learning-based framework for the detection of schools of herring in echograms. *NeurIPS 2019 Workshop on Tackling Climate Change with Machine Learning*. arXiv:1910.08215. https://arxiv.org/abs/1910.08215

> A two-stage system on AZFP data from Discovery Passage, BC: a rule-based detector (median filtering, adaptive thresholding, morphological opening/closing, dropping small or flat blobs) proposes regions, then a CNN classifies each as herring or background. DenseNet201 performed best (F1 ~ 0.82).

**Rousseau, S., Gauthier, S., Johnson, S., Neville, C., & Trudel, M. (2018).** *Juvenile salmon acoustic monitoring in the Discovery Islands, British Columbia* (Canadian Technical Report of Fisheries and Aquatic Sciences 3277). Fisheries and Oceans Canada.

**Rousseau, S., Gauthier, S., Neville, C., Johnson, S., & Trudel, M. (2022).** Acoustic classification of juvenile Pacific salmon (*Oncorhynchus* spp) and Pacific herring (*Clupea pallasii*) schools using random forests. *Frontiers in Marine Science*, 9, 857645. https://doi.org/10.3389/fmars.2022.857645

**Selvaraju, R. R., Cogswell, M., Das, A., Vedantam, R., Parikh, D., & Batra, D. (2017).** Grad-CAM: Visual explanations from deep networks via gradient-based localization. In *Proceedings of the IEEE International Conference on Computer Vision (ICCV)* (pp. 618–626). https://doi.org/10.1109/ICCV.2017.74

> Introduces Grad-CAM, which produces a heatmap showing which parts of an image a CNN relied on for its prediction. We use it to check that our CNN focuses on the fish school rather than the surface or background.

**Slonimer, A. (2022).** *Automatic classification of fish and bubbles at pixel-level precision in multi-frequency acoustic echograms using U-Net convolutional neural networks* [Master's thesis, University of Victoria]. http://hdl.handle.net/1828/13850

**Slonimer, A. L., Dosso, S. E., Branzan Albu, A., Cote, M., Marques, T. P., Rezvanifar, A., & Ersahin, K. (2023).** Classification of herring, salmon, and bubbles in multifrequency echograms using U-Net neural networks. *IEEE Journal of Oceanic Engineering*, 48(4), 1236–1254. https://doi.org/10.1109/JOE.2023.3272393

