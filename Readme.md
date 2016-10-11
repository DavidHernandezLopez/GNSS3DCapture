**GNSS 3D CAPTURE**
===================


This is a QGis plugin to measure 3D points from a GNSS connection

1. Install the plugin
2. In a QGis project, set a valid GNSS connection
3. Open the plugin
4. Set the Configuration:
	1. Select output CSV file
	2. Select output Coordinate Reference System
	3. If the NMEA sentence includes the ellipsoid height and you need the orthometric heigth (height from mean sea level), you can select the option of substract a geoid height from a selected geoid model (.gtx file in your \share\proj folder in QGis installation)
	4. Select the fields to be recorded for each point
5. Select update position to get current position
6. Select the values of the fields for the point to save
7. Set the antenna height for get the ground height
8. Save a point
9. ...

Notes:  

* The accuracy of the point depends on the accuracy of the position in NMEA sentence. Besides, the accuracy in orthometric height depends on the accuracy of the geoid model
* When you accept the configuration:  

	* A CSV file will be created. If a file exists with the same name in the same folder, the plugin rename it with a suffix including the date and time
	* A temporary layer will be created and added to map canvas. If exists a previous temporary layer with the same name, the plugin rename it with a suffix including the date and time. A style file is applied to a temporary folder from a template included into the /templates folder of the plugin
* Every time you save a point with the plugin, it will be saved to the CSV file and it will be added to the temporary layer
* When the you finish the work, you can save the temporary layer to a shapefile with the QGis tools

A set of images:

->![](/images/image001.png)<-

->![](/images/image002.png)<-

->![](/images/image003.png)<-

Contact:  
David Hernández López, david.hernandez@uclm.es