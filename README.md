# Running the Combinatorial Media Pipeline

This repository contains the required code and instructions to perform a media optimization campaign using the Automated Recommendation Tool (ART), uploading and accessing the data through the Experimental Data Depot (EDD). The required equipment is a Biomek-NX-S8 (to build the media) and a Biolector (for fermentation).

To do so, run the notebooks in order. 

1) Before the first experiment, and once the media components and bounds are selected, go through notebooks "A_Find_Stock_Concentrations.ipynb"  and "B_Create_Stock_Plates.ipynb" to design your experimental process. These will provide the required stock concentrations to build all the media within the defined bounds constrained by solubility, total volume and minimal transfer volume.

2) For the first 2 DBTL cycles, create initial media designs using the notebook "C_Initial_Media_Designs.ipynb". This will generate 2 biolector plates with media that maximally span the media phase space.

3) Once the media designs are generated, go through "D_Create_Transfers.ipynb" to generate the instruction for the liquid handler, and build the media directly on the biolector plate.

4) Once the media is complete, transfer this to the biolector, run your ferementation and measure the output (in this case it was OD340). Create the files to upload to EDD using the notebook "E_Create_EDD_Study_Files.ipynb".

5) Once the data is collected and uploaded to EDD, go through the notebook "F_Analysis.ipynb"

6) To move to the next DBTL cycle after the first 2 cycles, go through the notebook "C_ART_Media_Designs.ipynb" and move to step 3.

7) For every new DBTL cycle, iterate steps 6->3->4->5
