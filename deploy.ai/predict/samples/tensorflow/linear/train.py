from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import argparse
import tensorflow as tf
import numpy as np
import os

parser = argparse.ArgumentParser()
parser.add_argument('--learning_rate', type=float, help='Learning Rate')
parser.add_argument('--train_dir', type=str, help='Train Dir')
parser.add_argument('--test_dir', type=str, help='Test Dir')
FLAGS, unparsed = parser.parse_known_args()
print(FLAGS)
print(unparsed)

#tf.app.flags.DEFINE_integer('learning_rate', 0.025, 'Learning Rate')

tf.reset_default_graph()

config = tf.ConfigProto(
  allow_soft_placement = True,  
  log_device_placement=True
)
print(config)

sess = tf.Session(config=config)
print(sess)

num_samples = 10000

x_train = np.random.rand(num_samples).astype(np.float32)
print(x_train)

noise = np.random.normal(scale=0.01, size=len(x_train))

y_train = x_train * 0.1 + 0.3 + noise
print(y_train)


x_test = np.random.rand(len(x_train)).astype(np.float32)
print(x_test)

noise = np.random.normal(scale=.01, size=len(x_train))

y_test = x_test * 0.1 + 0.3 + noise
print(y_test)


with tf.device("/cpu:0"):
    W = tf.get_variable(shape=[], name='weights')
    print(W)

    b = tf.get_variable(shape=[], name='bias')
    print(b)

    x_observed = tf.placeholder(shape=[None], 
                                dtype=tf.float32, 
                                name='x_observed')
    print(x_observed)

    y_pred = W * x_observed + b
    print(y_pred)

learning_rate = FLAGS.learning_rate

global loss_op

with tf.device("/cpu:0"):
    y_observed = tf.placeholder(shape=[None], dtype=tf.float32, name='y_observed')
    print(y_observed)

    loss_op = tf.reduce_mean(tf.square(y_pred - y_observed))
    optimizer_op = tf.train.GradientDescentOptimizer(learning_rate)
    
    train_op = optimizer_op.minimize(loss_op)  

    print("Loss Scalar: ", loss_op)
    print("Optimizer Op: ", optimizer_op)
    print("Train Op: ", train_op)

with tf.device("/cpu:0"):
    init_op = tf.global_variables_initializer()
    print(init_op)

sess.run(init_op)
print("Initial random W: %f" % sess.run(W))
print("Initial random b: %f" % sess.run(b))

def test(x, y):
    return sess.run(loss_op, feed_dict={x_observed: x, y_observed: y})

test(x_train, y_train)

loss_summary_scalar_op = tf.summary.scalar('loss', loss_op)
loss_summary_merge_all_op = tf.summary.merge_all()

from datetime import datetime 
version = int(datetime.now().strftime("%s"))

train_summary_writer = tf.summary.FileWriter(FLAGS.train_dir, 
                                            graph=tf.get_default_graph())

test_summary_writer = tf.summary.FileWriter(FLAGS.test_dir,
                                            graph=tf.get_default_graph())

with tf.device("/cpu:0"):
    run_metadata = tf.RunMetadata()
    max_steps = 401
    for step in range(max_steps):
        if (step < max_steps - 1):
            test_summary_log, _ = sess.run([loss_summary_merge_all_op, loss_op], feed_dict={x_observed: x_test, y_observed: y_test})
            train_summary_log, _ = sess.run([loss_summary_merge_all_op, train_op], feed_dict={x_observed: x_train, y_observed: y_train})
        else:  
            test_summary_log, _ = sess.run([loss_summary_merge_all_op, loss_op], feed_dict={x_observed: x_test, y_observed: y_test})
            train_summary_log, _ = sess.run([loss_summary_merge_all_op, train_op], feed_dict={x_observed: x_train, y_observed: y_train}, 
                                            options=tf.RunOptions(trace_level=tf.RunOptions.FULL_TRACE), 
                                            run_metadata=run_metadata)
        if step % 10 == 0:
            print(step, sess.run([W, b]))
            train_summary_writer.add_summary(train_summary_log, step)
            train_summary_writer.flush()
            test_summary_writer.add_summary(test_summary_log, step)
            test_summary_writer.flush()

from tensorflow.python.saved_model import utils
from tensorflow.python.saved_model import signature_constants
from tensorflow.python.saved_model import signature_def_utils

graph = tf.get_default_graph()

x_observed = graph.get_tensor_by_name('x_observed:0')
y_pred = graph.get_tensor_by_name('add:0')

tensor_info_x_observed = utils.build_tensor_info(x_observed)
print(tensor_info_x_observed)

tensor_info_y_pred = utils.build_tensor_info(y_pred)
print(tensor_info_y_pred)

prediction_signature = signature_def_utils.build_signature_def(inputs = 
                {'x_observed': tensor_info_x_observed}, 
                outputs = {'y_pred': tensor_info_y_pred}, 
                method_name = signature_constants.PREDICT_METHOD_NAME)

from tensorflow.python.saved_model import builder as saved_model_builder
from tensorflow.python.saved_model import tag_constants

fully_optimized_saved_model_path = './export-%s' % version
print(fully_optimized_saved_model_path)

builder = saved_model_builder.SavedModelBuilder(fully_optimized_saved_model_path)
builder.add_meta_graph_and_variables(sess, 
                                     [tag_constants.SERVING],
                                     signature_def_map={'predict':prediction_signature,                                     
signature_constants.DEFAULT_SERVING_SIGNATURE_DEF_KEY:prediction_signature}, 
                                     clear_devices=True,
)

builder.save(as_text=False)
print('')
print('Model training completed and saved here:  ./export-%s' % version)
print('')
