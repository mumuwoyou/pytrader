# coding: utf-8
import numpy as np
import tensorflow as tf
from .DNCore import DNCoreDeepLSTM

class Classifier_DNCoreDeepLSTM(object):

    def __init__(self,
                 inputs,
                 targets,
                 gather_list=None,
                 batch_size=1,
                 hidden_size=20,
                 memory_size=20,
                 num_reads=3,
                 num_writes=1,
                 learning_rate = 1e-3,
                 optimizer_epsilon = 1e-8,
                 l2_coefficient = 1e-3,
                 max_gard_norm = 50,
                 reset_graph = True):

        if reset_graph:
            tf.reset_default_graph()
        # 控制参数
        self._tmp_inputs = inputs
        self._tmp_targets = targets
        self._in_length = None
        self._in_width = inputs.shape[2]
        self._out_length = None
        self._out_width = targets.shape[2]
        self._batch_size = batch_size

        # 声明会话
        self._sess = tf.InteractiveSession()

        self._inputs = tf.placeholder(
            dtype=tf.float32,
            shape=[self._in_length, self._batch_size, self._in_width],
            name='inputs')
        self._targets = tf.placeholder(
            dtype=tf.float32,
            shape=[self._out_length, self._batch_size, self._out_width],
            name='targets')

        self._RNNCoreCell = DNCoreDeepLSTM(
            dnc_output_size=self._out_width,
            hidden_size=hidden_size,
            memory_size=memory_size,
            word_size=self._in_width,
            num_read_heads=num_reads,
            num_write_heads=num_writes)

        self._initial_state = \
        self._RNNCoreCell.initial_state(batch_size)

        output_sequences, _ = \
        tf.nn.dynamic_rnn(cell= self._RNNCoreCell,
                          inputs=self._inputs,
                          initial_state=self._initial_state,
                          time_major=True)

        self._original_output_sequences = output_sequences
        if gather_list is not None:
            output_sequences = tf.gather(output_sequences, gather_list)

        # L2 正则化测试 2017-09-03
        self._trainable_variables = tf.trainable_variables()
        _l2_regularizer = tf.add_n([tf.nn.l2_loss(v) for v in self._trainable_variables])
        self._l2_regularizer = _l2_regularizer * l2_coefficient / len(self._trainable_variables)

        rnn_cost = tf.nn.softmax_cross_entropy_with_logits(
            labels=self._targets, logits=output_sequences)
        self._rnn_cost = tf.reduce_mean(rnn_cost)
        self._cost = self._rnn_cost + self._l2_regularizer


        train_pred = tf.nn.softmax(output_sequences, dim=2)
        correct_pred = tf.equal(tf.argmax(train_pred,2), tf.argmax(self._targets,2))
        self._accuracy = tf.reduce_mean(tf.cast(correct_pred, tf.float32))

        # Set up optimizer with global norm clipping.
        trainable_variables = tf.trainable_variables()
        grads, _ = tf.clip_by_global_norm(
            tf.gradients(self._cost, trainable_variables), max_gard_norm)
        global_step = tf.get_variable(
            name="global_step",
            shape=[],
            dtype=tf.int64,
            initializer=tf.zeros_initializer(),
            trainable=False,
            collections=[tf.GraphKeys.GLOBAL_VARIABLES, tf.GraphKeys.GLOBAL_STEP])

        optimizer = tf.contrib.opt.NadamOptimizer(
            learning_rate=learning_rate, epsilon=optimizer_epsilon)
        self._train_step = optimizer.apply_gradients(
            zip(grads, trainable_variables), global_step=global_step)

        self._sess.run(tf.global_variables_initializer())
        self._variables_saver = tf.train.Saver()


    def fit(self,
            training_iters =1e2,
            display_step = 5,
            save_path = None,
            restore_path = None):

        if restore_path is not None:
            self._variables_saver.restore(self._sess, restore_path)

        for scope in range(np.int(training_iters)):
            self._sess.run([self._train_step],
                           feed_dict = {self._inputs:self._tmp_inputs, self._targets:self._tmp_targets})

            if scope % display_step == 0:
                loss, acc, l2_loss, rnn_loss = self._sess.run(
                    [self._cost, self._accuracy, self._l2_regularizer, self._rnn_cost],
                    feed_dict = {self._inputs:self._tmp_inputs, self._targets:self._tmp_targets})
                print (scope, '  loss--', loss, '  acc--', acc, '  l2_loss', l2_loss, '  rnn_cost', rnn_loss)

        print ("Optimization Finished!")
        loss, acc, l2_loss, rnn_loss = self._sess.run(
            [self._cost, self._accuracy, self._l2_regularizer, self._rnn_cost],
            feed_dict = {self._inputs:self._tmp_inputs, self._targets:self._tmp_targets})
        print ('Model assessment  loss--', loss, '  acc--', acc, '  l2_loss', l2_loss, '  rnn_cost', rnn_loss)
        # 保存模型可训练变量
        if save_path is not None:
            self._variables_saver.save(self._sess, save_path)

    def close(self):
        self._sess.close()
        print ('结束进程，清理tensorflow内存/显存占用')

    def pred(self, inputs, gather_list=None, restore_path=None):
        output_sequences = self._original_output_sequences
        if gather_list is not None:
            output_sequences = tf.gather(output_sequences, gather_list)
        probability = tf.nn.softmax(output_sequences)
        classification = tf.argmax(probability, axis=-1)
        return self._sess.run([probability, classification],feed_dict = {self._inputs:inputs})

    def restore_trainable_variables(self, restore_path):
        self._variables_saver.restore(self._sess, restore_path)

    def score(self, inputs, targets, gather_list=None):
        acc = self._sess.run(
            self._accuracy,
            feed_dict = {self._inputs:self._tmp_inputs,
                         self._targets:self._tmp_targets})
        return acc