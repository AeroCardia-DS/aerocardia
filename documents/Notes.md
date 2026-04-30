### Notes Matthew

The data dictionary is our planned list of features, so it is just listing what the **feature name** is, **what it means**, the 
**theoretical equation for calculating it**, and what **type of metric it is**.The dataset has the columns for everything we are
directly measuring and the things being calculated already in the system.

The blank spaces in the Heart Rate and SpO2 (%) are when there is poor contact between the user's lip and the device, 
or the algorithm is not yet certain of the value. The numbers are being calculated from the PPG IR and PPG Red data in 
columns Z and AA. We use an algorithm derived from the Max30102 basic one, Measure Heart Rate and SpO2 with MAX30102 
| Arduino Project Hub RER is being calculated from the O2 and CO2 data, and has a floor of 0.7 while we await our CO2 
sensors to arrive in the mail. Pressure A, B, & C are used for our volume flow algorithm, while columns O & P are 
calculated differentials. Q, R and S are the temperatures at each pressure board, they are used for calibrating the 
sensors. T through Y are IMU outputs, they will be more interesting in the data from the test protocol.
Here is the link to the video of the protocol parts, https://photos.app.goo.gl/dXNo9RkhWuqum7aJ6, and I have attached 
the current state of the protocol. We are planning on adding a timed up and go next.

As for your questions: success will be measured by learning, and determining interesting things from the data, be that 
a biomarker, or a problem with it. I want to define success with you all.
Data is collected daily from our user, and protocols will also be run daily starting next week. 
There are no assumptions that come to mind
There will be biases due to data not coming from a representative sampling of people, currently it will be limited to 
the protocol attached, but I can add other tests if you think they are useful.
A recurrent meeting would be great, I agree. Does Thursday at 3 pm CST/5 pm EST still work, or do we need another time?
