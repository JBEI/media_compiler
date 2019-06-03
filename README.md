# Running the Combinatorial Media Pipeline
This repository contains the code required to compile a media specification into liquid handler instruction csvs compatable with a BioMek NXP robot.  This code is used to realize an automated Design Build Test Learn \[DBTL\] cycle for media optimization.  In this file I explain how to use this code in conjunction with robots to complete a DBTL cycle which optimizes media for a particular bioproduct producing strain. The whole process is visualized below:

![Combinatorial Media DBTL Cycle Diagram](static/DBTL.png "DBTL Cycle")

For the remiander of the document we will refer to each step by its number and discuss how to conduct each one.

## 1. Defining The Media
If this is the first cycle, media must either be prespecified or created using the create initial media function. In either case the first step is to create a media specification csv file.  This file contains a list of all possible media components along with the range of possible concentrations and the stock solution concentration. An example is provided below.