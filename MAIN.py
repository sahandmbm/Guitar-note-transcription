"""
guitar_sonification.py - Guitar Sonification: Audio to MIDI Conversion
By Sahand ShahRiari
"""

### SEGMENTING AUDIO



print("\n<<Guitar Sonification>>\nLoading...\n")
question1 = 'random'
while question1 != 'y':
    question1 = input('do you want to find your notes? (y/n)\n')
    if question1 == 'y':
        question2 = input('\n\nPress 1 to start recording \nPress 2 to load existing file\n')
        if question2 == '1':
            question3 = int(input('How may seconds do you want to Record? \n'))
        else:
            print ("")
            question3 = 0
    if question1 == 'n':
        print("Sorry to hear that\nBye!")
        exit()

### IMPORTING LIBRARIES
print("\n<<Guitar Sonification: Importing libraries>>\nLoading...\n")
import librosa, librosa.display, numpy, scipy
import matplotlib.pyplot as plt
import sounddevice as sd
from audiolazy import freq2str
import time
import math
import wave
import curses
import pyaudio
import struct
import numpy
from numpy.fft import rfft
from numpy import argmax, mean, diff, log, polyfit, arange
from matplotlib.mlab import find
from scipy.signal import blackmanharris, fftconvolve
from pylab import subplot, plot, log, copy, show
import sys, soundfile
from pysndfx import AudioEffectsChain
import python_speech_features
import scipy as sp
from scipy import signal


# 'curses' configuration
stdscr = curses.initscr()
stdscr.nodelay(True)
curses.noecho()
curses.cbreak()

# PyAudio object variable
pa = pyaudio.PyAudio()
# Size of each read-in chunk
CHUNK = 1
# Set how often data for the result will be saved (every nth CHUNK)
NTH_ITERATION = 1
BUFFER_SIZE = 1024  # Increase this if playback becomes choppy, decrease to reduce latency
CHANNELS = 2
RECORD_SECONDS = question3
WAVE_OUTPUT_FILENAME = "file.wav"
FORMAT = pyaudio.paInt16




### RECORDING AUDIO --------------------------------------------------------------------------------------------------------------------------------

def recording():

    print("\n<<Guitar Sonification: Record >>\nLoading...\n")
    print("\n\n<<Sound Card Details>>")
    sound_card = pyaudio.PyAudio()
    input_info = sound_card.get_default_input_device_info()

    for i in input_info:
        print( i + ": " + str(input_info[i]))
    print()

    line_in = sound_card.open(format=FORMAT,
                              frames_per_buffer=BUFFER_SIZE,
                              channels= CHANNELS,
                              rate = int(input_info["defaultSampleRate"]),
                              input=True,
                              output=True)
    print(" \n\n ------------------------\n NOW RECORDING... \n------------------------\n")
    
    frames = []
    for i in range(0, int(int(input_info["defaultSampleRate"]) / BUFFER_SIZE * RECORD_SECONDS)):
        data = line_in.read(BUFFER_SIZE)
        frames.append(data)

    print ("finished recording!")

    # stop Recording
    line_in.stop_stream()
    line_in.close()
    sound_card.terminate()
    
    waveFile = wave.open(WAVE_OUTPUT_FILENAME, 'wb')
    waveFile.setnchannels(CHANNELS)
    waveFile.setsampwidth(sound_card.get_sample_size(FORMAT))
    waveFile.setframerate(int(input_info["defaultSampleRate"]))
    waveFile.writeframes(b''.join(frames))
    waveFile.close()


def loadFile(fn):
    # Load a wave file
    x, sr = librosa.load("fn")
    print("LOADING... \n FILE LOADED: " , fn)
    print("Sample Rate = " + str(sr))
    return x, sr
















### NOISE CANCELLATION --------------------------------------------------------------------------------------------------------------------------------

### INVERT CANCELLATION -------------------------------------------------------------------------------------------------------------------------------
def noise(filename):
    # Read in the given file
    (waveform, stream) = readin(filename)

    # Give some feedback
    stdscr.addstr('Now noise-cancelling the file')

    # Collecting the volume levels in decibels in a list
    decibel_levels = []

    # Collecting the waves into lists
    total_original = []
    total_inverted = []
    total_difference = []

    # Counting the iterations of the while-loop
    iteration = 0

    # Determines the ratio of the mix
    ratio = 1.0

    # Determines if the noise-cancellation is active
    active = True

    # Read a first chunk and continue to do so for as long as there is a stream to read in
    original = waveform.readframes(CHUNK)
    while original != b'':
        try:
            # Capture if a key was pressed
            pressed_key = stdscr.getch()

            # If the 'o' key was pressed toggle the 'active' variable
            if pressed_key == 111:
                active = not active
                # While the noise-cancellation is not activated the ratio should be 100% towards the orginial audio
                if not active:
                    ratio = 2.0
                else:
                    ratio = 1.0
            # Increase the ratio of the mix
            elif pressed_key == 43:
                ratio += 0.01
            # Decrease the ratio of the mix
            elif pressed_key == 45:
                ratio -= 0.01
            # If the 'x' key was pressed abort the loop
            elif pressed_key == 120:
                break

            # Invert the original audio
            inverted = invert(original)

            # Play back a mixed audio stream of both, original source and the inverted one
            if active:
                mix = mix_samples(original, inverted, ratio)
                stream.write(mix)
            # In case the noise-cancellation is not turned off temporarily, only play the orignial audio source
            else:
                stream.write(original)

            # On every nth iteration append the difference between the level of the source audio and the inverted one
            if iteration % NTH_ITERATION == 0:
                # Clear the terminal before outputting the new value
                stdscr.clear()
                # Calculate the difference of the source and the inverted audio
                difference = calculate_difference(original, inverted)
                # Print the current difference
                stdscr.addstr('Difference (in dB): {}\n'.format(difference))
                # Append the difference to the list used for the plot
                decibel_levels.append(difference)
                # Calculate the waves for the graph
                int_original, int_inverted, int_difference = calculate_wave(original, inverted, ratio)
                total_original.append(int_original)
                total_inverted.append(int_inverted)
                total_difference.append(int_difference)

            # Read in the next chunk of data
            original = waveform.readframes(CHUNK)

            # Add up one to the iterations
            iteration += 1

        except (KeyboardInterrupt, SystemExit):
            break

    # Stop the stream after there is no more data to read
    stream.stop_stream()
    stream.close()

    # Outputting feedback regarding the end of the file
    print('Finished noise-cancelling the file')

    # Plot the results
    plot_results(decibel_levels, NTH_ITERATION)
    plot_wave_results(total_original, total_inverted, total_difference, NTH_ITERATION)

    # Revert the changes from 'curses'
    curses.endwin()

    # Terminate PyAudio
    pa.terminate()


def readin(file):
    """
    Reads in the given wave file and returns a new PyAudio stream object from it.

    :param file: The path to the file to read in
    :return (waveform, stream): (The actual audio data as a waveform, the PyAudio object for said data)
    """

    # Open the waveform from the command argument
    try:
        waveform = wave.open(file, 'r')
    except wave.Error:
        print('The program can only process wave audio files (.wav)')
        sys.exit()
    except FileNotFoundError:
        print('The chosen file does not exist')
        sys.exit()

    # Load PyAudio and create a useable waveform object
    stream = pa.open(
        format=pa.get_format_from_width(waveform.getsampwidth()),
        channels=waveform.getnchannels(),
        rate=waveform.getframerate(),
        output=True
    )

    # Return the waveform as well as the generated PyAudio stream object
    return waveform, stream


def invert(data):
    """
    Inverts the byte data it received utilizing an XOR operation.

    :param data: A chunk of byte data
    :return inverted: The same size of chunked data inverted bitwise
    """

    # Convert the bytestring into an integer
    intwave = numpy.fromstring(data, numpy.int32)
    # Invert the integer
    intwave = numpy.invert(intwave)
    # Convert the integer back into a bytestring
    inverted = numpy.frombuffer(intwave, numpy.byte)
    # Return the inverted audio data
    return inverted


def mix_samples(sample_1, sample_2, ratio):
    """
    Mixes two samples into each other

    :param sample_1: A bytestring containing the first audio source
    :param sample_2: A bytestring containing the second audio source
    :param ratio: A float which determines the mix-ratio of the two samples (the higher, the louder the first sample)
    :return mix: A bytestring containing the two samples mixed together
    """

    # Calculate the actual ratios based on the float the function received
    (ratio_1, ratio_2) = get_ratios(ratio)
    # Convert the two samples to integers
    intwave_sample_1 = numpy.fromstring(sample_1, numpy.int16)
    intwave_sample_2 = numpy.fromstring(sample_2, numpy.int16)
    # Mix the two samples together based on the calculated ratios
    intwave_mix = (intwave_sample_1 * ratio_1 + intwave_sample_2 * ratio_2).astype(numpy.int16)
    # Convert the new mix back to a playable bytestring
    mix = numpy.frombuffer(intwave_mix, numpy.byte)
    return mix


def get_ratios(ratio):
    """
    Calculates the ratios using a received float

    :param ratio: A float betwenn 0 and 2 resembling the ratio between two things
    :return ratio_1, ratio_2: The two calculated actual ratios
    """

    ratio = float(ratio)
    ratio_1 = ratio / 2
    ratio_2 = (2 - ratio) / 2
    return ratio_1, ratio_2


def calculate_decibel(data):
    """
    Calculates the volume level in decibel of the given data

    :param data: A bytestring used to calculate the decibel level
    :return db: The calculated volume level in decibel
    """

    count = len(data) / 2
    form = "%dh" % count
    shorts = struct.unpack(form, data)
    sum_squares = 0.0
    for sample in shorts:
        n = sample * (1.0 / 32768)
        sum_squares += n * n
    rms = math.sqrt(sum_squares / count) + 0.0001
    db = 20 * math.log10(rms)
    return db


def calculate_difference(data_1, data_2):
    """
    Calculates the difference level in decibel between the received binary inputs

    :param data_1: The first binary digit
    :param data_2: The second binary digit
    :return difference: The calculated difference level (in dB)
    """

    difference = calculate_decibel(data_1) - calculate_decibel(data_2)
    return difference


def calculate_wave(original, inverted, ratio):
    """
    Converts the bytestrings it receives into plottable integers and calculates the difference between both

    :param original: A bytestring of sound
    :param inverted: A bytestring of sound
    :param ratio: A float which determines the mix-ratio of the two samples
    :return int_original, int_inverted, int_difference: A tupel of the three calculated integers
    """

    # Calculate the actual ratios based on the float the function received
    (ratio_1, ratio_2) = get_ratios(ratio)
    # Convert the two samples to integers to be able to add them together
    int_original = numpy.fromstring(original, numpy.int16)[0] * ratio_1
    int_inverted = numpy.fromstring(inverted, numpy.int16)[0] * ratio_2
    # Calculate the difference between the two samples
    int_difference = (int_original + int_inverted)

    return int_original, int_inverted, int_difference


def plot_results(data, nth_iteration):
    """
    Plots the list it receives and cuts off the first ten entries to circumvent the plotting of initial silence

    :param data: A list of data to be plotted
    :param nth_iteration: Used for the label of the x axis
    """

    # Plot the data
    plt.plot(data[10:])

    # Label the axes
    plt.xlabel('Time (every {}th {} byte)'.format(nth_iteration, CHUNK))
    plt.ylabel('Volume level difference (in dB)')

    # Calculate and output the absolute median difference level
    plt.suptitle('Difference - Median (in dB): {}'.format(numpy.round(numpy.fabs(numpy.median(data)), decimals=5)), fontsize=14)

    # Display the plotted graph
    plt.show()


def plot_wave_results(total_original, total_inverted, total_difference, nth_iteration):
    """
    Plots the three waves of the original sound, the inverted one and their difference

    :param total_original: A list of the original wave data
    :param total_inverted: A list of the inverted wave data
    :param total_difference: A list of the difference of 'total_original' and 'total_inverted'
    :param nth_iteration: Used for the label of the x axis
    """

    # Plot the three waves
    plt.plot(total_original, 'b')
    plt.plot(total_inverted, 'r')
    plt.plot(total_difference, 'g')

    # Label the axes
    plt.xlabel('Time (per {}th {} byte chunk)'.format(nth_iteration, CHUNK))
    plt.ylabel('Amplitude (integer representation of each {} byte chunk)'.format(nth_iteration, CHUNK))

    # Calculate and output the absolute median difference level
    plt.suptitle('Waves: original (blue), inverted (red), output (green)', fontsize=14)

    # Display the plotted graph
    plt.show()












### NOISE CANCELLATION MAIN --------------------------------------------------------------------------------------------------------------------------------

'''------------------------------------
NOISE REDUCTION USING POWER:
    receives an audio matrix,
    returns the matrix after gain reduction on noise
------------------------------------'''
def reduce_noise_power(y, sr):

    cent = librosa.feature.spectral_centroid(y=y, sr=sr)

    threshold_h = round(numpy.median(cent))*1.5
    threshold_l = round(numpy.median(cent))*0.1

    less_noise = AudioEffectsChain().lowshelf(gain=-30.0, frequency=threshold_l, slope=0.8).highshelf(gain=-12.0, frequency=threshold_h, slope=0.5)#.limiter(gain=6.0)
    y_clean = less_noise(y)

    return y_clean


'''------------------------------------
NOISE REDUCTION USING CENTROID ANALYSIS:
    receives an audio matrix,
    returns the matrix after gain reduction on noise
------------------------------------'''

def reduce_noise_centroid_s(y, sr):

    cent = librosa.feature.spectral_centroid(y=y, sr=sr)

    threshold_h = numpy.max(cent)
    threshold_l = numpy.min(cent)

    less_noise = AudioEffectsChain().lowshelf(gain=-12.0, frequency=threshold_l, slope=0.5).highshelf(gain=-12.0, frequency=threshold_h, slope=0.5).limiter(gain=6.0)

    y_cleaned = less_noise(y)

    return y_cleaned

def reduce_noise_centroid_mb(y, sr):

    cent = librosa.feature.spectral_centroid(y=y, sr=sr)

    threshold_h = numpy.max(cent)
    threshold_l = numpy.min(cent)

    less_noise = AudioEffectsChain().lowshelf(gain=-30.0, frequency=threshold_l, slope=0.5).highshelf(gain=-30.0, frequency=threshold_h, slope=0.5).limiter(gain=10.0)
    # less_noise = AudioEffectsChain().lowpass(frequency=threshold_h).highpass(frequency=threshold_l)
    y_cleaned = less_noise(y)


    cent_cleaned = librosa.feature.spectral_centroid(y=y_cleaned, sr=sr)
    columns, rows = cent_cleaned.shape
    boost_h = math.floor(rows/3*2)
    boost_l = math.floor(rows/6)
    boost = math.floor(rows/3)

    # boost_bass = AudioEffectsChain().lowshelf(gain=20.0, frequency=boost, slope=0.8)
    boost_bass = AudioEffectsChain().lowshelf(gain=16.0, frequency=boost_h, slope=0.5)#.lowshelf(gain=-20.0, frequency=boost_l, slope=0.8)
    y_clean_boosted = boost_bass(y_cleaned)

    return y_clean_boosted


'''------------------------------------
NOISE REDUCTION USING MFCC:
    receives an audio matrix,
    returns the matrix after gain reduction on noise
------------------------------------'''
def reduce_noise_mfcc_down(y, sr):

    hop_length = 512

    ## librosa
    # mfcc = librosa.feature.mfcc(y=y, sr=sr, hop_length=hop_length, n_mfcc=13)
    # librosa.mel_to_hz(mfcc)

    ## mfcc
    mfcc = python_speech_features.base.mfcc(y)
    mfcc = python_speech_features.base.logfbank(y)
    mfcc = python_speech_features.base.lifter(mfcc)

    sum_of_squares = []
    index = -1
    for r in mfcc:
        sum_of_squares.append(0)
        index = index + 1
        for n in r:
            sum_of_squares[index] = sum_of_squares[index] + n**2

    strongest_frame = sum_of_squares.index(max(sum_of_squares))
    hz = python_speech_features.base.mel2hz(mfcc[strongest_frame])

    max_hz = max(hz)
    min_hz = min(hz)

    speech_booster = AudioEffectsChain().highshelf(frequency=min_hz*(-1)*1.2, gain=-12.0, slope=0.6).limiter(gain=8.0)
    y_speach_boosted = speech_booster(y)

    return (y_speach_boosted)

def reduce_noise_mfcc_up(y, sr):

    hop_length = 512

    ## librosa
    # mfcc = librosa.feature.mfcc(y=y, sr=sr, hop_length=hop_length, n_mfcc=13)
    # librosa.mel_to_hz(mfcc)

    ## mfcc
    mfcc = python_speech_features.base.mfcc(y)
    mfcc = python_speech_features.base.logfbank(y)
    mfcc = python_speech_features.base.lifter(mfcc)

    sum_of_squares = []
    index = -1
    for r in mfcc:
        sum_of_squares.append(0)
        index = index + 1
        for n in r:
            sum_of_squares[index] = sum_of_squares[index] + n**2

    strongest_frame = sum_of_squares.index(max(sum_of_squares))
    hz = python_speech_features.base.mel2hz(mfcc[strongest_frame])

    max_hz = max(hz)
    min_hz = min(hz)

    speech_booster = AudioEffectsChain().lowshelf(frequency=min_hz*(-1), gain=12.0, slope=0.5)#.highshelf(frequency=min_hz*(-1)*1.2, gain=-12.0, slope=0.5)#.limiter(gain=8.0)
    y_speach_boosted = speech_booster(y)

    return (y_speach_boosted)

'''------------------------------------
NOISE REDUCTION USING MEDIAN:
    receives an audio matrix,
    returns the matrix after gain reduction on noise
------------------------------------'''

def reduce_noise_median(y, sr):
    y = sp.signal.medfilt(y,3)
    return (y)


'''------------------------------------
SILENCE TRIMMER:
    receives an audio matrix,
    returns an audio matrix with less silence and the amout of time that was trimmed
------------------------------------'''
def trim_silence(y):
    y_trimmed, index = librosa.effects.trim(y, top_db=20, frame_length=2, hop_length=500)
    trimmed_length = librosa.get_duration(y) - librosa.get_duration(y_trimmed)

    return y_trimmed, trimmed_length


'''------------------------------------
AUDIO ENHANCER:
    receives an audio matrix,
    returns the same matrix after audio manipulation
------------------------------------'''
def enhance(y):
    apply_audio_effects = AudioEffectsChain().lowshelf(gain=10.0, frequency=260, slope=0.1).reverb(reverberance=25, hf_damping=5, room_scale=5, stereo_depth=50, pre_delay=20, wet_gain=0, wet_only=False)#.normalize()
    y_enhanced = apply_audio_effects(y)

    return y_enhanced

'''------------------------------------
OUTPUT GENERATOR:
    receives a destination path, file name, audio matrix, and sample rate,
    generates a wav file based on input
------------------------------------'''
def output_file(destination ,filename, y, sr, ext=""):
    destination = destination + filename[:-4] + ext + '.wav'
    librosa.output.write_wav(destination, y, sr)











### ONSET DETECTION AND SEGMENTATION ---------------------------------------------------------------------------------------------------------------
def onset(x, sr):
    # Short-time Fourier transform (for EQ, must do inverse Fourier transform after)
    X = librosa.stft(x)

    # Find the frames when onsets occur
    onset_frames = librosa.onset.onset_detect(x, sr=sr)
    print("Onset Frames = " + str(onset_frames) + "\n ")

    # Find the times, in seconds, when onsets occur in the audio signal
    onset_times = librosa.frames_to_time(onset_frames, sr=sr)
    print("Onset Times = " + str(onset_times) + "\n ")

    # Convert the onset frames into sample indices to play "BEEB" sound on it
    onset_samples = librosa.frames_to_samples(onset_frames)
    print("Onset Samples = " + str(onset_samples) + "\n ")

    # Use the "length" parameter so the click track is the same length as the original signal
    clicks = librosa.clicks(times=onset_times, length=len(x))

    # Play the click track "added to" the original signal
    sd.play(x + clicks, sr)

    # Display the waveform of the original signal
    librosa.display.waveplot(x, sr)
    plt.title("Original Signal")
    plt.show()  # Close window to resume

    return onset_frames, onset_times, onset_samples
# Concatenate the segments and pad them with silence
def concatenate_segments(segments, sr=22050, pad_time=0.100):
    padded_segments = [numpy.concatenate([segment, numpy.zeros(int(pad_time * sr))]) for segment in segments]
    return numpy.concatenate(padded_segments)

def segment(x, sr, onset_samples):

    frame_sz = int(0.100 * sr)
    segments = numpy.array([x[i:i + frame_sz] for i in onset_samples])
    concatenated_signal = concatenate_segments(segments, sr)
    # Play the segmented signal
    sd.play(concatenated_signal, sr)
    # Display the waveform of the segmented signal
    librosa.display.waveplot(concatenated_signal, sr)
    plt.title("Segmented Signal")
    plt.show()  # Close window to resume

    return segments











### PITCH DETECTION --------------------------------------------------------------------------------------------------------------------------------

def parabolic(f, x):
    """
    Quadratic interpolation for estimating the true position of an
    inter-sample maximum when nearby samples are known.

    f is a vector and x is an index for that vector.

    Returns (vx, vy), the coordinates of the vertex of a parabola that goes
    through point x and its two neighbors.

    Example:
    Defining a vector f with a local maximum at index 3 (= 6), find local
    maximum if points 2, 3, and 4 actually defined a parabola.
    """
    xv = 1 / 2. * (f[x - 1] - f[x + 1]) / (f[x - 1] - 2 * f[x] + f[x + 1]) + x
    yv = f[x] - 1 / 4. * (f[x - 1] - f[x + 1]) * (xv - x)
    return (xv, yv)


def parabolic_polyfit(f, x, n):
    """
    Use the built-in polyfit() function to find the peak of a parabola

    f is a vector and x is an index for that vector.

    n is the number of samples of the curve used to fit the parabola.
    """
    a, b, c = polyfit(arange(x - n // 2, x + n // 2 + 1), f[x - n // 2:x + n // 2 + 1], 2)
    xv = -0.5 * b / a
    yv = a * xv ** 2 + b * xv + c
    return (xv, yv)


def freq_from_crossings(sig, fs):
    """
    Estimate frequency by counting zero crossings
    """
    # Find all indices right before a rising-edge zero crossing
    indices = find((sig[1:] >= 0) & (sig[:-1] < 0))

    # Naive (Measures 1000.185 Hz for 1000 Hz, for instance)
    # crossings = indices

    # More accurate, using linear interpolation to find intersample
    # zero-crossings (Measures 1000.000129 Hz for 1000 Hz, for instance)
    crossings = [i - sig[i] / (sig[i + 1] - sig[i]) for i in indices]

    # Some other interpolation based on neighboring points might be better.
    # Spline, cubic, whatever

    return fs / mean(diff(crossings))


def freq_from_fft(sig, fs):
    """
    Estimate frequency from peak of FFT
    """
    # Compute Fourier transform of windowed signal
    windowed = sig * blackmanharris(len(sig))
    f = rfft(windowed)

    # Find the peak and interpolate to get a more accurate peak
    i = argmax(abs(f))  # Just use this for less-accurate, naive version
    true_i = parabolic(log(abs(f)), i)[0]

    # Convert to equivalent frequency
    return fs * true_i / len(windowed)


def freq_from_autocorr(sig, fs):

    """
    Estimate frequency using autocorrelation
    """
    # Calculate autocorrelation (same thing as convolution, but with
    # one input reversed in time), and throw away the negative lags
    corr = fftconvolve(sig, sig[::-1], mode='full')
    corr = corr[len(corr) // 2:]

    # Find the first low point
    d = diff(corr)
    start = find(d > 0)[0]

    # Find the next peak after the low point (other than 0 lag).  This bit is
    # not reliable for long signals, due to the desired peak occurring between
    # samples, and other peaks appearing higher.
    # Should use a weighting function to de-emphasize the peaks at longer lags.
    peak = argmax(corr[start:]) + start
    px, py = parabolic(corr, peak)

    return fs / px







### PRINT NOTES -----------------------------------------------------------------------------------------------------------------------------
def pitch(segment, sr):
    print("\n<<Guitar Sonification: Pitch Detection>>\nLoading...\n")
    try:
        signal, fs = segment, sr
    except NameError:
            signal, fs, enc = flacread(filename)

    print("Calculating frequency from FFT:")
    print("%f Hz" % freq_from_fft(signal, fs))
    a1 = freq_from_fft(signal, fs)
    b1 = freq2str(a1)
    print("MIDI NOTE: ", b1 + "\n")

    print("Calculating frequency from zero crossings:")
    print("%f Hz" % freq_from_crossings(signal, fs))
    a2 = freq_from_crossings(signal, fs)
    b2 = freq2str(a2)
    print("MIDI NOTE: ", b2 + "\n")

    print("Calculating frequency from autocorrelation:")
    print("%f Hz" % freq_from_autocorr(signal, fs))
    a3 = freq_from_autocorr(signal, fs)
    b3 = freq2str(a3)
    print("MIDI NOTE: ", b3)


    print("\n ________________________________ \n")



def pitchFFT(segment, sr):
    try:
        signal, fs = segment, sr
    except NameError:
            signal, fs, enc = flacread(filename)
    
    a1 = freq_from_fft(signal, fs)
    return a1
    




def pitchZCR(segment, sr):
    try:
        signal, fs = segment, sr
    except NameError:
            signal, fs, enc = flacread(filename)

    a2 = freq_from_crossings(signal, fs)
    return a2






def pitchAC(segment, sr):
    try:
        signal, fs = segment, sr
    except NameError:
            signal, fs, enc = flacread(filename)

    a3 = freq_from_autocorr(signal, fs)
    return a3




string6 = [330, 349, 370, 392, 415, 440, 466, 494, 523, 544, 587, 622, 659, 698, 740, 784, 831, 880, 932, 988, 1047]
string5 = [247, 262, 277, 294, 311, 330, 349, 370, 392, 415, 440, 466,  494, 523, 544, 587, 622, 659, 698, 740, 784]
string4 = [196, 208, 220, 233, 247, 262, 277, 294, 311, 330, 349, 370, 392, 415, 440, 466, 494, 523, 554, 587, 622]
string3 = [147, 156, 165, 175, 185, 196, 208, 220, 233, 247, 262, 277, 294, 311, 330, 349, 370, 392, 415, 440, 466]
string2 = [110, 117, 123, 131, 139, 147, 156, 165, 175, 185, 196, 208, 220, 233, 247, 262, 277, 294, 311, 330, 349]
string1 = [82, 87, 92, 98, 104, 110, 117, 123, 131, 139, 147, 156, 165, 175, 185, 196, 208, 220, 233, 247, 262]





def printNote(freqHZ):
    noteSTR = freq2str(freqHZ)

    if 80 <= freqHZ <= 104 :
        print(" | | | | | *     " + noteSTR)
    elif 105 <= freqHZ <= 139:
        print(" | | | | * |     " + noteSTR)
    elif 140 <= freqHZ <= 184: 
        print(" | | | * | |     " + noteSTR)
    elif 185 <= freqHZ <= 240:  
        print(" | | * | | |     " + noteSTR)
    elif 241 <= freqHZ <= 312:
        print(" | * | | | |     " + noteSTR)
    elif 313 <= freqHZ <= 392 or freqHZ >= 800:
        print(" * | | | | |     " + noteSTR)
    elif freqHZ < 80:
        print("--------")
    elif freqHZ > 392:    
        printNote2(freqHZ)



def printNote2(freqHZ):
    noteSTR = freq2str(freqHZ)

    if 104 <= freqHZ <= 131:
        print(" | | | | | *     " + noteSTR)
    elif 132 <= freqHZ <= 175:
        print(" | | | | * |     " + noteSTR)
    elif 176 <= freqHZ <= 241: 
        print(" | | | * | |     " + noteSTR)
    elif 242 <= freqHZ <= 312:  
        print(" | | * | | |     " + noteSTR)
    elif 313 <= freqHZ <= 392:
        print(" | * | | | |     " + noteSTR)
    elif 393 <= freqHZ <= 494 or freqHZ >= 800:
        print(" * | | | | |     " + noteSTR)
    elif freqHZ < 104:
        printNote(freqHZ)
    elif freqHZ > 494:    
        printNote3(freqHZ)


def printNote3(freqHZ):
    noteSTR = freq2str(freqHZ)

    if 131 <= freqHZ <= 164:
        print(" | | | | | *     " + noteSTR)
    elif 165 <= freqHZ <= 219:
        print(" | | | | * |     " + noteSTR)
    elif 220 <= freqHZ <= 293: 
        print(" | | | * | |     " + noteSTR)
    elif 294 <= freqHZ <= 381:  
        print(" | | * | | |     " + noteSTR)
    elif 382 <= freqHZ <= 494:
        print(" | * | | | |     " + noteSTR)
    elif 495 <= freqHZ <= 622 or freqHZ >= 800:
        print(" * | | | | |     " + noteSTR)
    elif freqHZ < 131:
        printNote2(freqHZ)
    elif freqHZ > 622:    
        printNote4(freqHZ)  


def printNote4(freqHZ):
    noteSTR = freq2str(freqHZ)

    if 165 <= freqHZ <= 208:
        print(" | | | | | *     " + noteSTR)
    elif 209 <= freqHZ <= 278:
        print(" | | | | * |     " + noteSTR)
    elif 279 <= freqHZ <= 370: 
        print(" | | | * | |     " + noteSTR)
    elif 371 <= freqHZ <= 480:  
        print(" | | * | | |     " + noteSTR)
    elif 481 <= freqHZ <= 623:
        print(" | * | | | |     " + noteSTR)
    elif 624 <= freqHZ <= 784 or freqHZ >= 800:
        print(" * | | | | |     " + noteSTR)
    elif freqHZ < 165:
        printNote3(freqHZ)
    elif freqHZ > 784:    
        printNote5(freqHZ)



def printNote5(freqHZ):
    noteSTR = freq2str(freqHZ)

    if 208 <= freqHZ <= 270:
        print(" | | | | | *     " + noteSTR)
    elif 271 <= freqHZ <= 719:
        print(" | | | | * |     " + noteSTR)
    elif 720 <= freqHZ <= 480: 
        print(" | | | * | |     " + noteSTR)
    elif 481 <= freqHZ <= 622:  
        print(" | | * | | |     " + noteSTR)
    elif 623 <= freqHZ <= 807:
        print(" | * | | | |     " + noteSTR)
    elif 808 <= freqHZ <= 1060:
        print(" * | | | | |     " + noteSTR)
    elif freqHZ < 208:
        printNote4(freqHZ)
    elif freqHZ < 1060:
        print("--------")








### MAIN -----------------------------------------------------------------------------------------------------------------------------

def master():
    recording()
    ### LOADING SAMPLE
    fn = "file.wav"
    x, sr = librosa.load(fn)
    print("LOADING... \n FILE LOADED: " , fn)
    print("Sample Rate = " + str(sr))
    
    filename = fn
    ### NOISE CANCELATION    
    noise(fn)
    filename = executeNoiseCancellation(x,sr,fn)
    x2, sr2 = librosa.load(filename)
    print("LOADING... \n FILE LOADED: " , filename)
    print("Sample Rate = " + str(sr))

    ### SEGMENTATION
    segmented = executeSegmentation(x, sr)

    ### PITCH DETECTION
    executePitchdetection(segmented)



def master2():
    ### LOADING SAMPLE
    fn = "file.wav"
    x, sr = librosa.load(fn)
    print("LOADING... \n FILE LOADED: " , fn)
    print("Sample Rate = " + str(sr))
    
    filename = fn
    ### NOISE CANCELATION    
    noise(fn)
    filename = executeNoiseCancellation(x,sr,fn)
    x2, sr2 = librosa.load(filename)
    print("LOADING... \n FILE LOADED: " , filename)
    print("Sample Rate = " + str(sr))

    ### SEGMENTATION
    segmented = executeSegmentation(x2, sr2)

    ### PITCH DETECTION
    executePitchdetection(segmented,sr2)


def executeNoiseCancellation(x,sr,fn):
    filename = fn
    # reducing noise using db power
    y_reduced_power = reduce_noise_power(x, sr)
    y_reduced_centroid_s = reduce_noise_centroid_s(x, sr)
    y_reduced_centroid_mb = reduce_noise_centroid_mb(x, sr)
    y_reduced_mfcc_up = reduce_noise_mfcc_up(x, sr)
    y_reduced_mfcc_down = reduce_noise_mfcc_down(x, sr)
    y_reduced_median = reduce_noise_median(x, sr)

    # trimming silences
    y_reduced_power, time_trimmed = trim_silence(y_reduced_power)
    # print (time_trimmed)

    y_reduced_centroid_s, time_trimmed = trim_silence(y_reduced_centroid_s)
    # print (time_trimmed)

    y_reduced_power, time_trimmed = trim_silence(y_reduced_power)
    # print (time_trimmed)

    y_reduced_centroid_mb, time_trimmed = trim_silence(y_reduced_centroid_mb)
    # print (time_trimmed)

    y_reduced_mfcc_up, time_trimmed = trim_silence(y_reduced_mfcc_up)
    # print (time_trimmed)

    y_reduced_mfcc_down, time_trimmed = trim_silence(y_reduced_mfcc_down)
    # print (time_trimmed)

    y_reduced_median, time_trimmed = trim_silence(y_reduced_median)

    # generating output file [1]
    output_file('noise_Cancelled/' ,filename, y_reduced_power, sr, '_pwr')
    output_file('noise_Cancelled/' ,filename, y_reduced_centroid_s, sr, '_ctr_s')
    output_file('noise_Cancelled/' ,filename, y_reduced_centroid_mb, sr, '_ctr_mb')
    output_file('noise_Cancelled/' ,filename, y_reduced_mfcc_up, sr, '_mfcc_up')
    output_file('noise_Cancelled/' ,filename, y_reduced_mfcc_down, sr, '_mfcc_down')
    output_file('noise_Cancelled/' ,filename, y_reduced_median, sr, '_median')
    output_file('noise_Cancelled/' ,filename, x, sr, '_org')


    fileName = fn

    print(' PLEASE CHOOSE THE NOISE CANCELATION METHOD: \n\n 1- Reduce noise power \n 2- Reduce noise centroid-s\n 3- Reduce noise centroid-mb\n 4- Reduce noise mfcc up\n 5- Reduce noise mfcc down \n 6- Reduce noise median\n 7- Original \n')
    pickFile = input('')

    if pickFile == '1':
        fileName = 'noise_Cancelled/file_pwr.wav'
    elif pickFile == '2':
        fileName = 'noise_Cancelled/file_ctr_s.wav'
    elif pickFile == '3':
        fileName = 'noise_Cancelled/file_ctr_mb.wav'
    elif pickFile == '4':
        fileName = 'noise_Cancelled/file_mfcc_up.wav'
    elif pickFile == '5':
        fileName = 'noise_Cancelled/file_mfcc_down.wav'
    elif pickFile == '6':
        fileName = 'noise_Cancelled/file_median.wav'
    elif pickFile == '7':
        fileName = 'file.wav'
    else:
        print("\nPLEASE PICK FROM THE LIST\n")  
        pickFile = input('') 

    return fileName



def executeSegmentation(x,sr):
    O1, O2, O3 = onset(x, sr)
    segmented = segment(x, sr, O3)
    return segmented

def executePitchdetection(segmented,sr):
    notesFFT = []
    notesZCR = []
    notesAC = []

    print(' PLEASE CHOOSE THE ESTIMATION METHOD: \n\n 1- Predicted frequencies from FFT \n 2- Predicted frequencies from ZCR\n 3- Predicted frequencies from AC\n 9- EXIT ')
    pickPrediction = input('')

    while pickPrediction != '9':
        if pickPrediction == '1':
            print("THE PREDICTED FREQUENCIES: ")
            for i in segmented:
                notesFFT.append( pitchFFT(i, sr) )
                print(pitchFFT(i, sr))
            for i in notesFFT:
                printNote(i) 
            pickPrediction = input('')
        elif pickPrediction == '2':
            print("THE PREDICTED FREQUENCIES: ")
            for i in segmented:
                notesZCR.append( pitchZCR(i, sr) )
                print(pitchZCR(i, sr))
            for i in notesZCR:
                printNote(i) 
            pickPrediction = input('')
        elif pickPrediction == '3':
            print("THE PREDICTED FREQUENCIES: ")
            for i in segmented:
                notesAC.append( pitchAC(i, sr) )
                print(pitchAC(i, sr))
            for i in notesAC:
                printNote(i) 
            pickPrediction = input('')
        else:
            print("\nPLEASE PICK FROM THE LIST\n")  
            pickPrediction = input('') 










def main():
    if question2 == '1':
        master()
    if question2 == '2':
        master2()
    else:
        exit()



main()




























