# MeshStatistics


## What is it?
This extension contains one module of the same name. It allows users to compute different descriptive statistics on specific predefined regions or the entire model. 
MeshStatistics only works on a  model that  contains stored  surface distances computed with the ModelToModelDistance module (computes a point by point distance between two models loaded in Slicer http://www.slicer.org/slicerWiki/index.php/Documentation/Nightly/Extensions/ModelToModelDistance)

Statistics computed are:
* Minimum and maximum values
* Average
* Standard deviation
* Percentile (5th, 15th, 25th, 50th, 75th, 85th, 95th)

Statistics are displayed on a table and it is possible to export all those values as csv files. 
It is possible to compute statistics on several models at the same time as long as regions on which users want compute statistics are the same on each of them.


## License
Please see LICENSE.txt


