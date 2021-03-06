# -*- coding: utf-8 -*-
'''
example script for estimation of adaptation parameters of an adaptive leaky or 
exponential I&F neuron (LIF/EIF) subject to fluctuating inputs, using method 1b, 
cf. Ladenbauer et al. 2018 (Results section 5, Fig 6B)
-- written by Josef Ladenbauer in 2018 

run time was <7 min. on an Intel i7-2600 quad-core PC using Python 2.7 
(Anaconda distribution v. 5.0.1) 
'''

import inference_methods as im
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import time
import scipy.optimize
import scipy.io
import scipy.stats
matplotlib.rc('text', usetex=True)
matplotlib.rc('xtick', labelsize=12) 
matplotlib.rc('ytick', labelsize=12) 
                                        
# SET PARAMETERS --------------------------------------------------------------
params = dict()
# neuron model parameters:
params['tau_m'] = 20.0  # ms, membrane time constant
params['V_r'] = -70.0  # mV, reset voltage
params['V_s'] = -40.0  # mV, spike voltage
params['Delta_T'] = 0.0  # mV, threshold slope factor (set 0 for LIF model, 
                         #                                >0 for EIF model)  
params['V_T'] = -50.0  # mV, effective threshold voltage (only used for EIF)
params['T_ref'] = 0.0  # ms, refractory duration
tau_w_true = 100.0  #ms, adaptation time constant
Delta_w_true = 0.5 #mV/ms, adaptation strength

# input parameters:
mu = -1.75  # mV/ms, input mean
sigma = 2.5 # mV/sqrt(ms), input standard deviation (noise intensity)

# parameters for data generation:
params['dt_sim'] = 0.05  # ms, simulation time step
t_start = 0.0  # ms
t_end = 1e5  # ms
t_limits = [10e3, 11e3]  # ms, for plots
V_init = params['V_r']  # initial condition 
N_spk = 1000  # number of spikes used for estimation
np.random.seed(10)

# parameters for calculation of likelihood (method 1b) 
params['V_lb'] = -150.0  # mV, lower bound
params['neuron_model'] = 'LIF'
params['integration_method'] = 'implicit'
params['N_centers_fvm'] = 1000  # number of centers for voltage discretization
params['fvm_v_init'] = 'delta'  # voltage density initialization
params['fvm_delta_peak'] = params['V_r']  # location of initial density peak
params['fvm_dt'] = 0.05  # ms, time step for finite volume method
tau_w_init = 70.0  # initial tau_w value
Delta_w_vals = np.arange(0.1, 1.5, 0.005)  # Delta_w values to scan for each 
                                           # tau_w value
mu_pert_vals = np.arange(0.2, 2.51, 0.10)  # mean input perturbation magnitudes
                                           # which relate to adaptation strength
                                           # (see im.spiketrain_likel_adapt)

if __name__ == '__main__':
    
    # GENERATE SPIKE TRAIN from neuron model ----------------------------------
    tgrid = np.arange(t_start, t_end+params['dt_sim']/2, params['dt_sim'])
            # time points for simulation
    
    rand_vec = np.random.randn(len(tgrid))
    
    start = time.time()    
    V_trace, w_trace, Sp_times = \
        im.simulate_EIF_adapt_numba(tgrid, V_init, params['tau_m'], params['V_s'], 
                                    params['V_r'], params['V_T'], params['Delta_T'], 
                                    params['T_ref'], mu, sigma, Delta_w_true, 
                                    tau_w_true, rand_vec)
    print('')
    print('simulation took {dur}s'.format(dur=np.round(time.time() - start,2)))
    
    # for plots (further below)
    inds = (tgrid>=t_limits[0]) & (tgrid<=t_limits[1])
    V_trace = V_trace[inds]
    w_trace = w_trace[inds]
    
    Spt_obs = Sp_times[:N_spk]
    ISIs = np.diff(Spt_obs)
    ISImin = np.min(ISIs)
    ISImax = 1.1*np.max(ISIs)
    lastSpidx = [len(Spt_obs)-1]
      
    
    # ESTIMATE PARAMETERS from spike train ------------------------------------
    start = time.time()
    
    
    t_grid = np.arange(0, ISImax, params['fvm_dt'])
    params['t_grid'] = t_grid
    
    lastrun = False
    args_fixed = (mu, sigma, Delta_w_vals, mu_pert_vals, Spt_obs, lastSpidx, 
                  params, ISImin, ISImax, lastrun)

    print('')
    print('likelihood optimization may take a couple of minutes...')
    sol = scipy.optimize.minimize(im.spiketrain_likel_adapt, tau_w_init, 
                                  args=args_fixed, method='nelder-mead', 
                                  options={'xatol':0.5, 'fatol':0.1}) 
    # spiketrain_likel_adapt finds optimal Delta_w via brute force for given tau_w
    print('')
    print sol 
    
    tau_w_estim = sol.x
    
    lastrun = True  # another (last) run to get also Delta_w_estim 
    args_fixed = (mu, sigma, Delta_w_vals, mu_pert_vals, Spt_obs, lastSpidx, 
                  params, ISImin, ISImax, lastrun)
    Delta_w_estim, tau_w_estim, lval = im.spiketrain_likel_adapt(tau_w_estim, 
                                                                 *args_fixed)
    
    print('')
    print('estimation took {dur}s'.format(dur=np.round(time.time() - start,2)))
    print('')
            
    # PLOT --------------------------------------------------------------------         
    plt.figure()
    ax = plt.subplot(211)
    plt.plot(tgrid[inds], V_trace, color=(0.6,0.6,0.6))
    Spt_plot = Sp_times[(Sp_times>=t_limits[0]) & (Sp_times<=t_limits[1])]
    for i in range(len(Spt_plot)):
        plt.plot([Spt_plot[i], Spt_plot[i]], [params['V_s'], params['V_s']+2.5], 
                 'k', linewidth=2)
    plt.plot([10e3-50, 10e3-50], [-80, -60], 'k', linewidth=2)
    plt.plot([10e3-50, 10e3+150], [-80, -80], 'k',  linewidth=2)
    plt.ylim([-82, -35])
    plt.axis('off')
    
    plt.subplot(212, sharex=ax)
    plt.plot(tgrid[inds], w_trace, color=(0.6,0.6,0.6))
    plt.plot([10e3-50, 10e3-50], [0.1, 0.3], 'k', linewidth=2)
    plt.plot([10e3-50, 10e3+150], [0.1, 0.1], 'k', linewidth=2)
    plt.axis('off')
    
    tgrid_tmp, w_trace_estim = im.get_w_trace_numba(Spt_obs, tau_w_estim, 
                                                    params['dt_sim'])
    inds = (tgrid_tmp>=t_limits[0]) & (tgrid_tmp<=t_limits[1])
    plt.plot(tgrid_tmp[inds], Delta_w_estim*w_trace_estim[inds], 'g', linewidth=2)