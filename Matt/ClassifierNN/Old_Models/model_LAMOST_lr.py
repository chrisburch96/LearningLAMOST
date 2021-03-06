from plot_model import plot_results

import glob
from astropy.io import fits
import numpy as np
import tensorflow as tf


import time    

files = glob.glob('/data2/mrs493/DR1_3/*.fits')

classes = ['STAR', 'GALAXY', 'QSO', 'Unknown']

cls = len(classes)

flux = []
CLASS = []

wavelengths = 3800

train_frac = 0.7
batch_frac= 0.025

record = 100
train_steps = 10000

for idx, file in enumerate(files):
    with fits.open(file) as hdulist:
        flx = hdulist[0].data[0]
        flx = flx[:wavelengths]
        CLS = hdulist[0].header['CLASS']
    flux.append(flx)
    CLASS.append([0]*cls)
    CLASS[-1][classes.index(CLS)] = 1

flux = np.array(flux)
CLASS = np.array(CLASS)

for i in range(cls):
    print(classes[i], ': ', np.sum([x[i] for x in CLASS]))

split = np.random.random(len(files))>=train_frac

x_train = np.array(flux[split])
x_test = np.array(flux[[not s for s in split]])

y_train = np.array(CLASS[split])
y_test = np.array(CLASS[[not s for s in split]])

x = tf.placeholder(tf.float32, shape = [None, wavelengths])
y_ = tf.placeholder(tf.float32, shape = [None, cls])

W = tf.Variable(tf.zeros([wavelengths,cls]))
b = tf.Variable(tf.zeros([cls]))

y = tf.nn.softmax(tf.matmul(x, W) + b)
cross_entropy = tf.reduce_mean(-tf.reduce_sum(y_ * tf.log(y), reduction_indices=[1]))

train_step = tf.train.GradientDescentOptimizer(0.5).minimize(cross_entropy)

correct_prediction = tf.equal(tf.argmax(y,1), tf.argmax(y_,1))
accuracy = tf.reduce_mean(tf.cast(correct_prediction, tf.float32))

accuracies = []

confusion = tf.confusion_matrix(tf.argmax(y,1), tf.argmax(y_,1))

with tf.Session() as sess:
    t = time.time()
    sess.run(tf.global_variables_initializer())
    for i in range(train_steps):
        batch = np.random.random(len(x_train))<=batch_frac
        batch_x = x_train[batch]
        batch_y = y_train[batch]
        if i%record == 0:
            train_accuracy = sess.run(accuracy, feed_dict={x: x_test, y_: y_test})
            print('step {} training accuracy {}'.format(i, train_accuracy))
            accuracies.append([i, train_accuracy])
        train_step.run(feed_dict={x: batch_x, y_: batch_y})
    conf, acc = sess.run([confusion, accuracy], feed_dict={x: x_test, y_: y_test})
    print('test accuracy {}'.format(acc))
    print(conf)
    accuracies.append([i+1, acc])
    np.savetxt('Files/LAMOST_lr/classes.csv', classes, fmt = '%s', delimiter = ',')
    np.savetxt('Files/LAMOST_lr/confusion.csv', conf, fmt = '%i', delimiter = ',')
    np.savetxt('Files/LAMOST_lr/accuracies.csv', accuracies, delimiter = ',')
    print('training time: ', time.time() - t, 's')

plot_results('LAMOST_lr')
