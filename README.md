# Running the Combinatorial Media Pipeline
This repository contains the code required to compile a media specification into liquid handler instruction csvs compatable with a BioMek NXP robot.  This code is used to realize an automated Design Build Test Learn \[DBTL\] cycle for media optimization.  In this file I explain how to use this code in conjunction with robots to complete a DBTL cycle which optimizes media for a particular bioproduct producing strain. The whole process is visualized below:

![Combinatorial Media DBTL Cycle Diagram](static/DBTL.png "DBTL Cycle")

For the remiander of the document we will refer to each step by its number and discuss how to conduct each one.

## 1. Defining The Initial Media
If this is the first cycle, media must either be prespecified or created using the create initial media function. In either case the first step is to create a media specification csv file.  This file contains a list of all possible media components along with the range of possible concentrations and the stock solution concentration. This defines a sample media phase space. An example is provided below with just two media components.  This example will not grow any microorganisms, but is provided to show how the software functions. So, please do not use this example for production.

> **_NOTE:_**  The headers must be spelled identically as above in order to work properly

> **_NOTE:_**  Glucose is specified in percent below.

| Media Components | Master Solution Concentration \[M\] | Min Concentration \[mM\] | Max Concentration \[mM\]
|---------|----|----|----|
| Glucose | 40 |   0|   5|
| Na2HPO4 |  1 |  10|  30|   


This file which we call 'example_stock_solutions.csv' is used to create a set of initial media compositions using the function below. In the case below we choose to create only two intial media variants.


```python 
import media_compiler as mc
df = mc.generate_initial_media('example_stock_solutions.csv')
```

This dataframe can then be directly used for downstream steps or exporeted as a csv for future use. If we choose to continue the dataframe can then be compiled into a set of instructions that are readable to the BioMek NxP platform. 

## 2. Generating Machine Readable BioMek NxP Instructions

In order to generate instuctions the input is a dataframe that looks like below.  The first two columns must be Plate and Well.  The last two columns are Volume and Target. The middle columns correspond to media components.

| Plate       |   Well |      Glucose |   Na2HPO4 |   Volume | Target   |
|:------------|-------:|-------------:|----------:|---------:|:---------|
| src_plate   |      1 | 40000        |    0      |     1000 | False    |
| src_plate   |      2 |     0        | 1000      |     1000 | False    |
| water_plate |      1 |     0        |    0      |     1600 | False    |
| water_plate |      2 |     0        |    0      |     1600 | False    |
| water_plate |      3 |     0        |    0      |     1600 | False    |
| water_plate |      4 |     0        |    0      |     1600 | False    |
| dest_plate  |      1 |     3.56712  |   14.8981 |     1100 | True     |
| dest_plate  |      9 |     3.56712  |   14.8981 |     1100 | True     |
| dest_plate  |     17 |     3.56712  |   14.8981 |     1100 | True     |
| dest_plate  |      2 |     0.265235 |   30.5683 |     1100 | True     |
| dest_plate  |     10 |     0.265235 |   30.5683 |     1100 | True     |
| dest_plate  |     18 |     0.265235 |   30.5683 |     1100 | True     |

> **_NOTE:_**  The above dataframe must have the indecies set to Plate and Well .

```python
df = df.set_index(['Plate','Well'])
mc.compile_media(df)
```

Running that command generates a set of csvs inside of the biomek_files directory. Now that the csvs are generated they can be used to create combinatorial media on the BioMek NxP platform.

## 3. Synthesize Media on the BioMek NxP Platform

> **_Point of Contact:_**  Tad Ogorzalek

> **_Note:_** I reccomend for anyone running this protocol to have Tad look over your work as you work with the biomek the first time.

In this step we synthesize all of the media required one plate must be created for each round of adaptation and/or production. Currently we use one adaptation round and one production round of fermentation, so two plates must be created. In order to synthesize one plate of media the following reagents are required.

- 3 Costar Deep Well Plates
- 1 BioMek Flower Plate
- 8 Plates of 200uL Robotic Tips

There is both a lab component and electronic component to this protocol.

1. [Lab] Fill up one of the deep well plates As specified by the dataframe used in step 2.  Using the example above Well 1 of the source plate would be filled with 1000 uL of Glucose and Well 2 would be filled with 1000 uL Na2HP04 stock solution.  Its a good idea to put more volume than is specified I usually add 1200 uL.

2. [Lab] Fill up a Costar Deep Well Plate 1700 uL of Water in each well.

3. [Electronic] Copy the following files from your local machine to the biomek NxP computer in the following directory: 

4. [Lab] Set up the Deck as specified above where the stock solution plate is in the first position in the to left.

5. [Electronic] Once the deck is configured

> **_NOTE:_**  In order to open the protocol it is in a password protected directory. The password is: z@k!

### Finishing the Media Plate
The Media Plate May need to be finished in order to move to the next step and do fermentation. Specifically, adding antibiotic, which is reccomended due to the fact that sterile conditions are hard to maintain in the robotics lab during the media creation process. Inducer needs to be added in the case of production. Innoculation is currently done by hand, either from an overnight culture on the first adaptation plate or from the previous plate. 
