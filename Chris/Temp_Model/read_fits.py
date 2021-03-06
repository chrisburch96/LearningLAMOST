#!/usr/bin/env python3

import numpy as np
import matplotlib.pyplot as plt
import glob
from astropy.io import fits
from astropy.convolution import convolve, Box1DKernel
import pandas as pd
import sys

class Spectrum():
    ''' A class to read in and process a fits file containing a LAMOST spectrum'''
    def __init__(self, fits_sfile, fdict={'cAll':[0,9000], 'cB':[3980, 4920], 'cV':[5070,5950]}):
        self.fits_sfile = fits_sfile
        self.fdict = fdict
        keys = [n[0] for n in fdict.items()]
        keys = keys + ['d1', 'd2', 'd3', 'FILENAME', 'designation', 'CLASS']
        self.df = pd.DataFrame(columns=keys)
        self.read_fits_file()
        self.get_smoothing_features()
        
    def read_fits_file(self):
        ''' Read in and store the fits file data '''
        hdulist = fits.open(self.fits_sfile)
        self.flux = (hdulist[0].data)[0]
        self.spec_class = hdulist[0].header['CLASS']
        self.fname = hdulist[0].header['FILENAME']
        self.designation = hdulist[0].header['DESIG'][7:]
        init = hdulist[0].header['COEFF0']
        disp = hdulist[0].header['COEFF1']
        self.wavelength = 10**(np.arange(init,init+disp*(len(self.flux)-0.9),disp))
        hdulist.close()
    
    def process_fits_file(self):
        ''' Kills negative flux values and deals with echelle overlap region @ ~5580 A '''
        self.flux[self.flux < 0] = np.nan
        self.flux[(self.wavelength > 5570) & (self.wavelength < 5590)] = np.nan
        
    def get_smoothing_features(self):
        ''' Smoothes spectum using two different boxcar functions and finds differences '''
        w1 = 10
        w2 = 100
        buff = 1      
        smooth1 = convolve(self.flux,Box1DKernel(w1))[buff*w2:-buff*w2]
        smooth2 = convolve(self.flux,Box1DKernel(w2))[buff*w2:-buff*w2]        
        self.process_fits_file()
        total_flux = np.nanmean(self.flux)
        self.d1 = np.nanmean(abs(self.flux[buff*w2:-buff*w2]-smooth1))/total_flux
        self.d2 = np.nanmean(abs(self.flux[buff*w2:-buff*w2]-smooth2))/total_flux
        self.d3 = np.nanmean(abs(smooth1-smooth2))/total_flux

    def get_features(self, verbose=False):
        ''' Calculates colour indices of continuum and equivalent widths of spectral lines '''
        feats = np.zeros(len(self.fdict))
        i = 0
        for feat, lam in self.fdict.items():
            sel = np.where(np.logical_and(self.wavelength > lam[0], self.wavelength < lam[1]))[0]
            if feat[0]=='c': 
                feats[i] = -2.5*np.log10(np.nanmean(self.flux[sel]))
                if feats[i] != feats[i] or feats[i] == np.inf or feats[i] == (-1)*np.inf:
                    print(feats[i])                   
                    feats[i] = 0
                i += 1
                if verbose:
                    print('Feature ' + feat + ' : ', feats[i])
            elif feat[0]=='l':
                spec_line_width = self.wavelength[sel][-1]-self.wavelength[sel][0]
                wSel = np.concatenate((self.wavelength[sel[0]-20:sel[0]],self.wavelength[sel[-1]:sel[-1]+20]))
                fSel = np.concatenate((self.flux[sel[0]-20:sel[0]],self.flux[sel[-1]:sel[-1]+20]))
                check_nan = np.logical_not(np.isnan(fSel))
                fSel = fSel[check_nan]
                wSel = wSel[check_nan]
                
                lin = np.polyfit(wSel,fSel,1)
                '''
                S = np.sum(1/fSel)
                Sx = np.sum(wSel/fSel)
                Sy = len(fSel)
                Sxx = np.sum(wSel**2/fSel)
                Sxy = np.sum(wSel)
                
                grad = S*Sxx - Sx**2
                a = (Sxx*Sy - Sx*Sxy)/grad
                b = (S*Sxy - Sx*Sy)/grad
                '''
                spec_line_area = np.trapz(self.flux[sel],self.wavelength[sel])
                #continuum_area = (b*(self.wavelength[sel][0]+self.wavelength[sel][-1])+2*a) * spec_line_width/2   
                continuum_area = (lin[0]*(self.wavelength[sel][0]+self.wavelength[sel][-1])+2*lin[1]) * spec_line_width/2  
                feats[i] = (continuum_area-spec_line_area)/continuum_area * spec_line_width
                if feats[i] != feats[i]:
                    feats[i] = 0
                i += 1
                if verbose:
                    print('Feature ' + feat + ' : ', feats[i])     
        self.df.loc[len(self.df)] = [*feats, self.d1, self.d2, self.d3, self.fname, self.designation, self.spec_class]
        return self.df
        
    def plot_flux(self):
        fig, ax = plt.subplots()
        ax.plot(self.wavelength, self.flux)
        plt.show()

    def __call__(self):
        ''' Calls helper functions in turn when instance of class is made '''
        return self.get_features()
        
if __name__ == "__main__":
    sdir = '/data2/mrs493/DR1_3/'
    files = glob.glob(sdir + '*.fits')
    fdict = {'cAll':[0,9000], 'cB':[3980, 4920], 'cV':[5070,5950], 'cR':[5890,7270], 'cI':[7310,8810],
             'lHa':[6555,6575], 'lHb':[4855,4870], 'lHg':[4320,4370], 'lHd':[4093,4113], 'lHe':[3960,3980], 
             'lNa':[5885,5905], 'lMg':[5167,5187], 'lK':[3925,3945], 'lG':[4240,4260]}
    if len(sys.argv) != 2:
        print('Usage : ./read_fits.py index')
    index = int(sys.argv[1])
    batch = 100
    print("Processing file numbers {} {}".format(index*batch, (index+1)*batch))
    for idx, f in enumerate(files[index*batch:(index+1)*batch]):
        try:
            spec = Spectrum(f,fdict)
            df = spec()
            if idx == 0:
                df_main = df.copy()
            else:
                df_main = pd.concat([df_main, df])
        except:
            print("Failed for file : ", f)
    df_main.to_csv('TempCSVs3/output_' + str(index) + '.csv')

