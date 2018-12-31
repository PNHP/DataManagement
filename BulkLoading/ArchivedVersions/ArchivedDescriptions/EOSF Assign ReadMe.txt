EO/SF Assign Script Tool ReadMe

------------------------------------------------------------------------------
Name:        EO/SF Assign
Purpose:     Used to prepare feature class or shapefile for bulk load into
             Biotics by assigning an existing EOID or new EO grouping string
             to observations based on separation distance.
Author:      MMOORE
Created:     02/13/2018
Updated:     10/02/2018
-------------------------------------------------------------------------------

Data needed to run EO/SF Assign Tool

- Spatial dataset of observations intended for bulk load. This dataset must include:
	- A field named 'SNAME' that includes scientific name of species

- Table of separation distances values for species present in spatial dataset. This dataset must include:
	- A field named 'SNAME' that includes scientific name of species
	- A field named 'sep_dist_km' that includes the separation distance for the species in kilometers

- Geodatabase containing existing source features in three feature classes named:
	- eo_sourcept
	- eo_sourceln
	- eo_sourcept