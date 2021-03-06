#!/usr/bin/env python3

import pandas as pd
import scipy as sp
import glob
from astropy.io import fits
from astropy.convolution import convolve, Box1DKernel
from scipy.interpolate import interp1d


import matplotlib.pyplot as plt

from fits import Spectrum

dataExample = Spectrum('/data2/cpb405/DR1/spec-55862-B6212_sp06-003.fits')

dataWavelength = dataExample.wavelength

width = 10

SDSS = pd.DataFrame(columns = ['totalCounts', 'B', 'V', 'R', 'I', 'BV', 'BR', 'BI', 'VR', 'VI', 'RI', 'Ha', 'Hb', 'Hg'])

letters = {"B":[3980,4920], "V":[5070,5950],"R":[5890,7270],"I":[7310,8810]}

lines = {'Ha':[6555, 6575], 'Hb':[4855, 4870], 'Hg':[4320,4370]}

for fitsName in glob.glob('/data2/mrs493/SDSS/*.fit'):
    
    hdulist = fits.open(fitsName)
    
    valid = True
            
    init = hdulist[0].header['COEFF0']
    disp = hdulist[0].header['COEFF1']
    flux = hdulist[0].data[0]

    wavelength = 10**sp.arange(init, init+disp*(len(flux)-0.9), disp)

    '''
    start conversion to data wavelength scale
        needed as wavelength range/intervals of SDSS different to LAMOST
    '''
    
    startIndex = sp.searchsorted(dataWavelength,wavelength[0],side="left")
    endIndex = sp.searchsorted(dataWavelength,wavelength[-1],side="right")
        #cannot interpolate outside given range, so cut off wavelengths outside
        
    plt.plot(wavelength, flux)
    
    fluxF = interp1d(wavelength, flux)
    flux = fluxF(dataWavelength[startIndex:endIndex])
    
    wavelength = dataWavelength[startIndex:endIndex]
    
    '''
    end
    '''
    
    stitchLower = sp.searchsorted(wavelength,5570,side="left")
    stitchUpper = sp.searchsorted(wavelength,5590,side="right")
    
    flux[stitchLower:stitchUpper] = sp.nan
        
    flux[flux<0] = sp.nan
        
    smoothFlux = convolve(flux,Box1DKernel(width))[5*width:-5*width] 
    flux = flux[5*width:-5*width]
    wavelength = wavelength[5*width:-5*width]
    
    totalCounts = sp.nansum(flux)
    #spike = sp.median(sp.diff(flux[::10]))
    
    plt.plot(wavelength, smoothFlux)
    
    '''
    start
    '''
    
    #testing = sp.diff(flux[::10])
    #testing2 = (testing==testing and abs(testing)>10)
#    counts = [abs(testing)]   
        #to do: look into 'spikeness' 
    
    
    '''
    end
    '''
    
    eqWid = {}
    
    for line in lines:
        wRange = lines[line]
    
        wLower = sp.searchsorted(wavelength, wRange[0], side = 'left')
        wUpper = sp.searchsorted(wavelength, wRange[1], side = 'right')
        
        if wLower == len(wavelength) or wUpper == 0:
            valid = False
            break
        
        ends = [flux[wLower], flux[wUpper - 1]]
        wRange = wavelength[wUpper-1] - wavelength[wLower]
        
        actualA = sp.trapz(flux[wLower:wUpper], wavelength[wLower:wUpper])
        theoA = (ends[0] + ends[1])*wRange/2.
        
        eqWid[line] = wRange*(1-(actualA/theoA))
        
        '''
        plt.plot(wavelength[wLower:wUpper], flux[wLower:wUpper])
        plt.plot([wavelength[wLower],wavelength[wUpper-1]], [flux[wLower], flux[wUpper - 1]])
        plt.annotate('Equivalent Width = {}'.format(eqWid[line]), xy = (0.05, 0.05), xycoords = 'axes fraction')#, color = 'red')
        plt.xlabel('Wavelength \ Angstroms')
        plt.ylabel('Flux')
        plt.title('{} line'.format(line))
        '''
            #for plotting the lines
        
        if not eqWid[line] == eqWid[line]:
            valid = False
             
    bands = {}
    
    for letter in letters:
        lower = sp.searchsorted(wavelength, letters[letter][0], side = 'left')
        upper = sp.searchsorted(wavelength, letters[letter][1], side = 'right')
        if lower == len(wavelength) or upper == 0:
            valid = False
        bandFlux = smoothFlux[lower:upper]
        bands[letter] = -2.5*sp.log10(sp.nanmean(bandFlux))
        if bands[letter] == sp.inf or bands[letter] == -sp.inf:
            bands[letter] = sp.nan
            valid = False
                
    BV = bands['B'] - bands['V']
    BR = bands['B'] - bands['R']
    BI = bands['B'] - bands['I']
    VR = bands['V'] - bands['R']
    VI = bands['V'] - bands['I']
    RI = bands['R'] - bands['I']
        
    if valid:
        SDSS.loc[len(SDSS)] = [totalCounts, bands['B'], bands['V'], bands['R'], bands['I'], BV, BR, BI, VR, VI, RI, eqWid['Ha'], eqWid['Hb'], eqWid['Hg']]

    hdulist.close()
    
    print valid
    plt.show()

SDSS.to_csv('/data2/mrs493/train.csv')