cmake_minimum_required(VERSION 2.8.9)

project(MeshStatisticsExtension)

#-----------------------------------------------------------------------------
# Extension meta-information
set(EXTENSION_HOMEPAGE "https://www.slicer.org/slicerWiki/index.php/Documentation/Nightly/Extensions/MeshStatistics")
set(EXTENSION_CATEGORY "Shape Analysis")
set(EXTENSION_CONTRIBUTORS "Lucie Macron (University of Michigan)")
set(EXTENSION_DESCRIPTION "Mesh Statistics allows users to compute descriptive statistics over specific and predefined regions")
set(EXTENSION_ICONURL "https://raw.githubusercontent.com/DCBIA-OrthoLab/MeshStatisticsExtension/master/MeshStatistics/Resources/Icons/MeshStatistics.png")
set(EXTENSION_SCREENSHOTURLS "https://www.slicer.org/slicerWiki/index.php/File:MeshStatistics_Interface.png")
set(EXTENSION_DEPENDS ModelToModelDistance)

#-----------------------------------------------------------------------------
# Extension dependencies
find_package(Slicer REQUIRED)
include(${Slicer_USE_FILE})

#-----------------------------------------------------------------------------
# Extension modules
add_subdirectory(MeshStatistics)
## NEXT_MODULE

#-----------------------------------------------------------------------------
include(${Slicer_EXTENSION_GENERATE_CONFIG})
include(${Slicer_EXTENSION_CPACK})
