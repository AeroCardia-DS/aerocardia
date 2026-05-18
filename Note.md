# Notes

- Add new features like sex, occupation, patient demographic, diet
- This is the most critical engineering step of the project. Translating raw sensor telemetry into validated 
physiological metrics is essentially signal processing and applied physics Since tackling all 30+ features at once is 
overwhelming, we can group them by the mathematical and programming techniques we will need to calculate them.

Example:

| Planned Feature | Raw Data Required | Mathematical Approach |
| :--- | :--- | :--- |
| **Respiratory Rate (RR)** | `lung_volume` or `p_bmpA` | Peak detection (e.g., `scipy.signal.find_peaks`) on the volume or pressure wave to count breaths per minute. |
| **Flow Rate** | `lung_volume`, `timestamp` | First derivative of volume over time. $$Flow = \frac{dV}{dt}$$ |
| **Work of Breathing** | `p_bmpA`, `lung_volume` | Integration of the pressure-volume loop for a single breath. $$WOB = \int P \, dV$$ |
| **Lung Compliance** | `lung_volume`, `p_bmpA` | Change in volume divided by change in pressure. $$C = \frac{\Delta V}{\Delta P}$$ |
| **Tidal Volume (VT)** | `lung_volume` | Maximum volume minus minimum volume for a single identified breath cycle. |


